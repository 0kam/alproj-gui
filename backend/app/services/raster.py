"""Raster and image file information services.

Provides functionality for:
- Reading GeoTIFF metadata (CRS, bounds, resolution, size)
- Generating raster thumbnails
- Reading image file information with EXIF data
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    import rasterio
    from PIL import Image
    from pyproj import CRS, Transformer

from app.api.deps import CRSMismatchError, FileError, ValidationError
from app.schemas import ExifData, ImageFile, RasterFile
from app.services.exif import read_exif

logger = logging.getLogger(__name__)

def _format_crs(crs: "rasterio.crs.CRS | None") -> str:
    if not crs:
        return "UNKNOWN"
    epsg = crs.to_epsg()
    if epsg:
        return f"EPSG:{epsg}"
    return crs.to_string() or str(crs)


def _to_pyproj_crs(src_crs: "rasterio.crs.CRS") -> "CRS":
    from pyproj import CRS

    epsg = src_crs.to_epsg()
    if epsg:
        return CRS.from_epsg(epsg)

    wkt = src_crs.to_wkt()
    if wkt:
        return CRS.from_wkt(wkt)

    return CRS.from_user_input(src_crs)


def _validate_projected_meters(
    src_crs: "rasterio.crs.CRS | None",
    path: str,
) -> "CRS":
    import os
    logger.debug(f"[CRS_VALIDATE] path={path}")
    logger.debug(f"[CRS_VALIDATE] PROJ_LIB={os.environ.get('PROJ_LIB', 'NOT SET')}")
    logger.debug(f"[CRS_VALIDATE] PROJ_DATA={os.environ.get('PROJ_DATA', 'NOT SET')}")

    if not src_crs:
        raise ValidationError(
            "CRS is not defined",
            detail=f"Path: {path}",
        )

    logger.debug(f"[CRS_VALIDATE] src_crs={src_crs}")
    logger.debug(f"[CRS_VALIDATE] src_crs.to_epsg()={src_crs.to_epsg()}")

    try:
        pyproj_crs = _to_pyproj_crs(src_crs)
        logger.debug(f"[CRS_VALIDATE] pyproj_crs={pyproj_crs}")
        logger.debug(f"[CRS_VALIDATE] pyproj_crs.is_projected={pyproj_crs.is_projected}")
    except Exception as e:
        logger.error(f"[CRS_VALIDATE] Failed to convert CRS: {e}")
        raise ValidationError(
            "CRS must be a projected coordinate system in meters",
            detail=f"Path: {path}, CRS: {_format_crs(src_crs)}, Error: {e}",
        )

    if not pyproj_crs.is_projected:
        raise ValidationError(
            "CRS must be a projected coordinate system in meters",
            detail=f"Path: {path}, CRS: {_format_crs(src_crs)}",
        )

    units = [axis.unit_name for axis in pyproj_crs.axis_info if axis.unit_name]
    if not units:
        raise ValidationError(
            "CRS unit is undefined",
            detail=f"Path: {path}, CRS: {_format_crs(src_crs)}",
        )

    def _is_meter(unit_name: str) -> bool:
        name = unit_name.lower()
        return "meter" in name or "metre" in name

    if not all(_is_meter(unit) for unit in units):
        raise ValidationError(
            "CRS unit must be meters",
            detail=f"Path: {path}, Units: {', '.join(units)}",
        )

    return pyproj_crs


def validate_raster_pair_crs(path_a: str, path_b: str) -> None:
    import rasterio

    with rasterio.open(path_a) as raster_a, rasterio.open(path_b) as raster_b:
        crs_a = raster_a.crs
        crs_b = raster_b.crs

        pyproj_a = _validate_projected_meters(crs_a, path_a)
        pyproj_b = _validate_projected_meters(crs_b, path_b)

        if not pyproj_a.equals(pyproj_b):
            raise CRSMismatchError(_format_crs(crs_a), _format_crs(crs_b))


def get_raster_info(path: str) -> RasterFile:
    """Read GeoTIFF raster file metadata.

    Args:
        path: Path to the GeoTIFF file.

    Returns:
        RasterFile schema with CRS, bounds, resolution, and size.

    Raises:
        FileError: If file does not exist or is not a valid raster.
    """
    file_path = Path(path)

    if not file_path.exists():
        raise FileError(f"File not found: {path}", path=path)

    try:
        import rasterio

        with rasterio.open(file_path) as dataset:
            _validate_projected_meters(dataset.crs, str(file_path))
            # Get CRS as string (e.g., "EPSG:6690")
            crs_str = _format_crs(dataset.crs)
            logger.debug(f"CRS: {crs_str}")

            # Get bounds (left, bottom, right, top)
            bounds = dataset.bounds
            bounds_tuple = (bounds.left, bounds.bottom, bounds.right, bounds.top)

            # Get resolution (x, y) - absolute values since resolution can be negative
            resolution = (abs(dataset.res[0]), abs(dataset.res[1]))

            # Get size (width, height)
            size = (dataset.width, dataset.height)

            # Convert bounds to WGS84 for map display
            bounds_wgs84 = None
            if dataset.crs:
                try:
                    bounds_wgs84 = _convert_bounds_to_wgs84(bounds_tuple, dataset.crs)
                    logger.debug(f"Bounds WGS84: {bounds_wgs84}")
                except Exception as e:
                    logger.warning(f"Failed to convert bounds to WGS84: {e}")

            return RasterFile(
                path=str(file_path.resolve()),
                crs=crs_str,
                bounds=bounds_tuple,
                bounds_wgs84=bounds_wgs84,
                resolution=resolution,
                size=size,
            )

    except rasterio.errors.RasterioIOError as e:
        raise FileError(f"Failed to read raster file: {e}", path=path) from e
    except Exception as e:
        logger.exception(f"Unexpected error reading raster: {path}")
        raise FileError(f"Failed to read raster file: {e}", path=path) from e


def _convert_bounds_to_wgs84(
    bounds: tuple[float, float, float, float],
    src_crs: "rasterio.crs.CRS",
) -> tuple[float, float, float, float]:
    """Convert bounds from source CRS to WGS84 (EPSG:4326).

    Args:
        bounds: Bounding box [xmin, ymin, xmax, ymax] in source CRS.
        src_crs: Source coordinate reference system.

    Returns:
        Bounding box [xmin, ymin, xmax, ymax] in WGS84 (lon, lat).
    """
    # Create transformer from source CRS to WGS84
    from pyproj import CRS, Transformer

    # Try different methods to create pyproj CRS from rasterio CRS
    src_crs_pyproj = None

    # Method 1: Try EPSG code if available
    epsg = src_crs.to_epsg()
    if epsg:
        try:
            src_crs_pyproj = CRS.from_epsg(epsg)
            logger.debug(f"Created CRS from EPSG:{epsg}")
        except Exception as e:
            logger.debug(f"Failed to create CRS from EPSG:{epsg}: {e}")

    # Method 2: Try WKT string
    if src_crs_pyproj is None:
        try:
            wkt = src_crs.to_wkt()
            if wkt:
                src_crs_pyproj = CRS.from_wkt(wkt)
                logger.debug(f"Created CRS from WKT")
        except Exception as e:
            logger.debug(f"Failed to create CRS from WKT: {e}")

    # Method 3: Fall back to from_user_input
    if src_crs_pyproj is None:
        src_crs_pyproj = CRS.from_user_input(src_crs)
        logger.debug(f"Created CRS from user_input")

    wgs84 = CRS.from_epsg(4326)
    transformer = Transformer.from_crs(src_crs_pyproj, wgs84, always_xy=True)

    xmin, ymin, xmax, ymax = bounds

    # Transform corner points
    lon_min, lat_min = transformer.transform(xmin, ymin)
    lon_max, lat_max = transformer.transform(xmax, ymax)

    # Also check other corners for rotated CRS
    lon1, lat1 = transformer.transform(xmin, ymax)
    lon2, lat2 = transformer.transform(xmax, ymin)

    # Get actual min/max after transformation
    final_lon_min = min(lon_min, lon_max, lon1, lon2)
    final_lat_min = min(lat_min, lat_max, lat1, lat2)
    final_lon_max = max(lon_min, lon_max, lon1, lon2)
    final_lat_max = max(lat_min, lat_max, lat1, lat2)

    return (final_lon_min, final_lat_min, final_lon_max, final_lat_max)


def get_raster_thumbnail(path: str, max_size: int = 256) -> bytes:
    """Generate a thumbnail PNG from a raster file.

    Args:
        path: Path to the raster file (GeoTIFF or other).
        max_size: Maximum dimension for the thumbnail (width or height).

    Returns:
        PNG image bytes.

    Raises:
        FileError: If file does not exist or thumbnail generation fails.
    """
    file_path = Path(path)

    if not file_path.exists():
        raise FileError(f"File not found: {path}", path=path)

    try:
        import numpy as np
        import rasterio
        from PIL import Image

        with rasterio.open(file_path) as dataset:
            # Calculate resampling factor for thumbnail
            width = dataset.width
            height = dataset.height
            scale = min(max_size / width, max_size / height, 1.0)

            out_width = max(1, int(width * scale))
            out_height = max(1, int(height * scale))

            # Read data with resampling
            # Handle different band counts
            count = min(dataset.count, 3)  # Use at most 3 bands for RGB

            if count == 1:
                # Single band - read and normalize to grayscale
                data = dataset.read(
                    1,
                    out_shape=(out_height, out_width),
                    resampling=rasterio.enums.Resampling.bilinear,
                )
                # Normalize to 0-255
                data = _normalize_to_uint8(data)
                # Convert to RGB by repeating channel
                rgb_data = np.stack([data, data, data], axis=-1)

            else:
                # Multi-band - read first 3 bands as RGB
                bands = []
                for i in range(1, count + 1):
                    band_data = dataset.read(
                        i,
                        out_shape=(out_height, out_width),
                        resampling=rasterio.enums.Resampling.bilinear,
                    )
                    bands.append(_normalize_to_uint8(band_data))

                # Pad to 3 channels if needed
                while len(bands) < 3:
                    bands.append(bands[0])

                rgb_data = np.stack(bands[:3], axis=-1)

            # Create PIL Image and save as PNG
            image = Image.fromarray(rgb_data, mode="RGB")

            # Save to bytes buffer
            buffer = io.BytesIO()
            image.save(buffer, format="PNG", optimize=True)
            buffer.seek(0)

            return buffer.getvalue()

    except rasterio.errors.RasterioIOError as e:
        raise FileError(f"Failed to read raster file: {e}", path=path) from e
    except Exception as e:
        logger.exception(f"Unexpected error generating thumbnail: {path}")
        raise FileError(f"Failed to generate thumbnail: {e}", path=path) from e


def _normalize_to_uint8(data: "np.ndarray") -> "np.ndarray":
    """Normalize array to uint8 (0-255) range.

    Args:
        data: Input array with any numeric type.

    Returns:
        uint8 array normalized to 0-255 range.
    """
    # Handle nodata/nan values
    import numpy as np

    valid_mask = ~np.isnan(data) & np.isfinite(data)

    if not valid_mask.any():
        return np.zeros(data.shape, dtype=np.uint8)

    valid_data = data[valid_mask]
    min_val = np.percentile(valid_data, 2)  # Use percentile to avoid outliers
    max_val = np.percentile(valid_data, 98)

    if max_val == min_val:
        # Constant image
        return np.full(data.shape, 128, dtype=np.uint8)

    # Normalize and clip
    normalized = (data - min_val) / (max_val - min_val)
    normalized = np.clip(normalized, 0, 1) * 255

    return normalized.astype(np.uint8)


def get_image_thumbnail(path: str, max_size: int = 256) -> bytes:
    """Generate a thumbnail PNG from an image file.

    Args:
        path: Path to the image file (JPEG, PNG, etc.).
        max_size: Maximum dimension for the thumbnail (width or height).

    Returns:
        PNG image bytes.

    Raises:
        FileError: If file does not exist or thumbnail generation fails.
    """
    file_path = Path(path)

    if not file_path.exists():
        raise FileError(f"File not found: {path}", path=path)

    try:
        from PIL import Image

        with Image.open(file_path) as img:
            # Convert to RGB if necessary (handles RGBA, P, etc.)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Calculate thumbnail size maintaining aspect ratio
            width, height = img.size
            scale = min(max_size / width, max_size / height, 1.0)
            new_width = max(1, int(width * scale))
            new_height = max(1, int(height * scale))

            # Resize using high-quality resampling
            thumbnail = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save to bytes buffer as PNG
            buffer = io.BytesIO()
            thumbnail.save(buffer, format="PNG", optimize=True)
            buffer.seek(0)

            return buffer.getvalue()

    except Image.UnidentifiedImageError as e:
        raise FileError(f"File is not a valid image: {e}", path=path) from e
    except Exception as e:
        logger.exception(f"Unexpected error generating image thumbnail: {path}")
        raise FileError(f"Failed to generate thumbnail: {e}", path=path) from e


def get_dsm_elevation(dsm_path: str, x: float, y: float) -> float | None:
    """Get elevation value from DSM at a specific coordinate.

    Args:
        dsm_path: Path to the DSM GeoTIFF file.
        x: X coordinate in the DSM's native CRS.
        y: Y coordinate in the DSM's native CRS.

    Returns:
        Elevation value at the coordinate, or None if outside bounds or nodata.

    Raises:
        FileError: If DSM file does not exist or is not a valid raster.
    """
    file_path = Path(dsm_path)

    if not file_path.exists():
        raise FileError(f"File not found: {dsm_path}", path=dsm_path)

    try:
        import numpy as np
        import rasterio

        with rasterio.open(file_path) as dataset:
            # Check if coordinate is within bounds
            bounds = dataset.bounds
            if not (bounds.left <= x <= bounds.right and bounds.bottom <= y <= bounds.top):
                logger.debug(f"Coordinate ({x}, {y}) is outside DSM bounds")
                return None

            # Convert coordinate to pixel row/col
            row, col = dataset.index(x, y)

            # Check if within valid pixel range
            if not (0 <= row < dataset.height and 0 <= col < dataset.width):
                return None

            # Read single pixel value
            window = rasterio.windows.Window(col, row, 1, 1)
            data = dataset.read(1, window=window)
            value = data[0, 0]

            # Check for nodata
            if dataset.nodata is not None and value == dataset.nodata:
                return None

            # Check for nan/inf
            if not np.isfinite(value):
                return None

            return float(value)

    except rasterio.errors.RasterioIOError as e:
        raise FileError(f"Failed to read DSM file: {e}", path=dsm_path) from e
    except Exception as e:
        logger.exception(f"Unexpected error reading elevation from DSM: {dsm_path}")
        raise FileError(f"Failed to read elevation: {e}", path=dsm_path) from e


def get_image_info(path: str) -> ImageFile:
    """Read image file information including EXIF data.

    Args:
        path: Path to the image file.

    Returns:
        ImageFile schema with size and optional EXIF data.

    Raises:
        FileError: If file does not exist or is not a valid image.
    """
    file_path = Path(path)

    if not file_path.exists():
        raise FileError(f"File not found: {path}", path=path)

    try:
        from PIL import Image

        # Open image with PIL to get dimensions
        with Image.open(file_path) as img:
            size = (img.width, img.height)

        # Try to read EXIF data
        exif_data: ExifData | None = None
        try:
            exif_data = read_exif(path)
        except Exception as e:
            logger.warning(f"Failed to read EXIF from {path}: {e}")

        return ImageFile(
            path=str(file_path.resolve()),
            size=size,
            exif=exif_data,
        )

    except Image.UnidentifiedImageError as e:
        raise FileError(f"File is not a valid image: {e}", path=path) from e
    except Exception as e:
        logger.exception(f"Unexpected error reading image: {path}")
        raise FileError(f"Failed to read image file: {e}", path=path) from e
