"""File API routes for raster and image information.

Provides endpoints for:
- POST /api/files/raster/info - Get GeoTIFF metadata
- POST /api/files/raster/thumbnail - Generate raster thumbnail
- POST /api/files/image/info - Get image metadata with EXIF
- POST /api/files/image/thumbnail - Generate image thumbnail
- POST /api/files/transform - Transform coordinates between CRS
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, Field
from app.schemas import ImageFile, RasterFile
from app.services.raster import (
    get_dsm_elevation,
    get_image_info,
    get_image_thumbnail,
    get_raster_info,
    get_raster_thumbnail,
    validate_raster_pair_crs,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])


# =============================================================================
# Request Models
# =============================================================================


class FilePathRequest(BaseModel):
    """Request body containing a file path."""

    path: str = Field(..., description="Absolute path to the file")


class RasterInfoRequest(BaseModel):
    """Request body for raster info with optional pair validation."""

    path: str = Field(..., description="Absolute path to the raster file")
    other_path: str | None = Field(
        default=None, description="Optional other raster path for CRS validation"
    )


class ThumbnailRequest(BaseModel):
    """Request body for thumbnail generation."""

    path: str = Field(..., description="Absolute path to the raster file")
    max_size: int = Field(
        default=256,
        ge=32,
        le=1024,
        description="Maximum thumbnail dimension (32-1024 pixels)",
    )


class CoordinateTransformRequest(BaseModel):
    """Request body for coordinate transformation."""

    x: float = Field(..., description="X coordinate (longitude in WGS84)")
    y: float = Field(..., description="Y coordinate (latitude in WGS84)")
    src_crs: str = Field(default="EPSG:4326", description="Source CRS (default: WGS84)")
    dst_crs: str = Field(..., description="Destination CRS (e.g., EPSG:3099)")


class CoordinateTransformResponse(BaseModel):
    """Response body for coordinate transformation."""

    x: float = Field(..., description="Transformed X coordinate")
    y: float = Field(..., description="Transformed Y coordinate")


class ElevationRequest(BaseModel):
    """Request body for elevation lookup from DSM."""

    dsm_path: str = Field(..., description="Path to DSM file")
    x: float = Field(..., description="X coordinate in DSM's native CRS")
    y: float = Field(..., description="Y coordinate in DSM's native CRS")


class ElevationResponse(BaseModel):
    """Response body for elevation lookup."""

    elevation: float | None = Field(..., description="Elevation value at the coordinate (None if outside DSM bounds)")
    unit: str = Field(default="meters", description="Unit of elevation")


# =============================================================================
# Raster Endpoints
# =============================================================================


@router.post("/raster/info", response_model=RasterFile)
async def get_raster_file_info(request: RasterInfoRequest) -> RasterFile:
    """Get metadata from a GeoTIFF raster file.

    Returns CRS, bounds, resolution, and size information.

    Args:
        request: Request containing the file path.

    Returns:
        RasterFile with metadata.

    Raises:
        400: If file not found or invalid raster format.
    """
    logger.info(f"Getting raster info for: {request.path}")
    if request.other_path:
        validate_raster_pair_crs(request.path, request.other_path)
    return get_raster_info(request.path)


@router.post("/raster/thumbnail")
async def get_raster_file_thumbnail(request: ThumbnailRequest) -> Response:
    """Generate a PNG thumbnail from a raster file.

    Args:
        request: Request containing file path and max size.

    Returns:
        PNG image response.

    Raises:
        400: If file not found or thumbnail generation fails.
    """
    logger.info(f"Generating thumbnail for: {request.path} (max_size={request.max_size})")
    thumbnail_bytes = get_raster_thumbnail(request.path, request.max_size)
    return Response(
        content=thumbnail_bytes,
        media_type="image/png",
    )


# =============================================================================
# Image Endpoints
# =============================================================================


@router.post("/image/info", response_model=ImageFile)
async def get_image_file_info(request: FilePathRequest) -> ImageFile:
    """Get metadata from an image file including EXIF data.

    Returns image size and optional EXIF metadata (GPS, focal length, etc.).

    Args:
        request: Request containing the file path.

    Returns:
        ImageFile with metadata and EXIF.

    Raises:
        400: If file not found or invalid image format.
    """
    logger.info(f"Getting image info for: {request.path}")
    return get_image_info(request.path)


@router.post("/image/thumbnail")
async def get_image_file_thumbnail(request: ThumbnailRequest) -> Response:
    """Generate a PNG thumbnail from an image file.

    Args:
        request: Request containing file path and max size.

    Returns:
        PNG image response.

    Raises:
        400: If file not found or thumbnail generation fails.
    """
    logger.info(f"Generating image thumbnail for: {request.path} (max_size={request.max_size})")
    thumbnail_bytes = get_image_thumbnail(request.path, request.max_size)
    return Response(
        content=thumbnail_bytes,
        media_type="image/png",
    )


@router.post("/image/full")
async def get_image_file_full(request: FilePathRequest) -> Response:
    """Get full-size image file.

    Args:
        request: Request containing file path.

    Returns:
        Image file response with appropriate media type.

    Raises:
        400: If file not found.
    """
    from pathlib import Path

    file_path = Path(request.path)
    logger.info(f"Getting full image for: {request.path}")

    if not file_path.exists():
        from app.core.exceptions import FileError

        raise FileError(f"File not found: {request.path}", path=request.path)

    # Determine media type from extension
    suffix = file_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    content = file_path.read_bytes()
    return Response(
        content=content,
        media_type=media_type,
    )


# =============================================================================
# Coordinate Transformation Endpoints
# =============================================================================


@router.post("/transform", response_model=CoordinateTransformResponse)
async def transform_coordinates(request: CoordinateTransformRequest) -> CoordinateTransformResponse:
    """Transform coordinates from one CRS to another.

    Primarily used to convert WGS84 (EPSG:4326) coordinates from map clicks
    to the native CRS of the raster data.

    Args:
        request: Request containing coordinates and CRS information.

    Returns:
        Transformed coordinates.

    Raises:
        400: If CRS is invalid or transformation fails.
    """
    logger.info(f"Transforming ({request.x}, {request.y}) from {request.src_crs} to {request.dst_crs}")

    try:
        from pyproj import CRS, Transformer

        src_crs = CRS.from_user_input(request.src_crs)
        dst_crs = CRS.from_user_input(request.dst_crs)
        transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)

        x_out, y_out = transformer.transform(request.x, request.y)

        return CoordinateTransformResponse(x=x_out, y=y_out)

    except Exception as e:
        logger.exception(f"Coordinate transformation failed: {e}")
        raise ValueError(f"Coordinate transformation failed: {e}") from e


@router.post("/raster/elevation", response_model=ElevationResponse)
async def get_elevation_from_dsm(request: ElevationRequest) -> ElevationResponse:
    """Get elevation value from DSM at a specific coordinate.

    Useful for automatically fetching terrain height when setting camera position.

    Args:
        request: Request containing DSM path and coordinates.

    Returns:
        Elevation value and unit.

    Raises:
        400: If DSM file not found or coordinate is outside bounds.
    """
    logger.info(f"Getting elevation from DSM at ({request.x}, {request.y})")

    elevation = get_dsm_elevation(request.dsm_path, request.x, request.y)

    return ElevationResponse(elevation=elevation, unit="meters")
