"""
Greenlight Cinema — Health Check Script
=========================================
Quick verification that all services are operational.

Usage:
    python scripts/run_health_check.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s",
                    datefmt="%H:%M:%S")

log = logging.getLogger("greenlight.health")


def main():
    print("\n" + "═" * 60)
    print("  GREENLIGHT CINEMA — System Health Check")
    print("═" * 60)

    # 1. DuckDB
    print("\n  ── DuckDB ──")
    try:
        from greenlight.analytics.engine import AnalyticsEngine
        engine = AnalyticsEngine()
        if engine.is_healthy():
            genres = engine.get_genre_roi(limit=5)
            print(f"  ✅ Connected — {len(genres)} genres available")
            for g in genres[:3]:
                print(f"     {g.genre}: median ROI {g.median_roi:.2f}x ({g.movie_count} films)")
        else:
            print("  ❌ Not available")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # 2. ChromaDB
    print("\n  ── ChromaDB ──")
    try:
        from greenlight.rag.retriever import RAGRetriever
        retriever = RAGRetriever()
        if retriever.is_healthy():
            count = retriever.get_collection_count()
            print(f"  ✅ Connected — {count:,} documents")

            # Quick retrieval test
            results = retriever.retrieve("Action", "A hero saves the world", n=2)
            if results:
                print(f"  ✅ Retrieval works — got {len(results)} results")
                for r in results[:2]:
                    print(f"     [{r.title}] ({r.genre}) dist={r.distance:.3f}")
        else:
            print("  ❌ Not available")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # 3. Ollama
    print("\n  ── Ollama ──")
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            print(f"  ✅ Connected — Models: {', '.join(models)}")
        else:
            print(f"  ❌ HTTP {resp.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # 4. Constraints
    print("\n  ── Constraint Engine ──")
    try:
        from greenlight.analytics.constraints import ConstraintEngine
        ce = ConstraintEngine()
        constraints = ce.generate("Action", 100_000_000)
        print(f"  ✅ Generated constraints for Action/$100M")
        print(f"     Target ROI: {constraints.target_roi:.2f}x")
        print(f"     Seasonal fit: {constraints.seasonal_fit}")
        print(f"     Top genres: {', '.join(constraints.top_genres[:3])}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    print("\n" + "═" * 60 + "\n")


if __name__ == "__main__":
    main()
