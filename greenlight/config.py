"""
Greenlight Cinema — Centralized Configuration
"""

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
DB_PATH      = PROJECT_ROOT / "greenlight.duckdb"
CHROMA_DIR   = PROJECT_ROOT / "chromadb_store"
SCRIPTS_DIR  = PROJECT_ROOT / "data" / "scripts"   # synthetic scripts for RAG

# ── DuckDB ───────────────────────────────────────────────────────────────────
DUCKDB_THREADS = int(os.getenv("DUCKDB_THREADS", "4"))

# ── Ollama ───────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "qwen3:4b")

# ── Embedding ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ── ChromaDB ─────────────────────────────────────────────────────────────────
CHROMA_COLLECTION = "scripts_collection"

# ── Agent Workflow ───────────────────────────────────────────────────────────
MAX_ITERATIONS   = int(os.getenv("MAX_ITERATIONS", "3"))
TARGET_SCORE     = float(os.getenv("TARGET_SCORE", "0.7"))
SYNOPSIS_WORDS   = int(os.getenv("SYNOPSIS_WORDS", "400"))

# ── Analytics ────────────────────────────────────────────────────────────────
MIN_FILMS_FOR_RANKING = int(os.getenv("MIN_FILMS_FOR_RANKING", "5"))
ROI_OUTLIER_CAP       = float(os.getenv("ROI_OUTLIER_CAP", "100.0"))

# ── API ──────────────────────────────────────────────────────────────────────
API_HOST       = os.getenv("API_HOST", "0.0.0.0")
API_PORT       = int(os.getenv("API_PORT", "8000"))
RATE_LIMIT     = os.getenv("RATE_LIMIT", "50/minute")

# ── Budget Tiers ─────────────────────────────────────────────────────────────
BUDGET_TIERS = {
    "Low":         (0,          15_000_000),
    "Mid":         (15_000_000, 50_000_000),
    "High":        (50_000_000, 100_000_000),
    "Blockbuster": (100_000_000, float("inf")),
}
