"""Project model for alproj-gui backend.

This module defines the Project model and related data structures for
georectification workflow management.
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from backend.app.models.camera import CameraParams
from backend.app.models.gcp import ProcessResult
from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """Project processing status."""

    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class BoundingBox(BaseModel):
    """Geographic bounding box (xmin, ymin, xmax, ymax)."""

    xmin: float = Field(..., description="Minimum X coordinate")
    ymin: float = Field(..., description="Minimum Y coordinate")
    xmax: float = Field(..., description="Maximum X coordinate")
    ymax: float = Field(..., description="Maximum Y coordinate")


class RasterFile(BaseModel):
    """GeoTIFF file reference with metadata.

    Represents a georeferenced raster file (DSM or ortho image).
    """

    path: str = Field(..., description="File path")
    crs: str = Field(..., description="Coordinate Reference System (EPSG code)")
    bounds: BoundingBox = Field(..., description="Geographic bounds")
    resolution: tuple[float, float] = Field(..., description="Resolution (x, y) in CRS units")
    size: tuple[int, int] = Field(..., description="Pixel size (width, height)")


class ExifData(BaseModel):
    """EXIF metadata extracted from image file."""

    datetime: datetime | None = Field(None, description="Capture datetime")
    gps_lat: float | None = Field(None, description="GPS latitude")
    gps_lon: float | None = Field(None, description="GPS longitude")
    gps_alt: float | None = Field(None, description="GPS altitude (meters)")
    focal_length: float | None = Field(None, description="Focal length (mm)")
    camera_model: str | None = Field(None, description="Camera model name")


class ImageFile(BaseModel):
    """Target image file reference with metadata.

    Represents the mountain photograph to be georectified.
    """

    path: str = Field(..., description="File path")
    size: tuple[int, int] = Field(..., description="Pixel size (width, height)")
    exif: ExifData | None = Field(None, description="EXIF metadata")


class InputData(BaseModel):
    """Input data set for georectification.

    Contains references to all required input files:
    - DSM (Digital Surface Model)
    - Ortho (aerial/satellite imagery)
    - Target image (mountain photograph)
    """

    dsm: RasterFile = Field(..., description="Digital Surface Model file")
    ortho: RasterFile = Field(..., description="Ortho image file")
    target_image: ImageFile = Field(..., description="Target mountain photograph")


class Project(BaseModel):
    """Georectification project.

    Represents a complete georectification workflow including:
    - Input data (DSM, ortho, target image)
    - Camera parameters (initial and optimized)
    - Processing results (GCPs, metrics, output GeoTIFF)

    State transitions:
        draft --(start processing)--> processing --(success)--> completed
                                           |
                                           +---(failure)--> error
    """

    id: UUID = Field(default_factory=uuid4, description="Unique project identifier")
    version: str = Field(default="1.0.0", description="Schema version (semver)")
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp (UTC)",
    )
    input_data: InputData = Field(..., description="Input data set")
    camera_params: CameraParams | None = Field(
        None, description="Camera parameters (initial and optimized)"
    )
    process_result: ProcessResult | None = Field(None, description="Processing results")
    status: ProjectStatus = Field(
        default=ProjectStatus.DRAFT, description="Project processing status"
    )

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time."""
        self.updated_at = datetime.now(UTC)
