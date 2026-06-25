"""
Greenlight Cinema — Validation Engine
=======================================
Produces a final validation report for a generated synopsis,
checking all constraint compliance.

Implements PRD FR-08.
"""

import logging
from dataclasses import dataclass, field, asdict

log = logging.getLogger("greenlight.validation.validator")


@dataclass
class ValidationReport:
    """Final validation report for a generated synopsis."""
    score: float = 0.0
    passed_constraints: list[str] = field(default_factory=list)
    failed_constraints: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    genre_compliant: bool = False
    budget_aligned: bool = False
    narrative_quality: str = "unknown"
    iterations_used: int = 0
    word_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


class ValidationEngine:
    """Validates generated synopses against constraints."""

    def validate(self, final_state: dict) -> ValidationReport:
        """
        Produce a validation report from the final graph state.

        Args:
            final_state: The final LangGraph state dict

        Returns:
            ValidationReport with pass/fail details
        """
        report = ValidationReport()

        synopsis = final_state.get("synopsis", "")
        critique = final_state.get("critique", {})
        constraints = final_state.get("constraints", {})
        score = final_state.get("score", 0.0)

        report.score = round(score, 3)
        report.iterations_used = final_state.get("iteration", 0)
        report.word_count = len(synopsis.split()) if synopsis else 0

        # ── Genre compliance ─────────────────────────────────────────────────
        genre_score = critique.get("genre_score", 0.5)
        if genre_score >= 0.6:
            report.genre_compliant = True
            report.passed_constraints.append(
                f"Genre compliance: {genre_score:.0%}"
            )
        else:
            report.failed_constraints.append(
                f"Genre compliance low: {genre_score:.0%}"
            )

        # ── Commercial viability ─────────────────────────────────────────────
        commercial_score = critique.get("commercial_score", 0.5)
        if commercial_score >= 0.6:
            report.budget_aligned = True
            report.passed_constraints.append(
                f"Commercial viability: {commercial_score:.0%}"
            )
        else:
            report.failed_constraints.append(
                f"Commercial viability low: {commercial_score:.0%}"
            )

        # ── Narrative quality ────────────────────────────────────────────────
        narrative_score = critique.get("narrative_score", 0.5)
        if narrative_score >= 0.8:
            report.narrative_quality = "excellent"
            report.passed_constraints.append(
                f"Narrative quality: {narrative_score:.0%}"
            )
        elif narrative_score >= 0.6:
            report.narrative_quality = "good"
            report.passed_constraints.append(
                f"Narrative quality: {narrative_score:.0%}"
            )
        else:
            report.narrative_quality = "needs improvement"
            report.failed_constraints.append(
                f"Narrative quality: {narrative_score:.0%}"
            )

        # ── Seasonal fit ─────────────────────────────────────────────────────
        seasonal_score = critique.get("seasonal_score", 0.5)
        if seasonal_score >= 0.6:
            report.passed_constraints.append(
                f"Seasonal fit: {seasonal_score:.0%}"
            )
        else:
            report.failed_constraints.append(
                f"Seasonal fit low: {seasonal_score:.0%}"
            )

        # ── Word count check ─────────────────────────────────────────────────
        if 100 <= report.word_count <= 250:
            report.passed_constraints.append(
                f"Word count: {report.word_count} (target: 150)"
            )
        else:
            report.failed_constraints.append(
                f"Word count: {report.word_count} (target: 150)"
            )

        # ── Overall score check ──────────────────────────────────────────────
        if score >= 0.7:
            report.passed_constraints.append(
                f"Overall score: {score:.0%} (threshold: 70%)"
            )
        else:
            report.failed_constraints.append(
                f"Overall score: {score:.0%} (threshold: 70%)"
            )

        # ── Aggregate suggestions ────────────────────────────────────────────
        report.suggestions = critique.get("suggestions", [])
        if not report.suggestions and report.score < 0.7:
            report.suggestions.append("Consider regenerating with adjusted constraints")

        log.info(f"Validation: score={report.score:.2f}, "
                 f"passed={len(report.passed_constraints)}, "
                 f"failed={len(report.failed_constraints)}")

        return report
