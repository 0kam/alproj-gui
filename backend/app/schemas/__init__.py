"""Pydantic schemas for API request/response models."""

from app.schemas.camera import (
    CameraParams,
    CameraParamsValues,
    SimulationRequest,
    SimulationResponse,
)
from app.schemas.gcp import (
    GCP,
    ProcessMetrics,
    ProcessResult,
)
from app.schemas.georectify import (
    EstimateRequest,
    EstimateResponse,
    MatchRequest,
    MatchResponse,
)
from app.schemas.job import (
    ExportRequest,
    Job,
    JobStatus,
    ProcessOptions,
    ProcessRequest,
)
from app.schemas.project import (
    CreateProjectRequest,
    ExifData,
    ImageFile,
    InputData,
    Project,
    ProjectStatus,
    ProjectSummary,
    RasterFile,
    UpdateProjectRequest,
)

__all__ = [
    # camera
    "CameraParams",
    "CameraParamsValues",
    "SimulationRequest",
    "SimulationResponse",
    # gcp
    "GCP",
    "ProcessMetrics",
    "ProcessResult",
    # georectify (stepwise)
    "EstimateRequest",
    "EstimateResponse",
    "MatchRequest",
    "MatchResponse",
    # job
    "ExportRequest",
    "Job",
    "JobStatus",
    "ProcessOptions",
    "ProcessRequest",
    # project
    "CreateProjectRequest",
    "ExifData",
    "ImageFile",
    "InputData",
    "Project",
    "ProjectStatus",
    "ProjectSummary",
    "RasterFile",
    "UpdateProjectRequest",
]
