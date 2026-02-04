"""Dependency injection and error handling for API routes.

Provides:
- Custom exception classes for domain-specific errors
- Exception handlers for FastAPI
- Common dependencies for route handlers
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exceptions
# =============================================================================


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str | None = None,
    ) -> None:
        """Initialize application exception.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code.
            detail: Optional detailed error information.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail


class NotFoundError(AppException):
    """Resource not found error."""

    def __init__(
        self,
        resource: str,
        identifier: str | UUID | None = None,
    ) -> None:
        """Initialize not found error.

        Args:
            resource: Type of resource (e.g., "Project", "Job").
            identifier: Resource identifier if available.
        """
        if identifier:
            message = f"{resource} with ID '{identifier}' not found"
        else:
            message = f"{resource} not found"
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)
        self.resource = resource
        self.identifier = identifier


class ValidationError(AppException):
    """Validation error for invalid input data."""

    def __init__(
        self,
        message: str,
        detail: str | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Validation error message.
            detail: Optional detailed validation info.
        """
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class FileError(AppException):
    """Error related to file operations."""

    def __init__(
        self,
        message: str,
        path: str | None = None,
    ) -> None:
        """Initialize file error.

        Args:
            message: Error message.
            path: File path if available.
        """
        detail = f"Path: {path}" if path else None
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        self.path = path


class ProcessingError(AppException):
    """Error during georectification or other processing."""

    def __init__(
        self,
        message: str,
        step: str | None = None,
        detail: str | None = None,
    ) -> None:
        """Initialize processing error.

        Args:
            message: Error message.
            step: Processing step where error occurred.
            detail: Detailed error information.
        """
        full_detail = f"Step: {step}. {detail}" if step and detail else step or detail
        super().__init__(
            message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=full_detail
        )
        self.step = step


class MemoryError(AppException):
    """Memory error with recommended resolution suggestion.

    This error is raised when the system runs out of memory during processing,
    typically with large DSM or orthophoto files.
    """

    def __init__(
        self,
        message: str,
        current_resolution: float | None = None,
        recommended_resolution: float | None = None,
    ) -> None:
        """Initialize memory error with resolution recommendations.

        Args:
            message: Error message.
            current_resolution: Current resolution in meters/pixel.
            recommended_resolution: Recommended resolution to avoid memory issues.
        """
        detail_parts = []
        if current_resolution is not None:
            detail_parts.append(f"Current resolution: {current_resolution:.2f}m/pixel")
        if recommended_resolution is not None:
            detail_parts.append(f"Recommended resolution: {recommended_resolution:.1f}m/pixel or higher")
        detail_parts.append(
            "Try reducing the processing area or increasing resolution value."
        )
        detail = " ".join(detail_parts)

        super().__init__(
            message, status_code=status.HTTP_507_INSUFFICIENT_STORAGE, detail=detail
        )
        self.current_resolution = current_resolution
        self.recommended_resolution = recommended_resolution


class MatchingError(AppException):
    """Image matching error with suggestions for resolution.

    This error is raised when image matching fails to find sufficient
    corresponding points between target and simulation images.
    """

    def __init__(
        self,
        message: str,
        points_found: int = 0,
        min_points_required: int = 4,
        suggestions: list[str] | None = None,
    ) -> None:
        """Initialize matching error with suggestions.

        Args:
            message: Error message.
            points_found: Number of matching points found.
            min_points_required: Minimum points required for processing.
            suggestions: List of suggested actions to resolve the issue.
        """
        default_suggestions = [
            "Adjust initial camera parameters closer to the actual position",
            "Try a different matching algorithm (e.g., SuperPoint-LightGlue, AKAZE, SIFT, MINIMA-ROMA, Tiny-ROMA)",
            "Ensure the target image is within the DSM/orthophoto coverage area",
            "Check that the camera position is approximately correct",
        ]
        self.suggestions = suggestions or default_suggestions
        self.points_found = points_found
        self.min_points_required = min_points_required

        detail_lines = [
            f"Found {points_found} points, minimum {min_points_required} required.",
            "Suggestions:",
        ]
        for i, suggestion in enumerate(self.suggestions, 1):
            detail_lines.append(f"  {i}. {suggestion}")

        super().__init__(
            message, status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="\n".join(detail_lines)
        )


class CRSMismatchError(AppException):
    """Coordinate Reference System mismatch error.

    This error is raised when DSM and orthophoto have different CRS.
    """

    def __init__(
        self,
        dsm_crs: str,
        ortho_crs: str,
    ) -> None:
        """Initialize CRS mismatch error.

        Args:
            dsm_crs: CRS of the DSM file.
            ortho_crs: CRS of the orthophoto file.
        """
        message = "Coordinate reference systems do not match"
        detail = (
            f"DSM CRS: {dsm_crs}, Orthophoto CRS: {ortho_crs}. "
            "Please ensure both files use the same coordinate reference system."
        )
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        self.dsm_crs = dsm_crs
        self.ortho_crs = ortho_crs


class JobError(AppException):
    """Error related to job operations."""

    def __init__(
        self,
        message: str,
        job_id: UUID | None = None,
    ) -> None:
        """Initialize job error.

        Args:
            message: Error message.
            job_id: Job ID if available.
        """
        detail = f"Job ID: {job_id}" if job_id else None
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        self.job_id = job_id


# =============================================================================
# Exception Handlers
# =============================================================================


def make_error_response(
    error: str,
    detail: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Create standardized error response body.

    Args:
        error: Error message.
        detail: Optional error detail.
        **extra: Additional fields to include.

    Returns:
        Error response dictionary.
    """
    response: dict[str, Any] = {"error": error}
    if detail:
        response["detail"] = detail
    response.update(extra)
    return response


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions.

    Args:
        request: The incoming request.
        exc: The raised AppException.

    Returns:
        JSON error response.
    """
    logger.warning(f"AppException: {exc.message} (status={exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content=make_error_response(exc.message, exc.detail),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException.

    Args:
        request: The incoming request.
        exc: The raised HTTPException.

    Returns:
        JSON error response.
    """
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=make_error_response(detail),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions.

    Args:
        request: The incoming request.
        exc: The raised exception.

    Returns:
        JSON error response.
    """
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=make_error_response(
            "Internal server error",
            detail=str(exc) if logger.isEnabledFor(logging.DEBUG) else None,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance.
    """
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)


# =============================================================================
# Dependencies
# =============================================================================


def get_job_queue_dep() -> Any:
    """Dependency to get the job queue.

    Returns:
        The global job queue instance.
    """
    from app.core.jobs import get_job_queue

    return get_job_queue()
