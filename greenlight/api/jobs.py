"""
Greenlight Cinema — Job Manager
=================================
In-memory job store for managing synopsis generation tasks.
Tracks status, progress, and results for async background jobs.

Implements PRD Section 15: Job Management.
"""

import logging
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

from greenlight.api.models import JobStatus

log = logging.getLogger("greenlight.api.jobs")


@dataclass
class Job:
    """Represents a single generation job."""
    job_id: str
    genre: str
    budget: int
    max_iterations: int
    status: JobStatus = JobStatus.QUEUED
    progress: str = "Queued"
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class JobManager:
    """
    In-memory job manager.

    Stores jobs in a dict and runs generation in background tasks.
    """

    def __init__(self):
        self._jobs: dict[str, Job] = {}

    def create_job(self, genre: str, budget: int, max_iterations: int) -> str:
        """Create a new job and return its ID."""
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            genre=genre,
            budget=budget,
            max_iterations=max_iterations,
        )
        self._jobs[job_id] = job
        log.info(f"Job created: {job_id} (genre={genre}, budget={budget})")
        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def update_progress(self, job_id: str, progress: str):
        """Update job progress text."""
        job = self._jobs.get(job_id)
        if job:
            job.progress = progress
            log.debug(f"Job {job_id}: {progress}")

    def mark_running(self, job_id: str):
        """Mark a job as running."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.RUNNING
            job.progress = "Running"

    def mark_completed(self, job_id: str, result: dict):
        """Mark a job as completed with results."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.COMPLETED
            job.result = result
            job.progress = "Completed"
            job.completed_at = datetime.now(timezone.utc)
            log.info(f"Job completed: {job_id}")

    def mark_failed(self, job_id: str, error: str):
        """Mark a job as failed."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.error = error
            job.progress = "Failed"
            job.completed_at = datetime.now(timezone.utc)
            log.error(f"Job failed: {job_id} — {error}")

    def list_jobs(self, limit: int = 50) -> list[Job]:
        """List recent jobs."""
        jobs = sorted(
            self._jobs.values(),
            key=lambda j: j.created_at,
            reverse=True,
        )
        return jobs[:limit]


# ── Singleton instance ──────────────────────────────────────────────────────

_job_manager = None


def get_job_manager() -> JobManager:
    """Get the global JobManager singleton."""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
