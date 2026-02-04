"""Project file I/O service for saving and loading .alproj files.

Provides:
- Save project to .alproj (JSON format)
- Load project from .alproj file
- Version migration for backward compatibility
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.schemas.project import (
    CameraParams,
    ExifData,
    ImageFile,
    InputData,
    ProcessResult,
    Project,
    ProjectStatus,
    RasterFile,
)

logger = logging.getLogger(__name__)

# Current project file version
CURRENT_VERSION = "1.0.0"

# Supported versions for migration
SUPPORTED_VERSIONS = ["1.0.0"]


class ProjectIOError(Exception):
    """Base exception for project I/O errors."""

    pass


class ProjectVersionError(ProjectIOError):
    """Raised when project file version is unsupported."""

    pass


class ProjectValidationError(ProjectIOError):
    """Raised when project data validation fails."""

    pass


def save_project(project: Project, path: str) -> None:
    """Save a project to a .alproj file (JSON format).

    Args:
        project: The project to save.
        path: Destination file path.

    Raises:
        ProjectIOError: If file cannot be written.
    """
    filepath = Path(path)

    # Ensure .alproj extension
    if filepath.suffix.lower() != ".alproj":
        filepath = filepath.with_suffix(".alproj")

    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Build file data structure
    file_data = {
        "version": CURRENT_VERSION,
        "saved_at": datetime.now(UTC).isoformat(),
        "project": project.model_dump(mode="json"),
    }

    try:
        # Write to temp file first, then rename for atomic operation
        temp_path = filepath.with_suffix(".alproj.tmp")

        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(file_data, f, ensure_ascii=False, indent=2)

        # Atomic rename (works on POSIX, Windows may need fallback)
        temp_path.replace(filepath)

        logger.info(f"Saved project to {filepath}")

    except OSError as e:
        logger.error(f"Failed to save project to {path}: {e}")
        raise ProjectIOError(f"Failed to save project: {e}") from e


def load_project(path: str) -> Project:
    """Load a project from a .alproj file.

    Performs version migration if needed for backward compatibility.

    Args:
        path: Path to the .alproj file.

    Returns:
        Loaded and migrated Project object.

    Raises:
        ProjectIOError: If file cannot be read.
        ProjectVersionError: If version is unsupported.
        ProjectValidationError: If project data is invalid.
    """
    filepath = Path(path)

    if not filepath.exists():
        raise ProjectIOError(f"Project file not found: {path}")

    try:
        with filepath.open("r", encoding="utf-8") as f:
            file_data: dict[str, Any] = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in project file {path}: {e}")
        raise ProjectIOError(f"Invalid project file format: {e}") from e
    except OSError as e:
        logger.error(f"Failed to read project file {path}: {e}")
        raise ProjectIOError(f"Failed to read project file: {e}") from e

    # Check version
    file_version = file_data.get("version", "unknown")
    if file_version not in SUPPORTED_VERSIONS:
        raise ProjectVersionError(
            f"Unsupported project file version: {file_version}. "
            f"Supported versions: {', '.join(SUPPORTED_VERSIONS)}"
        )

    # Migrate if needed
    project_data = file_data.get("project", {})
    migrated_data = migrate_project(project_data, file_version)

    # Validate and create Project object
    try:
        project = _dict_to_project(migrated_data)
        logger.info(f"Loaded project '{project.name}' from {filepath}")
        return project
    except Exception as e:
        logger.error(f"Failed to validate project data from {path}: {e}")
        raise ProjectValidationError(f"Invalid project data: {e}") from e


def migrate_project(data: dict[str, Any], from_version: str = "1.0.0") -> dict[str, Any]:
    """Migrate project data from older versions to current version.

    Args:
        data: Project data dictionary.
        from_version: Source version to migrate from.

    Returns:
        Migrated project data dictionary.
    """
    current_data = data.copy()

    # Version migration chain (future-proofing)
    # Each migration function transforms data to the next version

    if from_version == "1.0.0":
        # Current version, no migration needed
        pass

    # Future migrations would be added here:
    # if from_version == "0.9.0":
    #     current_data = _migrate_0_9_0_to_1_0_0(current_data)
    #     from_version = "1.0.0"

    # Ensure version is current
    current_data["version"] = CURRENT_VERSION

    return current_data


def _dict_to_project(data: dict[str, Any]) -> Project:
    """Convert a dictionary to a Project object with proper type handling.

    Args:
        data: Project data dictionary.

    Returns:
        Project object.
    """
    # Handle UUID conversion
    project_id = data.get("id")
    if isinstance(project_id, str):
        project_id = UUID(project_id)

    # Handle datetime conversion
    created_at = data.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

    updated_at = data.get("updated_at")
    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

    # Handle status enum
    status = data.get("status", "draft")
    if isinstance(status, str):
        status = ProjectStatus(status)

    # Build input_data
    input_data_dict = data.get("input_data", {})
    input_data = _build_input_data(input_data_dict)

    # Build camera_params
    camera_params = None
    camera_params_dict = data.get("camera_params")
    if camera_params_dict:
        camera_params = CameraParams(**camera_params_dict)

    # Build process_result
    process_result = None
    process_result_dict = data.get("process_result")
    if process_result_dict:
        process_result = ProcessResult(**process_result_dict)

    return Project(
        id=project_id,
        version=data.get("version", CURRENT_VERSION),
        name=data.get("name", "Untitled"),
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        input_data=input_data,
        camera_params=camera_params,
        camera_simulation=data.get("camera_simulation"),
        process_result=process_result,
    )


def _build_input_data(data: dict[str, Any]) -> InputData:
    """Build InputData from dictionary.

    Args:
        data: Input data dictionary.

    Returns:
        InputData object.
    """
    dsm = None
    ortho = None
    target_image = None

    if data.get("dsm"):
        dsm_data = data["dsm"]
        # Convert bounds list to tuple if needed
        bounds = dsm_data.get("bounds")
        if isinstance(bounds, list):
            bounds = tuple(bounds)
        bounds_wgs84 = dsm_data.get("bounds_wgs84")
        if isinstance(bounds_wgs84, list):
            bounds_wgs84 = tuple(bounds_wgs84)
        resolution = dsm_data.get("resolution")
        if isinstance(resolution, list):
            resolution = tuple(resolution)
        size = dsm_data.get("size")
        if isinstance(size, list):
            size = tuple(size)

        dsm = RasterFile(
            path=dsm_data["path"],
            crs=dsm_data["crs"],
            bounds=bounds,
            bounds_wgs84=bounds_wgs84,
            resolution=resolution,
            size=size,
        )

    if data.get("ortho"):
        ortho_data = data["ortho"]
        bounds = ortho_data.get("bounds")
        if isinstance(bounds, list):
            bounds = tuple(bounds)
        bounds_wgs84 = ortho_data.get("bounds_wgs84")
        if isinstance(bounds_wgs84, list):
            bounds_wgs84 = tuple(bounds_wgs84)
        resolution = ortho_data.get("resolution")
        if isinstance(resolution, list):
            resolution = tuple(resolution)
        size = ortho_data.get("size")
        if isinstance(size, list):
            size = tuple(size)

        ortho = RasterFile(
            path=ortho_data["path"],
            crs=ortho_data["crs"],
            bounds=bounds,
            bounds_wgs84=bounds_wgs84,
            resolution=resolution,
            size=size,
        )

    if data.get("target_image"):
        img_data = data["target_image"]
        size = img_data.get("size")
        if isinstance(size, list):
            size = tuple(size)

        exif = None
        if img_data.get("exif"):
            exif_data = img_data["exif"]
            taken_at = exif_data.get("datetime") or exif_data.get("taken_at")
            if isinstance(taken_at, str):
                taken_at = datetime.fromisoformat(taken_at.replace("Z", "+00:00"))
            exif = ExifData(
                taken_at=taken_at,
                gps_lat=exif_data.get("gps_lat"),
                gps_lon=exif_data.get("gps_lon"),
                gps_alt=exif_data.get("gps_alt"),
                focal_length=exif_data.get("focal_length"),
                camera_model=exif_data.get("camera_model"),
            )

        target_image = ImageFile(
            path=img_data["path"],
            size=size,
            exif=exif,
        )

    return InputData(
        dsm=dsm,
        ortho=ortho,
        target_image=target_image,
    )


def get_project_info(path: str) -> dict[str, Any]:
    """Get basic info about a project file without fully loading it.

    Args:
        path: Path to the .alproj file.

    Returns:
        Dictionary with project summary info.

    Raises:
        ProjectIOError: If file cannot be read.
    """
    filepath = Path(path)

    if not filepath.exists():
        raise ProjectIOError(f"Project file not found: {path}")

    try:
        with filepath.open("r", encoding="utf-8") as f:
            file_data: dict[str, Any] = json.load(f)

        project_data = file_data.get("project", {})
        return {
            "path": str(filepath.absolute()),
            "version": file_data.get("version", "unknown"),
            "saved_at": file_data.get("saved_at"),
            "id": project_data.get("id"),
            "name": project_data.get("name", "Unknown"),
            "status": project_data.get("status", "unknown"),
            "file_size": filepath.stat().st_size,
        }
    except (json.JSONDecodeError, OSError) as e:
        raise ProjectIOError(f"Failed to read project file: {e}") from e
