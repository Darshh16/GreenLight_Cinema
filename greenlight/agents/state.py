"""
Greenlight Cinema — Graph State Definition
============================================
Defines the TypedDict state shared across all agents
in the LangGraph workflow.
"""

from typing import TypedDict


class GraphState(TypedDict):
    """State passed through the LangGraph workflow."""

    # ── Input ────────────────────────────────────────────────────────────────
    user_prompt: str              # User's narrative prompt/idea
    genre: str                    # Target genre
    budget: int                   # Budget in USD (0 = unspecified)

    # ── Constraint & RAG Context ─────────────────────────────────────────────
    constraints: dict             # Market constraints from ConstraintEngine
    retrieved_examples: list      # Retrieved scenes from ChromaDB RAG

    # ── Generation State ─────────────────────────────────────────────────────
    synopsis: str                 # Current synopsis text
    critique: dict                # Latest critic evaluation
    score: float                  # Current composite score (0.0 - 1.0)

    # ── Loop Control ─────────────────────────────────────────────────────────
    iteration: int                # Current iteration number
    max_iterations: int           # Maximum allowed iterations

    # ── History ──────────────────────────────────────────────────────────────
    history: list                 # List of {iteration, synopsis, critique, score}

    # ── Status ───────────────────────────────────────────────────────────────
    status: str                   # "running", "completed", "failed"
    error: str                    # Error message if failed
