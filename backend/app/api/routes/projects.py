"""API routes for project management.

Provides:
- GET /api/projects: List all projects
- POST /api/projects: Create a new project
- GET /api/projects/{projectId}: Get project by ID
- PUT /api/projects/{projectId}: Update project (camera params, name, input data)
- DELETE /api/projects/{projectId}: Delete a project
- POST /api/projects/open: Open project from .alproj file
- POST /api/projects/{projectId}/save: Save project to .alproj file
- POST /api/projects/{projectId}/update-gcps: Update project GCPs
- POST /api/projects/reprocess: Partial reprocessing
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from app.api.deps import NotFoundError, ValidationError, get_job_queue_dep
from app.core.jobs import Job, JobQueue
from app.schemas import (
    CameraParams,
    GCP,
    InputData,
    ProcessOptions,
    Project,
    ProjectStatus,
    UpdateProjectRequest,
)
from app.schemas.job import JobStatus
from app.schemas.project import CreateProjectRequest, ProjectSummary
from app.services.project_io import (
    ProjectIOError,
    ProjectValidationError,
    ProjectVersionError,
    get_project_info,
    load_project as load_project_from_file,
    save_project as save_project_to_file,
)
from app.services.report import generate_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


# =============================================================================
# In-memory Project Storage
# =============================================================================

_projects: dict[str, Project] = {}


def get_project(project_id: str) -> Project | None:
    """Get a project by ID from in-memory storage.

    Args:
        project_id: Project UUID string.

    Returns:
        Project if found, None otherwise.
    """
    return _projects.get(project_id)


def save_project(project: Project) -> Project:
    """Save a project to in-memory storage.

    Args:
        project: Project to save.

    Returns:
        The saved project.
    """
    project.updated_at = datetime.now(UTC)
    _projects[str(project.id)] = project
    return project


def create_project_in_memory(name: str) -> Project:
    """Create a new project in memory.

    Args:
        name: Project name.

    Returns:
        The created project.
    """
    now = datetime.now(UTC)
    project = Project(
        id=uuid4(),
        name=name,
        status=ProjectStatus.DRAFT,
        created_at=now,
        updated_at=now,
        input_data=InputData(),
    )
    _projects[str(project.id)] = project
    return project


def delete_project_from_memory(project_id: str) -> bool:
    """Delete a project from in-memory storage.

    Args:
        project_id: Project UUID string.

    Returns:
        True if deleted, False if not found.
    """
    if project_id in _projects:
        del _projects[project_id]
        return True
    return False


def list_all_projects() -> list[Project]:
    """Get all projects from in-memory storage.

    Returns:
        List of all projects.
    """
    return list(_projects.values())


# =============================================================================
# Request/Response Models
# =============================================================================


class OpenProjectRequest(BaseModel):
    """Request body for opening a project file."""

    path: str = Field(..., description="Path to the .alproj file to open")


class SaveProjectResponse(BaseModel):
    """Response for saving a project to file."""

    path: str = Field(..., description="Path where the project was saved")
    message: str = Field(..., description="Success message")


class UpdateGcpsRequest(BaseModel):
    """Request body for updating project GCPs."""

    gcps: list[GCP] = Field(..., description="Updated list of GCPs")


class ReprocessRequest(BaseModel):
    """Request body for partial reprocessing."""

    project_id: UUID = Field(..., description="Project to reprocess")
    from_step: str = Field(
        ...,
        pattern="^(matching|optimization|export)$",
        description="Step to start reprocessing from",
    )
    options: ProcessOptions | None = Field(
        default=None, description="Processing options override"
    )


class ReprocessJobResponse(BaseModel):
    """Response for starting a reprocessing job (202 Accepted)."""

    id: UUID = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Initial job status")
    created_at: str = Field(..., description="Job creation timestamp (ISO 8601)")


# =============================================================================
# Project List and Create Endpoints
# =============================================================================


@router.get(
    "",
    response_model=list[ProjectSummary],
    summary="List all projects",
    description="List all projects in the current session, sorted by updated_at (newest first).",
)
async def list_projects() -> list[ProjectSummary]:
    """List all projects in the current session.

    Returns:
        List of project summaries.
    """
    projects = list_all_projects()
    summaries = [
        ProjectSummary(
            id=p.id,
            name=p.name,
            status=p.status,
            updated_at=p.updated_at,
        )
        for p in projects
    ]
    # Sort by updated_at descending (newest first)
    summaries.sort(key=lambda x: x.updated_at, reverse=True)
    return summaries


@router.post(
    "",
    response_model=Project,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="Create a new project with the given name.",
)
async def create_project(request: CreateProjectRequest) -> Project:
    """Create a new project.

    Args:
        request: Project creation request.

    Returns:
        The created project.
    """
    project = create_project_in_memory(request.name)
    logger.info(f"Created project: {project.id} ({project.name})")
    return project


# =============================================================================
# File Operations (must be before /{project_id} routes)
# =============================================================================


@router.post(
    "/open",
    response_model=Project,
    summary="Open project from file",
    description="Open a project from a .alproj file and add it to the current session.",
)
async def open_project(request: OpenProjectRequest) -> Project:
    """Open a project from a .alproj file.

    Args:
        request: Request with file path.

    Returns:
        The loaded project.

    Raises:
        NotFoundError: If file not found.
        ValidationError: If file format is invalid.
    """
    try:
        project = load_project_from_file(request.path)
        # Add to in-memory storage
        save_project(project)
        logger.info(f"Opened project from file: {request.path}")
        return project
    except ProjectVersionError as e:
        raise ValidationError(str(e))
    except ProjectValidationError as e:
        raise ValidationError(str(e))
    except ProjectIOError as e:
        raise NotFoundError("ProjectFile", request.path)


@router.get(
    "/info",
    response_model=dict[str, Any],
    summary="Get project file info",
    description="Get information about a project file without fully loading it.",
)
async def get_file_info(
    path: str = Query(..., description="Path to the .alproj file"),
) -> dict[str, Any]:
    """Get information about a project file.

    Args:
        path: Path to the .alproj file.

    Returns:
        Project file summary information.

    Raises:
        NotFoundError: If file not found.
    """
    try:
        return get_project_info(path)
    except ProjectIOError as e:
        raise NotFoundError("ProjectFile", path)


# =============================================================================
# Project CRUD Endpoints
# =============================================================================


@router.get(
    "/{project_id}",
    response_model=Project,
    summary="Get project by ID",
    description="Retrieve a project by its UUID.",
)
async def get_project_by_id(project_id: UUID) -> Project:
    """Get a project by ID.

    Args:
        project_id: Project UUID.

    Returns:
        The requested project.

    Raises:
        NotFoundError: If project doesn't exist.
    """
    project = get_project(str(project_id))
    if project is None:
        raise NotFoundError("Project", project_id)
    return project


@router.put(
    "/{project_id}",
    response_model=Project,
    summary="Update project",
    description="Update project name, input data, or camera parameters.",
)
async def update_project(
    project_id: UUID,
    request: UpdateProjectRequest,
) -> Project:
    """Update a project.

    Args:
        project_id: Project UUID.
        request: Update request with optional fields.

    Returns:
        The updated project.

    Raises:
        NotFoundError: If project doesn't exist.
        ValidationError: If update data is invalid.
    """
    project = get_project(str(project_id))
    if project is None:
        raise NotFoundError("Project", project_id)

    # Update fields if provided
    if request.name is not None:
        project.name = request.name

    if request.input_data is not None:
        project.input_data = request.input_data

    if "camera_params" in request.model_fields_set:
        project.camera_params = request.camera_params
        # Reset processing status when camera params change
        if request.camera_params is not None and project.status == ProjectStatus.COMPLETED:
            project.status = ProjectStatus.DRAFT
            logger.info(f"Project {project_id} status reset to DRAFT due to camera param change")

    if "camera_simulation" in request.model_fields_set:
        project.camera_simulation = request.camera_simulation

    if "process_result" in request.model_fields_set:
        project.process_result = request.process_result
        # Update status based on process result
        if project.process_result and project.process_result.gcps:
            project.status = ProjectStatus.COMPLETED
        elif project.status == ProjectStatus.COMPLETED:
            project.status = ProjectStatus.DRAFT

    if "matching_result" in request.model_fields_set:
        project.matching_result = request.matching_result

    if "estimation_result" in request.model_fields_set:
        project.estimation_result = request.estimation_result

    # Save updated project
    save_project(project)
    logger.info(f"Project {project_id} updated")

    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
    description="Delete a project from the current session. Saved files are not affected.",
)
async def delete_project(project_id: UUID) -> None:
    """Delete a project from the current session.

    Args:
        project_id: Project UUID.

    Raises:
        NotFoundError: If project doesn't exist.

    Note:
        This only removes the project from memory.
        Saved .alproj files are not affected.
    """
    if not delete_project_from_memory(str(project_id)):
        raise NotFoundError("Project", project_id)
    logger.info(f"Deleted project: {project_id}")


@router.post(
    "/{project_id}/save",
    response_model=SaveProjectResponse,
    summary="Save project to file",
    description="Save a project to a .alproj file.",
)
async def save_project_to_path(
    project_id: UUID,
    path: str = Query(..., description="Destination file path"),
) -> SaveProjectResponse:
    """Save a project to a .alproj file.

    Args:
        project_id: Project UUID.
        path: Destination file path.

    Returns:
        Response with saved file path.

    Raises:
        NotFoundError: If project doesn't exist.
        ValidationError: If file cannot be saved.
    """
    project = get_project(str(project_id))
    if project is None:
        raise NotFoundError("Project", project_id)

    try:
        save_project_to_file(project, path)
        logger.info(f"Saved project {project_id} to {path}")
        return SaveProjectResponse(path=path, message="Project saved successfully")
    except ProjectIOError as e:
        raise ValidationError(f"Failed to save project: {e}")


@router.post(
    "/{project_id}/update-gcps",
    response_model=Project,
    summary="Update project GCPs",
    description="Update the GCP list for a project.",
)
async def update_project_gcps(
    project_id: UUID,
    request: UpdateGcpsRequest,
) -> Project:
    """Update GCPs for a project.

    Args:
        project_id: Project UUID.
        request: GCP update request.

    Returns:
        The updated project.

    Raises:
        NotFoundError: If project doesn't exist.
        ValidationError: If project has no process result.
    """
    project = get_project(str(project_id))
    if project is None:
        raise NotFoundError("Project", project_id)

    if project.process_result is None:
        raise ValidationError("Project has no processing result to update GCPs for")

    # Update GCPs in process result
    project.process_result.gcps = request.gcps

    # Recalculate metrics based on enabled GCPs
    enabled_gcps = [gcp for gcp in request.gcps if gcp.enabled]
    if enabled_gcps:
        import numpy as np

        residuals = [gcp.residual for gcp in enabled_gcps if gcp.residual is not None]
        if residuals:
            residuals_arr = np.array(residuals)
            project.process_result.metrics.rmse = float(np.sqrt(np.mean(residuals_arr**2)))
            project.process_result.metrics.gcp_count = len(enabled_gcps)
            project.process_result.metrics.residual_mean = float(np.mean(residuals_arr))
            project.process_result.metrics.residual_std = float(np.std(residuals_arr))
            project.process_result.metrics.residual_max = float(np.max(residuals_arr))

    # Save updated project
    save_project(project)
    logger.info(f"Project {project_id} GCPs updated ({len(request.gcps)} GCPs)")

    return project


# =============================================================================
# Reprocess Endpoint
# =============================================================================


@router.post(
    "/reprocess",
    response_model=ReprocessJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reprocess from a specific step",
    description="Start partial reprocessing from a specified step.",
)
async def reprocess(
    request: ReprocessRequest,
    job_queue: JobQueue = Depends(get_job_queue_dep),
) -> ReprocessJobResponse:
    """Start partial reprocessing from a specific step.

    Args:
        request: Reprocessing request with project ID and step.
        job_queue: Job queue dependency.

    Returns:
        Job information including ID for status tracking.

    Raises:
        NotFoundError: If project doesn't exist.
        ValidationError: If project state is invalid for reprocessing.
    """
    project = get_project(str(request.project_id))
    if project is None:
        raise NotFoundError("Project", request.project_id)

    # Validate project state
    if request.from_step != "matching" and project.process_result is None:
        raise ValidationError(
            f"Cannot reprocess from '{request.from_step}' without prior processing results"
        )

    # Import reprocessing service
    from app.services.georectify import reprocess_from_step

    # Define the job function
    async def reprocess_job(job: Job) -> dict:
        """Execute reprocessing as a background job."""

        async def progress_callback(progress: float, step: str, message: str) -> None:
            await job.update_progress(progress, step, message)

        return await reprocess_from_step(
            project=project,
            from_step=request.from_step,
            options=request.options,
            progress_callback=progress_callback,
        )

    # Submit job to queue
    job = await job_queue.submit(reprocess_job)

    logger.info(
        f"Submitted reprocess job {job.id} for project {request.project_id} "
        f"from step '{request.from_step}'"
    )

    return ReprocessJobResponse(
        id=job.id,
        status=JobStatus(job.status.value),
        created_at=job.created_at.isoformat(),
    )


# =============================================================================
# Report Endpoint
# =============================================================================


@router.get(
    "/{project_id}/report",
    summary="Get project processing report",
    description="Generate a processing report for the project in JSON or text format.",
    responses={
        200: {
            "description": "Processing report",
            "content": {
                "application/json": {"example": {"project": {"name": "example"}}},
                "text/plain": {"example": "GEORECTIFICATION REPORT..."},
            },
        },
        404: {"description": "Project not found"},
    },
)
async def get_project_report(
    project_id: UUID,
    format: str = Query(
        default="json",
        pattern="^(json|text)$",
        description="Report format: 'json' or 'text'",
    ),
) -> Any:
    """Generate a processing report for a project.

    Args:
        project_id: Project UUID.
        format: Output format ('json' or 'text').

    Returns:
        Report in the requested format.

    Raises:
        NotFoundError: If project doesn't exist.
    """
    from fastapi.responses import PlainTextResponse, JSONResponse

    project = get_project(str(project_id))
    if project is None:
        raise NotFoundError("Project", project_id)

    report_content = generate_report(project, format=format)

    if format == "text":
        return PlainTextResponse(content=report_content, media_type="text/plain")
    else:
        import json
        return JSONResponse(content=json.loads(report_content))
