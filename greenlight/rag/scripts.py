"""
Greenlight Cinema — Script Source Registry
=============================================
Registry of screenplay sources and their metadata.
Used by the RAG pipeline (scripts/rag_pipeline.py) for downloading,
and by the ingestion module (greenlight/rag/ingest.py) for metadata lookup.
"""

import logging
from pathlib import Path

from greenlight.config import SCRIPTS_DIR

log = logging.getLogger("greenlight.rag.scripts")

# ── IMSDb Script source registry ────────────────────────────────────────────
# Each entry: (filename, url, genre_str, year)
# Note: IMSDb scripts are downloaded as HTML and the <pre> block is saved as .txt
SCRIPT_SOURCES = [
    # ── Action / SciFi ────────────────────────────────────────────────────────
    ("die_hard.txt",             "https://imsdb.com/scripts/Die-Hard.html",            "Action",          1988),
    ("matrix.txt",               "https://imsdb.com/scripts/Matrix,-The.html",         "Action|SciFi",    1999),
    ("terminator.txt",           "https://imsdb.com/scripts/Terminator.html",          "Action|SciFi",    1984),
    ("terminator_2.txt",         "https://imsdb.com/scripts/Terminator-2-Judgement-Day.html", "Action|SciFi", 1991),
    ("alien.txt",                "https://imsdb.com/scripts/Alien.html",               "SciFi|Horror",    1979),
    ("aliens.txt",               "https://imsdb.com/scripts/Aliens.html",              "Action|SciFi",    1986),
    ("blade_runner.txt",         "https://imsdb.com/scripts/Blade-Runner.html",        "SciFi|Thriller",  1982),
    ("jurassic_park.txt",        "https://imsdb.com/scripts/Jurassic-Park.html",       "Action|SciFi",    1993),
    ("minority_report.txt",      "https://imsdb.com/scripts/Minority-Report.html",     "SciFi|Action",    2002),
    ("inception.txt",            "https://imsdb.com/scripts/Inception.html",           "SciFi|Action",    2010),
    ("interstellar.txt",         "https://imsdb.com/scripts/Interstellar.html",        "SciFi|Drama",     2014),
    ("avatar.txt",               "https://imsdb.com/scripts/Avatar.html",              "Action|SciFi",    2009),
    ("batman_begins.txt",        "https://imsdb.com/scripts/Batman-Begins.html",       "Action|Crime",    2005),
    ("dark_knight.txt",          "https://imsdb.com/scripts/Dark-Knight,-The.html",    "Action|Crime",    2008),
    ("spiderman.txt",            "https://imsdb.com/scripts/Spider-Man.html",          "Action|Adventure",2002),
    ("gladiator.txt",            "https://imsdb.com/scripts/Gladiator.html",           "Action|Drama",    2000),
    ("braveheart.txt",           "https://imsdb.com/scripts/Braveheart.html",          "Action|Drama",    1995),
    ("lord_of_the_rings.txt",    "https://imsdb.com/scripts/Lord-of-the-Rings-Fellowship-of-the-Ring,-The.html", "Action|Fantasy", 2001),
    ("indiana_jones.txt",        "https://imsdb.com/scripts/Raiders-of-the-Lost-Ark.html", "Action|Adventure", 1981),
    ("star_wars_new_hope.txt",   "https://imsdb.com/scripts/Star-Wars-A-New-Hope.html","Action|SciFi",    1977),

    # ── Drama / Thriller ──────────────────────────────────────────────────────
    ("pulp_fiction.txt",         "https://imsdb.com/scripts/Pulp-Fiction.html",        "Crime|Drama",     1994),
    ("godfather.txt",            "https://imsdb.com/scripts/Godfather.html",           "Crime|Drama",     1972),
    ("godfather_part_ii.txt",    "https://imsdb.com/scripts/Godfather-Part-II.html",   "Crime|Drama",     1974),
    ("goodfellas.txt",           "https://imsdb.com/scripts/Goodfellas.html",          "Crime|Drama",     1990),
    ("shawshank_redemption.txt", "https://imsdb.com/scripts/Shawshank-Redemption,-The.html", "Drama",     1994),
    ("fight_club.txt",           "https://imsdb.com/scripts/Fight-Club.html",          "Drama|Thriller",  1999),
    ("se7en.txt",                "https://imsdb.com/scripts/Se7en.html",               "Crime|Thriller",  1995),
    ("silence_of_the_lambs.txt", "https://imsdb.com/scripts/Silence-of-the-Lambs.html","Crime|Thriller",  1991),
    ("usual_suspects.txt",       "https://imsdb.com/scripts/Usual-Suspects,-The.html", "Crime|Mystery",   1995),
    ("memento.txt",              "https://imsdb.com/scripts/Memento.html",             "Mystery|Thriller",2000),
    ("departed.txt",             "https://imsdb.com/scripts/Departed,-The.html",       "Crime|Thriller",  2006),
    ("no_country_for_old_men.txt","https://imsdb.com/scripts/No-Country-for-Old-Men.html","Crime|Thriller",2007),
    ("fargo.txt",                "https://imsdb.com/scripts/Fargo.html",               "Crime|Thriller",  1996),
    ("taxi_driver.txt",          "https://imsdb.com/scripts/Taxi-Driver.html",         "Crime|Drama",     1976),
    ("american_beauty.txt",      "https://imsdb.com/scripts/American-Beauty.html",     "Drama",           1999),
    ("good_will_hunting.txt",    "https://imsdb.com/scripts/Good-Will-Hunting.html",   "Drama",           1997),
    ("social_network.txt",       "https://imsdb.com/scripts/Social-Network,-The.html", "Drama|Biography", 2010),
    ("wolf_of_wall_street.txt",  "https://imsdb.com/scripts/Wolf-of-Wall-Street,-The.html", "Crime|Comedy", 2013),
    ("there_will_be_blood.txt",  "https://imsdb.com/scripts/There-Will-Be-Blood.html", "Drama",           2007),
    ("joker.txt",                "https://imsdb.com/scripts/Joker.html",               "Crime|Drama",     2019),

    # ── Comedy / Romance ──────────────────────────────────────────────────────
    ("big_lebowski.txt",         "https://imsdb.com/scripts/Big-Lebowski,-The.html",   "Comedy|Crime",    1998),
    ("groundhog_day.txt",        "https://imsdb.com/scripts/Groundhog-Day.html",       "Comedy|Fantasy",  1993),
    ("superbad.txt",             "https://imsdb.com/scripts/Superbad.html",            "Comedy",          2007),
    ("hangover.txt",             "https://imsdb.com/scripts/Hangover,-The.html",       "Comedy",          2009),
    ("bridesmaids.txt",          "https://imsdb.com/scripts/Bridesmaids.html",         "Comedy",          2011),
    ("office_space.txt",         "https://imsdb.com/scripts/Office-Space.html",        "Comedy",          1999),
    ("when_harry_met_sally.txt", "https://imsdb.com/scripts/When-Harry-Met-Sally.html","Comedy|Romance",  1989),
    ("eternal_sunshine.txt",     "https://imsdb.com/scripts/Eternal-Sunshine-of-the-Spotless-Mind.html", "Romance|SciFi", 2004),
    ("la_la_land.txt",           "https://imsdb.com/scripts/La-La-Land.html",          "Comedy|Romance",  2016),
    ("silver_linings.txt",       "https://imsdb.com/scripts/Silver-Linings-Playbook.html", "Comedy|Drama", 2012),
]


def get_script_metadata(filename: str) -> dict:
    """Look up metadata for a script by filename."""
    for fname, _, genre, year in SCRIPT_SOURCES:
        if fname == filename:
            return {
                "genre": genre,
                "year": year,
                "title": Path(filename).stem.replace("_", " ").title(),
            }
    return {
        "genre": "Unknown",
        "year": 0,
        "title": Path(filename).stem.replace("_", " ").title(),
    }


def get_available_scripts() -> list[Path]:
    """Return list of downloaded screenplay files (both txt and pdf)."""
    txt_files = list(SCRIPTS_DIR.glob("*.txt"))
    pdf_files = list(SCRIPTS_DIR.glob("*.pdf"))
    return sorted(txt_files + pdf_files)
