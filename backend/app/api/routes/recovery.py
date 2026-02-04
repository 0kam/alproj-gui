"""Recovery API routes for crash recovery functionality.

Provides endpoints for:
- GET /api/recovery/check: Check for recovery files
- POST /api/recovery/restore: Restore project from recovery file
- DELETE /api/recovery/{filename}: Delete a recovery file
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import NotFoundError
from app.api.routes.projects import save_project
from app.schemas.project import Project
from app.services.project_io import ProjectValidationError, _dict_to_project
from app.services.recovery import (
    RecoveryInfo,
    clear_recovery_state,
    cleanup_old_recovery_files,
    list_recovery_files,
    load_recovery_state,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recovery", tags=["recovery"])


# =============================================================================
# Request/Response Models
# =============================================================================


class RecoveryCheckResponse(BaseModel):
    """Response for recovery check endpoint."""

    has_recovery_files: bool = Field(
        ..., description="Whether there are recovery files available"
    )
    files: list[dict[str, Any]] = Field(
        default_factory=list, description="List of recovery file information"
    )


class RestoreRequest(BaseModel):
    """Request body for restoring from a recovery file."""

    path: str = Field(..., description="Path to the recovery file to restore from")


class RestoreResponse(BaseModel):
    """Response for successful restore operation."""

    project: Project = Field(..., description="The restored project")
    message: str = Field(..., description="Success message")


class DeleteResponse(BaseModel):
    """Response for delete operation."""

    success: bool = Field(..., description="Whether the deletion was successful")
    message: str = Field(..., description="Status message")


# =============================================================================
# Recovery Endpoints
# =============================================================================


@router.get(
    "/check",
    response_model=RecoveryCheckResponse,
    summary="Check for recovery files",
    description="Check if there are any recovery files from previous sessions that can be restored.",
)
async def check_recovery() -> RecoveryCheckResponse:
    """Check for available recovery files.

    Returns:
        Response indicating whether recovery files exist and their details.
    """
    # Clean up old recovery files first (older than 7 days)
    cleanup_old_recovery_files(max_age_days=7)

    # Get list of recovery files
    recovery_files = list_recovery_files()

    return RecoveryCheckResponse(
        has_recovery_files=len(recovery_files) > 0,
        files=[rf.to_dict() for rf in recovery_files],
    )


@router.post(
    "/restore",
    response_model=RestoreResponse,
    summary="Restore project from recovery file",
    description="Restore a project from a recovery file and add it to the current session.",
)
async def restore_project(request: RestoreRequest) -> RestoreResponse:
    """Restore a project from a recovery file.

    Args:
        request: Request with path to recovery file.

    Returns:
        The restored project.

    Raises:
        NotFoundError: If recovery file not found.
        HTTPException: If recovery file is invalid.
    """
    filepath = Path(request.path)

    if not filepath.exists():
        raise NotFoundError("RecoveryFile", request.path)

    # Load recovery data
    recovery_data = load_recovery_state(request.path)
    if recovery_data is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to load recovery file: invalid format",
        )

    # Extract project data
    project_data = recovery_data.get("project")
    if not project_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Recovery file does not contain valid project data",
        )

    # Convert to Project object
    try:
        project = _dict_to_project(project_data)
    except Exception as e:
        logger.error(f"Failed to parse project from recovery file: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse project data: {e}",
        )

    # Add to session storage
    save_project(project)

    # Clear the recovery file after successful restore
    clear_recovery_state(str(project.id))

    logger.info(f"Restored project {project.id} from recovery file: {request.path}")

    return RestoreResponse(
        project=project,
        message=f"Successfully restored project '{project.name}'",
    )


@router.delete(
    "/{filename}",
    response_model=DeleteResponse,
    summary="Delete a recovery file",
    description="Delete a specific recovery file by filename.",
)
async def delete_recovery_file(filename: str) -> DeleteResponse:
    """Delete a specific recovery file.

    Args:
        filename: Name of the recovery file (not full path).

    Returns:
        Response indicating success or failure.

    Raises:
        NotFoundError: If recovery file not found.
    """
    # Extract project_id from filename (format: {project_id}.alproj.tmp)
    if filename.endswith(".alproj.tmp"):
        project_id = filename[:-11]  # Remove ".alproj.tmp" suffix
    else:
        project_id = filename

    success = clear_recovery_state(project_id)

    if not success:
        raise NotFoundError("RecoveryFile", filename)

    logger.info(f"Deleted recovery file: {filename}")

    return DeleteResponse(
        success=True,
        message=f"Successfully deleted recovery file: {filename}",
    )


@router.delete(
    "",
    response_model=DeleteResponse,
    summary="Delete all recovery files",
    description="Delete all recovery files.",
)
async def delete_all_recovery_files() -> DeleteResponse:
    """Delete all recovery files.

    Returns:
        Response indicating success.
    """
    recovery_files = list_recovery_files()
    deleted_count = 0

    for rf in recovery_files:
        # Extract project_id from path
        filepath = Path(rf.path)
        filename = filepath.name
        if filename.endswith(".alproj.tmp"):
            project_id = filename[:-11]
            if clear_recovery_state(project_id):
                deleted_count += 1

    logger.info(f"Deleted {deleted_count} recovery files")

    return DeleteResponse(
        success=True,
        message=f"Successfully deleted {deleted_count} recovery file(s)",
    )
