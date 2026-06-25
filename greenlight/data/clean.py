"""
Greenlight Cinema — Data Cleaning Pipeline v2
================================================
Merges ALL 9 datasets into a single master table:

  Primary:   IMDB TMDB Big Dataset (1M) — richest source (42 cols)
  Enrich:    tmdb.csv — overviews, taglines, keywords
  Credits:   credits.csv — structured cast/crew JSON
  Clean:     data_movies_clean.csv — pre-cleaned budget/revenue
  Bollywood: bollywood_full.csv — Indian cinema coverage
  Ratings:   ratings.csv — 33M audience ratings (aggregated)
  Links:     links.csv — MovieLens ↔ TMDB ID mapping
  Movies:    movies.csv — MovieLens genre tags
  Tags:      tags.csv — user-generated keywords

Goal: ~500K+ valid rows with legitimate data.
"""

import logging
import json
import ast
import re
from pathlib import Path

import pandas as pd
import numpy as np
from tqdm import tqdm

from greenlight.config import DATA_DIR, ROI_OUTLIER_CAP, BUDGET_TIERS

log = logging.getLogger("greenlight.data.clean")


# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════


def _safe_json_list(val) -> list:
    """Parse a JSON-like string into a list safely."""
    if pd.isna(val) or val == "" or val == "[]":
        return []
    if isinstance(val, list):
        return val
    s = str(val).strip()
    # Try JSON first
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return parsed
        return [parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    # Try ast.literal_eval
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list):
            return parsed
        return [parsed]
    except (ValueError, SyntaxError):
        pass
    # Pipe-separated
    if "|" in s:
        return [x.strip() for x in s.split("|") if x.strip()]
    # Comma-separated (only if no complex JSON)
    if "," in s and "{" not in s:
        return [x.strip() for x in s.split(",") if x.strip()]
    return [s] if s else []


def _extract_genre_names(val) -> str:
    """Extract genre names from various formats into pipe-separated string."""
    items = _safe_json_list(val)
    if not items:
        return ""
    names = []
    for item in items:
        if isinstance(item, dict):
            names.append(item.get("name", ""))
        elif isinstance(item, str):
            names.append(item.strip())
    return "|".join([n for n in names if n])


def _extract_keyword_names(val) -> str:
    """Extract keyword names from JSON/list."""
    items = _safe_json_list(val)
    if not items:
        return ""
    names = []
    for item in items:
        if isinstance(item, dict):
            names.append(item.get("name", ""))
        elif isinstance(item, str):
            names.append(item.strip().strip("'\""))
    return "|".join([n for n in names if n][:20])  # Cap at 20


def _parse_cast_json(val, max_actors: int = 5) -> str:
    """Parse credits.csv cast JSON into top actor names."""
    items = _safe_json_list(val)
    if not items:
        return ""
    names = []
    for item in items[:max_actors]:
        if isinstance(item, dict):
            names.append(item.get("name", ""))
        elif isinstance(item, str):
            names.append(item.strip())
    return "|".join([n for n in names if n])


def _parse_directors(val) -> str:
    """Parse credits.csv crew JSON for directors."""
    items = _safe_json_list(val)
    if not items:
        return ""
    directors = []
    for item in items:
        if isinstance(item, dict):
            if item.get("job") == "Director" or item.get("department") == "Directing":
                directors.append(item.get("name", ""))
    return "|".join([d for d in directors if d])


def _assign_budget_tier(budget: float) -> str:
    """Assign budget tier based on thresholds."""
    if pd.isna(budget) or budget <= 0:
        return "Unknown"
    for tier, (lo, hi) in BUDGET_TIERS.items():
        if lo <= budget < hi:
            return tier
    return "Blockbuster"


def _extract_release_info(date_str):
    """Extract year, month, quarter from date string."""
    if pd.isna(date_str) or str(date_str).strip() == "":
        return None, None, None
    s = str(date_str).strip()
    # Try YYYY-MM-DD
    match = re.match(r"(\d{4})-(\d{1,2})", s)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        quarter = f"Q{(month - 1) // 3 + 1}"
        return year, month, quarter
    # Try just year
    match = re.match(r"(\d{4})", s)
    if match:
        return int(match.group(1)), None, None
    return None, None, None


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════


def run_cleaning_pipeline() -> dict:
    """
    Run the full data cleaning and merging pipeline.

    Returns:
        dict with keys: 'master', 'ratings_agg', 'tags_agg'
    """
    log.info("== Greenlight Cinema -- Data Cleaning Pipeline v2 START ==")

    # ── Step 1: Load IMDB TMDB Big Dataset (primary source) ──────────────────
    log.info("Step 1: Loading IMDB TMDB Big Dataset (1M) ...")
    imdb_path = DATA_DIR / "IMDB TMDB Movie Metadata Big Dataset (1M).csv"
    df_imdb = pd.read_csv(imdb_path, encoding="utf-8", on_bad_lines="skip",
                          low_memory=False)
    log.info(f"  Raw: {len(df_imdb):,} rows x {len(df_imdb.columns)} cols")

    # Standardize column names
    df_imdb = df_imdb.rename(columns={
        "id": "tmdb_id",
        "Director": "director",
        "Writer": "writer",
        "Star1": "star1",
        "Star2": "star2",
        "Star3": "star3",
        "Star4": "star4",
        "IMDB_Rating": "imdb_rating",
        "Meta_score": "meta_score",
        "AverageRating": "avg_rating",
        "Director_of_Photography": "dop",
        "Producers": "producers",
        "Music_Composer": "music_composer",
        "Cast_list": "cast_list",
        "overview_sentiment": "sentiment",
        "all_combined_keywords": "combined_keywords",
        "genres_list": "genres_list_str",
    })

    # Core filters
    df_imdb["tmdb_id"] = pd.to_numeric(df_imdb["tmdb_id"], errors="coerce")
    df_imdb = df_imdb.dropna(subset=["tmdb_id"])
    df_imdb["tmdb_id"] = df_imdb["tmdb_id"].astype(int)

    # Filter: Released only
    if "status" in df_imdb.columns:
        before = len(df_imdb)
        df_imdb = df_imdb[df_imdb["status"] == "Released"]
        log.info(f"  Released filter: {len(df_imdb):,} rows (dropped {before - len(df_imdb):,})")

    # Filter: Non-adult
    if "adult" in df_imdb.columns:
        df_imdb = df_imdb[df_imdb["adult"].astype(str).str.lower() != "true"]
        log.info(f"  Adult filter: {len(df_imdb):,} rows")

    # Numeric conversions
    for col in ["budget", "revenue", "runtime", "vote_count", "vote_average",
                "popularity", "imdb_rating", "meta_score", "sentiment", "release_year"]:
        if col in df_imdb.columns:
            df_imdb[col] = pd.to_numeric(df_imdb[col], errors="coerce")

    # Filter: Must have title
    df_imdb = df_imdb[df_imdb["title"].notna() & (df_imdb["title"].str.strip() != "")]
    log.info(f"  Title filter: {len(df_imdb):,} rows")

    # Drop exact duplicates by tmdb_id (keep first)
    df_imdb = df_imdb.drop_duplicates(subset=["tmdb_id"], keep="first")
    log.info(f"  Deduplicated: {len(df_imdb):,} rows")

    # ── Step 2: Enrich with tmdb.csv (overviews, taglines, keywords) ─────────
    log.info("Step 2: Enriching with tmdb.csv ...")
    tmdb_path = DATA_DIR / "tmdb.csv"
    df_tmdb = pd.read_csv(tmdb_path, encoding="utf-8", on_bad_lines="skip",
                          low_memory=False,
                          usecols=["id", "overview", "tagline", "genres", "keywords"])
    df_tmdb = df_tmdb.rename(columns={"id": "tmdb_id"})
    df_tmdb["tmdb_id"] = pd.to_numeric(df_tmdb["tmdb_id"], errors="coerce")
    df_tmdb = df_tmdb.dropna(subset=["tmdb_id"])
    df_tmdb["tmdb_id"] = df_tmdb["tmdb_id"].astype(int)
    df_tmdb = df_tmdb.drop_duplicates(subset=["tmdb_id"], keep="first")
    log.info(f"  tmdb.csv: {len(df_tmdb):,} rows loaded")

    # Fill missing overviews and taglines
    df_imdb = df_imdb.merge(
        df_tmdb[["tmdb_id", "overview", "tagline", "genres", "keywords"]].rename(
            columns={"overview": "overview_tmdb", "tagline": "tagline_tmdb",
                     "genres": "genres_json", "keywords": "keywords_json"}
        ),
        on="tmdb_id", how="left"
    )

    # Fill gaps
    if "overview" in df_imdb.columns:
        df_imdb["overview"] = df_imdb["overview"].fillna(df_imdb["overview_tmdb"])
    else:
        df_imdb["overview"] = df_imdb["overview_tmdb"]

    if "tagline" in df_imdb.columns:
        df_imdb["tagline"] = df_imdb["tagline"].fillna(df_imdb["tagline_tmdb"])
    else:
        df_imdb["tagline"] = df_imdb["tagline_tmdb"]

    df_imdb.drop(columns=["overview_tmdb", "tagline_tmdb"], inplace=True, errors="ignore")
    log.info(f"  Overviews filled: {df_imdb['overview'].notna().sum():,} / {len(df_imdb):,}")

    # ── Step 3: Merge credits.csv (cast/crew JSON) ──────────────────────────
    log.info("Step 3: Merging credits.csv ...")
    credits_path = DATA_DIR / "credits.csv"
    df_credits = pd.read_csv(credits_path, encoding="utf-8", on_bad_lines="skip")
    df_credits = df_credits.rename(columns={"id": "tmdb_id"})
    df_credits["tmdb_id"] = pd.to_numeric(df_credits["tmdb_id"], errors="coerce")
    df_credits = df_credits.dropna(subset=["tmdb_id"])
    df_credits["tmdb_id"] = df_credits["tmdb_id"].astype(int)
    log.info(f"  credits.csv: {len(df_credits):,} rows")

    # Parse cast and crew
    log.info("  Parsing cast & crew (this may take a moment) ...")
    df_credits["credits_cast"] = df_credits["cast"].apply(_parse_cast_json)
    df_credits["credits_directors"] = df_credits["crew"].apply(_parse_directors)

    df_imdb = df_imdb.merge(
        df_credits[["tmdb_id", "credits_cast", "credits_directors"]],
        on="tmdb_id", how="left"
    )

    # Merge star columns into a unified top_cast
    star_cols = [c for c in ["star1", "star2", "star3", "star4"] if c in df_imdb.columns]
    if star_cols:
        def _merge_stars(row):
            stars = []
            for col in star_cols:
                if pd.notna(row.get(col)) and str(row[col]).strip():
                    stars.append(str(row[col]).strip())
            credits = str(row.get("credits_cast", "")) if pd.notna(row.get("credits_cast")) else ""
            if credits:
                for s in credits.split("|"):
                    if s.strip() and s.strip() not in stars:
                        stars.append(s.strip())
            return "|".join(stars[:6])  # Top 6

        df_imdb["top_cast"] = df_imdb.apply(_merge_stars, axis=1)
    else:
        df_imdb["top_cast"] = df_imdb.get("credits_cast", "")

    # Merge directors
    if "director" in df_imdb.columns:
        df_imdb["directors"] = df_imdb.apply(
            lambda r: str(r["director"]).strip()
            if pd.notna(r.get("director")) and str(r["director"]).strip()
            else (str(r["credits_directors"]).strip() if pd.notna(r.get("credits_directors")) else ""),
            axis=1
        )
    else:
        df_imdb["directors"] = df_imdb.get("credits_directors", "")

    log.info(f"  Directors populated: {(df_imdb['directors'] != '').sum():,}")
    log.info(f"  Cast populated: {(df_imdb['top_cast'] != '').sum():,}")

    # ── Step 4: Merge data_movies_clean.csv (budget/revenue fill) ────────────
    log.info("Step 4: Merging data_movies_clean.csv for budget/revenue gaps ...")
    clean_path = DATA_DIR / "data_movies_clean.csv"
    df_clean = pd.read_csv(clean_path, encoding="utf-8", on_bad_lines="skip",
                           low_memory=False,
                           usecols=["id", "budget", "revenue", "runtime",
                                    "vote_average", "vote_count", "genre_names",
                                    "production_company_names"])
    df_clean = df_clean.rename(columns={
        "id": "tmdb_id", "budget": "budget_clean", "revenue": "revenue_clean",
        "runtime": "runtime_clean", "vote_average": "va_clean",
        "vote_count": "vc_clean", "genre_names": "genres_clean",
        "production_company_names": "companies_clean",
    })
    df_clean["tmdb_id"] = pd.to_numeric(df_clean["tmdb_id"], errors="coerce")
    df_clean = df_clean.dropna(subset=["tmdb_id"])
    df_clean["tmdb_id"] = df_clean["tmdb_id"].astype(int)
    df_clean = df_clean.drop_duplicates(subset=["tmdb_id"], keep="first")
    log.info(f"  data_movies_clean.csv: {len(df_clean):,} rows")

    df_imdb = df_imdb.merge(df_clean, on="tmdb_id", how="left")

    # Fill budget/revenue gaps
    for src, dst in [("budget_clean", "budget"), ("revenue_clean", "revenue"),
                     ("runtime_clean", "runtime"), ("va_clean", "vote_average"),
                     ("vc_clean", "vote_count")]:
        if dst in df_imdb.columns:
            mask = df_imdb[dst].isna() | (df_imdb[dst] == 0)
            if src in df_imdb.columns:
                df_imdb.loc[mask, dst] = df_imdb.loc[mask, src]
        elif src in df_imdb.columns:
            df_imdb[dst] = df_imdb[src]
    df_imdb.drop(columns=["budget_clean", "revenue_clean", "runtime_clean",
                          "va_clean", "vc_clean"], inplace=True, errors="ignore")
    log.info(f"  Budget filled: {(df_imdb['budget'].notna() & (df_imdb['budget'] > 0)).sum():,}")

    # ── Step 5: Merge Bollywood dataset ──────────────────────────────────────
    log.info("Step 5: Integrating bollywood_full.csv ...")
    bolly_path = DATA_DIR / "bollywood_full.csv"
    df_bolly = pd.read_csv(bolly_path, encoding="utf-8", on_bad_lines="skip")
    log.info(f"  bollywood_full.csv: {len(df_bolly):,} rows")

    # Standardize Bollywood to match schema
    bolly_records = []
    max_tmdb_id = int(df_imdb["tmdb_id"].max()) + 1
    for i, row in df_bolly.iterrows():
        title = str(row.get("title", "")).strip()
        if not title:
            continue
        # Check if already in master by title
        record = {
            "tmdb_id": max_tmdb_id + i,
            "title": title,
            "overview": str(row.get("summary", "")).strip() if pd.notna(row.get("summary")) else "",
            "tagline": str(row.get("tagline", "")).strip() if pd.notna(row.get("tagline")) else "",
            "genre_str": str(row.get("genres", "")).replace("|", "|") if pd.notna(row.get("genres")) else "",
            "top_cast": str(row.get("actors", "")).replace("|", "|")[:200] if pd.notna(row.get("actors")) else "",
            "directors": "",
            "runtime": pd.to_numeric(row.get("runtime"), errors="coerce"),
            "vote_average": pd.to_numeric(row.get("imdb_rating"), errors="coerce"),
            "vote_count": pd.to_numeric(row.get("imdb_votes"), errors="coerce"),
            "original_language": "hi",
            "budget": 0,
            "revenue": 0,
            "source": "bollywood",
        }
        # Extract year from release_date
        rd = str(row.get("year_of_release", ""))
        match = re.match(r"(\d{4})", rd)
        if match:
            record["release_year"] = int(match.group(1))
        bolly_records.append(record)

    if bolly_records:
        df_bolly_std = pd.DataFrame(bolly_records)
        # Only add Bollywood films not already in master (by title match)
        existing_titles = set(df_imdb["title"].str.lower().str.strip())
        df_bolly_std = df_bolly_std[~df_bolly_std["title"].str.lower().str.strip().isin(existing_titles)]
        log.info(f"  Adding {len(df_bolly_std):,} unique Bollywood films")

    # ── Step 6: Process genres ───────────────────────────────────────────────
    log.info("Step 6: Processing genres ...")

    # Build genre_str from multiple sources
    def _build_genre_str(row):
        # Priority: genres_list_str > genres_json > genres_clean > genre_str
        for col in ["genres_list_str", "genres_json", "genres_clean"]:
            val = row.get(col)
            if pd.notna(val) and str(val).strip() and str(val).strip() != "[]":
                result = _extract_genre_names(val)
                if result:
                    return result
        # Fallback: existing genre_str
        gs = row.get("genre_str")
        if pd.notna(gs) and str(gs).strip():
            return str(gs).strip()
        return ""

    df_imdb["genre_str"] = df_imdb.apply(_build_genre_str, axis=1)
    log.info(f"  Genre populated: {(df_imdb['genre_str'] != '').sum():,} / {len(df_imdb):,}")

    # Process keywords
    def _build_keyword_str(row):
        for col in ["combined_keywords", "keywords_json"]:
            val = row.get(col)
            if pd.notna(val) and str(val).strip() and str(val).strip() != "[]":
                result = _extract_keyword_names(val)
                if result:
                    return result
        return ""

    df_imdb["keyword_str"] = df_imdb.apply(_build_keyword_str, axis=1)

    # ── Step 7: Extract release info ─────────────────────────────────────────
    log.info("Step 7: Processing release dates ...")
    if "release_year" not in df_imdb.columns or df_imdb["release_year"].isna().sum() > len(df_imdb) * 0.5:
        release_info = df_imdb["release_date"].apply(
            lambda x: pd.Series(_extract_release_info(x),
                                index=["release_year_ext", "release_month", "release_quarter"])
        )
        if "release_year" in df_imdb.columns:
            df_imdb["release_year"] = df_imdb["release_year"].fillna(release_info["release_year_ext"])
        else:
            df_imdb["release_year"] = release_info["release_year_ext"]
        df_imdb["release_month"] = release_info["release_month"]
        df_imdb["release_quarter"] = release_info["release_quarter"]
    else:
        # Build month/quarter from release_date
        release_info = df_imdb["release_date"].apply(
            lambda x: pd.Series(_extract_release_info(x),
                                index=["_yr", "release_month", "release_quarter"])
        )
        df_imdb["release_month"] = release_info["release_month"]
        df_imdb["release_quarter"] = release_info["release_quarter"]

    # ── Step 8: Compute ROI ──────────────────────────────────────────────────
    log.info("Step 8: Computing ROI and budget tiers ...")
    df_imdb["budget"] = df_imdb["budget"].fillna(0)
    df_imdb["revenue"] = df_imdb["revenue"].fillna(0)

    # Flag genuine budget+revenue rows
    df_imdb["roi_is_real"] = (df_imdb["budget"] > 1000) & (df_imdb["revenue"] > 1000)
    real_count = df_imdb["roi_is_real"].sum()
    log.info(f"  Genuine budget+revenue: {real_count:,} rows ({real_count/len(df_imdb)*100:.1f}%)")

    # Compute ROI
    df_imdb["roi"] = np.where(
        df_imdb["roi_is_real"],
        df_imdb["revenue"] / df_imdb["budget"],
        np.nan
    )
    # Cap outliers
    df_imdb["roi"] = df_imdb["roi"].clip(upper=ROI_OUTLIER_CAP)

    # Budget tiers
    df_imdb["budget_tier"] = df_imdb["budget"].apply(_assign_budget_tier)

    # ── Step 9: Build ratings aggregates ─────────────────────────────────────
    log.info("Step 9: Aggregating ratings (33M+ rows) ...")
    ratings_path = DATA_DIR / "ratings.csv"
    links_path = DATA_DIR / "links.csv"

    # Load links for movieId -> tmdbId mapping
    df_links = pd.read_csv(links_path)
    df_links["tmdbId"] = pd.to_numeric(df_links["tmdbId"], errors="coerce")
    df_links = df_links.dropna(subset=["tmdbId"])
    df_links["tmdbId"] = df_links["tmdbId"].astype(int)

    # Chunked ratings aggregation
    chunk_size = 5_000_000
    ratings_chunks = []
    for i, chunk in enumerate(pd.read_csv(ratings_path, chunksize=chunk_size)):
        log.info(f"  Processing ratings chunk {i+1} ({len(chunk):,} rows) ...")
        agg = chunk.groupby("movieId").agg(
            ml_avg_rating=("rating", "mean"),
            ml_rating_count=("rating", "count"),
        ).reset_index()
        ratings_chunks.append(agg)

    ratings_agg = pd.concat(ratings_chunks).groupby("movieId").agg(
        ml_avg_rating=("ml_avg_rating", "mean"),
        ml_rating_count=("ml_rating_count", "sum"),
    ).reset_index()

    # Map movieId -> tmdbId
    ratings_agg = ratings_agg.merge(df_links[["movieId", "tmdbId"]], on="movieId", how="inner")
    ratings_agg = ratings_agg.rename(columns={"tmdbId": "tmdb_id"})
    ratings_agg = ratings_agg.drop(columns=["movieId"])
    log.info(f"  Ratings aggregated: {len(ratings_agg):,} movies with audience scores")

    # Merge into master
    df_imdb = df_imdb.merge(ratings_agg, on="tmdb_id", how="left")

    # ── Step 10: Tags aggregation ────────────────────────────────────────────
    log.info("Step 10: Aggregating user tags ...")
    tags_path = DATA_DIR / "tags.csv"
    df_tags = pd.read_csv(tags_path, encoding="utf-8", on_bad_lines="skip",
                          usecols=["movieId", "tag"])
    df_tags = df_tags.dropna(subset=["tag"])
    df_tags["tag"] = df_tags["tag"].astype(str).str.strip().str.lower()
    df_tags = df_tags[df_tags["tag"] != ""]

    tags_agg = df_tags.groupby("movieId")["tag"].apply(
        lambda x: "|".join(x.unique()[:15])
    ).reset_index()
    tags_agg.columns = ["movieId", "user_tags"]

    # Map to tmdb_id
    tags_agg = tags_agg.merge(df_links[["movieId", "tmdbId"]], on="movieId", how="inner")
    tags_agg = tags_agg.rename(columns={"tmdbId": "tmdb_id"})
    tags_agg = tags_agg.drop(columns=["movieId"])

    df_imdb = df_imdb.merge(tags_agg, on="tmdb_id", how="left")
    log.info(f"  Tags merged: {df_imdb['user_tags'].notna().sum():,} movies with user tags")

    # ── Step 11: Append Bollywood ────────────────────────────────────────────
    if bolly_records and len(df_bolly_std) > 0:
        log.info(f"Step 11: Appending {len(df_bolly_std):,} Bollywood films ...")
        # Align columns
        for col in df_imdb.columns:
            if col not in df_bolly_std.columns:
                df_bolly_std[col] = np.nan
        df_bolly_std = df_bolly_std[df_imdb.columns]
        df_imdb = pd.concat([df_imdb, df_bolly_std], ignore_index=True)

    # ── Step 12: Final quality filters ───────────────────────────────────────
    log.info("Step 12: Final quality filters ...")

    # Must have title
    df_imdb = df_imdb[df_imdb["title"].notna() & (df_imdb["title"].str.strip() != "")]

    # Runtime > 0 (if available, but don't drop if missing)
    has_runtime = df_imdb["runtime"].notna() & (df_imdb["runtime"] > 0)
    no_runtime = df_imdb["runtime"].isna()
    df_imdb = df_imdb[has_runtime | no_runtime]

    # Release year sanity: 1900-2030
    df_imdb = df_imdb[
        df_imdb["release_year"].isna() |
        ((df_imdb["release_year"] >= 1900) & (df_imdb["release_year"] <= 2030))
    ]

    # Final dedup on tmdb_id
    df_imdb = df_imdb.drop_duplicates(subset=["tmdb_id"], keep="first")

    log.info(f"  Final master shape: {len(df_imdb):,} rows x {len(df_imdb.columns)} cols")

    # ── Step 13: Select final columns ────────────────────────────────────────
    log.info("Step 13: Selecting final columns ...")
    keep_cols = [
        "tmdb_id", "title", "overview", "tagline",
        "genre_str", "keyword_str", "top_cast", "directors",
        "writer", "dop", "producers", "music_composer",
        "original_language", "runtime",
        "budget", "revenue", "roi", "roi_is_real", "budget_tier",
        "vote_average", "vote_count", "popularity",
        "imdb_rating", "meta_score", "sentiment",
        "imdb_id",
        "release_year", "release_month", "release_quarter",
        "ml_avg_rating", "ml_rating_count",
        "user_tags",
        "companies_clean",
    ]
    # Only keep columns that exist
    final_cols = [c for c in keep_cols if c in df_imdb.columns]
    df_master = df_imdb[final_cols].copy()

    # Rename for clarity
    if "companies_clean" in df_master.columns:
        df_master = df_master.rename(columns={"companies_clean": "production_companies"})

    log.info(f"  Master table: {len(df_master):,} rows x {len(df_master.columns)} cols")
    log.info(f"  With overview: {df_master['overview'].notna().sum():,}")
    log.info(f"  With genres: {(df_master['genre_str'] != '').sum():,}")
    log.info(f"  With directors: {(df_master['directors'] != '').sum():,}")
    log.info(f"  With cast: {(df_master['top_cast'] != '').sum():,}")
    log.info(f"  With real ROI: {df_master['roi_is_real'].sum():,}")

    log.info("== Data Cleaning Pipeline v2 COMPLETE ==")

    return {
        "master": df_master,
        "ratings_agg": ratings_agg,
    }
