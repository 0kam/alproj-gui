"""Auto-save and recovery service for crash protection.

Provides:
- Automatic state saving before processing
- Recovery file management
- Cleanup after successful processing
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.schemas.project import Project

logger = logging.getLogger(__name__)

# Default recovery directory
RECOVERY_DIR = Path.home() / ".alproj" / "recovery"


@dataclass
class RecoveryInfo:
    """Information about a recovery file."""

    path: str
    project_id: str
    project_name: str
    saved_at: datetime
    file_size: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "path": self.path,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "saved_at": self.saved_at.isoformat(),
            "file_size": self.file_size,
        }


def _get_recovery_dir() -> Path:
    """Get the recovery directory, creating it if needed.

    Returns:
        Path to recovery directory.
    """
    recovery_dir = RECOVERY_DIR
    recovery_dir.mkdir(parents=True, exist_ok=True)
    return recovery_dir


def _get_recovery_filename(project_id: str) -> str:
    """Generate recovery filename for a project.

    Args:
        project_id: Project UUID string.

    Returns:
        Recovery filename.
    """
    return f"{project_id}.alproj.tmp"


def save_recovery_state(project: Project) -> str:
    """Save project state to a recovery file before processing.

    Args:
        project: Project model to save.

    Returns:
        Path to the saved recovery file.

    Raises:
        IOError: If file cannot be written.
    """
    recovery_dir = _get_recovery_dir()
    filename = _get_recovery_filename(str(project.id))
    filepath = recovery_dir / filename

    # Build recovery data with metadata
    recovery_data = {
        "version": "1.0.0",
        "saved_at": datetime.now(UTC).isoformat(),
        "project": project.model_dump(mode="json"),
    }

    try:
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(recovery_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved recovery state for project {project.id} to {filepath}")
        return str(filepath)

    except OSError as e:
        logger.error(f"Failed to save recovery state: {e}")
        raise OSError(f"Failed to save recovery state: {e}") from e


def clear_recovery_state(project_id: str) -> bool:
    """Delete recovery file after successful processing.

    Args:
        project_id: Project UUID string.

    Returns:
        True if file was deleted, False if it didn't exist.
    """
    recovery_dir = _get_recovery_dir()
    filename = _get_recovery_filename(project_id)
    filepath = recovery_dir / filename

    try:
        if filepath.exists():
            filepath.unlink()
            logger.info(f"Cleared recovery state for project {project_id}")
            return True
        return False

    except OSError as e:
        logger.warning(f"Failed to clear recovery state: {e}")
        return False


def list_recovery_files() -> list[RecoveryInfo]:
    """List all available recovery files.

    Returns:
        List of RecoveryInfo objects sorted by saved_at (newest first).
    """
    recovery_dir = _get_recovery_dir()
    recovery_files: list[RecoveryInfo] = []

    try:
        for filepath in recovery_dir.glob("*.alproj.tmp"):
            try:
                with filepath.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                project_data = data.get("project", {})
                saved_at_str = data.get("saved_at", "")

                # Parse saved_at datetime
                try:
                    saved_at = datetime.fromisoformat(saved_at_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    saved_at = datetime.fromtimestamp(
                        filepath.stat().st_mtime, tz=UTC
                    )

                recovery_info = RecoveryInfo(
                    path=str(filepath),
                    project_id=project_data.get("id", "unknown"),
                    project_name=project_data.get("name", "Unknown Project"),
                    saved_at=saved_at,
                    file_size=filepath.stat().st_size,
                )
                recovery_files.append(recovery_info)

            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Invalid recovery file {filepath}: {e}")
                continue

    except OSError as e:
        logger.error(f"Failed to list recovery files: {e}")
        return []

    # Sort by saved_at (newest first)
    recovery_files.sort(key=lambda x: x.saved_at, reverse=True)
    return recovery_files


def load_recovery_state(filepath: str) -> dict[str, Any] | None:
    """Load project state from a recovery file.

    Args:
        filepath: Path to recovery file.

    Returns:
        Recovery data dict containing project data, or None if invalid.
    """
    try:
        with Path(filepath).open("r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load recovery file {filepath}: {e}")
        return None


def cleanup_old_recovery_files(max_age_days: int = 7) -> int:
    """Remove recovery files older than max_age_days.

    Args:
        max_age_days: Maximum age in days for recovery files.

    Returns:
        Number of files removed.
    """
    recovery_dir = _get_recovery_dir()
    now = datetime.now(UTC)
    removed_count = 0

    try:
        for filepath in recovery_dir.glob("*.alproj.tmp"):
            try:
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=UTC)
                age_days = (now - mtime).days

                if age_days > max_age_days:
                    filepath.unlink()
                    removed_count += 1
                    logger.info(f"Removed old recovery file: {filepath}")

            except OSError as e:
                logger.warning(f"Failed to process recovery file {filepath}: {e}")
                continue

    except OSError as e:
        logger.error(f"Failed to cleanup recovery files: {e}")

    if removed_count > 0:
        logger.info(f"Cleaned up {removed_count} old recovery files")

    return removed_count
