"""Pydantic schemas for Camera-related models."""

from pydantic import BaseModel, Field


class CameraParamsValues(BaseModel):
    """Camera parameters including position, orientation, and lens distortion."""

    # Position (in project CRS)
    x: float = Field(..., description="Camera X coordinate")
    y: float = Field(..., description="Camera Y coordinate")
    z: float = Field(..., description="Camera Z coordinate (elevation)")

    # Orientation
    fov: float = Field(..., ge=1.0, le=180.0, description="Field of view in degrees (1-180)")
    pan: float = Field(..., ge=0.0, le=360.0, description="Pan/azimuth angle in degrees (0-360)")
    tilt: float = Field(
        ..., ge=-90.0, le=90.0, description="Tilt/pitch angle in degrees (-90 to 90)"
    )
    roll: float = Field(..., ge=-180.0, le=180.0, description="Roll angle in degrees (-180 to 180)")

    # Lens distortion coefficients (rational model)
    a1: float = Field(default=1.0, description="Aspect ratio coefficient")
    a2: float = Field(default=1.0, description="Second aspect coefficient")

    # Radial distortion
    k1: float = Field(default=0.0, description="Radial distortion k1")
    k2: float = Field(default=0.0, description="Radial distortion k2")
    k3: float = Field(default=0.0, description="Radial distortion k3")
    k4: float = Field(default=0.0, description="Radial distortion k4")
    k5: float = Field(default=0.0, description="Radial distortion k5")
    k6: float = Field(default=0.0, description="Radial distortion k6")

    # Tangential distortion
    p1: float = Field(default=0.0, description="Tangential distortion p1")
    p2: float = Field(default=0.0, description="Tangential distortion p2")

    # Thin prism distortion
    s1: float = Field(default=0.0, description="Thin prism distortion s1")
    s2: float = Field(default=0.0, description="Thin prism distortion s2")
    s3: float = Field(default=0.0, description="Thin prism distortion s3")
    s4: float = Field(default=0.0, description="Thin prism distortion s4")

    # Principal point offset
    cx: float | None = Field(default=None, description="Principal point X offset from center")
    cy: float | None = Field(default=None, description="Principal point Y offset from center")


class CameraParams(BaseModel):
    """Container for initial and optimized camera parameters."""

    initial: CameraParamsValues | None = Field(
        default=None, description="Initial (user-provided) camera parameters"
    )
    optimized: CameraParamsValues | None = Field(
        default=None, description="Optimized camera parameters after processing"
    )


class SimulationRequest(BaseModel):
    """Request body for generating a simulation image."""

    dsm_path: str = Field(..., description="Path to DSM file")
    ortho_path: str = Field(..., description="Path to orthophoto file")
    target_image_path: str = Field(..., description="Path to target photograph")
    camera_params: CameraParamsValues = Field(..., description="Camera parameters")
    max_size: int = Field(
        default=800, ge=100, le=4096, description="Maximum output image size (pixels)"
    )
    surface_distance: float = Field(
        default=2000.0,
        ge=100.0,
        le=10000.0,
        description="Surface extraction distance from camera (meters). Will be auto-adjusted if too large.",
    )


class SimulationResponse(BaseModel):
    """Response containing a simulation image."""

    image_base64: str = Field(..., description="Base64-encoded PNG image")
