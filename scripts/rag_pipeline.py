"""
Greenlight Cinema — RAG Pipeline (IMSDb Scraper)
==================================================
Handles downloading screenplays from IMSDb and triggering ingestion.

Run:
    python scripts/rag_pipeline.py --download   # Download IMSDb scripts
    python scripts/rag_pipeline.py --ingest     # Run hybrid ChromaDB ingestion
    python scripts/rag_pipeline.py --all        # Do everything

Requirements:
    pip install requests beautifulsoup4 chromadb sentence-transformers
"""

import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
import logging
import argparse
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from greenlight.config import SCRIPTS_DIR
from greenlight.rag.scripts import SCRIPT_SOURCES
from greenlight.rag.ingest import ingest_to_chromadb

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("rag")


def download_imsdb_scripts():
    """Scrape IMSDb for scripts, extract <pre> tags, save as .txt"""
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    log.info(f"══ Downloading {len(SCRIPT_SOURCES)} scripts from IMSDb to {SCRIPTS_DIR} ══")
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    success, skipped, failed = 0, 0, []

    for filename, url, genre, year in tqdm(SCRIPT_SOURCES, desc="Downloading from IMSDb"):
        dest = SCRIPTS_DIR / filename
        
        # Skip if we already have a decent sized file
        if dest.exists() and dest.stat().st_size > 5000:
            skipped += 1
            continue
            
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                pre_tag = soup.find('pre')
                
                if pre_tag and len(pre_tag.text) > 5000:
                    # Some scripts are inside a <td class="scrtext"> if <pre> is missing/small
                    script_text = pre_tag.text
                    dest.write_text(script_text, encoding="utf-8", errors="replace")
                    success += 1
                else:
                    # Fallback check for class scrtext
                    td = soup.find('td', class_="scrtext")
                    if td and len(td.text) > 5000:
                        dest.write_text(td.text, encoding="utf-8", errors="replace")
                        success += 1
                    else:
                        failed.append((filename, "Could not find <pre> or <td class='scrtext'> with sufficient text"))
            else:
                failed.append((filename, f"HTTP {resp.status_code}"))
                
            time.sleep(1.0)  # Be nice to IMSDb servers
            
        except Exception as e:
            failed.append((filename, str(e)))

    log.info(f"  ✓ Downloaded: {success}  Skipped: {skipped}  Failed: {len(failed)}")
    if failed:
        log.warning("  Failed to download the following scripts:")
        for fname, reason in failed[:10]:
            log.warning(f"    {fname}: {reason}")
        if len(failed) > 10:
            log.warning(f"    ... and {len(failed)-10} more.")


def main():
    parser = argparse.ArgumentParser(description="Greenlight Cinema RAG Pipeline")
    parser.add_argument("--download", action="store_true", help="Scrape IMSDb scripts")
    parser.add_argument("--ingest",   action="store_true", help="Run hybrid ChromaDB ingestion")
    parser.add_argument("--all",      action="store_true", help="Download + ingest")
    args = parser.parse_args()

    if args.all:
        download_imsdb_scripts()
        ingest_to_chromadb(100)
    else:
        if args.download: 
            download_imsdb_scripts()
        if args.ingest:   
            ingest_to_chromadb(100)
        if not any(vars(args).values()):
            parser.print_help()


if __name__ == "__main__":
    main()
