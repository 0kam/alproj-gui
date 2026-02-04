"""Schemas for stepwise georectification endpoints."""

from pydantic import BaseModel, Field

from app.schemas.camera import CameraParamsValues


class MatchRequest(BaseModel):
    """Request body for image matching step."""

    dsm_path: str = Field(..., description="Path to DSM file")
    ortho_path: str = Field(..., description="Path to orthophoto file")
    target_image_path: str = Field(..., description="Path to target photograph")
    camera_params: CameraParamsValues = Field(..., description="Initial camera parameters")
    matching_method: str = Field(
        default="superpoint-lightglue",
        pattern="^(akaze|sift|superpoint-lightglue|minima-roma|tiny-roma)$",
        description="Image matching method",
    )
    outlier_filter: str | None = Field(
        default="fundamental",
        description="Outlier filter type (e.g., fundamental, essential)",
    )
    spatial_thin_grid: int | None = Field(
        default=50,
        ge=1,
        description="Spatial thinning grid size for matches",
    )
    spatial_thin_selection: str | None = Field(
        default="center",
        description="Spatial thinning selection strategy (e.g., center, random)",
    )
    resize: int | str | None = Field(
        default=None,
        description="Resize longest edge for matching (integer pixels or 'none')",
    )
    threshold: float = Field(
        default=30.0, ge=0.0, description="Matching threshold (method-dependent)"
    )
    surface_distance: float = Field(
        default=3000.0,
        ge=0.0,
        description="Surface extraction distance from camera (meters)",
    )
    simulation_min_distance: float = Field(
        default=100.0,
        ge=0.0,
        description="Minimum distance to render in simulation (meters)",
    )


class MatchResponse(BaseModel):
    """Response for image matching step."""

    match_plot_base64: str = Field(..., description="Base64-encoded matching plot image (PNG)")
    match_count: int | None = Field(default=None, description="Number of matched points")
    match_id: str | None = Field(
        default=None,
        description="Cached match ID for reusing Step 3 results in estimation",
    )
    log: list[str] = Field(default_factory=list, description="Log messages")


class EstimateRequest(BaseModel):
    """Request body for camera parameter estimation step."""

    dsm_path: str = Field(..., description="Path to DSM file")
    ortho_path: str = Field(..., description="Path to orthophoto file")
    target_image_path: str = Field(..., description="Path to target photograph")
    camera_params: CameraParamsValues = Field(..., description="Initial camera parameters")
    matching_method: str = Field(
        default="superpoint-lightglue",
        pattern="^(akaze|sift|superpoint-lightglue|minima-roma|tiny-roma)$",
        description="Image matching method",
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
    match_id: str | None = Field(
        default=None,
        description="Cached match ID from Step 3 to reuse matching results",
    )
    two_stage: bool = Field(
        default=False,
        description="Enable two-stage estimation (non-distortion, then distortion)",
    )
    outlier_filter: str | None = Field(
        default="fundamental",
        description="Outlier filter type (e.g., fundamental, essential)",
    )
    spatial_thin_grid: int | None = Field(
        default=50,
        ge=1,
        description="Spatial thinning grid size for matches",
    )
    spatial_thin_selection: str | None = Field(
        default="center",
        description="Spatial thinning selection strategy (e.g., center, random)",
    )
    resize: int | str | None = Field(
        default=None,
        description="Resize longest edge for matching (integer pixels or 'none')",
    )
    threshold: float = Field(
        default=30.0, ge=0.0, description="Matching threshold (method-dependent)"
    )
    surface_distance: float = Field(
        default=3000.0,
        ge=0.0,
        description="Surface extraction distance from camera (meters)",
    )
    simulation_min_distance: float = Field(
        default=100.0,
        ge=0.0,
        description="Minimum distance to render in simulation (meters)",
    )
    optimize_position: bool = Field(
        default=True,
        description="Optimize camera position (x, y, z)",
    )
    optimize_orientation: bool = Field(
        default=True,
        description="Optimize camera orientation (pan, tilt, roll)",
    )
    optimize_fov: bool = Field(
        default=True,
        description="Optimize field of view (fov, a1, a2)",
    )
    optimize_distortion: bool = Field(
        default=True,
        description="Optimize distortion parameters (k, p, s)",
    )


class EstimateResponse(BaseModel):
    """Response for camera parameter estimation step."""

    simulation_base64: str = Field(
        ..., description="Base64-encoded simulation image (PNG)"
    )
    optimized_params: CameraParamsValues | None = Field(
        default=None, description="Optimized camera parameters"
    )
    log: list[str] = Field(default_factory=list, description="Log messages")
