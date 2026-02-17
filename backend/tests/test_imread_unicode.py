"""Tests for app.utils.image (Unicode-safe image I/O)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.utils.image import imread_unicode, safe_image_path


@pytest.fixture()
def sample_image(tmp_path: Path) -> Path:
    """Create a small test PNG in *tmp_path*."""
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    img[:, :] = (0, 128, 255)
    path = tmp_path / "test.png"
    cv2.imwrite(str(path), img)
    return path


# ---- imread_unicode --------------------------------------------------------


class TestImreadUnicode:
    def test_reads_ascii_path(self, sample_image: Path) -> None:
        img = imread_unicode(sample_image)
        assert img is not None
        assert img.shape == (10, 10, 3)

    def test_reads_japanese_path(self, sample_image: Path) -> None:
        jp_dir = sample_image.parent / "日本語パス"
        jp_dir.mkdir()
        jp_path = jp_dir / "テスト画像.png"
        jp_path.write_bytes(sample_image.read_bytes())

        img = imread_unicode(jp_path)
        assert img is not None
        assert img.shape == (10, 10, 3)

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        assert imread_unicode(tmp_path / "missing.png") is None

    def test_returns_none_for_invalid_data(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.png"
        bad.write_bytes(b"not an image")
        assert imread_unicode(bad) is None

    def test_accepts_string_path(self, sample_image: Path) -> None:
        img = imread_unicode(str(sample_image))
        assert img is not None

    def test_grayscale_flag(self, sample_image: Path) -> None:
        img = imread_unicode(sample_image, flags=cv2.IMREAD_GRAYSCALE)
        assert img is not None
        assert img.ndim == 2


# ---- safe_image_path -------------------------------------------------------


class TestSafeImagePath:
    def test_ascii_path_is_unchanged(self, sample_image: Path) -> None:
        with safe_image_path(str(sample_image)) as p:
            assert p == str(sample_image)

    def test_non_ascii_path_is_copied(self, sample_image: Path) -> None:
        jp_dir = sample_image.parent / "日本語パス"
        jp_dir.mkdir()
        jp_path = jp_dir / "テスト画像.png"
        jp_path.write_bytes(sample_image.read_bytes())

        with safe_image_path(str(jp_path)) as p:
            assert p != str(jp_path)
            # Temporary path must be ASCII-only
            p.encode("ascii")
            # File should be readable via cv2.imread
            img = cv2.imread(p)
            assert img is not None

    def test_temp_file_cleaned_up(self, sample_image: Path) -> None:
        jp_dir = sample_image.parent / "日本語パス"
        jp_dir.mkdir()
        jp_path = jp_dir / "テスト画像.png"
        jp_path.write_bytes(sample_image.read_bytes())

        tmp: str = ""
        with safe_image_path(str(jp_path)) as p:
            tmp = p
            assert Path(tmp).exists()
        # After context manager exits, temp file should be removed
        assert not Path(tmp).exists()
