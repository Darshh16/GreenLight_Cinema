"""
Greenlight Cinema — Data Setup Script v2
==========================================
1. Clean & merge all 9 datasets into master table
2. Load into DuckDB with 11 analytics tables
3. Generate scripts and ingest into ChromaDB

Usage:
    python scripts/setup_data.py
    python scripts/setup_data.py --skip-rag
"""

import sys
import logging
import argparse
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from greenlight.data.clean import run_cleaning_pipeline
from greenlight.data.load import run_load_pipeline


def main():
    parser = argparse.ArgumentParser(description="Greenlight Cinema -- Data Setup v2")
    parser.add_argument("--skip-rag", action="store_true", help="Skip ChromaDB ingestion")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("greenlight")

    total_start = time.time()

    # Step 1: Clean & merge all datasets
    log.info("=" * 60)
    log.info("STEP 1: Data Cleaning & Merging (all 9 datasets)")
    log.info("=" * 60)
    start = time.time()
    cleaned_data = run_cleaning_pipeline()
    log.info(f"Cleaning completed in {time.time() - start:.1f}s")

    # Step 2: Load into DuckDB
    log.info("")
    log.info("=" * 60)
    log.info("STEP 2: DuckDB Loading (11 analytics tables)")
    log.info("=" * 60)
    start = time.time()
    run_load_pipeline(cleaned_data)
    log.info(f"DuckDB loading completed in {time.time() - start:.1f}s")

    # Step 3: ChromaDB RAG
    if not args.skip_rag:
        log.info("")
        log.info("=" * 60)
        log.info("STEP 3: ChromaDB RAG Ingestion (scripts from master dataset)")
        log.info("=" * 60)
        start = time.time()
        try:
            from greenlight.rag.ingest import ingest_to_chromadb
            doc_count = ingest_to_chromadb(n_scripts=60)
            log.info(f"ChromaDB ingestion completed in {time.time() - start:.1f}s "
                     f"({doc_count} documents)")
        except Exception as e:
            log.error(f"ChromaDB ingestion failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        log.info("\nSkipping ChromaDB ingestion (--skip-rag)")

    total_elapsed = time.time() - total_start
    log.info("")
    log.info("=" * 60)
    log.info(f"SETUP COMPLETE -- Total time: {total_elapsed:.1f}s")
    log.info("=" * 60)
    log.info("")
    log.info("Next steps:")
    log.info("  1. Start FastAPI:   venv\\Scripts\\python.exe -m uvicorn greenlight.api.main:app --port 8000")
    log.info("  2. Start Streamlit: venv\\Scripts\\python.exe -m streamlit run frontend\\app.py")


if __name__ == "__main__":
    main()
