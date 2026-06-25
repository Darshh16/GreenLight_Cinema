"""
Greenlight Cinema — Pydantic Models / API Schemas
===================================================
Request/response schemas for the FastAPI backend.
Implements PRD Section 14: API Contracts.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Request Models ───────────────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    """POST /generate-synopsis request body."""
    genre: str = Field(..., description="Target genre (e.g., Action, Horror, Comedy)")
    budget: Optional[int] = Field(None, description="Budget in USD", ge=0)
    iterations: int = Field(3, description="Max refinement iterations", ge=1, le=5)


# ── Response Models ──────────────────────────────────────────────────────────


class GenerateResponse(BaseModel):
    """POST /generate-synopsis response."""
    job_id: str = Field(..., description="Unique job identifier (UUID)")


class CritiqueDetail(BaseModel):
    """Embedded critique scores."""
    score: float = 0.0
    genre_score: float = 0.0
    commercial_score: float = 0.0
    narrative_score: float = 0.0
    seasonal_score: float = 0.0
    issues: list[str] = []
    suggestions: list[str] = []
    strengths: list[str] = []


class IterationDetail(BaseModel):
    """Single iteration history entry."""
    iteration: int
    synopsis: str = ""
    critique: CritiqueDetail = CritiqueDetail()
    score: float = 0.0


class ValidationDetail(BaseModel):
    """Validation report."""
    score: float = 0.0
    passed_constraints: list[str] = []
    failed_constraints: list[str] = []
    suggestions: list[str] = []
    genre_compliant: bool = False
    budget_aligned: bool = False
    narrative_quality: str = "unknown"
    iterations_used: int = 0
    word_count: int = 0


class JobResult(BaseModel):
    """Full generation result."""
    synopsis: str = ""
    score: float = 0.0
    critique: CritiqueDetail = CritiqueDetail()
    validation: ValidationDetail = ValidationDetail()
    history: list[IterationDetail] = []
    constraints_used: dict = {}


class JobStatusResponse(BaseModel):
    """GET /status/{job_id} response."""
    job_id: str
    status: JobStatus
    progress: str = ""
    result: Optional[JobResult] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class ConstraintResponse(BaseModel):
    """GET /constraints response."""
    genre: str
    constraints: dict


class ServiceHealth(BaseModel):
    """Health of a single service."""
    name: str
    healthy: bool
    details: str = ""


class HealthResponse(BaseModel):
    """GET /health response."""
    status: str
    services: list[ServiceHealth] = []
    uptime_seconds: float = 0.0


# ── Analytics Response Models ────────────────────────────────────────────────


class GenreROIResponse(BaseModel):
    genre: str
    avg_roi: float
    median_roi: float
    movie_count: int
    avg_revenue: float = 0.0
    avg_budget: float = 0.0


class SeasonalResponse(BaseModel):
    release_quarter: str
    avg_roi: float
    median_roi: float
    movie_count: int
    avg_revenue: float = 0.0


class TalentResponse(BaseModel):
    name: str
    avg_roi: float
    median_roi: float
    movie_count: int
    avg_revenue: float = 0.0


class BudgetTierResponse(BaseModel):
    tier: str
    median_roi: float
    avg_roi: float
    avg_revenue: float
    avg_budget: float
    movie_count: int
