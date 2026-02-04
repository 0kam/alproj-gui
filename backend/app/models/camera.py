"""Camera parameters model for alproj-gui backend.

This module defines camera parameter structures used for georectification,
including position, orientation, field of view, and lens distortion coefficients.
"""

from pydantic import BaseModel, Field


class CameraParamsValues(BaseModel):
    """Camera parameter values for georectification.

    Contains all parameters needed to define camera position, orientation,
    and lens characteristics including distortion coefficients.

    Coordinate System:
        - Position (x, y, z) is in the CRS units (typically meters)
        - Angles are in degrees

    Validation Rules:
        - x, y: Should be within DSM/Ortho bounds
        - z: Must be >= 0
        - fov: 1-180 degrees
        - pan: 0-360 degrees (0=North, 90=East)
        - tilt: -90 to 90 degrees (0=horizontal)
        - roll: -180 to 180 degrees
    """

    # Camera position
    x: float = Field(..., description="Camera position X (CRS units, typically meters)")
    y: float = Field(..., description="Camera position Y (CRS units, typically meters)")
    z: float = Field(..., ge=0, description="Camera position Z / altitude (meters)")

    # Camera orientation
    fov: float = Field(..., ge=1, le=180, description="Field of view (degrees)")
    pan: float = Field(
        ..., ge=0, le=360, description="Pan angle / azimuth (degrees, 0=North, 90=East)"
    )
    tilt: float = Field(..., ge=-90, le=90, description="Tilt angle (degrees, 0=horizontal)")
    roll: float = Field(..., ge=-180, le=180, description="Roll angle (degrees)")

    # Distortion coefficients (all optional)
    a1: float | None = Field(None, description="Distortion coefficient a1")
    a2: float | None = Field(None, description="Distortion coefficient a2")

    # Radial distortion coefficients
    k1: float | None = Field(None, description="Radial distortion coefficient k1")
    k2: float | None = Field(None, description="Radial distortion coefficient k2")
    k3: float | None = Field(None, description="Radial distortion coefficient k3")
    k4: float | None = Field(None, description="Radial distortion coefficient k4")
    k5: float | None = Field(None, description="Radial distortion coefficient k5")
    k6: float | None = Field(None, description="Radial distortion coefficient k6")

    # Tangential distortion coefficients
    p1: float | None = Field(None, description="Tangential distortion coefficient p1")
    p2: float | None = Field(None, description="Tangential distortion coefficient p2")

    # Thin prism distortion coefficients
    s1: float | None = Field(None, description="Thin prism distortion coefficient s1")
    s2: float | None = Field(None, description="Thin prism distortion coefficient s2")
    s3: float | None = Field(None, description="Thin prism distortion coefficient s3")
    s4: float | None = Field(None, description="Thin prism distortion coefficient s4")

    # Principal point offset
    cx: float | None = Field(None, description="Principal point X offset (pixels)")
    cy: float | None = Field(None, description="Principal point Y offset (pixels)")


class CameraParams(BaseModel):
    """Camera parameters container with initial and optimized values.

    Contains:
        - initial: User-provided or EXIF-derived initial camera parameters
        - optimized: Parameters after optimization (available after processing)
    """

    initial: CameraParamsValues = Field(..., description="Initial camera parameters (user input)")
    optimized: CameraParamsValues | None = Field(
        None, description="Optimized camera parameters (after processing)"
    )
