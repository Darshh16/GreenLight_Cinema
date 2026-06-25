import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format='%(message)s')

from greenlight.rag.ingest import ingest_to_chromadb

print("Starting RAG ingestion with LLM screenplay generation...")
ingest_to_chromadb(n_scripts=50)
print("Done.")
