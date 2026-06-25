"""
Greenlight Cinema — IMSDB Scraper
===================================
Scrapes screenplay text from imsdb.com and saves as .txt files.
These .txt files are then picked up by rag_pipeline.py --ingest

Run:
    python scrape_imsdb.py            # scrape all 100 scripts
    python scrape_imsdb.py --test 3   # test with first 3 only
    python scrape_imsdb.py --resume   # skip already downloaded

How IMSDB works:
    Movie page:  https://imsdb.com/scripts/Die-Hard.html
    The actual script text is inside <pre class="scrtext"> tag
    We extract that, clean it, save as .txt

Requirements:
    pip install requests beautifulsoup4 tqdm
"""

import re
import time
import logging
import argparse
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
log = logging.getLogger("scraper")

# ── Paths ───────────────────────────────────────────────────────────────────────
SCRIPTS_DIR = Path("data/scripts")
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Request config ───────────────────────────────────────────────────────────────
BASE_URL  = "https://imsdb.com/scripts"
HEADERS   = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://imsdb.com/",
}
DELAY_BETWEEN = 2.5   # seconds between requests — be polite, avoid bans
MAX_RETRIES   = 3
RETRY_DELAY   = 8     # seconds to wait after a failed request


# ══════════════════════════════════════════════════════════════════════════════
# SCRIPT CATALOGUE
# Format: (save_filename, imsdb_slug, genre, year)
# imsdb_slug is the part after /scripts/ in the URL e.g. "Die-Hard.html"
# To find slugs: go to imsdb.com, search the movie, copy the URL slug
# ══════════════════════════════════════════════════════════════════════════════

SCRIPTS = [
    # ── Action ────────────────────────────────────────────────────────────────
    ("die_hard",              "Die-Hard",                  "Action",           1988),
    ("mad_max_fury_road",     "Mad-Max-Fury-Road",          "Action",           2015),
    ("the_matrix",            "Matrix,-The",               "Action|SciFi",     1999),
    ("terminator2",           "Terminator-2-Judgment-Day", "Action|SciFi",     1991),
    ("speed",                 "Speed",                     "Action|Thriller",  1994),
    ("lethal_weapon",         "Lethal-Weapon",             "Action",           1987),
    ("heat",                  "Heat",                      "Action|Crime",     1995),
    ("the_rock",              "Rock,-The",                 "Action|Thriller",  1996),
    ("top_gun",               "Top-Gun",                   "Action",           1986),
    ("true_lies",             "True-Lies",                 "Action|Comedy",    1994),

    # ── Drama ─────────────────────────────────────────────────────────────────
    ("the_godfather",         "Godfather,-The",            "Drama|Crime",      1972),
    ("schindlers_list",       "Schindler's-List",          "Drama|History",    1993),
    ("forrest_gump",          "Forrest-Gump",              "Drama",            1994),
    ("good_will_hunting",     "Good-Will-Hunting",         "Drama",            1997),
    ("american_beauty",       "American-Beauty",           "Drama",            1999),
    ("the_shawshank_redemption","Shawshank-Redemption,-The","Drama",           1994),
    ("rain_man",              "Rain-Man",                  "Drama",            1988),
    ("philadelphia",          "Philadelphia",              "Drama",            1993),
    ("million_dollar_baby",   "Million-Dollar-Baby",       "Drama|Sport",      2004),
    ("the_green_mile",        "Green-Mile,-The",           "Drama|Fantasy",    1999),

    # ── Comedy ────────────────────────────────────────────────────────────────
    ("home_alone",            "Home-Alone",                "Comedy|Family",    1990),
    ("groundhog_day",         "Groundhog-Day",             "Comedy|Fantasy",   1993),
    ("the_hangover",          "Hangover,-The",             "Comedy",           2009),
    ("superbad",              "Superbad",                  "Comedy",           2007),
    ("anchorman",             "Anchorman-The-Legend-of-Ron-Burgundy", "Comedy",2004),
    ("dumb_and_dumber",       "Dumb-and-Dumber",           "Comedy",           1994),
    ("mrs_doubtfire",         "Mrs.-Doubtfire",            "Comedy|Family",    1993),
    ("liar_liar",             "Liar-Liar",                 "Comedy",           1997),
    ("the_mask",              "Mask,-The",                 "Comedy|Fantasy",   1994),
    ("wayne's_world",         "Wayne's-World",             "Comedy",           1992),

    # ── Thriller / Mystery ────────────────────────────────────────────────────
    ("silence_of_the_lambs",  "Silence-of-the-Lambs,-The", "Thriller|Crime",  1991),
    ("seven",                 "Seven",                     "Thriller|Crime",   1995),
    ("the_usual_suspects",    "Usual-Suspects,-The",       "Thriller|Mystery", 1995),
    ("memento",               "Memento",                   "Thriller|Mystery", 2000),
    ("the_sixth_sense",       "Sixth-Sense,-The",          "Thriller|Mystery", 1999),
    ("psycho",                "Psycho",                    "Thriller|Horror",  1960),
    ("rear_window",           "Rear-Window",               "Thriller|Mystery", 1954),
    ("zodiac",                "Zodiac",                    "Thriller|Crime",   2007),
    ("prisoners",             "Prisoners",                 "Thriller|Crime",   2013),
    ("gone_girl",             "Gone-Girl",                 "Thriller|Drama",   2014),

    # ── Sci-Fi ────────────────────────────────────────────────────────────────
    ("alien",                 "Alien",                     "SciFi|Horror",     1979),
    ("blade_runner",          "Blade-Runner",              "SciFi|Thriller",   1982),
    ("2001_space_odyssey",    "2001-A-Space-Odyssey",      "SciFi",            1968),
    ("arrival",               "Arrival",                   "SciFi|Drama",      2016),
    ("ex_machina",            "Ex-Machina",                "SciFi|Thriller",   2014),
    ("interstellar",          "Interstellar",              "SciFi|Drama",      2014),
    ("the_martian",           "Martian,-The",              "SciFi|Drama",      2015),
    ("district_9",            "District-9",                "SciFi|Action",     2009),
    ("looper",                "Looper",                    "SciFi|Action",     2012),
    ("inception",             "Inception",                 "SciFi|Action",     2010),

    # ── Horror ────────────────────────────────────────────────────────────────
    ("the_shining",           "Shining,-The",              "Horror|Thriller",  1980),
    ("get_out",               "Get-Out",                   "Horror|Thriller",  2017),
    ("hereditary",            "Hereditary",                "Horror|Drama",     2018),
    ("a_quiet_place",         "Quiet-Place,-A",            "Horror|SciFi",     2018),
    ("the_witch",             "Witch,-The",                "Horror|Drama",     2015),
    ("midsommar",             "Midsommar",                 "Horror|Drama",     2019),
    ("us",                    "Us",                        "Horror|Thriller",  2019),
    ("it",                    "It",                        "Horror",           2017),
    ("the_babadook",          "Babadook,-The",             "Horror|Drama",     2014),
    ("sinister",              "Sinister",                  "Horror|Thriller",  2012),

    # ── Romance ───────────────────────────────────────────────────────────────
    ("when_harry_met_sally",  "When-Harry-Met-Sally",      "Romance|Comedy",   1989),
    ("pretty_woman",          "Pretty-Woman",              "Romance|Comedy",   1990),
    ("titanic",               "Titanic",                   "Romance|Drama",    1997),
    ("eternal_sunshine",      "Eternal-Sunshine-of-the-Spotless-Mind","Romance|SciFi",2004),
    ("la_la_land",            "La-La-Land",                "Romance|Musical",  2016),
    ("the_notebook",          "Notebook,-The",             "Romance|Drama",    2004),
    ("notting_hill",          "Notting-Hill",              "Romance|Comedy",   1999),
    ("hitch",                 "Hitch",                     "Romance|Comedy",   2005),
    ("crazy_stupid_love",     "Crazy-Stupid-Love",         "Romance|Comedy",   2011),
    ("silver_linings_playbook","Silver-Linings-Playbook",  "Romance|Drama",    2012),

    # ── Animation / Family ────────────────────────────────────────────────────
    ("toy_story",             "Toy-Story",                 "Animation|Family", 1995),
    ("the_lion_king",         "Lion-King,-The",            "Animation|Family", 1994),
    ("finding_nemo",          "Finding-Nemo",              "Animation|Family", 2003),
    ("up",                    "Up",                        "Animation|Family", 2009),
    ("inside_out",            "Inside-Out",                "Animation|Family", 2015),
    ("shrek",                 "Shrek",                     "Animation|Comedy", 2001),
    ("the_incredibles",       "Incredibles,-The",          "Animation|Action", 2004),
    ("wall_e",                "WALL-E",                    "Animation|SciFi",  2008),
    ("ratatouille",           "Ratatouille",               "Animation|Comedy", 2007),
    ("monsters_inc",          "Monsters,-Inc.",            "Animation|Comedy", 2001),

    # ── Crime / Heist ─────────────────────────────────────────────────────────
    ("pulp_fiction",          "Pulp-Fiction",              "Crime|Drama",      1994),
    ("goodfellas",            "Goodfellas",                "Crime|Drama",      1990),
    ("oceans_eleven",         "Ocean's-Eleven",            "Crime|Comedy",     2001),
    ("reservoir_dogs",        "Reservoir-Dogs",            "Crime|Thriller",   1992),
    ("the_departed",          "Departed,-The",             "Crime|Thriller",   2006),
    ("fargo",                 "Fargo",                     "Crime|Drama",      1996),
    ("no_country_for_old_men","No-Country-for-Old-Men",    "Crime|Thriller",   2007),
    ("the_big_lebowski",      "Big-Lebowski,-The",         "Crime|Comedy",     1998),
    ("training_day",          "Training-Day",              "Crime|Thriller",   2001),
    ("inside_man",            "Inside-Man",                "Crime|Thriller",   2006),

    # ── Biography / History ───────────────────────────────────────────────────
    ("the_social_network",    "Social-Network,-The",       "Biography|Drama",  2010),
    ("spotlight",             "Spotlight",                 "Biography|Drama",  2015),
    ("the_imitation_game",    "Imitation-Game,-The",       "Biography|Drama",  2014),
    ("whiplash",              "Whiplash",                  "Drama|Music",      2014),
    ("the_wolf_of_wall_street","Wolf-of-Wall-Street,-The", "Biography|Crime",  2013),
    ("capote",                "Capote",                    "Biography|Drama",  2005),
    ("lincoln",               "Lincoln",                   "Biography|History",2012),
    ("the_aviator",           "Aviator,-The",              "Biography|Drama",  2004),
    ("ray",                   "Ray",                       "Biography|Music",  2004),
    ("ali",                   "Ali",                       "Biography|Sport",  2001),
]


# ══════════════════════════════════════════════════════════════════════════════
# TEXT CLEANING
# ══════════════════════════════════════════════════════════════════════════════

def clean_script_text(raw_text: str) -> str:
    """
    Clean raw HTML-extracted screenplay text.
    Removes HTML artifacts, normalises whitespace, keeps screenplay structure.
    """
    # Remove HTML tags if any leaked through
    raw_text = re.sub(r"<[^>]+>", " ", raw_text)

    # Decode common HTML entities
    raw_text = (raw_text
        .replace("&amp;",  "&")
        .replace("&lt;",   "<")
        .replace("&gt;",   ">")
        .replace("&quot;", '"')
        .replace("&#39;",  "'")
        .replace("&nbsp;", " ")
    )

    # Normalise Windows line endings
    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse 3+ consecutive blank lines into 2
    raw_text = re.sub(r"\n{3,}", "\n\n", raw_text)

    # Strip trailing whitespace on each line (keep leading — important for
    # screenplay formatting like character names and dialogue indentation)
    lines = [line.rstrip() for line in raw_text.split("\n")]
    raw_text = "\n".join(lines)

    return raw_text.strip()


def is_valid_script(text: str) -> bool:
    """
    Basic sanity check — is this actually a screenplay?
    Looks for scene headers or dialogue patterns.
    """
    if len(text) < 2000:   # too short to be a real script
        return False

    has_scene = bool(re.search(r"(?m)^(INT\.|EXT\.|INT/EXT\.)\s+", text))
    has_alpha  = sum(c.isalpha() for c in text) / max(len(text), 1) > 0.5

    return has_alpha and (has_scene or len(text) > 10000)


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPER
# ══════════════════════════════════════════════════════════════════════════════

def fetch_script(slug: str) -> str | None:
    """
    Fetch and extract screenplay text from one IMSDB page.

    IMSDB structure:
        https://imsdb.com/scripts/{Slug}.html
        Script text is inside: <td class="scrtext"><pre>...</pre></td>
        OR:                     <pre class="scrtext">...</pre>
    """
    url = f"{BASE_URL}/{slug}.html"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)

            if resp.status_code == 404:
                log.warning(f"  404 — {slug} not found on IMSDB")
                return None

            if resp.status_code == 429:
                wait = RETRY_DELAY * attempt
                log.warning(f"  429 rate limited — waiting {wait}s …")
                time.sleep(wait)
                continue

            if resp.status_code != 200:
                log.warning(f"  HTTP {resp.status_code} for {slug}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Strategy 1: <td class="scrtext"><pre>
            td = soup.find("td", class_="scrtext")
            if td:
                pre = td.find("pre")
                if pre:
                    return clean_script_text(pre.get_text())

            # Strategy 2: <pre class="scrtext">
            pre = soup.find("pre", class_="scrtext")
            if pre:
                return clean_script_text(pre.get_text())

            # Strategy 3: any large <pre> block (some pages differ)
            all_pres = soup.find_all("pre")
            if all_pres:
                # Pick the largest <pre> block — most likely the script
                biggest = max(all_pres, key=lambda p: len(p.get_text()))
                text = clean_script_text(biggest.get_text())
                if len(text) > 3000:
                    return text

            log.warning(f"  Could not find script text block in {slug}")
            return None

        except requests.exceptions.Timeout:
            log.warning(f"  Timeout on {slug} (attempt {attempt}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
        except Exception as e:
            log.warning(f"  Error fetching {slug}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    return None


def scrape_all(limit: int = None, resume: bool = True):
    """
    Scrape all scripts in the catalogue and save as .txt files.

    Args:
        limit:  If set, only scrape the first N scripts (for testing)
        resume: If True, skip scripts that already have a .txt file
    """
    targets = SCRIPTS[:limit] if limit else SCRIPTS
    log.info(f"══ IMSDB Scraper — {len(targets)} scripts ══")

    success, skipped, failed = 0, 0, []

    for filename, slug, genre, year in tqdm(targets, desc="Scraping"):
        save_path = SCRIPTS_DIR / f"{filename}.txt"

        # Skip already downloaded
        if resume and save_path.exists() and save_path.stat().st_size > 1000:
            skipped += 1
            continue

        log.info(f"  Fetching: {slug} …")
        text = fetch_script(slug)

        if not text:
            log.warning(f"  ✗ Failed: {filename} ({slug})")
            failed.append((filename, slug))
            time.sleep(DELAY_BETWEEN)
            continue

        if not is_valid_script(text):
            log.warning(f"  ✗ Invalid script content: {filename} — too short or no scene markers")
            failed.append((filename, slug))
            time.sleep(DELAY_BETWEEN)
            continue

        # Save metadata header + script text
        header = (
            f"TITLE: {filename.replace('_', ' ').title()}\n"
            f"GENRE: {genre}\n"
            f"YEAR:  {year}\n"
            f"SOURCE: imsdb.com/scripts/{slug}.html\n"
            f"{'='*60}\n\n"
        )
        save_path.write_text(header + text, encoding="utf-8")

        word_count = len(text.split())
        log.info(f"  ✓ Saved {filename}.txt — {word_count:,} words")
        success += 1

        time.sleep(DELAY_BETWEEN)   # polite delay between requests

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("  IMSDB Scrape Summary")
    print("═" * 60)
    print(f"  ✓ Saved:   {success}")
    print(f"  ↷ Skipped: {skipped}  (already downloaded)")
    print(f"  ✗ Failed:  {len(failed)}")

    if failed:
        print("\n  Failed scripts (add manually):")
        for fname, slug in failed:
            print(f"    {fname:35s} → https://imsdb.com/scripts/{slug}.html")
        print("\n  For failed ones: open the URL in browser, Ctrl+A, Ctrl+C,")
        print("  paste into data/scripts/<name>.txt manually.")

    total_txt = len(list(SCRIPTS_DIR.glob("*.txt")))
    print(f"\n  Total .txt files in data/scripts/: {total_txt}")
    print("═" * 60)
    print("\n  Next step:")
    print("    python rag_pipeline.py --ingest")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# UPDATE rag_pipeline to also handle .txt files
# ══════════════════════════════════════════════════════════════════════════════

def print_rag_patch_instructions():
    """
    The rag_pipeline.py ingest_scripts() currently only globs *.pdf
    Print a reminder to also handle *.txt
    """
    print("\n  ⚠️  IMPORTANT: Update rag_pipeline.py ingest_scripts()")
    print("  Change this line:")
    print('    pdf_files = sorted(SCRIPTS_DIR.glob("*.pdf"))')
    print("  To this:")
    print('    pdf_files = sorted(SCRIPTS_DIR.glob("*.pdf")) + \\')
    print('                sorted(SCRIPTS_DIR.glob("*.txt"))')
    print()
    print("  And in extract_text_from_pdf(), add at the very top:")
    print("    if pdf_path.suffix == '.txt':")
    print("        return pdf_path.read_text(encoding='utf-8', errors='ignore')")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Greenlight Cinema — IMSDB Scraper")
    parser.add_argument("--test",   type=int, metavar="N",
                        help="Only scrape first N scripts (for testing)")
    parser.add_argument("--resume", action="store_true", default=True,
                        help="Skip already downloaded scripts (default: True)")
    parser.add_argument("--no-resume", action="store_false", dest="resume",
                        help="Re-download everything even if .txt exists")
    args = parser.parse_args()

    scrape_all(limit=args.test, resume=args.resume)
    print_rag_patch_instructions()


if __name__ == "__main__":
    main()