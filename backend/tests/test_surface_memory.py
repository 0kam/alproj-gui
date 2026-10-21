"""Tests for distance-dependent (multi-resolution) surface extraction."""

import numpy as np
import pytest
import rasterio
from pydantic import ValidationError as PydanticValidationError
from rasterio.transform import from_origin

from app.schemas.camera import SimulationRequest
from app.schemas.georectify import MatchRequest
from app.services.georectify import (
    SURFACE_VERTEX_BUDGET,
    create_geo_object,
    plan_surface_levels,
)


def _camera_params() -> dict[str, float]:
    return {
        "x": 0.0,
        "y": 0.0,
        "z": 100.0,
        "fov": 60.0,
        "pan": 0.0,
        "tilt": 0.0,
        "roll": 0.0,
    }


def _vertex_count(levels: list[tuple[float, float]]) -> float:
    total = 0.0
    inner = 0.0
    for half_size, res in levels:
        total += (2 * half_size / res) ** 2 - (2 * max(inner - res, 0.0) / res) ** 2
        inner = half_size
    return total


def test_small_area_keeps_uniform_resolution() -> None:
    assert plan_surface_levels(distance=3000, resolution=1.0) == [(3000, 1.0)]


@pytest.mark.parametrize("distance", [5_000, 10_000, 21_000, 50_000])
def test_large_area_coarsens_with_distance_within_budget(distance: float) -> None:
    levels = plan_surface_levels(distance=distance, resolution=1.0)

    assert len(levels) > 1
    assert levels[0][1] == 1.0
    assert levels[-1][0] == distance
    for (inner, inner_res), (outer, outer_res) in zip(levels, levels[1:], strict=False):
        assert outer > inner
        assert outer_res == inner_res * 2
    assert _vertex_count(levels) <= SURFACE_VERTEX_BUDGET


def test_create_geo_object_builds_seamless_multi_level_mesh(tmp_path) -> None:
    size, pixel = 200, 10.0
    transform = from_origin(-1000, 1000, pixel, pixel)
    profile = {
        "driver": "GTiff",
        "width": size,
        "height": size,
        "transform": transform,
        "crs": "EPSG:32654",
    }
    yy, xx = np.mgrid[0:size, 0:size]
    dsm_path = tmp_path / "dsm.tif"
    with rasterio.open(dsm_path, "w", count=1, dtype="float32", **profile) as dst:
        dst.write((100 + xx + yy).astype("float32"), 1)
    ortho_path = tmp_path / "ortho.tif"
    with rasterio.open(ortho_path, "w", count=3, dtype="uint8", **profile) as dst:
        dst.write(np.full((3, size, size), 128, dtype="uint8"))

    budget = 50_000
    geo = create_geo_object(
        dsm_path=str(dsm_path),
        ortho_path=str(ortho_path),
        camera_x=0.0,
        camera_y=0.0,
        distance=900.0,
        resolution=5.0,
        max_vertices=budget,
    )

    assert len(plan_surface_levels(900.0, 5.0, budget)) > 1
    assert len(geo.vert) <= budget
    assert geo.vert.shape == geo.col.shape
    assert geo.ind.min() >= 0 and geo.ind.max() < len(geo.vert)
    # Vertices span the full requested extent
    xs = geo.vert[:, 0] + geo.offsets[0]
    assert xs.min() <= -890 and xs.max() >= 880


def test_simulation_request_accepts_distance_over_ten_kilometers() -> None:
    request = SimulationRequest(
        dsm_path="dsm.tif",
        ortho_path="ortho.tif",
        target_image_path="target.jpg",
        camera_params=_camera_params(),
        surface_distance=21_000,
    )

    assert request.surface_distance == 21_000


def test_matching_request_requires_positive_surface_resolution() -> None:
    with pytest.raises(PydanticValidationError):
        MatchRequest(
            dsm_path="dsm.tif",
            ortho_path="ortho.tif",
            target_image_path="target.jpg",
            camera_params=_camera_params(),
            surface_resolution=0,
        )
