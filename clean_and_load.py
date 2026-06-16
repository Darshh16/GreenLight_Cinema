"""
Greenlight Cinema — Data Cleaning & DuckDB Loading Pipeline
============================================================
Run: python clean_and_load.py

Expects these files in a ./data/ folder:
  - tmdb.csv
  - credits.csv
  - links.csv
  - movies.csv
  - ratings.csv
  - tags.csv

Outputs:
  - greenlight.duckdb  (all cleaned tables + derived analytics tables)
"""

import os
import ast
import json
import logging
import duckdb
import pandas as pd
import numpy as np
from pathlib import Path

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("greenlight")

# ── Paths ───────────────────────────────────────────────────────────────────────
DATA_DIR = Path("data")
DB_PATH  = Path("greenlight.duckdb")

# ── Helpers ─────────────────────────────────────────────────────────────────────

def safe_parse(val):
    """Parse a stringified Python list/dict without crashing."""
    if pd.isna(val) or val == "":
        return []
    try:
        return ast.literal_eval(val)
    except Exception:
        try:
            return json.loads(val)
        except Exception:
            return []


def extract_names(val, key="name"):
    """Return a list of 'name' values from a JSON column."""
    items = safe_parse(val)
    if not isinstance(items, list):
        return []
    return [i.get(key, "") for i in items if isinstance(i, dict) and i.get(key)]


def missing_pct(series: pd.Series) -> float:
    return round(series.isna().mean() * 100, 2)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — CLEAN TMDB
# ══════════════════════════════════════════════════════════════════════════════

def clean_tmdb() -> pd.DataFrame:
    log.info("Loading tmdb.csv …")
    df = pd.read_csv(DATA_DIR / "tmdb.csv", low_memory=False)
    log.info(f"  Raw shape: {df.shape}")

    # ── Drop columns we don't need ────────────────────────────────────────────
    drop_cols = [
        "adult", "backdrop_path", "homepage", "poster_path",
        "production_countries", "spoken_languages", "original_title",
    ]
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True)

    # ── Keep only Released films ───────────────────────────────────────────────
    if "status" in df.columns:
        before = len(df)
        df = df[df["status"] == "Released"].copy()
        log.info(f"  After status='Released' filter: {len(df)} rows (dropped {before - len(df)})")

    # ── Parse release_date → year, month, quarter ─────────────────────────────
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["release_year"]    = df["release_date"].dt.year
    df["release_month"]   = df["release_date"].dt.month
    df["release_quarter"] = df["release_date"].dt.quarter.map(
        {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
    )
    df.drop(columns=["release_date"], inplace=True)

    # ── Filter out films with unreliable vote data ─────────────────────────────
    if "vote_count" in df.columns:
        before = len(df)
        df = df[df["vote_count"] >= 10].copy()
        log.info(f"  After vote_count>=10 filter: {len(df)} rows (dropped {before - len(df)})")

    # ── Filter out bad runtimes ────────────────────────────────────────────────
    if "runtime" in df.columns:
        before = len(df)
        df = df[df["runtime"].notna() & (df["runtime"] > 0)].copy()
        log.info(f"  After runtime>0 filter: {len(df)} rows (dropped {before - len(df)})")

    # ── Handle budget / revenue ────────────────────────────────────────────────
    for col in ["budget", "revenue"]:
        if col not in df.columns:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
        # treat 0 as missing — studios often log 0 instead of NaN
        df[col] = df[col].replace(0, np.nan)

        pct = missing_pct(df[col])
        log.info(f"  {col}: {pct}% missing")
        if pct > 30:
            # Fill with genre-group median (use raw genres string as proxy)
            group_median = df.groupby("genres")[col].transform("median")
            global_median = df[col].median()
            df[col] = df[col].fillna(group_median).fillna(global_median)
            log.info(f"  {col}: filled with genre-group median (>{30}% missing)")
        else:
            before = len(df)
            df = df[df[col].notna()].copy()
            log.info(f"  {col}: dropped {before - len(df)} rows with nulls (<={30}% missing)")

    # ── Compute ROI ────────────────────────────────────────────────────────────
    if "budget" in df.columns and "revenue" in df.columns:
        df["roi"] = np.where(
            (df["budget"] > 0) & (df["revenue"] > 0),
            df["revenue"] / df["budget"],
            np.nan,
        )
        log.info(f"  ROI computed: {df['roi'].notna().sum()} valid rows")

    # ── Parse genres → clean list → genre_list (stored as string) ────────────
    if "genres" in df.columns:
        df["genre_list"] = df["genres"].apply(lambda v: extract_names(v))
        df["genre_str"]  = df["genre_list"].apply(lambda g: "|".join(g))
        df.drop(columns=["genres"], inplace=True)

    # ── Parse keywords ────────────────────────────────────────────────────────
    if "keywords" in df.columns:
        df["keyword_list"] = df["keywords"].apply(lambda v: extract_names(v))
        df["keyword_str"]  = df["keyword_list"].apply(lambda k: "|".join(k))
        df.drop(columns=["keywords"], inplace=True)

    # ── Parse production_companies ────────────────────────────────────────────
    if "production_companies" in df.columns:
        df["company_list"] = df["production_companies"].apply(lambda v: extract_names(v))
        df["company_str"]  = df["company_list"].apply(lambda c: "|".join(c))
        df.drop(columns=["production_companies"], inplace=True)

    # ── Drop leftover list columns (DuckDB prefers strings/scalars) ───────────
    for col in ["genre_list", "keyword_list", "company_list"]:
        if col in df.columns:
            df.drop(columns=[col], inplace=True)

    # ── Rename id for clarity ─────────────────────────────────────────────────
    df.rename(columns={"id": "tmdb_id"}, inplace=True)
    df["tmdb_id"] = pd.to_numeric(df["tmdb_id"], errors="coerce")
    df.dropna(subset=["tmdb_id"], inplace=True)
    df["tmdb_id"] = df["tmdb_id"].astype(int)

    # ── Final dedup ───────────────────────────────────────────────────────────
    df.drop_duplicates(subset=["tmdb_id"], inplace=True)

    log.info(f"  ✓ TMDB clean shape: {df.shape}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — CLEAN CREDITS
# ══════════════════════════════════════════════════════════════════════════════

def clean_credits() -> pd.DataFrame:
    log.info("Loading credits.csv …")
    df = pd.read_csv(DATA_DIR / "credits.csv", low_memory=False)
    log.info(f"  Raw shape: {df.shape}")

    # ── Extract top 5 cast members (by order field) ───────────────────────────
    def top_cast(val, n=5):
        items = safe_parse(val)
        if not isinstance(items, list):
            return ""
        # sort by order field ascending
        sorted_items = sorted(
            [i for i in items if isinstance(i, dict)],
            key=lambda x: x.get("order", 9999),
        )
        return "|".join([i["name"] for i in sorted_items[:n] if "name" in i])

    # ── Extract director(s) from crew ─────────────────────────────────────────
    def extract_directors(val):
        items = safe_parse(val)
        if not isinstance(items, list):
            return ""
        directors = [
            i["name"]
            for i in items
            if isinstance(i, dict)
            and i.get("job") == "Director"
            and "name" in i
        ]
        return "|".join(directors)

    df["top_cast"]   = df["cast"].apply(top_cast)
    df["directors"]  = df["crew"].apply(extract_directors)

    # ── Keep only what we need ────────────────────────────────────────────────
    df = df[["id", "top_cast", "directors"]].copy()
    df.rename(columns={"id": "tmdb_id"}, inplace=True)
    df["tmdb_id"] = pd.to_numeric(df["tmdb_id"], errors="coerce")
    df.dropna(subset=["tmdb_id"], inplace=True)
    df["tmdb_id"] = df["tmdb_id"].astype(int)

    df.drop_duplicates(subset=["tmdb_id"], inplace=True)

    log.info(f"  ✓ Credits clean shape: {df.shape}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — CLEAN MOVIELENS FILES
# ══════════════════════════════════════════════════════════════════════════════

def clean_links() -> pd.DataFrame:
    log.info("Loading links.csv …")
    df = pd.read_csv(DATA_DIR / "links.csv", low_memory=False)
    log.info(f"  Raw shape: {df.shape}")

    # Drop rows where tmdbId is missing — can't join without it
    before = len(df)
    df.dropna(subset=["tmdbId"], inplace=True)
    log.info(f"  Dropped {before - len(df)} rows with null tmdbId")

    df["tmdbId"] = df["tmdbId"].astype(int)
    df.rename(columns={"tmdbId": "tmdb_id", "movieId": "movie_id"}, inplace=True)

    # Drop imdbId — not needed
    df.drop(columns=["imdbId"], errors="ignore", inplace=True)
    df.drop_duplicates(inplace=True)

    log.info(f"  ✓ Links clean shape: {df.shape}")
    return df


def clean_ml_movies() -> pd.DataFrame:
    log.info("Loading movies.csv (MovieLens) …")
    df = pd.read_csv(DATA_DIR / "movies.csv", low_memory=False)
    log.info(f"  Raw shape: {df.shape}")

    # Drop "(no genres listed)"
    before = len(df)
    df = df[df["genres"] != "(no genres listed)"].copy()
    log.info(f"  Dropped {before - len(df)} rows with no genres")

    df.rename(columns={"movieId": "movie_id", "genres": "ml_genres"}, inplace=True)
    df.drop(columns=["title"], inplace=True)   # title already in TMDB
    df.drop_duplicates(subset=["movie_id"], inplace=True)

    log.info(f"  ✓ ML movies clean shape: {df.shape}")
    return df


def clean_ratings() -> pd.DataFrame:
    log.info("Loading ratings.csv …")
    df = pd.read_csv(DATA_DIR / "ratings.csv", low_memory=False)
    log.info(f"  Raw shape: {df.shape}")

    # Validate rating range
    df = df[(df["rating"] >= 0.5) & (df["rating"] <= 5.0)].copy()

    # Convert timestamp → year
    df["rating_year"] = pd.to_datetime(df["timestamp"], unit="s").dt.year
    df.drop(columns=["timestamp"], inplace=True)

    # Drop duplicates (same user rating same movie twice)
    before = len(df)
    df.drop_duplicates(subset=["userId", "movieId"], inplace=True)
    log.info(f"  Dropped {before - len(df)} duplicate (user, movie) pairs")

    df.rename(columns={"userId": "user_id", "movieId": "movie_id"}, inplace=True)
    log.info(f"  ✓ Ratings clean shape: {df.shape}")
    return df


def clean_tags() -> pd.DataFrame:
    log.info("Loading tags.csv …")
    df = pd.read_csv(DATA_DIR / "tags.csv", low_memory=False)
    log.info(f"  Raw shape: {df.shape}")

    # Lowercase & strip
    df["tag"] = df["tag"].str.lower().str.strip()

    # Drop nulls / empty
    before = len(df)
    df.dropna(subset=["tag"], inplace=True)
    df = df[df["tag"] != ""].copy()
    log.info(f"  Dropped {before - len(df)} null/empty tags")

    # Drop timestamp
    df.drop(columns=["timestamp"], errors="ignore", inplace=True)

    # Deduplicate (same user tagging same movie with same tag)
    before = len(df)
    df.drop_duplicates(subset=["userId", "movieId", "tag"], inplace=True)
    log.info(f"  Dropped {before - len(df)} duplicate tags")

    df.rename(columns={"userId": "user_id", "movieId": "movie_id"}, inplace=True)
    log.info(f"  ✓ Tags clean shape: {df.shape}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — BUILD MASTER TABLE
# ══════════════════════════════════════════════════════════════════════════════

def build_master(tmdb, credits, links, ml_movies) -> pd.DataFrame:
    log.info("Building master movie table …")

    # TMDB ← credits (left join — keep all TMDB rows)
    master = tmdb.merge(credits, on="tmdb_id", how="left")

    # master ← links (left join — attach movie_id bridge)
    master = master.merge(links, on="tmdb_id", how="left")

    # master ← ml_movies genres (left join)
    master = master.merge(ml_movies, on="movie_id", how="left")

    log.info(f"  ✓ Master shape: {master.shape}")
    return master


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — DERIVE ANALYTICS TABLES
# ══════════════════════════════════════════════════════════════════════════════

def _explode_pipe_col(master: pd.DataFrame, col: str, keep_cols: list) -> pd.DataFrame:
    """
    Utility: take a pipe-separated string column, explode it into one row
    per value, and return a tidy DataFrame with `keep_cols` attached.
    Handles nulls, empty strings, and missing columns gracefully.
    """
    if col not in master.columns:
        log.warning(f"  Column '{col}' not found in master — skipping.")
        return pd.DataFrame()

    df = master[keep_cols + [col]].copy()
    df = df[df[col].notna() & (df[col].astype(str).str.strip() != "")]

    # Split pipe-separated strings into lists
    df[col] = df[col].astype(str).str.split("|")

    # Explode → one row per value
    df = df.explode(col)
    df[col] = df[col].str.strip()
    df = df[df[col] != ""]
    return df


def build_genre_roi(master: pd.DataFrame) -> pd.DataFrame:
    """Average ROI, revenue, budget per genre."""
    log.info("Deriving genre_roi table …")

    keep = [c for c in ["roi", "revenue", "budget"] if c in master.columns]
    df = _explode_pipe_col(master.dropna(subset=["roi"]), "genre_str", keep)

    if df.empty:
        log.warning("  genre_roi: no data — returning empty table")
        return pd.DataFrame(columns=["genre", "avg_roi", "median_roi",
                                     "avg_revenue", "avg_budget", "movie_count"])

    df = df.rename(columns={"genre_str": "genre"})
    agg_dict = {"roi": ["mean", "median", "count"]}
    if "revenue" in df.columns:
        agg_dict["revenue"] = "mean"
    if "budget" in df.columns:
        agg_dict["budget"] = "mean"

    result = df.groupby("genre").agg(agg_dict)
    result.columns = ["avg_roi", "median_roi", "movie_count"] + (
        ["avg_revenue"] if "revenue" in df.columns else []
    ) + (
        ["avg_budget"] if "budget" in df.columns else []
    )
    result = result.reset_index().sort_values("avg_roi", ascending=False)
    log.info(f"  ✓ genre_roi: {result.shape}")
    return result


def build_seasonal_performance(master: pd.DataFrame) -> pd.DataFrame:
    """Average ROI per release quarter."""
    log.info("Deriving seasonal_performance table …")

    needed = ["release_quarter", "roi"]
    missing_cols = [c for c in needed if c not in master.columns]
    if missing_cols:
        log.warning(f"  seasonal_performance: missing columns {missing_cols} — skipping")
        return pd.DataFrame(columns=["release_quarter", "avg_roi",
                                     "median_roi", "avg_revenue", "movie_count"])

    df = master.dropna(subset=needed).copy()
    agg = {"roi": ["mean", "median", "count"]}
    if "revenue" in df.columns:
        agg["revenue"] = "mean"

    result = df.groupby("release_quarter").agg(agg)
    result.columns = ["avg_roi", "median_roi", "movie_count"] + (
        ["avg_revenue"] if "revenue" in df.columns else []
    )
    result = result.reset_index().sort_values("avg_roi", ascending=False)
    log.info(f"  ✓ seasonal_performance: {result.shape}")
    return result


def build_director_roi(master: pd.DataFrame) -> pd.DataFrame:
    """Average ROI per director."""
    log.info("Deriving director_roi table …")

    keep = [c for c in ["roi", "revenue"] if c in master.columns]
    df = _explode_pipe_col(master.dropna(subset=["roi"]), "directors", keep)

    if df.empty:
        log.warning("  director_roi: no data — returning empty table")
        return pd.DataFrame(columns=["director", "avg_roi", "median_roi",
                                     "avg_revenue", "movie_count"])

    df = df.rename(columns={"directors": "director"})
    agg = {"roi": ["mean", "median", "count"]}
    if "revenue" in df.columns:
        agg["revenue"] = "mean"

    result = df.groupby("director").agg(agg)
    result.columns = ["avg_roi", "median_roi", "movie_count"] + (
        ["avg_revenue"] if "revenue" in df.columns else []
    )
    result = (
        result.reset_index()
        .query("movie_count >= 2")
        .sort_values("avg_roi", ascending=False)
    )
    log.info(f"  ✓ director_roi: {result.shape}")
    return result


def build_actor_trends(master: pd.DataFrame) -> pd.DataFrame:
    """Average ROI per actor (top-billed only)."""
    log.info("Deriving actor_trends table …")

    keep = [c for c in ["roi", "revenue", "release_year"] if c in master.columns]
    df = _explode_pipe_col(master.dropna(subset=["roi"]), "top_cast", keep)

    if df.empty:
        log.warning("  actor_trends: no data — returning empty table")
        return pd.DataFrame(columns=["actor", "avg_roi", "median_roi",
                                     "avg_revenue", "movie_count"])

    df = df.rename(columns={"top_cast": "actor"})
    agg = {"roi": ["mean", "median", "count"]}
    if "revenue" in df.columns:
        agg["revenue"] = "mean"

    result = df.groupby("actor").agg(agg)
    result.columns = ["avg_roi", "median_roi", "movie_count"] + (
        ["avg_revenue"] if "revenue" in df.columns else []
    )
    result = (
        result.reset_index()
        .query("movie_count >= 2")
        .sort_values("avg_roi", ascending=False)
    )
    log.info(f"  ✓ actor_trends: {result.shape}")
    return result


def build_movie_ratings_summary(ratings: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    """Per-movie average audience rating from MovieLens."""
    log.info("Deriving movie_ratings_summary table …")
    summary = (
        ratings.groupby("movie_id")
        .agg(
            avg_ml_rating=("rating", "mean"),
            rating_count=("rating", "count"),
        )
        .reset_index()
    )
    # Attach tmdb_id so we can join back to master
    result = summary.merge(links[["movie_id", "tmdb_id"]], on="movie_id", how="left")
    log.info(f"  ✓ movie_ratings_summary: {result.shape}")
    return result


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — LOAD INTO DUCKDB
# ══════════════════════════════════════════════════════════════════════════════

def load_to_duckdb(tables: dict):
    log.info(f"Loading into DuckDB at {DB_PATH} …")

    if DB_PATH.exists():
        DB_PATH.unlink()           # fresh load every run

    con = duckdb.connect(str(DB_PATH))

    for name, df in tables.items():
        log.info(f"  Writing table: {name:35s} → {df.shape[0]:>8,} rows × {df.shape[1]} cols")
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")

    con.close()
    log.info(f"  ✓ DuckDB written: {DB_PATH}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — HEALTH SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def health_check():
    log.info("Running health check …")
    con = duckdb.connect(str(DB_PATH), read_only=True)

    tables = con.execute("SHOW TABLES").fetchall()
    print("\n" + "═" * 60)
    print("  GREENLIGHT CINEMA — DuckDB Health Summary")
    print("═" * 60)
    for (tbl,) in tables:
        count = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        cols  = len(con.execute(f"DESCRIBE {tbl}").fetchall())
        print(f"  {tbl:35s}  {count:>10,} rows   {cols:>3} cols")

    print("\n  ── Top 5 Genres by Avg ROI ──")
    rows = con.execute(
        "SELECT genre, ROUND(avg_roi,2) AS avg_roi, movie_count "
        "FROM genre_roi ORDER BY avg_roi DESC LIMIT 5"
    ).fetchall()
    for r in rows:
        print(f"    {r[0]:20s}  ROI: {r[1]:>6}   ({r[2]} films)")

    print("\n  ── Seasonal Performance ──")
    rows = con.execute(
        "SELECT release_quarter, ROUND(avg_roi,2) AS avg_roi, movie_count "
        "FROM seasonal_performance ORDER BY avg_roi DESC"
    ).fetchall()
    for r in rows:
        print(f"    {r[0]}  ROI: {r[1]:>6}   ({r[2]} films)")

    print("\n  ── Top 5 Directors by Avg ROI ──")
    rows = con.execute(
        "SELECT director, ROUND(avg_roi,2) AS avg_roi, movie_count "
        "FROM director_roi ORDER BY avg_roi DESC LIMIT 5"
    ).fetchall()
    for r in rows:
        print(f"    {r[0]:25s}  ROI: {r[1]:>6}   ({r[2]} films)")

    print("\n  ── Top 5 Actors by Avg ROI ──")
    rows = con.execute(
        "SELECT actor, ROUND(avg_roi,2) AS avg_roi, movie_count "
        "FROM actor_trends ORDER BY avg_roi DESC LIMIT 5"
    ).fetchall()
    for r in rows:
        print(f"    {r[0]:25s}  ROI: {r[1]:>6}   ({r[2]} films)")

    print("═" * 60 + "\n")
    con.close()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    log.info("══ Greenlight Cinema — Data Pipeline START ══")

    # ── Check all files exist ─────────────────────────────────────────────────
    required = ["tmdb.csv", "credits.csv", "links.csv",
                "movies.csv", "ratings.csv", "tags.csv"]
    missing = [f for f in required if not (DATA_DIR / f).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing files in {DATA_DIR}/: {missing}\n"
            "Place all CSVs in the data/ folder and re-run."
        )

    # ── Clean ─────────────────────────────────────────────────────────────────
    tmdb     = clean_tmdb()
    credits  = clean_credits()
    links    = clean_links()
    ml_movies= clean_ml_movies()
    ratings  = clean_ratings()
    tags     = clean_tags()

    # ── Master ────────────────────────────────────────────────────────────────
    master   = build_master(tmdb, credits, links, ml_movies)

    # ── Derived analytics ─────────────────────────────────────────────────────
    genre_roi       = build_genre_roi(master)
    seasonal_perf   = build_seasonal_performance(master)
    director_roi    = build_director_roi(master)
    actor_trends    = build_actor_trends(master)
    ratings_summary = build_movie_ratings_summary(ratings, links)

    # ── Load into DuckDB ──────────────────────────────────────────────────────
    tables = {
        # raw cleaned tables
        "movies":                master,
        "ratings":               ratings,
        "tags":                  tags,
        # derived analytics
        "genre_roi":             genre_roi,
        "seasonal_performance":  seasonal_perf,
        "director_roi":          director_roi,
        "actor_trends":          actor_trends,
        "movie_ratings_summary": ratings_summary,
    }
    load_to_duckdb(tables)

    # ── Health check ──────────────────────────────────────────────────────────
    health_check()

    log.info("══ Pipeline COMPLETE ══")


if __name__ == "__main__":
    main()