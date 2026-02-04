"""Pydantic schemas for Project-related models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """Project status enumeration."""

    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class ExifData(BaseModel):
    """EXIF metadata extracted from an image file."""

    model_config = {"populate_by_name": True}

    taken_at: datetime | None = Field(
        default=None,
        alias="datetime",
        serialization_alias="datetime",
        description="Date and time the image was taken",
    )
    gps_lat: float | None = Field(default=None, description="GPS latitude")
    gps_lon: float | None = Field(default=None, description="GPS longitude")
    gps_alt: float | None = Field(default=None, description="GPS altitude (m)")
    focal_length: float | None = Field(default=None, description="Focal length (mm)")
    camera_model: str | None = Field(default=None, description="Camera model name")


class RasterFile(BaseModel):
    """Raster file information (DSM or ortho image)."""

    path: str = Field(..., description="File path")
    crs: str = Field(..., description="Coordinate reference system (e.g., EPSG:6690)")
    bounds: tuple[float, float, float, float] = Field(
        ..., description="Bounding box [xmin, ymin, xmax, ymax] in native CRS"
    )
    bounds_wgs84: tuple[float, float, float, float] | None = Field(
        default=None, description="Bounding box [xmin, ymin, xmax, ymax] in WGS84 (EPSG:4326)"
    )
    resolution: tuple[float, float] = Field(..., description="Pixel resolution [x, y] in CRS units")
    size: tuple[int, int] = Field(..., description="Image size [width, height]")


class ImageFile(BaseModel):
    """Image file information (target photograph)."""

    path: str = Field(..., description="File path")
    size: tuple[int, int] = Field(..., description="Image size [width, height]")
    exif: ExifData | None = Field(default=None, description="EXIF metadata if available")


class InputData(BaseModel):
    """Input data for georectification."""

    dsm: RasterFile | None = Field(default=None, description="Digital Surface Model file")
    ortho: RasterFile | None = Field(default=None, description="Orthophoto/aerial image file")
    target_image: ImageFile | None = Field(default=None, description="Target mountain photograph")


class ProjectSummary(BaseModel):
    """Summary of a project for listing."""

    id: UUID = Field(..., description="Project unique identifier")
    name: str = Field(..., description="Project name")
    status: ProjectStatus = Field(..., description="Current project status")
    updated_at: datetime = Field(..., description="Last update timestamp")


class Project(BaseModel):
    """Full project model with all details."""

    id: UUID = Field(..., description="Project unique identifier")
    version: str = Field(default="1.0.0", description="Project file version")
    name: str = Field(..., description="Project name")
    status: ProjectStatus = Field(default=ProjectStatus.DRAFT, description="Current project status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    input_data: InputData = Field(default_factory=InputData, description="Input files and data")
    camera_params: Optional["CameraParams"] = Field(
        default=None, description="Camera parameters (initial and optimized)"
    )
    camera_simulation: str | None = Field(
        default=None, description="Camera setup simulation preview image (data URL/base64)"
    )
    process_result: Optional["ProcessResult"] = Field(
        default=None, description="Processing results if completed"
    )


class CreateProjectRequest(BaseModel):
    """Request body for creating a new project."""

    name: str = Field(..., min_length=1, max_length=255, description="Project name (1-255 chars)")


class UpdateProjectRequest(BaseModel):
    """Request body for updating a project."""

    name: str | None = Field(
        default=None, min_length=1, max_length=255, description="New project name"
    )
    input_data: InputData | None = Field(default=None, description="Updated input data")
    camera_params: Optional["CameraParams"] = Field(
        default=None, description="Updated camera parameters"
    )
    camera_simulation: str | None = Field(
        default=None, description="Updated camera setup simulation preview image"
    )
    process_result: Optional["ProcessResult"] = Field(
        default=None, description="Updated processing results"
    )


# Avoid circular imports by using forward references
from app.schemas.camera import CameraParams  # noqa: E402
from app.schemas.gcp import ProcessResult  # noqa: E402

Project.model_rebuild()
UpdateProjectRequest.model_rebuild()
