"""Data models for alproj-gui backend."""

# Import order matters: camera and gcp first (no dependencies),
# then project (depends on camera and gcp)
from backend.app.models.camera import (
    CameraParams,
    CameraParamsValues,
)
from backend.app.models.gcp import (
    GCP,
    ProcessMetrics,
    ProcessResult,
)
from backend.app.models.project import (
    BoundingBox,
    ExifData,
    ImageFile,
    InputData,
    Project,
    ProjectStatus,
    RasterFile,
)

__all__ = [
    # Project models
    "Project",
    "ProjectStatus",
    "InputData",
    "RasterFile",
    "ImageFile",
    "ExifData",
    "BoundingBox",
    # Camera models
    "CameraParams",
    "CameraParamsValues",
    # GCP models
    "GCP",
    "ProcessResult",
    "ProcessMetrics",
]
