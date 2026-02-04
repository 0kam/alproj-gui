"""API routes for job management.

Provides:
- GET /api/jobs/{jobId}: Get job status and result
- DELETE /api/jobs/{jobId}: Cancel a running job
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import NotFoundError, get_job_queue_dep
from app.core.jobs import Job, JobQueue
from app.core.jobs import JobStatus as CoreJobStatus
from app.schemas.job import Job as JobSchema
from app.schemas.job import JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _job_to_schema(job: Job) -> JobSchema:
    """Convert internal Job to API schema.

    Args:
        job: Internal Job instance from jobs.py core module.

    Returns:
        JobSchema instance for API response.
    """
    return JobSchema(
        id=job.id,
        status=JobStatus(job.status.value),
        progress=job.progress,
        step=job.step or None,
        message=job.message or None,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error=job.error,
        result=job.result,
    )


@router.get(
    "/{job_id}",
    response_model=JobSchema,
    summary="Get job status",
    description="Retrieve the current status and result of a job.",
)
async def get_job(
    job_id: UUID,
    job_queue: JobQueue = Depends(get_job_queue_dep),
) -> JobSchema:
    """Get job status by ID.

    Args:
        job_id: Job UUID.
        job_queue: Job queue dependency.

    Returns:
        Job status and result.

    Raises:
        NotFoundError: If job not found.
    """
    job = await job_queue.get(job_id)
    if job is None:
        raise NotFoundError("Job", job_id)

    return _job_to_schema(job)


@router.delete(
    "/{job_id}",
    response_model=JobSchema,
    summary="Cancel job",
    description="Request cancellation of a pending or running job.",
)
async def cancel_job(
    job_id: UUID,
    job_queue: JobQueue = Depends(get_job_queue_dep),
) -> JobSchema:
    """Cancel a job.

    Args:
        job_id: Job UUID to cancel.
        job_queue: Job queue dependency.

    Returns:
        Updated job with cancelled status.

    Raises:
        NotFoundError: If job not found.
        HTTPException: If job cannot be cancelled.
    """
    job = await job_queue.get(job_id)
    if job is None:
        raise NotFoundError("Job", job_id)

    # Check if job can be cancelled
    if job.status not in (CoreJobStatus.PENDING, CoreJobStatus.RUNNING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status '{job.status.value}'. "
            "Only pending or running jobs can be cancelled.",
        )

    # Request cancellation
    cancelled_job = await job_queue.cancel(job_id)
    if cancelled_job is None:
        raise NotFoundError("Job", job_id)

    logger.info(f"Job {job_id} cancellation requested")
    return _job_to_schema(cancelled_job)
