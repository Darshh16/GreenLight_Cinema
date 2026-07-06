"""
Greenlight Cinema — Analytics Engine v2
=========================================
DuckDB-backed analytics with expanded query methods.
All queries run against pre-computed tables — fast.
"""

import logging
from dataclasses import dataclass
import duckdb

from greenlight.config import DB_PATH

log = logging.getLogger("greenlight.analytics.engine")


@dataclass
class GenreROI:
    genre: str
    avg_roi: float
    median_roi: float
    avg_revenue: float
    avg_budget: float
    avg_rating: float
    movie_count: int

@dataclass
class SeasonalTrend:
    release_quarter: str
    avg_roi: float
    median_roi: float
    avg_revenue: float
    movie_count: int

@dataclass
class TalentImpact:
    name: str
    avg_roi: float
    median_roi: float
    avg_revenue: float
    avg_rating: float
    movie_count: int

@dataclass
class EmergingTalent:
    name: str
    role: str
    avg_roi: float
    median_roi: float
    avg_revenue: float
    avg_rating: float
    movie_count: int
    latest_year: int

@dataclass
class BudgetTier:
    tier: str
    avg_roi: float
    median_roi: float
    avg_revenue: float
    avg_budget: float
    avg_rating: float
    movie_count: int

@dataclass
class GenreTrend:
    genre: str
    decade: int
    movie_count: int
    avg_rating: float
    avg_revenue: float

@dataclass
class StudioRanking:
    studio: str
    avg_roi: float
    median_roi: float
    avg_revenue: float
    avg_budget: float
    movie_count: int


class AnalyticsEngine:
    """DuckDB-backed analytics query engine."""

    def __init__(self):
        self._db_path = str(DB_PATH)

    def _query(self, sql: str):
        con = duckdb.connect(self._db_path, read_only=True)
        result = con.execute(sql).fetchall()
        con.close()
        return result

    def is_healthy(self) -> bool:
        try:
            self._query("SELECT 1")
            return True
        except Exception:
            return False

    def get_genre_roi(self, limit: int = 20) -> list[GenreROI]:
        rows = self._query(
            f"SELECT genre, avg_roi, median_roi, avg_revenue, avg_budget, "
            f"avg_rating, movie_count FROM genre_roi "
            f"ORDER BY median_roi DESC LIMIT {limit}"
        )
        return [GenreROI(*r) for r in rows]

    def get_seasonal_trends(self, genre: str = None) -> list[SeasonalTrend]:
        if genre:
            query = f"""
            SELECT 
                release_quarter, 
                AVG(roi) as avg_roi, 
                MEDIAN(roi) as median_roi, 
                AVG(revenue) as avg_revenue, 
                COUNT(*) as movie_count 
            FROM movies 
            WHERE roi_is_real = true AND genre_str LIKE '%{genre}%' AND release_quarter IS NOT NULL
            GROUP BY release_quarter
            ORDER BY median_roi DESC
            """
            rows = self._query(query)
        else:
            rows = self._query(
                "SELECT release_quarter, avg_roi, median_roi, avg_revenue, movie_count "
                "FROM seasonal_performance ORDER BY median_roi DESC"
            )
        return [SeasonalTrend(*r) for r in rows]

    def get_top_directors(self, limit: int = 20, genre: str = None) -> list[TalentImpact]:
        genre_filter = f"AND genre_str LIKE '%{genre}%'" if genre else ""
        query = f"""
        SELECT 
            TRIM(director) as director,
            AVG(roi) as avg_roi,
            MEDIAN(roi) as median_roi,
            AVG(revenue) as avg_revenue,
            AVG(vote_average) as avg_rating,
            COUNT(*) as movie_count
        FROM (
            SELECT TRIM(UNNEST(string_split(directors, '|'))) as director, roi, revenue, vote_average
            FROM movies 
            WHERE roi_is_real = true {genre_filter} AND directors IS NOT NULL AND release_year >= 2020 AND vote_count > 50 AND TRIM(directors) != ''
        )
        WHERE director != ''
        GROUP BY 1 
        HAVING COUNT(*) >= 2
        ORDER BY median_roi DESC
        LIMIT {limit}
        """
        rows = self._query(query)
        return [TalentImpact(*r) for r in rows]

    def get_top_actors(self, limit: int = 20, genre: str = None) -> list[TalentImpact]:
        genre_filter = f"AND genre_str LIKE '%{genre}%'" if genre else ""
        query = f"""
        SELECT 
            TRIM(actor) as actor,
            AVG(roi) as avg_roi,
            MEDIAN(roi) as median_roi,
            AVG(revenue) as avg_revenue,
            AVG(vote_average) as avg_rating,
            COUNT(*) as movie_count
        FROM (
            SELECT TRIM(UNNEST(string_split(top_cast, '|'))) as actor, roi, revenue, vote_average
            FROM movies 
            WHERE roi_is_real = true {genre_filter} AND top_cast IS NOT NULL AND release_year >= 2020 AND vote_count > 50 AND TRIM(top_cast) != ''
        )
        WHERE actor != ''
        GROUP BY 1 
        HAVING COUNT(*) >= 2
        ORDER BY median_roi DESC
        LIMIT {limit}
        """
        rows = self._query(query)
        return [TalentImpact(*r) for r in rows]

    def get_emerging_talent(self, limit: int = 20, genre: str = None) -> list[EmergingTalent]:
        try:
            genre_filter = f"AND genre_str LIKE '%{genre}%'" if genre else ""
            query = f"""
            SELECT name, role, avg_roi, median_roi, avg_revenue, avg_rating, movie_count, latest_year
            FROM (
                SELECT 
                    TRIM(director) as name,
                    'director' as role,
                    AVG(roi) as avg_roi,
                    MEDIAN(roi) as median_roi,
                    AVG(revenue) as avg_revenue,
                    AVG(vote_average) as avg_rating,
                    COUNT(*) as movie_count,
                    MAX(release_year) as latest_year
                FROM (
                    SELECT UNNEST(string_split(directors, '|')) as director, roi, revenue, vote_average, release_year
                    FROM movies 
                    WHERE roi_is_real = true {genre_filter} AND directors IS NOT NULL AND release_year >= 2015 AND vote_count > 50
                )
                GROUP BY 1
                
                UNION ALL
                
                SELECT 
                    TRIM(actor) as name,
                    'actor' as role,
                    AVG(roi) as avg_roi,
                    MEDIAN(roi) as median_roi,
                    AVG(revenue) as avg_revenue,
                    AVG(vote_average) as avg_rating,
                    COUNT(*) as movie_count,
                    MAX(release_year) as latest_year
                FROM (
                    SELECT UNNEST(string_split(top_cast, '|')) as actor, roi, revenue, vote_average, release_year
                    FROM movies 
                    WHERE roi_is_real = true {genre_filter} AND top_cast IS NOT NULL AND release_year >= 2015 AND vote_count > 50
                )
                GROUP BY 1
            )
            WHERE movie_count >= 2 AND movie_count <= 4 AND median_roi >= 2.0
            ORDER BY median_roi DESC
            LIMIT {limit}
            """
            rows = self._query(query)
            return [EmergingTalent(*r) for r in rows]
        except Exception:
            return []

    def get_budget_tiers(self) -> list[BudgetTier]:
        rows = self._query(
            "SELECT tier, avg_roi, median_roi, avg_revenue, avg_budget, "
            "avg_rating, movie_count FROM budget_tiers ORDER BY median_roi DESC"
        )
        return [BudgetTier(*r) for r in rows]

    def get_genre_trends(self, genre: str = None) -> list[GenreTrend]:
        try:
            if genre:
                rows = self._query(
                    f"SELECT genre, decade, movie_count, avg_rating, avg_revenue "
                    f"FROM genre_trends WHERE genre = '{genre}' ORDER BY decade"
                )
            else:
                rows = self._query(
                    "SELECT genre, decade, movie_count, avg_rating, avg_revenue "
                    "FROM genre_trends ORDER BY genre, decade"
                )
            return [GenreTrend(*r) for r in rows]
        except Exception:
            return []

    def get_studio_rankings(self, limit: int = 20) -> list[StudioRanking]:
        try:
            rows = self._query(
                f"SELECT studio, avg_roi, median_roi, avg_revenue, avg_budget, movie_count "
                f"FROM studio_rankings ORDER BY median_roi DESC LIMIT {limit}"
            )
            return [StudioRanking(*r) for r in rows]
        except Exception:
            return []

    def get_genre_for_constraint(self, genre: str) -> dict:
        """Get constraint-relevant data for a specific genre."""
        result = {"genre": genre}
        try:
            rows = self._query(
                f"SELECT avg_roi, median_roi, avg_revenue, avg_budget, avg_rating, movie_count "
                f"FROM genre_roi WHERE genre = '{genre}' LIMIT 1"
            )
            if rows:
                r = rows[0]
                result.update({
                    "avg_roi": r[0], "median_roi": r[1],
                    "avg_revenue": r[2], "avg_budget": r[3],
                    "avg_rating": r[4], "movie_count": r[5],
                })
        except Exception:
            pass
        return result
