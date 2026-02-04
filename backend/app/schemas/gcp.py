"""Pydantic schemas for GCP (Ground Control Points) and process results."""

from pydantic import BaseModel, Field


class GCP(BaseModel):
    """Ground Control Point linking image and geographic coordinates."""

    id: int = Field(..., description="GCP identifier")
    image_x: float = Field(..., description="X coordinate in image (pixels)")
    image_y: float = Field(..., description="Y coordinate in image (pixels)")
    geo_x: float = Field(..., description="X coordinate in geographic CRS")
    geo_y: float = Field(..., description="Y coordinate in geographic CRS")
    geo_z: float = Field(..., description="Z coordinate / elevation (m)")
    residual: float | None = Field(
        default=None, description="Residual error after optimization (pixels)"
    )
    enabled: bool = Field(default=True, description="Whether this GCP is used")


class ProcessMetrics(BaseModel):
    """Processing quality metrics."""

    rmse: float = Field(..., description="Root mean square error (pixels)")
    gcp_count: int = Field(..., ge=0, description="Number of enabled GCPs used")
    gcp_total: int = Field(..., ge=0, description="Total number of GCPs detected")
    residual_mean: float | None = Field(default=None, description="Mean residual (pixels)")
    residual_std: float | None = Field(
        default=None, description="Standard deviation of residuals (pixels)"
    )
    residual_max: float | None = Field(default=None, description="Maximum residual (pixels)")


class ProcessResult(BaseModel):
    """Results from georectification processing."""

    gcps: list[GCP] = Field(
        default_factory=list, description="List of detected ground control points"
    )
    metrics: ProcessMetrics | None = Field(default=None, description="Quality metrics")
    geotiff_path: str | None = Field(default=None, description="Path to output GeoTIFF file")
    log: list[str] = Field(default_factory=list, description="Processing log messages")
