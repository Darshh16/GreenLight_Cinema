"""
Greenlight Cinema — ScriptSlug Downloader
==========================================
Downloads 50 random screenplay PDFs from scriptslug.com

How it works:
  1. Fetches the RSS feed  → gets latest ~100 script slugs
  2. Fetches genre pages   → scrapes more slugs across all genres
  3. Visits each script page → finds the PDF URL
  4. Downloads the PDF      → saves to data/scripts/

PDF URL pattern discovered:
  https://assets.scriptslug.com/live/pdf/scripts/{slug}.pdf

Run:
    python scriptslug_downloader.py           # download 50 random scripts
    python scriptslug_downloader.py --count 30  # download 30 instead
    python scriptslug_downloader.py --resume    # skip already downloaded

Requirements:
    pip install requests beautifulsoup4 tqdm
"""

import re
import time
import random
import logging
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scriptslug")

# ── Paths ───────────────────────────────────────────────────────────────────────
SCRIPTS_DIR = Path("data/scripts")
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Config ──────────────────────────────────────────────────────────────────────
BASE_URL        = "https://www.scriptslug.com"
ASSETS_URL      = "https://assets.scriptslug.com/live/pdf/scripts"
RSS_URL         = "https://www.scriptslug.com/rss/scripts"
DELAY           = 2.0    # seconds between requests
RETRY_DELAY     = 8.0
MAX_RETRIES     = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.scriptslug.com/",
}

# All genres on scriptslug — we'll scrape each to collect slugs
GENRES = [
    "action", "adventure", "animation", "biography", "comedy",
    "crime", "drama", "family", "fantasy", "film-noir",
    "history", "horror", "mystery", "romance", "science-fiction",
    "thriller", "war", "western", "sport", "musical",
]


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — COLLECT SCRIPT SLUGS
# ══════════════════════════════════════════════════════════════════════════════

def slugs_from_rss() -> list[tuple[str, str]]:
    """
    Parse the RSS feed → list of (slug, title).
    Returns up to ~100 recent scripts.
    """
    log.info("Fetching RSS feed …")
    try:
        resp = requests.get(RSS_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        results = []
        for item in root.findall(".//item"):
            link  = item.findtext("link", "")
            title = item.findtext("title", "")
            if "/script/" in link:
                slug = link.rstrip("/").split("/script/")[-1]
                results.append((slug, title))
        log.info(f"  RSS → {len(results)} slugs")
        return results
    except Exception as e:
        log.warning(f"  RSS fetch failed: {e}")
        return []


def slugs_from_genre_page(genre: str) -> list[tuple[str, str]]:
    """
    Scrape a genre listing page → list of (slug, title).
    ScriptSlug renders script cards as <a href="/script/..."> links.
    """
    url = f"{BASE_URL}/scripts/genre/{genre}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/script/") and href.count("/") == 2:
                slug  = href.split("/script/")[-1].strip("/")
                title = a.get_text(strip=True) or slug
                if slug:
                    results.append((slug, title))
        # deduplicate
        seen = set()
        deduped = []
        for s, t in results:
            if s not in seen:
                seen.add(s)
                deduped.append((s, t))
        return deduped
    except Exception as e:
        log.debug(f"  Genre {genre} failed: {e}")
        return []


def collect_all_slugs(target: int = 200) -> list[tuple[str, str]]:
    """
    Gather enough slugs to randomly pick `target` from.
    Strategy: RSS first, then genre pages until we have enough.
    """
    log.info("══ Collecting script slugs ══")
    all_slugs = []
    seen = set()

    def add(items):
        for slug, title in items:
            if slug not in seen:
                seen.add(slug)
                all_slugs.append((slug, title))

    # RSS is fast — do it first
    add(slugs_from_rss())
    time.sleep(DELAY)

    # Genre pages — shuffle so we get variety
    genres = GENRES.copy()
    random.shuffle(genres)

    for genre in genres:
        if len(all_slugs) >= target:
            break
        log.info(f"  Scraping genre: {genre} …")
        add(slugs_from_genre_page(genre))
        time.sleep(DELAY)

    log.info(f"  Total unique slugs collected: {len(all_slugs)}")
    return all_slugs


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — FIND PDF URL FROM SCRIPT PAGE
# ══════════════════════════════════════════════════════════════════════════════

def get_pdf_url(slug: str) -> str | None:
    """
    Visit the script page and extract the direct PDF URL.

    Two strategies:
      1. Construct URL directly from slug pattern (fastest, works ~90% of time)
         → https://assets.scriptslug.com/live/pdf/scripts/{slug}.pdf
      2. Scrape the page and find the PDF link (fallback)
    """
    # Strategy 1: direct construction (discovered pattern)
    direct_url = f"{ASSETS_URL}/{slug}.pdf"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # HEAD request — check if PDF exists without downloading it
            resp = requests.head(
                direct_url, headers=HEADERS, timeout=10, allow_redirects=True
            )
            if resp.status_code == 200:
                ct = resp.headers.get("content-type", "")
                if "pdf" in ct or "octet-stream" in ct or resp.headers.get("content-length", "0") != "0":
                    return direct_url

            if resp.status_code == 404:
                break   # doesn't exist at direct URL, try page scrape

            if resp.status_code == 429:
                wait = RETRY_DELAY * attempt
                log.warning(f"  429 rate limited — waiting {wait}s")
                time.sleep(wait)
                continue

        except Exception as e:
            log.debug(f"  HEAD request failed for {slug}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    # Strategy 2: scrape the script page
    page_url = f"{BASE_URL}/script/{slug}"
    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for PDF links in <a> tags
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" in href and "scriptslug" in href:
                return href

        # Also check for meta or script tags with PDF urls
        text = resp.text
        match = re.search(r'https://assets\.scriptslug\.com/[^"\']+\.pdf', text)
        if match:
            return match.group(0)

    except Exception as e:
        log.debug(f"  Page scrape failed for {slug}: {e}")

    return None


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — DOWNLOAD PDF
# ══════════════════════════════════════════════════════════════════════════════

def download_pdf(pdf_url: str, save_path: Path) -> bool:
    """Download a PDF from url and save to save_path. Returns True on success."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(
                pdf_url, headers=HEADERS, timeout=30, stream=True
            )

            if resp.status_code == 429:
                wait = RETRY_DELAY * attempt
                log.warning(f"  429 — waiting {wait}s …")
                time.sleep(wait)
                continue

            if resp.status_code != 200:
                log.warning(f"  HTTP {resp.status_code} for {pdf_url}")
                return False

            # Check content type
            ct = resp.headers.get("content-type", "")
            if "html" in ct:
                log.warning(f"  Got HTML instead of PDF — skipping")
                return False

            # Write in chunks (handles large files)
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Verify file is a real PDF
            size = save_path.stat().st_size
            if size < 1000:
                save_path.unlink(missing_ok=True)
                log.warning(f"  File too small ({size} bytes) — not a valid PDF")
                return False

            # Check PDF magic bytes
            with open(save_path, "rb") as f:
                magic = f.read(4)
            if magic != b"%PDF":
                save_path.unlink(missing_ok=True)
                log.warning(f"  Not a valid PDF (wrong magic bytes)")
                return False

            return True

        except Exception as e:
            log.warning(f"  Download error (attempt {attempt}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    return False


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def run(count: int = 50, resume: bool = True, seed: int = None):
    """
    Main entry point.

    Args:
        count:  Number of scripts to download
        resume: Skip slugs that already have a PDF in data/scripts/
        seed:   Random seed for reproducibility (default: random)
    """
    if seed is not None:
        random.seed(seed)

    log.info(f"══ ScriptSlug Downloader — target: {count} scripts ══")

    # ── Collect slugs ──────────────────────────────────────────────────────────
    all_slugs = collect_all_slugs(target=count * 3)   # collect 3× target for headroom

    if not all_slugs:
        log.error("No slugs found — check your internet connection")
        return

    # ── Filter already downloaded ──────────────────────────────────────────────
    if resume:
        existing = {p.stem for p in SCRIPTS_DIR.glob("*.pdf")}
        all_slugs = [(s, t) for s, t in all_slugs if s not in existing]
        log.info(f"  After resume filter: {len(all_slugs)} slugs remaining")

    if not all_slugs:
        log.info("  Nothing to download — all scripts already present")
        return

    # ── Pick random subset ─────────────────────────────────────────────────────
    random.shuffle(all_slugs)
    targets = all_slugs[:min(count * 2, len(all_slugs))]
    log.info(f"  Selected {len(targets)} candidates (will try until {count} succeed)")

    # ── Download loop ──────────────────────────────────────────────────────────
    success = 0
    failed  = []

    for slug, title in tqdm(targets, desc="Downloading"):
        if success >= count:
            break

        save_path = SCRIPTS_DIR / f"{slug}.pdf"

        # Skip if exists
        if resume and save_path.exists() and save_path.stat().st_size > 1000:
            success += 1
            continue

        log.info(f"  [{success+1}/{count}] {title} ({slug})")

        # Find PDF URL
        pdf_url = get_pdf_url(slug)
        if not pdf_url:
            log.warning(f"  No PDF found for {slug}")
            failed.append((slug, "no PDF URL"))
            time.sleep(DELAY)
            continue

        log.debug(f"  PDF URL: {pdf_url}")

        # Download
        ok = download_pdf(pdf_url, save_path)
        if ok:
            size_kb = save_path.stat().st_size // 1024
            log.info(f"  ✓ {slug}.pdf ({size_kb} KB)")
            success += 1
        else:
            failed.append((slug, "download failed"))
            save_path.unlink(missing_ok=True)

        time.sleep(DELAY)

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("  ScriptSlug Download Summary")
    print("═" * 60)
    print(f"  ✓ Downloaded: {success}")
    print(f"  ✗ Failed:     {len(failed)}")

    total = len(list(SCRIPTS_DIR.glob("*.pdf")))
    print(f"  Total PDFs in data/scripts/: {total}")

    if failed:
        print("\n  Failed slugs:")
        for slug, reason in failed[:10]:
            print(f"    {slug}: {reason}")
        if len(failed) > 10:
            print(f"    ... and {len(failed)-10} more")

    if success > 0:
        print("\n  Next step:")
        print("    python rag_pipeline.py --ingest")
    print("═" * 60)


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Download screenplay PDFs from scriptslug.com"
    )
    parser.add_argument(
        "--count", type=int, default=50,
        help="Number of scripts to download (default: 50)"
    )
    parser.add_argument(
        "--resume", action="store_true", default=True,
        help="Skip already downloaded scripts (default: True)"
    )
    parser.add_argument(
        "--no-resume", action="store_false", dest="resume",
        help="Re-download everything"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility"
    )
    args = parser.parse_args()
    run(count=args.count, resume=args.resume, seed=args.seed)


if __name__ == "__main__":
    main()