"""
Greenlight Cinema — Constraints Engine v2
===========================================
Generates commercial constraints for the AI agents based on DuckDB analytics.
In v2, this includes rich data on top directors, actors, and emerging talent.
"""

import logging
import json
from dataclasses import dataclass, asdict

from greenlight.analytics.engine import AnalyticsEngine

log = logging.getLogger("greenlight.analytics.constraints")


@dataclass
class MarketConstraints:
    genre: str
    target_budget_tier: str
    target_audience_rating: float
    expected_roi_multiplier: float
    best_release_quarters: list[str]
    suggested_directors: list[str]
    suggested_cast: list[str]
    emerging_talent: list[str]

    def to_dict(self):
        return asdict(self)

    def to_prompt_text(self) -> str:
        """Format constraints clearly for the LLM prompt."""
        lines = [
            f"- TARGET BUDGET TIER: {self.target_budget_tier}",
            f"- REQUIRED RELEASE WINDOW: {', '.join(self.best_release_quarters)}",
            f"- COMMERCIAL TARGET: Minimum {self.expected_roi_multiplier:.1f}x ROI",
            f"- AUDIENCE TARGET: {self.target_audience_rating:.1f}/10 average rating",
        ]

        if self.suggested_directors:
            lines.append(f"- SUGGESTED DIRECTORS (High ROI): {', '.join(self.suggested_directors)}")
        
        if self.suggested_cast:
            lines.append(f"- SUGGESTED CAST (High ROI): {', '.join(self.suggested_cast)}")

        if self.emerging_talent:
            lines.append(f"- EMERGING TALENT (<5 films, High ROI): {', '.join(self.emerging_talent)}")

        lines.append("")
        lines.append("INSTRUCTIONS:")
        lines.append("Design a story that feels perfectly calibrated for these constraints. "
                     "If the budget is low, avoid massive CGI set pieces. If the release "
                     "is Q4, consider awards-season themes or holiday counter-programming.")

        return "\n".join(lines)


class ConstraintEngine:
    """Generates market-aware constraints for script generation."""

    def __init__(self):
        self.analytics = AnalyticsEngine()

    def generate(self, genre: str, budget: int = None) -> MarketConstraints:
        """
        Generate constraints based on real DuckDB analytics.
        """
        log.info(f"Generating constraints for {genre} (Budget: {budget})")

        # 1. Base genre metrics
        genre_data = self.analytics.get_genre_for_constraint(genre)
        avg_rating = genre_data.get("avg_rating", 6.0)
        median_roi = genre_data.get("median_roi", 1.5)

        # 2. Budget tier
        if budget:
            if budget >= 100_000_000:
                tier = "Blockbuster ($100M+)"
            elif budget >= 50_000_000:
                tier = "High Budget ($50-100M)"
            elif budget >= 15_000_000:
                tier = "Mid Budget ($15-50M)"
            else:
                tier = "Low Budget (under $15M)"
        else:
            tier = "Mid Budget ($15-50M)"

        # 3. Seasonal data
        seasonal = self.analytics.get_seasonal_trends(genre=genre)
        best_quarters = [s.release_quarter for s in seasonal[:2]] if seasonal else ["Q4", "Q3"]

        # 4. Talent
        # Dynamically query a larger pool of talent SPECIFIC to this genre and sample randomly
        import random

        all_directors = [d.name for d in self.analytics.get_top_directors(limit=20, genre=genre)]
        top_directors = random.sample(all_directors, min(5, len(all_directors))) if all_directors else []

        all_actors = [a.name for a in self.analytics.get_top_actors(limit=30, genre=genre)]
        top_actors = random.sample(all_actors, min(8, len(all_actors))) if all_actors else []
        
        # Grab a mix of emerging talent
        emerging = self.analytics.get_emerging_talent(limit=40, genre=genre)
        emerging_names_pool = []
        for e in emerging:
            if e.name not in top_directors and e.name not in top_actors:
                emerging_names_pool.append(e.name)
        
        emerging_names = random.sample(emerging_names_pool, min(5, len(emerging_names_pool))) if emerging_names_pool else []

        constraints = MarketConstraints(
            genre=genre,
            target_budget_tier=tier,
            target_audience_rating=round(avg_rating + 0.5, 1), # Aim higher than average
            expected_roi_multiplier=round(median_roi * 1.5, 1), # Aim for upper quartile
            best_release_quarters=best_quarters,
            suggested_directors=top_directors,
            suggested_cast=top_actors,
            emerging_talent=emerging_names,
        )

        return constraints
