"""GCP and processing result models for alproj-gui backend.

This module defines Ground Control Point (GCP) structures and processing
result containers used for georectification accuracy assessment.
"""

from pydantic import BaseModel, Field


class GCP(BaseModel):
    """Ground Control Point (GCP).

    Represents a correspondence between image coordinates and geographic coordinates,
    used for georectification accuracy assessment and optimization.

    Coordinate System:
        - Image coordinates (image_x, image_y) are in pixels
        - Geographic coordinates (geo_x, geo_y, geo_z) are in CRS units (typically meters)
    """

    id: int = Field(..., description="GCP identifier")
    image_x: float = Field(..., description="Image coordinate X (pixels)")
    image_y: float = Field(..., description="Image coordinate Y (pixels)")
    geo_x: float = Field(..., description="Geographic coordinate X (CRS units)")
    geo_y: float = Field(..., description="Geographic coordinate Y (CRS units)")
    geo_z: float = Field(..., description="Geographic coordinate Z / altitude (meters)")
    residual: float | None = Field(None, description="Residual error (pixels)")
    enabled: bool = Field(default=True, description="Whether this GCP is used for optimization")


class ProcessMetrics(BaseModel):
    """Processing accuracy metrics.

    Contains statistical measures of georectification accuracy based on
    GCP residuals.
    """

    rmse: float = Field(..., description="Root Mean Square Error")
    gcp_count: int = Field(..., ge=0, description="Number of GCPs used for optimization")
    gcp_total: int = Field(..., ge=0, description="Total number of detected GCPs")
    residual_mean: float = Field(..., description="Mean residual (pixels)")
    residual_std: float = Field(..., description="Residual standard deviation (pixels)")
    residual_max: float = Field(..., description="Maximum residual (pixels)")


class ProcessResult(BaseModel):
    """Georectification processing result.

    Contains all outputs from a georectification processing run:
    - GCP list with residuals
    - Accuracy metrics
    - Output GeoTIFF path
    - Processing log
    """

    gcps: list[GCP] = Field(default_factory=list, description="Detected GCP list")
    metrics: ProcessMetrics = Field(..., description="Accuracy metrics")
    geotiff_path: str | None = Field(None, description="Output GeoTIFF file path")
    log: list[str] = Field(default_factory=list, description="Processing log entries")
