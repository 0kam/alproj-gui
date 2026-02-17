"""Image I/O utilities for Unicode-safe file handling.

On Windows, ``cv2.imread()`` fails when the file path contains non-ASCII
characters (e.g. Japanese) because OpenCV converts the path using the
system's default code page.  The helpers in this module work around that
limitation.
"""

from __future__ import annotations

import contextlib
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np


def imread_unicode(path: str | Path, flags: int = cv2.IMREAD_COLOR) -> np.ndarray | None:
    """Read an image from a Unicode-safe path.

    Uses ``pathlib.Path.read_bytes()`` + ``cv2.imdecode()`` so that
    non-ASCII characters in the path never reach the C runtime.

    Args:
        path: Image file path (may contain non-ASCII characters).
        flags: OpenCV imread flags (default: ``cv2.IMREAD_COLOR``).

    Returns:
        The decoded image array, or ``None`` if the file does not exist
        or cannot be decoded.
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return None
    try:
        data = np.frombuffer(path_obj.read_bytes(), dtype=np.uint8)
        return cv2.imdecode(data, flags)
    except Exception:
        return None


@contextlib.contextmanager
def safe_image_path(path: str) -> Iterator[str]:
    """Yield an ASCII-safe copy of *path* when it contains non-ASCII chars.

    External libraries such as ``alproj.gcp.image_match`` call
    ``cv2.imread`` internally, so we cannot replace the call site.
    This context manager transparently copies the file to a temporary
    directory with an ASCII-only name when necessary and cleans up
    afterwards.

    If *path* is already ASCII-safe the original path is yielded
    without any copy.

    Args:
        path: Original image file path.

    Yields:
        A path string that is safe for ``cv2.imread`` on all platforms.
    """
    try:
        path.encode("ascii")
    except UnicodeEncodeError:
        pass
    else:
        # Path is pure ASCII — no copy needed.
        yield path
        return

    # Non-ASCII path: copy to a temp directory with an ASCII name.
    suffix = Path(path).suffix
    tmp_dir = tempfile.mkdtemp(prefix="alproj_")
    tmp_path = str(Path(tmp_dir) / f"image{suffix}")
    try:
        shutil.copy2(path, tmp_path)
        yield tmp_path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
