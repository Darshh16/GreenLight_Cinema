"""
Greenlight Cinema — DuckDB Loader v2
======================================
Loads the cleaned master dataset into DuckDB with derived analytics tables:

  1. movies              — Master table (~500K+ rows)
  2. genre_roi           — Top genres by ROI
  3. seasonal_performance— Quarterly trends
  4. director_impact     — Director ROI + ratings
  5. actor_impact        — Actor ROI + ratings
  6. emerging_talent     — New talent with high ROI (<5 films)
  7. budget_tiers        — ROI by budget tier
  8. genre_seasonal      — Best season per genre
  9. ratings_summary     — Audience rating stats per movie
  10. genre_trends       — Genre popularity by decade
  11. studio_rankings    — Production company ROI

All analytics run ONCE and persist in DuckDB — no re-computation needed.
"""

import logging
import duckdb
import pandas as pd
import numpy as np
from pathlib import Path

from greenlight.config import DB_PATH, MIN_FILMS_FOR_RANKING

log = logging.getLogger("greenlight.data.load")


# ══════════════════════════════════════════════════════════════════════════════
# DERIVED TABLE BUILDERS
# ══════════════════════════════════════════════════════════════════════════════


def _build_genre_roi(df: pd.DataFrame) -> pd.DataFrame:
    """Top genres by ROI — uses only genuine budget+revenue rows."""
    real = df[df["roi_is_real"] == True].copy()
    log.info(f"  Using {len(real):,} genuine ROI rows")

    rows = []
    for _, row in real.iterrows():
        genres = str(row.get("genre_str", ""))
        if not genres:
            continue
        for genre in genres.split("|"):
            g = genre.strip()
            if g:
                rows.append({
                    "genre": g,
                    "roi": row["roi"],
                    "revenue": row["revenue"],
                    "budget": row["budget"],
                    "vote_average": row.get("vote_average", 0),
                })

    if not rows:
        return pd.DataFrame()

    df_exp = pd.DataFrame(rows)
    result = df_exp.groupby("genre").agg(
        avg_roi=("roi", "mean"),
        median_roi=("roi", "median"),
        avg_revenue=("revenue", "mean"),
        avg_budget=("budget", "mean"),
        avg_rating=("vote_average", "mean"),
        movie_count=("roi", "count"),
    ).reset_index()

    result = result[result["movie_count"] >= MIN_FILMS_FOR_RANKING]
    result = result.sort_values("median_roi", ascending=False).reset_index(drop=True)
    log.info(f"  genre_roi: ({len(result)}, {len(result.columns)})")
    return result


def _build_seasonal(df: pd.DataFrame) -> pd.DataFrame:
    """Seasonal performance by release quarter."""
    real = df[(df["roi_is_real"] == True) & df["release_quarter"].notna()].copy()

    result = real.groupby("release_quarter").agg(
        avg_roi=("roi", "mean"),
        median_roi=("roi", "median"),
        avg_revenue=("revenue", "mean"),
        movie_count=("roi", "count"),
    ).reset_index()

    result = result.sort_values("median_roi", ascending=False).reset_index(drop=True)
    log.info(f"  seasonal_performance: ({len(result)}, {len(result.columns)})")
    return result


def _build_director_impact(df: pd.DataFrame) -> pd.DataFrame:
    """Director impact — ROI, ratings, film count."""
    real = df[df["roi_is_real"] == True].copy()

    rows = []
    for _, row in real.iterrows():
        directors = str(row.get("directors", ""))
        if not directors:
            continue
        for d in directors.split("|"):
            d = d.strip()
            if d:
                rows.append({
                    "director": d,
                    "roi": row["roi"],
                    "revenue": row["revenue"],
                    "budget": row["budget"],
                    "vote_average": row.get("vote_average", 0),
                    "imdb_rating": row.get("imdb_rating", 0),
                })

    if not rows:
        return pd.DataFrame()

    df_exp = pd.DataFrame(rows)
    result = df_exp.groupby("director").agg(
        avg_roi=("roi", "mean"),
        median_roi=("roi", "median"),
        avg_revenue=("revenue", "mean"),
        avg_budget=("budget", "mean"),
        avg_rating=("vote_average", "mean"),
        avg_imdb=("imdb_rating", "mean"),
        movie_count=("roi", "count"),
    ).reset_index()

    result = result[result["movie_count"] >= 3]
    result = result.sort_values("median_roi", ascending=False).reset_index(drop=True)
    log.info(f"  director_impact: ({len(result)}, {len(result.columns)})")
    return result


def _build_actor_impact(df: pd.DataFrame) -> pd.DataFrame:
    """Actor impact — ROI, ratings, film count."""
    real = df[df["roi_is_real"] == True].copy()

    rows = []
    for _, row in real.iterrows():
        cast = str(row.get("top_cast", ""))
        if not cast:
            continue
        for actor in cast.split("|")[:4]:  # Top 4 only
            a = actor.strip()
            if a:
                rows.append({
                    "actor": a,
                    "roi": row["roi"],
                    "revenue": row["revenue"],
                    "vote_average": row.get("vote_average", 0),
                })

    if not rows:
        return pd.DataFrame()

    df_exp = pd.DataFrame(rows)
    result = df_exp.groupby("actor").agg(
        avg_roi=("roi", "mean"),
        median_roi=("roi", "median"),
        avg_revenue=("revenue", "mean"),
        avg_rating=("vote_average", "mean"),
        movie_count=("roi", "count"),
    ).reset_index()

    result = result[result["movie_count"] >= 3]
    result = result.sort_values("median_roi", ascending=False).reset_index(drop=True)
    log.info(f"  actor_impact: ({len(result)}, {len(result.columns)})")
    return result


def _build_emerging_talent(df: pd.DataFrame) -> pd.DataFrame:
    """Emerging talent — directors/actors with <5 films but high ROI."""
    real = df[df["roi_is_real"] == True].copy()

    rows = []
    # Directors
    for _, row in real.iterrows():
        directors = str(row.get("directors", ""))
        for d in directors.split("|"):
            d = d.strip()
            if d:
                rows.append({"name": d, "role": "director", "roi": row["roi"],
                             "revenue": row["revenue"],
                             "vote_average": row.get("vote_average", 0),
                             "release_year": row.get("release_year")})
    # Actors
    for _, row in real.iterrows():
        cast = str(row.get("top_cast", ""))
        for a in cast.split("|")[:3]:
            a = a.strip()
            if a:
                rows.append({"name": a, "role": "actor", "roi": row["roi"],
                             "revenue": row["revenue"],
                             "vote_average": row.get("vote_average", 0),
                             "release_year": row.get("release_year")})

    if not rows:
        return pd.DataFrame()

    df_exp = pd.DataFrame(rows)
    result = df_exp.groupby(["name", "role"]).agg(
        avg_roi=("roi", "mean"),
        median_roi=("roi", "median"),
        avg_revenue=("revenue", "mean"),
        avg_rating=("vote_average", "mean"),
        movie_count=("roi", "count"),
        latest_year=("release_year", "max"),
    ).reset_index()

    # Emerging = 2-4 films AND high ROI AND recent
    result = result[
        (result["movie_count"] >= 2) &
        (result["movie_count"] <= 4) &
        (result["median_roi"] >= 2.0)
    ]
    result = result.sort_values("median_roi", ascending=False).head(100).reset_index(drop=True)
    log.info(f"  emerging_talent: ({len(result)}, {len(result.columns)})")
    return result


def _build_budget_tiers(df: pd.DataFrame) -> pd.DataFrame:
    """Budget tier analysis."""
    real = df[(df["roi_is_real"] == True) & (df["budget_tier"] != "Unknown")].copy()

    result = real.groupby("budget_tier").agg(
        avg_roi=("roi", "mean"),
        median_roi=("roi", "median"),
        avg_revenue=("revenue", "mean"),
        avg_budget=("budget", "mean"),
        avg_rating=("vote_average", "mean"),
        movie_count=("roi", "count"),
    ).reset_index()
    result.columns = ["tier", "avg_roi", "median_roi", "avg_revenue",
                       "avg_budget", "avg_rating", "movie_count"]
    log.info(f"  budget_tiers: ({len(result)}, {len(result.columns)})")
    return result


def _build_genre_seasonal(df: pd.DataFrame) -> pd.DataFrame:
    """Genre x Season cross-analysis."""
    real = df[(df["roi_is_real"] == True) & df["release_quarter"].notna()].copy()

    rows = []
    for _, row in real.iterrows():
        genres = str(row.get("genre_str", ""))
        for genre in genres.split("|"):
            g = genre.strip()
            if g:
                rows.append({
                    "genre": g,
                    "release_quarter": row["release_quarter"],
                    "roi": row["roi"],
                    "revenue": row["revenue"],
                })

    if not rows:
        return pd.DataFrame()

    df_exp = pd.DataFrame(rows)
    result = df_exp.groupby(["genre", "release_quarter"]).agg(
        median_roi=("roi", "median"),
        avg_revenue=("revenue", "mean"),
        movie_count=("roi", "count"),
    ).reset_index()

    result = result[result["movie_count"] >= 3]
    log.info(f"  genre_seasonal: ({len(result)}, {len(result.columns)})")
    return result


def _build_genre_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Genre trends by decade."""
    valid = df[df["release_year"].notna()].copy()
    valid["decade"] = (valid["release_year"] // 10 * 10).astype(int)

    rows = []
    for _, row in valid.iterrows():
        genres = str(row.get("genre_str", ""))
        for genre in genres.split("|"):
            g = genre.strip()
            if g:
                rows.append({
                    "genre": g,
                    "decade": row["decade"],
                    "vote_average": row.get("vote_average", 0),
                    "revenue": row.get("revenue", 0),
                })

    if not rows:
        return pd.DataFrame()

    df_exp = pd.DataFrame(rows)
    result = df_exp.groupby(["genre", "decade"]).agg(
        movie_count=("genre", "count"),
        avg_rating=("vote_average", "mean"),
        avg_revenue=("revenue", "mean"),
    ).reset_index()

    result = result[result["movie_count"] >= 5]
    result = result.sort_values(["genre", "decade"]).reset_index(drop=True)
    log.info(f"  genre_trends: ({len(result)}, {len(result.columns)})")
    return result


def _build_studio_rankings(df: pd.DataFrame) -> pd.DataFrame:
    """Production company ROI rankings."""
    real = df[df["roi_is_real"] == True].copy()

    rows = []
    for _, row in real.iterrows():
        companies = str(row.get("production_companies", ""))
        if not companies or companies == "nan":
            continue
        # Handle both pipe-separated and list formats
        company_list = _parse_companies(companies)
        for co in company_list[:3]:  # Top 3 companies per film
            if co:
                rows.append({
                    "studio": co,
                    "roi": row["roi"],
                    "revenue": row["revenue"],
                    "budget": row["budget"],
                })

    if not rows:
        return pd.DataFrame()

    df_exp = pd.DataFrame(rows)
    result = df_exp.groupby("studio").agg(
        avg_roi=("roi", "mean"),
        median_roi=("roi", "median"),
        avg_revenue=("revenue", "mean"),
        avg_budget=("budget", "mean"),
        movie_count=("roi", "count"),
    ).reset_index()

    result = result[result["movie_count"] >= 5]
    result = result.sort_values("median_roi", ascending=False).head(50).reset_index(drop=True)
    log.info(f"  studio_rankings: ({len(result)}, {len(result.columns)})")
    return result


def _parse_companies(val) -> list:
    """Parse production company strings."""
    if pd.isna(val) or str(val).strip() in ("", "nan", "[]"):
        return []
    s = str(val).strip()
    # Try JSON list
    try:
        import json
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return [item.get("name", str(item)) if isinstance(item, dict) else str(item)
                    for item in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    # Try ast
    try:
        import ast
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list):
            return [str(x).strip().strip("'\"") for x in parsed]
    except (ValueError, SyntaxError):
        pass
    # Comma-separated
    if "," in s:
        return [x.strip() for x in s.split(",") if x.strip()]
    return [s] if s else []


def _build_ratings_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-movie rating summary."""
    cols = ["tmdb_id", "vote_average", "vote_count"]
    extra = []
    if "ml_avg_rating" in df.columns:
        extra += ["ml_avg_rating", "ml_rating_count"]
    if "imdb_rating" in df.columns:
        extra.append("imdb_rating")
    if "meta_score" in df.columns:
        extra.append("meta_score")

    result = df[cols + extra].copy()
    result = result[result["vote_count"].notna() & (result["vote_count"] > 0)]
    log.info(f"  ratings_summary: ({len(result)}, {len(result.columns)})")
    return result


# ══════════════════════════════════════════════════════════════════════════════
# MAIN LOADER
# ══════════════════════════════════════════════════════════════════════════════


def run_load_pipeline(cleaned_data: dict):
    """
    Build all derived tables and write everything to DuckDB.

    Args:
        cleaned_data: dict from run_cleaning_pipeline() with 'master' key
    """
    log.info("== DuckDB Load Pipeline v2 START ==")

    df = cleaned_data["master"]

    # Build derived tables
    log.info("Building derived analytics tables ...")
    tables = {
        "movies": df,
        "genre_roi": _build_genre_roi(df),
        "seasonal_performance": _build_seasonal(df),
        "director_impact": _build_director_impact(df),
        "actor_impact": _build_actor_impact(df),
        "emerging_talent": _build_emerging_talent(df),
        "budget_tiers": _build_budget_tiers(df),
        "genre_seasonal": _build_genre_seasonal(df),
        "genre_trends": _build_genre_trends(df),
        "studio_rankings": _build_studio_rankings(df),
        "ratings_summary": _build_ratings_summary(df),
    }

    # Write to DuckDB
    log.info(f"Writing to DuckDB at {DB_PATH} ...")

    # Remove old DB
    if DB_PATH.exists():
        DB_PATH.unlink()

    con = duckdb.connect(str(DB_PATH))

    for table_name, table_df in tables.items():
        if table_df is None or len(table_df) == 0:
            log.warning(f"  Skipping empty table: {table_name}")
            continue
        con.execute(f"DROP TABLE IF EXISTS {table_name}")
        con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM table_df")
        rows = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        cols = len(con.execute(f"DESCRIBE {table_name}").fetchall())
        log.info(f"  {table_name:30s}  {rows:>10,} rows  {cols:>3} cols")

    con.close()
    log.info(f"  DuckDB written: {DB_PATH}")

    # Health check
    health_check()

    log.info("== DuckDB Load Pipeline v2 COMPLETE ==")


def health_check():
    """Quick DuckDB health check."""
    log.info("Running health check ...")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    tables = con.execute("SHOW TABLES").fetchall()

    def _safe(s, maxlen=30):
        """Make string safe for cp1252 console output."""
        s = str(s)
        try:
            s.encode("cp1252")
        except (UnicodeEncodeError, UnicodeDecodeError):
            s = s.encode("ascii", errors="replace").decode("ascii")
        return s[:maxlen].ljust(maxlen)

    print("\n" + "=" * 65)
    print("  GREENLIGHT CINEMA -- DuckDB Health Summary v2")
    print("=" * 65)

    for (tbl,) in tables:
        count = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        cols = len(con.execute(f"DESCRIBE {tbl}").fetchall())
        print(f"  {tbl:35s}  {count:>10,} rows   {cols:>3} cols")

    # Top 10 genres
    print("\n  -- Top 10 Genres by Median ROI --")
    rows = con.execute(
        "SELECT genre, ROUND(median_roi,2), ROUND(avg_roi,2), movie_count, ROUND(avg_rating,1) "
        "FROM genre_roi ORDER BY median_roi DESC LIMIT 10"
    ).fetchall()
    for r in rows:
        print(f"    {_safe(r[0], 20)}  Median: {r[1]:>6}x  Avg: {r[2]:>6}x  ({r[3]} films)  Rating: {r[4]}")

    # Seasonal
    print("\n  -- Seasonal Performance --")
    rows = con.execute(
        "SELECT release_quarter, ROUND(median_roi,2), movie_count "
        "FROM seasonal_performance ORDER BY median_roi DESC"
    ).fetchall()
    for r in rows:
        print(f"    {r[0]}  Median ROI: {r[1]:>6}x  ({r[2]} films)")

    # Top 5 Directors
    print("\n  -- Top 5 Directors --")
    rows = con.execute(
        "SELECT director, ROUND(median_roi,2), movie_count, ROUND(avg_rating,1) "
        "FROM director_impact ORDER BY median_roi DESC LIMIT 5"
    ).fetchall()
    for r in rows:
        print(f"    {_safe(r[0])}  ROI: {r[1]:>6}x  ({r[2]} films)  Rating: {r[3]}")

    # Top 5 Actors
    print("\n  -- Top 5 Actors --")
    rows = con.execute(
        "SELECT actor, ROUND(median_roi,2), movie_count, ROUND(avg_rating,1) "
        "FROM actor_impact ORDER BY median_roi DESC LIMIT 5"
    ).fetchall()
    for r in rows:
        print(f"    {_safe(r[0])}  ROI: {r[1]:>6}x  ({r[2]} films)  Rating: {r[3]}")

    # Emerging Talent
    try:
        print("\n  -- Emerging Talent (Top 5) --")
        rows = con.execute(
            "SELECT name, role, ROUND(median_roi,2), movie_count "
            "FROM emerging_talent ORDER BY median_roi DESC LIMIT 5"
        ).fetchall()
        for r in rows:
            print(f"    {_safe(r[0])}  [{r[1]}]  ROI: {r[2]:>6}x  ({r[3]} films)")
    except Exception:
        pass

    print("=" * 65 + "\n")
    con.close()

