"""EXIF metadata reading service.

Provides functionality for:
- Extracting GPS coordinates (latitude, longitude, altitude)
- Estimating FOV from focal length (assuming 35mm full-frame sensor)
- Reading camera model and capture date
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

from app.schemas import ExifData

logger = logging.getLogger(__name__)

# 35mm full-frame sensor dimensions (mm)
SENSOR_WIDTH_35MM = 36.0
SENSOR_HEIGHT_35MM = 24.0


def read_exif(path: str) -> ExifData | None:
    """Read EXIF metadata from an image file.

    Extracts:
    - GPS coordinates (latitude, longitude, altitude)
    - Focal length and estimated FOV
    - Camera model
    - Capture datetime

    Args:
        path: Path to the image file.

    Returns:
        ExifData schema with extracted metadata, or None if no EXIF data found.
    """
    file_path = Path(path)

    if not file_path.exists():
        return None

    try:
        with Image.open(file_path) as img:
            exif_raw = img._getexif()  # type: ignore[union-attr]

            if exif_raw is None:
                return None

            # Convert numeric tags to names
            exif_data: dict[str, object] = {}
            for tag_id, value in exif_raw.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                exif_data[tag_name] = value

            # Extract GPS info
            gps_lat, gps_lon, gps_alt = _extract_gps(exif_data)

            # Extract focal length
            focal_length = _extract_focal_length(exif_data)

            # Extract camera model
            camera_model = _extract_camera_model(exif_data)

            # Extract datetime
            taken_at = _extract_datetime(exif_data)

            return ExifData(
                taken_at=taken_at,
                gps_lat=gps_lat,
                gps_lon=gps_lon,
                gps_alt=gps_alt,
                focal_length=focal_length,
                camera_model=camera_model,
            )

    except Exception as e:
        logger.warning(f"Failed to read EXIF from {path}: {e}")
        return None


def estimate_fov_from_focal_length(
    focal_length_mm: float,
    sensor_width_mm: float = SENSOR_WIDTH_35MM,
) -> float:
    """Estimate horizontal field of view from focal length.

    Assumes a 35mm full-frame sensor by default.
    FOV = 2 * arctan(sensor_width / (2 * focal_length))

    Args:
        focal_length_mm: Focal length in millimeters.
        sensor_width_mm: Sensor width in millimeters (default: 36mm for 35mm full-frame).

    Returns:
        Horizontal field of view in degrees.
    """
    if focal_length_mm <= 0:
        return 60.0  # Default fallback

    # FOV formula: 2 * arctan(sensor_width / (2 * focal_length))
    fov_rad = 2.0 * math.atan(sensor_width_mm / (2.0 * focal_length_mm))
    fov_deg = math.degrees(fov_rad)

    # Clamp to reasonable range
    return max(1.0, min(fov_deg, 180.0))


def _extract_gps(exif_data: dict[str, object]) -> tuple[float | None, float | None, float | None]:
    """Extract GPS coordinates from EXIF data.

    Args:
        exif_data: Dictionary of EXIF tag names to values.

    Returns:
        Tuple of (latitude, longitude, altitude) in decimal degrees/meters.
        Any value may be None if not found.
    """
    gps_info_raw = exif_data.get("GPSInfo")

    if gps_info_raw is None:
        return None, None, None

    # GPSInfo is a dict with numeric keys
    gps_info: dict[str, object] = {}
    if isinstance(gps_info_raw, dict):
        for key, value in gps_info_raw.items():
            tag_name = GPSTAGS.get(key, str(key))
            gps_info[tag_name] = value

    # Extract latitude
    lat = _gps_to_decimal(
        gps_info.get("GPSLatitude"),
        gps_info.get("GPSLatitudeRef"),
    )

    # Extract longitude
    lon = _gps_to_decimal(
        gps_info.get("GPSLongitude"),
        gps_info.get("GPSLongitudeRef"),
    )

    # Extract altitude
    alt = _extract_altitude(
        gps_info.get("GPSAltitude"),
        gps_info.get("GPSAltitudeRef"),
    )

    return lat, lon, alt


def _gps_to_decimal(
    coords: object,
    ref: object,
) -> float | None:
    """Convert GPS coordinates from DMS to decimal degrees.

    Args:
        coords: Tuple of (degrees, minutes, seconds) as rationals or floats.
        ref: Reference direction ("N", "S", "E", "W").

    Returns:
        Decimal degrees, or None if conversion fails.
    """
    if coords is None:
        return None

    try:
        # coords can be tuple of IFDRational or float values
        if isinstance(coords, (list, tuple)) and len(coords) >= 3:
            degrees = _rational_to_float(coords[0])
            minutes = _rational_to_float(coords[1])
            seconds = _rational_to_float(coords[2])

            if degrees is None or minutes is None or seconds is None:
                return None

            decimal = degrees + minutes / 60.0 + seconds / 3600.0

            # Apply reference direction
            if ref in ("S", "W"):
                decimal = -decimal

            return decimal

    except Exception as e:
        logger.debug(f"Failed to convert GPS coordinates: {e}")

    return None


def _rational_to_float(value: object) -> float | None:
    """Convert EXIF rational value to float.

    Args:
        value: EXIF value (could be IFDRational, tuple, or numeric).

    Returns:
        Float value, or None if conversion fails.
    """
    if value is None:
        return None

    try:
        # Handle IFDRational
        if hasattr(value, "numerator") and hasattr(value, "denominator"):
            if value.denominator == 0:  # type: ignore[union-attr]
                return None
            return float(value.numerator) / float(value.denominator)  # type: ignore[union-attr]

        # Handle tuple (numerator, denominator)
        if isinstance(value, tuple) and len(value) == 2:
            if value[1] == 0:
                return None
            return float(value[0]) / float(value[1])

        # Direct numeric value
        return float(value)

    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _extract_altitude(
    altitude: object,
    altitude_ref: object,
) -> float | None:
    """Extract altitude from GPS EXIF data.

    Args:
        altitude: Altitude value (rational or float).
        altitude_ref: Reference (0 = above sea level, 1 = below).

    Returns:
        Altitude in meters, or None if not found.
    """
    if altitude is None:
        return None

    alt = _rational_to_float(altitude)
    if alt is None:
        return None

    # Apply reference (0 = above sea level, 1 = below sea level)
    if altitude_ref == 1:
        alt = -alt

    return alt


def _extract_focal_length(exif_data: dict[str, object]) -> float | None:
    """Extract focal length from EXIF data.

    Args:
        exif_data: Dictionary of EXIF tag names to values.

    Returns:
        Focal length in millimeters, or None if not found.
    """
    focal_length = exif_data.get("FocalLength")

    if focal_length is None:
        return None

    return _rational_to_float(focal_length)


def _extract_camera_model(exif_data: dict[str, object]) -> str | None:
    """Extract camera model from EXIF data.

    Args:
        exif_data: Dictionary of EXIF tag names to values.

    Returns:
        Camera model string, or None if not found.
    """
    # Try Model first, then fall back to Make + Model
    model = exif_data.get("Model")
    make = exif_data.get("Make")

    if model:
        model_str = str(model).strip()
        # Include make if model doesn't already contain it
        if make:
            make_str = str(make).strip()
            if make_str.lower() not in model_str.lower():
                return f"{make_str} {model_str}"
        return model_str

    if make:
        return str(make).strip()

    return None


def _extract_datetime(exif_data: dict[str, object]) -> datetime | None:
    """Extract capture datetime from EXIF data.

    Args:
        exif_data: Dictionary of EXIF tag names to values.

    Returns:
        Datetime object, or None if not found or invalid.
    """
    # Try different datetime tags in order of preference
    datetime_tags = ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]

    for tag in datetime_tags:
        dt_str = exif_data.get(tag)
        if dt_str:
            parsed = _parse_exif_datetime(str(dt_str))
            if parsed:
                return parsed

    return None


def _parse_exif_datetime(dt_str: str) -> datetime | None:
    """Parse EXIF datetime string.

    EXIF datetime format is typically "YYYY:MM:DD HH:MM:SS"

    Args:
        dt_str: Datetime string from EXIF.

    Returns:
        Parsed datetime, or None if parsing fails.
    """
    formats = [
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(dt_str.strip(), fmt)
        except ValueError:
            continue

    return None
