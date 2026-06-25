import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import chromadb
from greenlight.config import CHROMA_DIR, CHROMA_COLLECTION

def get_chroma_count():
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_collection(name=CHROMA_COLLECTION)
        count = collection.count()
        print(f"ChromaDB '{CHROMA_COLLECTION}' count: {count}")
    except Exception as e:
        print(f"Error accessing ChromaDB: {e}")

if __name__ == "__main__":
    get_chroma_count()
