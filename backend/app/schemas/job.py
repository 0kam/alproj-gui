"""Pydantic schemas for Job management."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.gcp import ProcessResult


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessOptions(BaseModel):
    """Options for georectification processing."""

    matching_method: str = Field(
        default="superpoint-lightglue",
        pattern="^(akaze|sift|superpoint-lightglue|minima-roma|tiny-roma)$",
        description="Image matching algorithm",
    )
    optimizer: str = Field(
        default="cma",
        pattern="^(cma|lsq)$",
        description="Optimization method (CMA-ES or Least Squares)",
    )
    max_generations: int = Field(
        default=300, ge=10, le=10000, description="Maximum optimizer generations"
    )
    min_gcp_distance: float = Field(
        default=100.0,
        ge=0.0,
        description="Minimum GCP distance from camera (meters)",
    )


class ProcessRequest(BaseModel):
    """Request body for starting georectification processing."""

    project_id: str = Field(..., description="Project ID to process")
    options: ProcessOptions | None = Field(
        default_factory=ProcessOptions, description="Processing options"
    )


class ExportRequest(BaseModel):
    """Request body for exporting GeoTIFF."""

    project_id: str = Field(..., description="Project ID to export")
    output_path: str | None = Field(
        default=None,
        description="Output file path (single-image export mode)",
    )
    target_image_path: str | None = Field(
        default=None,
        description="Optional alternate target image path for single-image export",
    )
    target_image_paths: list[str] | None = Field(
        default=None,
        description="Optional list of target image paths for batch export",
    )
    output_dir: str | None = Field(
        default=None,
        description="Output directory for batch export",
    )
    output_name_template: str | None = Field(
        default=None,
        description="Output filename template for batch export ({name}, {date}, {index})",
    )
    resolution: float = Field(default=1.0, gt=0.0, description="Output resolution (m/pixel)")
    crs: str = Field(default="EPSG:6690", description="Output coordinate reference system")
    interpolate: bool = Field(default=True, description="Enable interpolation for smoother output")
    max_dist: float | None = Field(
        default=None,
        ge=0.0,
        description="Maximum interpolation distance (meters). Defaults to resolution if not specified.",
    )
    surface_distance: float = Field(
        default=3000.0,
        ge=0.0,
        description="Surface extraction distance from camera (meters)",
    )
    template_path: str | None = Field(
        default=None,
        description="Optional template raster path for georeferencing (e.g., orthophoto)",
    )


class Job(BaseModel):
    """Asynchronous job status and result."""

    id: UUID = Field(..., description="Job unique identifier")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Current job status")
    progress: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Progress ratio (0.0 to 1.0)"
    )
    step: str | None = Field(default=None, description="Current processing step name")
    message: str | None = Field(default=None, description="Current status message")
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: datetime | None = Field(default=None, description="Job completion timestamp")
    error: str | None = Field(default=None, description="Error message if failed")
    result: ProcessResult | None = Field(default=None, description="Processing result if completed")
