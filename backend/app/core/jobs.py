"""In-memory job queue with asyncio support.

Provides:
- Job model with status, progress, and cancellation support
- JobQueue for managing concurrent jobs
- Progress callback for WebSocket notifications
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobProgress:
    """Progress update for a job."""

    progress: float  # 0.0 to 1.0
    step: str  # Current step name
    message: str = ""  # Optional message


@dataclass
class Job:
    """Represents an async job with status tracking and cancellation support."""

    id: UUID = field(default_factory=uuid4)
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    step: str = ""
    message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: Any = None

    # Internal state
    _task: asyncio.Task[Any] | None = field(default=None, repr=False)
    _cancel_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    _progress_callbacks: list[Callable[[JobProgress], Awaitable[None]]] = field(
        default_factory=list, repr=False
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary for API response."""
        return {
            "id": str(self.id),
            "status": self.status.value,
            "progress": self.progress,
            "step": self.step,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "result": self.result,
        }

    @property
    def is_cancellation_requested(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancel_event.is_set()

    def request_cancellation(self) -> None:
        """Request cancellation of this job."""
        self._cancel_event.set()

    async def check_cancellation(self) -> None:
        """Check if cancellation was requested and raise if so.

        Call this periodically in long-running job functions.

        Raises:
            asyncio.CancelledError: If cancellation was requested.
        """
        if self._cancel_event.is_set():
            raise asyncio.CancelledError("Job was cancelled by user request")

    def add_progress_callback(
        self, callback: Callable[[JobProgress], Awaitable[None]]
    ) -> None:
        """Add a callback to be notified of progress updates."""
        self._progress_callbacks.append(callback)

    def remove_progress_callback(
        self, callback: Callable[[JobProgress], Awaitable[None]]
    ) -> None:
        """Remove a progress callback."""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)

    async def update_progress(
        self, progress: float, step: str, message: str = ""
    ) -> None:
        """Update job progress and notify callbacks.

        Args:
            progress: Progress value between 0.0 and 1.0.
            step: Current step name.
            message: Optional progress message.
        """
        self.progress = max(0.0, min(1.0, progress))
        self.step = step
        self.message = message

        # Notify all callbacks
        update = JobProgress(progress=self.progress, step=step, message=message)
        for callback in self._progress_callbacks:
            try:
                await callback(update)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")


# Type alias for job function
JobFunc = Callable[[Job], Awaitable[Any]]


class JobQueue:
    """In-memory async job queue with concurrency control.

    Example usage:
        queue = JobQueue(max_concurrent=1)

        async def my_job(job: Job):
            for i in range(10):
                await job.check_cancellation()
                await job.update_progress(i / 10, "processing", f"Step {i}")
                await asyncio.sleep(1)
            return {"result": "done"}

        job = await queue.submit(my_job)
        # Later...
        await queue.cancel(job.id)
    """

    def __init__(self, max_concurrent: int = 1) -> None:
        """Initialize job queue.

        Args:
            max_concurrent: Maximum number of concurrent jobs.
        """
        self._jobs: dict[UUID, Job] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()

    @property
    def jobs(self) -> dict[UUID, Job]:
        """Get all jobs."""
        return self._jobs.copy()

    async def get(self, job_id: UUID) -> Job | None:
        """Get a job by ID.

        Args:
            job_id: The job UUID.

        Returns:
            The job if found, None otherwise.
        """
        return self._jobs.get(job_id)

    async def submit(self, func: JobFunc) -> Job:
        """Submit a new job to the queue.

        Args:
            func: Async function that takes a Job and returns a result.

        Returns:
            The created Job instance.
        """
        job = Job()
        async with self._lock:
            self._jobs[job.id] = job

        # Start the job wrapper task
        job._task = asyncio.create_task(self._run_job(job, func))
        logger.info(f"Job {job.id} submitted")

        return job

    async def _run_job(self, job: Job, func: JobFunc) -> None:
        """Run a job with semaphore control.

        Args:
            job: The job instance.
            func: The job function to execute.
        """
        # Wait for semaphore (concurrency control)
        async with self._semaphore:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(UTC)
            logger.info(f"Job {job.id} started")

            try:
                result = await func(job)
                job.result = result
                job.status = JobStatus.COMPLETED
                job.progress = 1.0
                logger.info(f"Job {job.id} completed")

            except asyncio.CancelledError:
                job.status = JobStatus.CANCELLED
                job.error = "Job was cancelled"
                logger.info(f"Job {job.id} cancelled")

            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                logger.error(f"Job {job.id} failed: {e}")

            finally:
                job.completed_at = datetime.now(UTC)

    async def cancel(self, job_id: UUID) -> Job | None:
        """Cancel a running or pending job.

        Args:
            job_id: The job UUID to cancel.

        Returns:
            The cancelled job if found, None otherwise.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return None

        if job.status in (JobStatus.PENDING, JobStatus.RUNNING):
            # Request cancellation via event (cooperative)
            job.request_cancellation()

            # Also cancel the asyncio task if running
            if job._task and not job._task.done():
                job._task.cancel()
                try:
                    await job._task
                except asyncio.CancelledError:
                    pass

            logger.info(f"Job {job_id} cancellation requested")

        return job

    async def cleanup_completed(self, max_age_seconds: int = 3600) -> int:
        """Remove completed/failed/cancelled jobs older than max_age.

        Args:
            max_age_seconds: Maximum age in seconds for completed jobs.

        Returns:
            Number of jobs removed.
        """
        now = datetime.now(UTC)
        to_remove: list[UUID] = []

        async with self._lock:
            for job_id, job in self._jobs.items():
                if job.status in (
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                    JobStatus.CANCELLED,
                ):
                    if job.completed_at:
                        age = (now - job.completed_at).total_seconds()
                        if age > max_age_seconds:
                            to_remove.append(job_id)

            for job_id in to_remove:
                del self._jobs[job_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} completed jobs")

        return len(to_remove)


# Global job queue instance (initialized with settings in main.py)
_job_queue: JobQueue | None = None


def get_job_queue() -> JobQueue:
    """Get the global job queue instance.

    Returns:
        The global JobQueue instance.

    Raises:
        RuntimeError: If job queue is not initialized.
    """
    if _job_queue is None:
        raise RuntimeError("Job queue not initialized. Call init_job_queue() first.")
    return _job_queue


def init_job_queue(max_concurrent: int = 1) -> JobQueue:
    """Initialize the global job queue.

    Args:
        max_concurrent: Maximum number of concurrent jobs.

    Returns:
        The initialized JobQueue instance.
    """
    global _job_queue
    _job_queue = JobQueue(max_concurrent=max_concurrent)
    logger.info(f"Job queue initialized with max_concurrent={max_concurrent}")
    return _job_queue
