"""Report generation service for georectification results.

Provides:
- JSON format report generation
- Text format report generation
- Report data structure for API responses
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.schemas import CameraParamsValues, ProcessMetrics
    from app.schemas.project import Project

logger = logging.getLogger(__name__)


def generate_report(
    project: Project,
    format: str = "json",
) -> str:
    """Generate a processing report for a project.

    Generates a detailed report containing:
    - Project metadata (name, creation date, etc.)
    - Input data information (DSM, orthophoto, target image)
    - Camera parameters (initial and optimized)
    - Processing metrics (RMSE, GCP count, residuals)
    - GCP details (if available)

    Args:
        project: Project instance with processing results.
        format: Output format ("json" or "text").

    Returns:
        Report string in the specified format.

    Raises:
        ValueError: If format is not supported.
    """
    if format not in ("json", "text"):
        raise ValueError(f"Unsupported report format: {format}. Use 'json' or 'text'.")

    report_data = _build_report_data(project)

    if format == "json":
        return _format_json(report_data)
    else:
        return _format_text(report_data)


def _build_report_data(project: Project) -> dict[str, Any]:
    """Build report data structure from project.

    Args:
        project: Project instance.

    Returns:
        Dictionary containing all report data.
    """
    report: dict[str, Any] = {
        "report_generated_at": datetime.now().isoformat(),
        "report_version": "1.0",
        "project": {
            "id": str(project.id),
            "name": project.name,
            "status": project.status.value,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
            "version": project.version,
        },
        "input_data": {},
        "camera_params": {},
        "processing_result": {},
    }

    # Input data section
    input_data = project.input_data
    if input_data:
        if input_data.dsm:
            report["input_data"]["dsm"] = {
                "path": input_data.dsm.path,
                "crs": input_data.dsm.crs,
                "bounds": input_data.dsm.bounds,
                "resolution": input_data.dsm.resolution,
                "size": input_data.dsm.size,
            }
        if input_data.ortho:
            report["input_data"]["ortho"] = {
                "path": input_data.ortho.path,
                "crs": input_data.ortho.crs,
                "bounds": input_data.ortho.bounds,
                "resolution": input_data.ortho.resolution,
                "size": input_data.ortho.size,
            }
        if input_data.target_image:
            report["input_data"]["target_image"] = {
                "path": input_data.target_image.path,
                "size": input_data.target_image.size,
            }
            if input_data.target_image.exif:
                exif = input_data.target_image.exif
                report["input_data"]["target_image"]["exif"] = {
                    "taken_at": exif.taken_at.isoformat() if exif.taken_at else None,
                    "gps_lat": exif.gps_lat,
                    "gps_lon": exif.gps_lon,
                    "gps_alt": exif.gps_alt,
                    "focal_length": exif.focal_length,
                    "camera_model": exif.camera_model,
                }

    # Camera parameters section
    if project.camera_params:
        params = project.camera_params
        report["camera_params"]["initial"] = _camera_params_to_dict(params.initial)
        if params.optimized:
            report["camera_params"]["optimized"] = _camera_params_to_dict(params.optimized)

    # Processing result section
    if project.process_result:
        result = project.process_result
        if result.metrics:
            report["processing_result"]["metrics"] = {
                "rmse": result.metrics.rmse,
                "gcp_count": result.metrics.gcp_count,
                "gcp_total": result.metrics.gcp_total,
                "residual_mean": result.metrics.residual_mean,
                "residual_std": result.metrics.residual_std,
                "residual_max": result.metrics.residual_max,
            }
        if result.gcps:
            report["processing_result"]["gcps"] = [
                {
                    "id": gcp.id,
                    "image_x": gcp.image_x,
                    "image_y": gcp.image_y,
                    "geo_x": gcp.geo_x,
                    "geo_y": gcp.geo_y,
                    "geo_z": gcp.geo_z,
                    "residual": gcp.residual,
                    "enabled": gcp.enabled,
                }
                for gcp in result.gcps
            ]

    return report


def _camera_params_to_dict(params: CameraParamsValues | None) -> dict[str, Any] | None:
    """Convert camera parameters to dictionary.

    Args:
        params: Camera parameters instance.

    Returns:
        Dictionary representation or None.
    """
    if params is None:
        return None

    return {
        "position": {
            "x": params.x,
            "y": params.y,
            "z": params.z,
        },
        "orientation": {
            "pan": params.pan,
            "tilt": params.tilt,
            "roll": params.roll,
        },
        "lens": {
            "fov": params.fov,
            "cx": params.cx,
            "cy": params.cy,
        },
        "distortion": {
            "a1": params.a1,
            "a2": params.a2,
            "k1": params.k1,
            "k2": params.k2,
            "k3": params.k3,
            "k4": params.k4,
            "k5": params.k5,
            "k6": params.k6,
            "p1": params.p1,
            "p2": params.p2,
            "s1": params.s1,
            "s2": params.s2,
            "s3": params.s3,
            "s4": params.s4,
        },
    }


def _format_json(data: dict[str, Any]) -> str:
    """Format report data as JSON.

    Args:
        data: Report data dictionary.

    Returns:
        JSON string with indentation.
    """
    return json.dumps(data, indent=2, ensure_ascii=False)


def _format_text(data: dict[str, Any]) -> str:
    """Format report data as human-readable text.

    Args:
        data: Report data dictionary.

    Returns:
        Formatted text string.
    """
    lines: list[str] = []

    # Header
    lines.append("=" * 60)
    lines.append("GEORECTIFICATION PROCESSING REPORT")
    lines.append("=" * 60)
    lines.append("")

    # Report metadata
    lines.append(f"Generated at: {data['report_generated_at']}")
    lines.append(f"Report version: {data['report_version']}")
    lines.append("")

    # Project info
    lines.append("-" * 40)
    lines.append("PROJECT INFORMATION")
    lines.append("-" * 40)
    project = data.get("project", {})
    lines.append(f"Name: {project.get('name', 'N/A')}")
    lines.append(f"ID: {project.get('id', 'N/A')}")
    lines.append(f"Status: {project.get('status', 'N/A')}")
    lines.append(f"Created: {project.get('created_at', 'N/A')}")
    lines.append(f"Updated: {project.get('updated_at', 'N/A')}")
    lines.append("")

    # Input data
    lines.append("-" * 40)
    lines.append("INPUT DATA")
    lines.append("-" * 40)
    input_data = data.get("input_data", {})

    if "dsm" in input_data:
        dsm = input_data["dsm"]
        lines.append("DSM (Digital Surface Model):")
        lines.append(f"  Path: {dsm.get('path', 'N/A')}")
        lines.append(f"  CRS: {dsm.get('crs', 'N/A')}")
        lines.append(f"  Size: {dsm.get('size', 'N/A')}")
        lines.append(f"  Resolution: {dsm.get('resolution', 'N/A')}")
        lines.append("")

    if "ortho" in input_data:
        ortho = input_data["ortho"]
        lines.append("Orthophoto:")
        lines.append(f"  Path: {ortho.get('path', 'N/A')}")
        lines.append(f"  CRS: {ortho.get('crs', 'N/A')}")
        lines.append(f"  Size: {ortho.get('size', 'N/A')}")
        lines.append("")

    if "target_image" in input_data:
        target = input_data["target_image"]
        lines.append("Target Image:")
        lines.append(f"  Path: {target.get('path', 'N/A')}")
        lines.append(f"  Size: {target.get('size', 'N/A')}")
        if "exif" in target and target["exif"]:
            exif = target["exif"]
            lines.append(f"  EXIF - Camera: {exif.get('camera_model', 'N/A')}")
            if exif.get("gps_lat") and exif.get("gps_lon"):
                lines.append(f"  EXIF - GPS: {exif['gps_lat']}, {exif['gps_lon']}")
            if exif.get("focal_length"):
                lines.append(f"  EXIF - Focal length: {exif['focal_length']}mm")
        lines.append("")

    # Camera parameters
    lines.append("-" * 40)
    lines.append("CAMERA PARAMETERS")
    lines.append("-" * 40)
    camera = data.get("camera_params", {})

    if "initial" in camera and camera["initial"]:
        initial = camera["initial"]
        lines.append("Initial Parameters:")
        pos = initial.get("position", {})
        lines.append(f"  Position: X={pos.get('x', 'N/A')}, Y={pos.get('y', 'N/A')}, Z={pos.get('z', 'N/A')}")
        ori = initial.get("orientation", {})
        lines.append(f"  Orientation: Pan={ori.get('pan', 'N/A')}, Tilt={ori.get('tilt', 'N/A')}, Roll={ori.get('roll', 'N/A')}")
        lens = initial.get("lens", {})
        lines.append(f"  FOV: {lens.get('fov', 'N/A')}")
        lines.append("")

    if "optimized" in camera and camera["optimized"]:
        optimized = camera["optimized"]
        lines.append("Optimized Parameters:")
        pos = optimized.get("position", {})
        lines.append(f"  Position: X={pos.get('x', 'N/A')}, Y={pos.get('y', 'N/A')}, Z={pos.get('z', 'N/A')}")
        ori = optimized.get("orientation", {})
        lines.append(f"  Orientation: Pan={ori.get('pan', 'N/A')}, Tilt={ori.get('tilt', 'N/A')}, Roll={ori.get('roll', 'N/A')}")
        lens = optimized.get("lens", {})
        lines.append(f"  FOV: {lens.get('fov', 'N/A')}")
        lines.append("")

    # Processing results
    lines.append("-" * 40)
    lines.append("PROCESSING RESULTS")
    lines.append("-" * 40)
    result = data.get("processing_result", {})

    if "metrics" in result:
        metrics = result["metrics"]
        lines.append("Quality Metrics:")
        lines.append(f"  RMSE: {metrics.get('rmse', 'N/A'):.4f} pixels" if isinstance(metrics.get('rmse'), (int, float)) else f"  RMSE: {metrics.get('rmse', 'N/A')}")
        lines.append(f"  GCP Count: {metrics.get('gcp_count', 'N/A')} / {metrics.get('gcp_total', 'N/A')}")
        lines.append(f"  Residual Mean: {metrics.get('residual_mean', 'N/A'):.4f}" if isinstance(metrics.get('residual_mean'), (int, float)) else f"  Residual Mean: {metrics.get('residual_mean', 'N/A')}")
        lines.append(f"  Residual Std: {metrics.get('residual_std', 'N/A'):.4f}" if isinstance(metrics.get('residual_std'), (int, float)) else f"  Residual Std: {metrics.get('residual_std', 'N/A')}")
        lines.append(f"  Residual Max: {metrics.get('residual_max', 'N/A'):.4f}" if isinstance(metrics.get('residual_max'), (int, float)) else f"  Residual Max: {metrics.get('residual_max', 'N/A')}")
        lines.append("")

    if "gcps" in result and result["gcps"]:
        lines.append("Ground Control Points:")
        lines.append("  ID    Image (X, Y)         Geo (X, Y, Z)                    Residual  Enabled")
        lines.append("  " + "-" * 85)
        for gcp in result["gcps"]:
            enabled = "Yes" if gcp.get("enabled", True) else "No"
            lines.append(
                f"  {gcp.get('id', 'N/A'):4}  "
                f"({gcp.get('image_x', 0):8.1f}, {gcp.get('image_y', 0):8.1f})  "
                f"({gcp.get('geo_x', 0):12.2f}, {gcp.get('geo_y', 0):12.2f}, {gcp.get('geo_z', 0):8.2f})  "
                f"{gcp.get('residual', 0):8.4f}  {enabled}"
            )
        lines.append("")

    lines.append("=" * 60)
    lines.append("END OF REPORT")
    lines.append("=" * 60)

    return "\n".join(lines)
