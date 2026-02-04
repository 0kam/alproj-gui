"""Georectification service wrapping alproj library.

Provides:
- GeoObject creation from DSM/orthophoto
- Simulation image generation
- Full georectification processing
- GeoTIFF export
"""

from __future__ import annotations

import asyncio
import builtins
import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import rasterio

from app.api.deps import FileError, MatchingError, MemoryError, ProcessingError
from app.schemas import GCP, CameraParamsValues, ProcessMetrics

if TYPE_CHECKING:
    import pandas as pd

    from app.core.jobs import Job
    from app.schemas.job import ProcessOptions

logger = logging.getLogger(__name__)


def _normalize_resize(method: str, resize: int | str | None) -> int | str:
    """Normalize resize value based on matching method defaults."""
    if isinstance(resize, str):
        return resize
    if resize is not None:
        return resize
    if method in ("minima-roma",):
        return 800
    return "none"


# =============================================================================
# GeoObject: Container for alproj surface mesh data
# =============================================================================


class GeoObject:
    """Container for alproj geo data (surface mesh and metadata).

    Holds the precomputed 3D surface data needed for projection operations.
    """

    def __init__(
        self,
        vert: np.ndarray,
        col: np.ndarray,
        ind: np.ndarray,
        offsets: np.ndarray,
        crs: str,
    ) -> None:
        """Initialize GeoObject with surface mesh data.

        Args:
            vert: Vertex coordinates array.
            col: Vertex colors array.
            ind: Triangle indices array.
            offsets: Coordinate offsets for numeric stability.
            crs: Coordinate reference system string.
        """
        self.vert = vert
        self.col = col
        self.ind = ind
        self.offsets = offsets
        self.crs = crs


def create_geo_object(
    dsm_path: str,
    ortho_path: str,
    camera_x: float,
    camera_y: float,
    crs: str | None = None,
    distance: float = 3000.0,
    resolution: float = 1.0,
) -> GeoObject:
    """Create a GeoObject from DSM and orthophoto files.

    Loads the DSM and orthophoto, extracts the colored surface mesh
    centered on the camera position.

    Args:
        dsm_path: Path to the Digital Surface Model (GeoTIFF).
        ortho_path: Path to the orthophoto (GeoTIFF).
        camera_x: Camera X coordinate in the projected CRS.
        camera_y: Camera Y coordinate in the projected CRS.
        crs: Optional CRS override. If None, uses DSM's CRS.
        distance: Distance from camera to surface edge (meters).
        resolution: Surface mesh resolution (meters).

    Returns:
        GeoObject containing the surface mesh data.

    Raises:
        FileError: If files cannot be read.
        ProcessingError: If surface extraction fails.
    """
    from alproj.surface import get_colored_surface

    dsm_file = Path(dsm_path)
    ortho_file = Path(ortho_path)

    if not dsm_file.exists():
        raise FileError(f"DSM file not found: {dsm_path}", path=dsm_path)
    if not ortho_file.exists():
        raise FileError(f"Orthophoto not found: {ortho_path}", path=ortho_path)

    try:
        with rasterio.open(dsm_file) as dsm, rasterio.open(ortho_file) as ortho:
            # Use DSM CRS if not specified
            if crs is None:
                crs = str(dsm.crs) if dsm.crs else "UNKNOWN"

            shooting_point = {"x": camera_x, "y": camera_y}

            vert, col, ind, offsets = get_colored_surface(
                aerial=ortho,
                dsm=dsm,
                shooting_point=shooting_point,
                distance=distance,
                res=resolution,
            )

            return GeoObject(
                vert=vert,
                col=col,
                ind=ind,
                offsets=offsets,
                crs=crs,
            )

    except FileError:
        raise
    except MemoryError as e:
        # Re-raise if it's already our custom MemoryError
        raise
    except builtins.MemoryError as e:
        # Catch Python's built-in MemoryError and convert to our custom one
        logger.exception(f"Memory error during surface extraction: {e}")
        # Estimate recommended resolution based on current settings
        recommended = max(resolution * 2, 5.0)  # Double resolution or at least 5m
        raise MemoryError(
            "Out of memory during surface extraction",
            current_resolution=resolution,
            recommended_resolution=recommended,
        ) from e
    except ValueError as e:
        raise ProcessingError(
            f"Failed to create surface: {e}",
            step="surface_extraction",
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception(f"Failed to create GeoObject: {e}")
        raise ProcessingError(
            f"Failed to create GeoObject: {e}",
            step="surface_extraction",
        ) from e


def create_geo_object_with_auto_adjust(
    dsm_path: str,
    ortho_path: str,
    camera_x: float,
    camera_y: float,
    distance: float = 3000.0,
    resolution: float = 1.0,
    crs: str | None = None,
    max_retries: int = 3,
) -> tuple[GeoObject, float]:
    """Create a GeoObject with automatic distance adjustment if too large.

    If the requested distance exceeds the DSM/orthophoto bounds, automatically
    reduces the distance and retries up to max_retries times.

    Args:
        dsm_path: Path to the Digital Surface Model (GeoTIFF).
        ortho_path: Path to the orthophoto (GeoTIFF).
        camera_x: Camera X coordinate in the projected CRS.
        camera_y: Camera Y coordinate in the projected CRS.
        distance: Initial distance from camera to surface edge (meters).
        resolution: Surface mesh resolution (meters).
        crs: Optional CRS override. If None, uses DSM's CRS.
        max_retries: Maximum number of retry attempts with reduced distance.

    Returns:
        Tuple of (GeoObject, actual_distance_used).

    Raises:
        FileError: If files cannot be read.
        ProcessingError: If surface extraction fails after all retries.
        MemoryError: If out of memory during processing.
    """
    current_distance = distance

    for attempt in range(max_retries):
        try:
            geo = create_geo_object(
                dsm_path=dsm_path,
                ortho_path=ortho_path,
                camera_x=camera_x,
                camera_y=camera_y,
                crs=crs,
                distance=current_distance,
                resolution=resolution,
            )
            if current_distance != distance:
                logger.info(
                    f"Successfully created GeoObject with adjusted distance: "
                    f"{distance}m -> {current_distance:.1f}m"
                )
            return geo, current_distance
        except ProcessingError as e:
            # Check if error is about distance being too large
            error_msg = str(e)
            match = re.search(r"less than (\d+\.?\d*)", error_msg)
            if match and attempt < max_retries - 1:
                max_allowed = float(match.group(1))
                # Use 90% of max allowed distance for safety margin
                current_distance = max_allowed * 0.9
                logger.warning(
                    f"Surface distance {distance}m too large, "
                    f"retrying with {current_distance:.1f}m (attempt {attempt + 2}/{max_retries})"
                )
            else:
                raise

    # Should not reach here, but just in case
    raise RuntimeError("Failed to create GeoObject after multiple attempts")


def generate_simulation(
    geo: GeoObject,
    camera_params: CameraParamsValues,
    target_width: int,
    target_height: int,
    min_distance: float | None = None,
) -> np.ndarray:
    """Generate a simulated landscape image from camera parameters.

    Uses OpenGL-based rendering to project the 3D surface mesh
    onto a 2D image plane.

    Args:
        geo: GeoObject containing surface mesh data.
        camera_params: Camera parameters (position, orientation, lens).
        target_width: Output image width in pixels.
        target_height: Output image height in pixels.
        min_distance: Optional minimum distance from camera (meters).
            Pixels closer than this will be rendered black.

    Returns:
        BGR image array (OpenCV format).

    Raises:
        ProcessingError: If simulation generation fails.
    """
    from alproj.project import sim_image

    try:
        # Build params dict for alproj
        params = _camera_params_to_dict(camera_params, target_width, target_height)

        # Generate simulation image
        img = sim_image(
            vert=geo.vert,
            color=geo.col,
            ind=geo.ind,
            params=params,
            offsets=geo.offsets,
            min_distance=min_distance,
        )

        return img

    except Exception as e:
        logger.exception(f"Failed to generate simulation: {e}")
        raise ProcessingError(
            f"Failed to generate simulation image: {e}",
            step="simulation",
        ) from e


def _camera_params_to_dict(
    params: CameraParamsValues,
    width: int,
    height: int,
) -> dict[str, Any]:
    """Convert CameraParamsValues to alproj params dict.

    Args:
        params: Camera parameters schema.
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        Dictionary compatible with alproj functions.
    """
    return {
        "x": params.x,
        "y": params.y,
        "z": params.z,
        "fov": params.fov,
        "pan": params.pan,
        "tilt": params.tilt,
        "roll": params.roll,
        "w": width,
        "h": height,
        "cx": params.cx if params.cx is not None else width / 2,
        "cy": params.cy if params.cy is not None else height / 2,
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
    }


def dict_to_camera_params(params_dict: dict[str, Any]) -> CameraParamsValues:
    """Convert alproj params dict to CameraParamsValues.

    Args:
        params_dict: Dictionary from alproj optimization.

    Returns:
        CameraParamsValues schema.
    """
    return CameraParamsValues(
        x=params_dict["x"],
        y=params_dict["y"],
        z=params_dict["z"],
        fov=params_dict["fov"],
        pan=params_dict["pan"],
        tilt=params_dict["tilt"],
        roll=params_dict["roll"],
        a1=params_dict.get("a1", 1.0),
        a2=params_dict.get("a2", 1.0),
        k1=params_dict.get("k1", 0.0),
        k2=params_dict.get("k2", 0.0),
        k3=params_dict.get("k3", 0.0),
        k4=params_dict.get("k4", 0.0),
        k5=params_dict.get("k5", 0.0),
        k6=params_dict.get("k6", 0.0),
        p1=params_dict.get("p1", 0.0),
        p2=params_dict.get("p2", 0.0),
        s1=params_dict.get("s1", 0.0),
        s2=params_dict.get("s2", 0.0),
        s3=params_dict.get("s3", 0.0),
        s4=params_dict.get("s4", 0.0),
        cx=params_dict.get("cx"),
        cy=params_dict.get("cy"),
    )


def _build_gcp_list(gcps_df: pd.DataFrame, projected: pd.DataFrame) -> list[GCP]:
    """Build GCP list with residuals from dataframes.

    Args:
        gcps_df: DataFrame with columns u, v, x, y, z.
        projected: DataFrame with projected u, v coordinates.

    Returns:
        List of GCP schemas with residuals.
    """
    gcps = []

    for i, (_, row) in enumerate(gcps_df.iterrows()):
        proj_row = projected.iloc[i]

        # Calculate residual (Euclidean distance in pixels)
        residual = float(
            np.sqrt((row["u"] - proj_row["u"]) ** 2 + (row["v"] - proj_row["v"]) ** 2)
        )

        gcps.append(
            GCP(
                id=i,
                image_x=float(row["u"]),
                image_y=float(row["v"]),
                geo_x=float(row["x"]),
                geo_y=float(row["y"]),
                geo_z=float(row["z"]),
                residual=residual,
                enabled=True,
            )
        )

    return gcps


def _calculate_metrics(gcps_df: pd.DataFrame, projected: pd.DataFrame) -> ProcessMetrics:
    """Calculate processing quality metrics.

    Args:
        gcps_df: DataFrame with observed GCP coordinates.
        projected: DataFrame with projected coordinates.

    Returns:
        ProcessMetrics with RMSE and residual statistics.
    """
    # Calculate residuals
    residuals = np.sqrt(
        (gcps_df["u"].values - projected["u"].values) ** 2
        + (gcps_df["v"].values - projected["v"].values) ** 2
    )

    return ProcessMetrics(
        rmse=float(np.sqrt(np.mean(residuals**2))),
        gcp_count=len(gcps_df),
        gcp_total=len(gcps_df),
        residual_mean=float(np.mean(residuals)),
        residual_std=float(np.std(residuals)),
        residual_max=float(np.max(residuals)),
    )


# =============================================================================
# Async API functions (for FastAPI routes)
# =============================================================================


async def run_estimation(
    dsm_path: str,
    ortho_path: str,
    target_image_path: str,
    camera_params: CameraParamsValues,
    matching_method: str = "superpoint-lightglue",
    optimizer: str = "cma",
    max_generations: int = 300,
    min_gcp_distance: float = 100.0,
    match_id: str | None = None,
    two_stage: bool = False,
    outlier_filter: str | None = None,
    spatial_thin_grid: int | None = None,
    spatial_thin_selection: str | None = None,
    resize: int | str | None = None,
    threshold: float = 30.0,
    surface_distance: float = 3000.0,
    simulation_min_distance: float = 100.0,
    optimize_position: bool = True,
    optimize_orientation: bool = True,
    optimize_fov: bool = True,
    optimize_distortion: bool = True,
) -> tuple[bytes, CameraParamsValues, list[str]]:
    """Run camera parameter estimation using alproj optimization.

    Performs full optimization pipeline following example.py:
    1. Generate simulation image from initial parameters
    2. Run image matching between target and simulation
    3. Set GCPs from matching results
    4. Optimize camera parameters (Phase 1: position, orientation, FOV, aspect)
    5. If two_stage: re-match and optimize distortion parameters (Phase 2)

    Args:
        dsm_path: Path to Digital Surface Model file.
        ortho_path: Path to orthophoto file.
        target_image_path: Path to target photograph.
        camera_params: Initial camera parameters.
        matching_method: Image matching algorithm.
        optimizer: Optimization method ("cma" or "lsq").
        max_generations: Maximum optimizer iterations.
        min_gcp_distance: Minimum GCP distance from camera (meters).
        match_id: Optional cached match ID from Step 3 to reuse matching results.
        two_stage: Enable two-stage estimation.
        outlier_filter: Outlier filter type (fundamental/essential).
        spatial_thin_grid: Spatial thinning grid size.
        spatial_thin_selection: Spatial thinning selection strategy.
        resize: Resize for matching.
        threshold: Matching threshold.
        surface_distance: Surface extraction distance from camera.
        simulation_min_distance: Minimum distance to render in simulation.
        optimize_position: Optimize camera position (x, y, z).
        optimize_orientation: Optimize camera orientation (pan, tilt, roll).
        optimize_fov: Optimize field of view (fov, a1, a2).
        optimize_distortion: Optimize distortion parameters (k, p, s).

    Returns:
        Tuple of (simulation_png_bytes, optimized_params, log_messages).

    Raises:
        FileNotFoundError: If input files don't exist.
        ProcessingError: If optimization fails.
    """
    import cv2
    from uuid import uuid4
    from app.core.config import settings

    # Validate file paths
    if not Path(dsm_path).exists():
        raise FileNotFoundError(f"DSM file not found: {dsm_path}")
    if not Path(ortho_path).exists():
        raise FileNotFoundError(f"Ortho file not found: {ortho_path}")
    if not Path(target_image_path).exists():
        raise FileNotFoundError(f"Target image not found: {target_image_path}")

    def _run() -> tuple[bytes, CameraParamsValues, list[str]]:
        from alproj.gcp import image_match, set_gcp, filter_gcp_distance
        from alproj.optimize import CMAOptimizer, LsqOptimizer
        from alproj.project import reverse_proj

        log: list[str] = []

        if not (optimize_position or optimize_orientation or optimize_fov or optimize_distortion or two_stage):
            raise ProcessingError(
                "No optimization targets selected",
                step="optimization",
            )

        # Get target image dimensions
        target_img = cv2.imread(target_image_path)
        if target_img is None:
            raise ValueError(f"Cannot read target image: {target_image_path}")
        target_h, target_w = target_img.shape[:2]
        log.append(f"Target image size: {target_w}x{target_h}")

        # Build params dict with correct dimensions
        params_dict = _camera_params_to_dict(camera_params, target_w, target_h)
        log.append(f"Initial params: x={params_dict['x']}, y={params_dict['y']}, z={params_dict['z']}")

        # Create GeoObject with auto-adjustment if distance is too large
        log.append("Creating GeoObject from DSM/orthophoto...")
        geo, actual_distance = create_geo_object_with_auto_adjust(
            dsm_path=dsm_path,
            ortho_path=ortho_path,
            camera_x=camera_params.x,
            camera_y=camera_params.y,
            distance=surface_distance,
            resolution=1.0,  # Full resolution for accurate matching
        )
        if actual_distance != surface_distance:
            log.append(f"Surface distance adjusted: {surface_distance}m -> {actual_distance:.1f}m")

        # Generate initial simulation at full size
        log.append("Generating initial simulation image...")
        sim_img = generate_simulation(
            geo=geo,
            camera_params=camera_params,
            target_width=target_w,
            target_height=target_h,
            min_distance=simulation_min_distance,  # Mask closer area
        )

        # Save simulation to temp file for image_match
        settings.temp_dir.mkdir(parents=True, exist_ok=True)
        sim_path = settings.temp_dir / f"sim_est_{uuid4().hex}.png"
        cv2.imwrite(str(sim_path), sim_img)

        # Reverse projection to get coordinate mapping
        log.append("Running reverse projection...")
        df = reverse_proj(sim_img, geo.vert, geo.ind, params_dict, geo.offsets)

        try:
            resize_value = _normalize_resize(matching_method, resize)
            if isinstance(resize_value, str) and resize_value.lower() == "none":
                resize_value = max(target_w, target_h)

            # Phase 1: Image matching (or reuse cached result)
            log.append(f"Running image matching ({matching_method})...")
            match_kwargs: dict[str, Any] = {
                "method": matching_method,
                "plot_result": False,
                "params": params_dict,
                "resize": resize_value,
                "threshold": threshold,
            }
            if outlier_filter:
                match_kwargs["outlier_filter"] = outlier_filter
            if spatial_thin_grid:
                match_kwargs["spatial_thin_grid"] = spatial_thin_grid
            if spatial_thin_selection:
                match_kwargs["spatial_thin_selection"] = spatial_thin_selection

            match = None
            if match_id:
                from app.core.match_cache import get_match

                cached = get_match(match_id)
                if cached is not None:
                    meta = cached.metadata
                    if (
                        meta.get("target_image_path") == target_image_path
                        and meta.get("params_dict") == params_dict
                        and meta.get("matching_method") == matching_method
                        and meta.get("resize") == resize_value
                        and meta.get("threshold") == threshold
                        and meta.get("outlier_filter") == outlier_filter
                        and meta.get("spatial_thin_grid") == spatial_thin_grid
                        and meta.get("spatial_thin_selection") == spatial_thin_selection
                        and meta.get("surface_distance") == surface_distance
                        and meta.get("actual_distance") == actual_distance
                        and meta.get("simulation_min_distance") == simulation_min_distance
                        and meta.get("target_w") == target_w
                        and meta.get("target_h") == target_h
                    ):
                        match = cached.match
                        log.append(f"Using cached matches: {match_id}")
                    else:
                        log.append("Cached matches not compatible; re-running image matching")
                else:
                    log.append("Cached matches not found or expired; re-running image matching")

            if match is None:
                match, _ = image_match(target_image_path, str(sim_path), **match_kwargs)
            log.append(f"Found {len(match)} matching points")

            if len(match) < 4:
                raise ProcessingError(
                    f"Insufficient matching points: {len(match)} (minimum 4 required)",
                    step="matching",
                )

            # Set GCPs from matching
            gcps = set_gcp(match, df)
            log.append(f"Set {len(gcps)} GCPs")

            # Filter GCPs by distance
            gcps = filter_gcp_distance(gcps, params_dict, min_distance=min_gcp_distance)
            log.append(f"After distance filter (>{min_gcp_distance}m): {len(gcps)} GCPs")

            if len(gcps) < 4:
                raise ProcessingError(
                    f"Insufficient GCPs after filtering: {len(gcps)} (minimum 4 required)",
                    step="gcp_filtering",
                )

            # Validate GCP DataFrame columns
            required_cols = {"x", "y", "z", "u", "v"}
            gcp_cols = set(gcps.columns)
            if not required_cols.issubset(gcp_cols):
                missing = required_cols - gcp_cols
                raise ProcessingError(
                    f"GCPs missing required columns: {missing}",
                    step="gcp_preparation",
                )

            # Phase 1 Optimization: position/orientation/FOV/aspect
            phase1_targets: list[str] = []
            if optimize_position:
                phase1_targets.extend(["x", "y", "z"])
            if optimize_orientation:
                phase1_targets.extend(["pan", "tilt", "roll"])
            if optimize_fov:
                phase1_targets.extend(["fov", "a1", "a2"])

            params_2nd = params_dict
            if phase1_targets:
                log.append(f"Phase 1: Optimizing position/orientation ({optimizer})...")
                if optimizer == "cma":
                    opt = CMAOptimizer(gcps[["x", "y", "z"]], gcps[["u", "v"]], params_dict)
                    opt.set_target(phase1_targets)
                    try:
                        params_2nd, error = opt.optimize(
                            generation=max_generations,
                            sigma=1.0,
                            population_size=150,
                            f_scale=10.0,
                        )
                    except Exception as e:
                        logger.exception("CMA-ES optimization failed")
                        raise ProcessingError(
                            f"CMA-ES optimization failed: {e}",
                            step="optimization_phase1",
                        ) from e
                else:  # lsq
                    opt = LsqOptimizer(gcps[["x", "y", "z"]], gcps[["u", "v"]], params_dict)
                    opt.set_target(phase1_targets)
                    try:
                        params_2nd, error = opt.optimize(method="trf", max_nfev=max_generations)
                    except Exception as e:
                        logger.exception("LSQ optimization failed")
                        raise ProcessingError(
                            f"LSQ optimization failed: {e}",
                            step="optimization_phase1",
                        ) from e

                # Validate optimizer return value
                if not isinstance(params_2nd, dict):
                    raise ProcessingError(
                        f"Optimizer returned unexpected type: {type(params_2nd)}",
                        step="optimization_phase1",
                    )

                # Check for NaN/inf values in optimized parameters
                for key, value in params_2nd.items():
                    if isinstance(value, (int, float)) and (np.isnan(value) or np.isinf(value)):
                        raise ProcessingError(
                            f"Optimizer returned invalid value for {key}: {value}",
                            step="optimization_phase1",
                        )

                log.append(f"Phase 1 complete. Error: {error:.4f}")
            else:
                log.append("Phase 1 skipped: no targets selected")

            optimized_params = params_2nd

            # Two-stage: Phase 2 for distortion parameters
            if optimize_distortion or two_stage:
                log.append("Phase 2: Re-matching with optimized parameters...")

                # Generate new simulation with Phase 1 results
                sim2_img = generate_simulation(
                    geo=geo,
                    camera_params=dict_to_camera_params(params_2nd),
                    target_width=target_w,
                    target_height=target_h,
                    min_distance=simulation_min_distance,
                )
                sim2_path = settings.temp_dir / f"sim_est2_{uuid4().hex}.png"
                cv2.imwrite(str(sim2_path), sim2_img)

                # Update params for matching
                df2 = reverse_proj(sim2_img, geo.vert, geo.ind, params_2nd, geo.offsets)

                # Phase 2 matching (tighter grid)
                match_kwargs2 = match_kwargs.copy()
                match_kwargs2["params"] = params_2nd
                match_kwargs2["outlier_filter"] = "essential"
                if spatial_thin_grid:
                    match_kwargs2["spatial_thin_grid"] = max(spatial_thin_grid // 2, 10)

                try:
                    match2, _ = image_match(target_image_path, str(sim2_path), **match_kwargs2)
                    log.append(f"Phase 2 matching: {len(match2)} points")

                    gcps2 = set_gcp(match2, df2)
                    gcps2 = filter_gcp_distance(gcps2, params_2nd, min_distance=min_gcp_distance)
                    log.append(f"Phase 2 GCPs after filter: {len(gcps2)}")

                    if len(gcps2) >= 4:
                        # Phase 2a Optimization: primary distortion parameters
                        # f_scale is set to 2x the previous error for robustness
                        phase2_f_scale = error * 2.0
                        log.append(
                            f"Phase 2a: Optimizing primary distortion ({optimizer}, f_scale={phase2_f_scale:.2f})..."
                        )
                        phase2a_targets: list[str] = ["fov", "a1", "k1", "k2", "k3", "p1", "p2", "s1", "s3"]

                        if optimizer == "cma":
                            opt2a = CMAOptimizer(gcps2[["x", "y", "z"]], gcps2[["u", "v"]], params_2nd)
                            opt2a.set_target(phase2a_targets)
                            try:
                                params_2a, error2a = opt2a.optimize(
                                    generation=max_generations,
                                    sigma=1.0,
                                    population_size=150,
                                    f_scale=phase2_f_scale,
                                )
                            except Exception as e:
                                logger.exception("Phase 2a CMA-ES optimization failed")
                                raise ProcessingError(
                                    f"Phase 2a CMA-ES optimization failed: {e}",
                                    step="optimization_phase2a",
                                ) from e
                        else:
                            opt2a = LsqOptimizer(gcps2[["x", "y", "z"]], gcps2[["u", "v"]], params_2nd)
                            opt2a.set_target(phase2a_targets)
                            try:
                                params_2a, error2a = opt2a.optimize(method="trf", max_nfev=max_generations)
                            except Exception as e:
                                logger.exception("Phase 2a LSQ optimization failed")
                                raise ProcessingError(
                                    f"Phase 2a LSQ optimization failed: {e}",
                                    step="optimization_phase2a",
                                ) from e

                        # Validate Phase 2a result
                        if not isinstance(params_2a, dict):
                            raise ProcessingError(
                                f"Phase 2a optimizer returned unexpected type: {type(params_2a)}",
                                step="optimization_phase2a",
                            )
                        for key, value in params_2a.items():
                            if isinstance(value, (int, float)) and (np.isnan(value) or np.isinf(value)):
                                raise ProcessingError(
                                    f"Phase 2a optimizer returned invalid value for {key}: {value}",
                                    step="optimization_phase2a",
                                )
                        log.append(f"Phase 2a complete. Error: {error2a:.4f}")

                        # Phase 2b Optimization: secondary distortion parameters
                        phase2b_f_scale = error2a * 2.0
                        log.append(
                            f"Phase 2b: Optimizing secondary distortion ({optimizer}, f_scale={phase2b_f_scale:.2f})..."
                        )
                        phase2b_targets: list[str] = ["k4", "k5", "k6", "s2", "s4"]

                        if optimizer == "cma":
                            opt2b = CMAOptimizer(gcps2[["x", "y", "z"]], gcps2[["u", "v"]], params_2a)
                            opt2b.set_target(phase2b_targets)
                            try:
                                # Phase 2b uses smaller population/generation since it optimizes fewer parameters
                                params_final, error2 = opt2b.optimize(
                                    generation=100,
                                    sigma=1.0,
                                    population_size=100,
                                    f_scale=phase2b_f_scale,
                                )
                            except Exception as e:
                                logger.exception("Phase 2b CMA-ES optimization failed")
                                raise ProcessingError(
                                    f"Phase 2b CMA-ES optimization failed: {e}",
                                    step="optimization_phase2b",
                                ) from e
                        else:
                            opt2b = LsqOptimizer(gcps2[["x", "y", "z"]], gcps2[["u", "v"]], params_2a)
                            opt2b.set_target(phase2b_targets)
                            try:
                                params_final, error2 = opt2b.optimize(method="trf", max_nfev=max_generations)
                            except Exception as e:
                                logger.exception("Phase 2b LSQ optimization failed")
                                raise ProcessingError(
                                    f"Phase 2b LSQ optimization failed: {e}",
                                    step="optimization_phase2b",
                                ) from e

                        # Validate Phase 2b result
                        if not isinstance(params_final, dict):
                            raise ProcessingError(
                                f"Phase 2b optimizer returned unexpected type: {type(params_final)}",
                                step="optimization_phase2b",
                            )
                        for key, value in params_final.items():
                            if isinstance(value, (int, float)) and (np.isnan(value) or np.isinf(value)):
                                raise ProcessingError(
                                    f"Phase 2b optimizer returned invalid value for {key}: {value}",
                                    step="optimization_phase2b",
                                )

                        log.append(f"Phase 2b complete. Error: {error2:.4f}")
                        optimized_params = params_final
                    else:
                        log.append("Phase 2 skipped: insufficient GCPs after filtering")
                except Exception as e:
                    log.append(f"Phase 2 matching failed: {e}, using Phase 1 results")
                finally:
                    try:
                        sim2_path.unlink(missing_ok=True)
                    except Exception:
                        pass

            # Generate final simulation image
            log.append("Generating final simulation image...")
            final_sim = generate_simulation(
                geo=geo,
                camera_params=dict_to_camera_params(optimized_params),
                target_width=target_w,
                target_height=target_h,
                min_distance=simulation_min_distance,
            )

            # Encode to PNG
            _, png_bytes = cv2.imencode(".png", final_sim)

            return bytes(png_bytes.tobytes()), dict_to_camera_params(optimized_params), log

        finally:
            # Cleanup temp files
            try:
                sim_path.unlink(missing_ok=True)
            except Exception:
                pass

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run)


async def generate_simulation_image(
    dsm_path: str,
    ortho_path: str,
    target_image_path: str,
    camera_params: CameraParamsValues,
    max_size: int = 800,
    surface_distance: float = 3000.0,
    simulation_min_distance: float = 100.0,
) -> bytes:
    """Generate a simulation preview image.

    Uses alproj to render what the camera would see with the given parameters,
    based on the DSM and orthophoto.

    Args:
        dsm_path: Path to Digital Surface Model file.
        ortho_path: Path to orthophoto file.
        target_image_path: Path to target photograph (for dimensions).
        camera_params: Camera position, orientation, and lens parameters.
        max_size: Maximum output image dimension.
        surface_distance: Surface extraction distance from camera.
        simulation_min_distance: Minimum distance to render in simulation.

    Returns:
        PNG image as bytes.

    Raises:
        FileNotFoundError: If input files don't exist.
        ValueError: If parameters are invalid.
        RuntimeError: If rendering fails.
    """
    # Validate file paths
    if not Path(dsm_path).exists():
        raise FileNotFoundError(f"DSM file not found: {dsm_path}")
    if not Path(ortho_path).exists():
        raise FileNotFoundError(f"Ortho file not found: {ortho_path}")
    if not Path(target_image_path).exists():
        raise FileNotFoundError(f"Target image not found: {target_image_path}")

    # Run in thread pool to avoid blocking
    def _generate() -> bytes:
        try:
            import cv2

            # Get target image dimensions
            target_img = cv2.imread(target_image_path)
            if target_img is None:
                raise ValueError(f"Cannot read target image: {target_image_path}")

            h, w = target_img.shape[:2]

            # Scale to max_size
            scale = min(max_size / w, max_size / h, 1.0)
            out_w, out_h = int(w * scale), int(h * scale)

            # Create GeoObject with auto-adjustment if distance is too large
            geo, _ = create_geo_object_with_auto_adjust(
                dsm_path=dsm_path,
                ortho_path=ortho_path,
                camera_x=camera_params.x,
                camera_y=camera_params.y,
                distance=surface_distance,
                resolution=5.0,  # Use coarser resolution for preview
            )

            # Generate simulation image
            sim_img = generate_simulation(
                geo=geo,
                camera_params=camera_params,
                target_width=out_w,
                target_height=out_h,
                min_distance=simulation_min_distance,
            )

            # Encode to PNG
            _, png_bytes = cv2.imencode(".png", sim_img)
            return bytes(png_bytes.tobytes())

        except ImportError as e:
            logger.error(f"alproj library import error: {e}")
            raise RuntimeError(
                f"alproj library import failed: {e}. "
                "Please ensure alproj is properly installed."
            ) from e
        except Exception as e:
            logger.exception("Simulation generation failed")
            raise RuntimeError(f"Failed to generate simulation: {e}") from e

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _generate)


async def run_georectification(
    project_id: str,
    options: ProcessOptions | None,
    job: Job,
) -> dict[str, Any]:
    """Run the full georectification process.

    Args:
        project_id: Project UUID string.
        options: Processing options.
        job: Job instance for progress updates.

    Returns:
        Processing result dict with GCPs, metrics, etc.

    Raises:
        ValueError: If project or data is invalid.
        RuntimeError: If processing fails.
    """
    # Import recovery service
    from app.services.recovery import clear_recovery_state

    result: dict[str, Any] = {
        "gcps": [],
        "metrics": None,
        "geotiff_path": None,
        "log": [],
    }

    try:
        # Step 1: Initialize
        await job.update_progress(0.0, "initializing", "Loading project data...")
        await asyncio.sleep(0.1)  # Allow UI to update
        await job.check_cancellation()

        # TODO: Load project from storage
        # project = await load_project(project_id)

        result["log"].append(f"Processing project: {project_id}")

        # Step 2: Feature matching
        await job.update_progress(0.1, "matching", "Detecting features...")
        await job.check_cancellation()

        # Simulate processing time for now
        # In real implementation, this would call alproj
        for i in range(5):
            await asyncio.sleep(0.2)
            await job.check_cancellation()
            await job.update_progress(
                0.1 + (i + 1) * 0.1,
                "matching",
                f"Matching features... ({(i+1)*20}%)",
            )

        result["log"].append("Feature matching complete")

        # Step 3: Optimization
        await job.update_progress(0.6, "optimizing", "Optimizing camera parameters...")
        await job.check_cancellation()

        for i in range(3):
            await asyncio.sleep(0.3)
            await job.check_cancellation()
            await job.update_progress(
                0.6 + (i + 1) * 0.1,
                "optimizing",
                f"Optimization iteration {i+1}...",
            )

        result["log"].append("Optimization complete")

        # Step 4: Generate GCPs
        await job.update_progress(0.9, "generating", "Generating GCP list...")
        await job.check_cancellation()

        # Placeholder GCPs
        result["gcps"] = [
            {
                "id": 1,
                "image_x": 100.0,
                "image_y": 200.0,
                "geo_x": 500000.0,
                "geo_y": 4000000.0,
                "geo_z": 1500.0,
                "residual": 2.5,
                "enabled": True,
            },
            {
                "id": 2,
                "image_x": 300.0,
                "image_y": 400.0,
                "geo_x": 500100.0,
                "geo_y": 4000100.0,
                "geo_z": 1600.0,
                "residual": 1.8,
                "enabled": True,
            },
        ]

        result["metrics"] = {
            "rmse": 2.15,
            "gcp_count": 2,
            "gcp_total": 2,
            "residual_mean": 2.15,
            "residual_std": 0.35,
            "residual_max": 2.5,
        }

        result["log"].append("GCP generation complete")

        # Step 5: Finalize
        await job.update_progress(1.0, "complete", "Processing complete")

        # Clear recovery state on success
        clear_recovery_state(project_id)

        return result

    except asyncio.CancelledError:
        result["log"].append("Processing cancelled by user")
        raise
    except Exception as e:
        result["log"].append(f"Error: {e}")
        logger.exception("Georectification failed")
        raise


async def run_export_job(
    project_id: str,
    output_path: str,
    resolution: float = 1.0,
    crs: str = "EPSG:6690",
    interpolate: bool = True,
    max_dist: float | None = None,
    surface_distance: float = 3000.0,
    template_path: str | None = None,
    job: "Job | None" = None,
) -> dict[str, Any]:
    """Run GeoTIFF export as a background job with progress reporting.

    Args:
        project_id: Project UUID string.
        output_path: Destination file path.
        resolution: Output resolution in meters per pixel.
        crs: Output coordinate reference system.
        interpolate: Whether to interpolate for smoother output.
        max_dist: Maximum interpolation distance (meters). Defaults to resolution.
        surface_distance: Surface extraction distance from camera.
        template_path: Optional template raster path.
        job: Job instance for progress updates.

    Returns:
        Dict with path to exported file.

    Raises:
        FileNotFoundError: If project or result not found.
        ValueError: If parameters are invalid.
        RuntimeError: If export fails.
    """
    result: dict[str, Any] = {"path": None, "log": []}

    async def update_progress(progress: float, step: str, message: str) -> None:
        """Update progress if job is provided."""
        if job:
            await job.update_progress(progress, step, message)
            await job.check_cancellation()

    try:
        # Step 1: Validation
        await update_progress(0.0, "validating", "Validating parameters...")

        # Validate output path
        output_dir = Path(output_path).parent
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                raise ValueError(
                    f"Cannot create output directory '{output_dir}': Permission denied. "
                    "Please choose a different location."
                ) from e

        # Check write permission
        if not os.access(output_dir, os.W_OK):
            raise ValueError(
                f"Cannot write to directory '{output_dir}': Permission denied. "
                "Please choose a different location."
            )

        result["log"].append(f"Output path: {output_path}")

        # Step 2: Load project
        await update_progress(0.05, "loading", "Loading project data...")

        from app.api.routes.projects import get_project, save_project

        project = get_project(project_id)
        if project is None:
            raise FileNotFoundError(f"Project not found: {project_id}")

        input_data = project.input_data
        if not input_data or not input_data.dsm or not input_data.ortho or not input_data.target_image:
            raise FileNotFoundError("Project input data is incomplete")

        dsm_path = input_data.dsm.path
        ortho_path = input_data.ortho.path
        target_image_path = input_data.target_image.path

        if not Path(dsm_path).exists():
            raise FileNotFoundError(f"DSM file not found: {dsm_path}")
        if not Path(ortho_path).exists():
            raise FileNotFoundError(f"Ortho file not found: {ortho_path}")
        if not Path(target_image_path).exists():
            raise FileNotFoundError(f"Target image not found: {target_image_path}")

        camera_params = None
        if project.camera_params:
            camera_params = project.camera_params.optimized or project.camera_params.initial
        if camera_params is None:
            raise ValueError("Camera parameters are not set for this project")

        if template_path:
            template = Path(template_path)
            if not template.exists():
                raise FileNotFoundError(f"Template raster not found: {template_path}")

        result["log"].append("Project data loaded")

        # Step 3: Load target image (CPU-intensive, run in executor)
        await update_progress(0.1, "loading_image", "Loading target image...")

        def _load_image() -> tuple[np.ndarray, int, int]:
            import cv2
            target_img = cv2.imread(target_image_path)
            if target_img is None:
                raise ValueError(f"Cannot read target image: {target_image_path}")
            target_h, target_w = target_img.shape[:2]
            return target_img, target_w, target_h

        loop = asyncio.get_running_loop()
        target_img, target_w, target_h = await loop.run_in_executor(None, _load_image)
        result["log"].append(f"Target image: {target_w}x{target_h}")

        # Build params dict for alproj with correct dimensions
        params_dict = _camera_params_to_dict(camera_params, target_w, target_h)

        # Step 4: Create GeoObject (CPU-intensive)
        await update_progress(0.15, "surface", "Creating surface mesh...")

        def _create_geo() -> GeoObject:
            geo, _ = create_geo_object_with_auto_adjust(
                dsm_path=dsm_path,
                ortho_path=ortho_path,
                camera_x=camera_params.x,
                camera_y=camera_params.y,
                distance=surface_distance,
                resolution=resolution,
            )
            return geo

        geo = await loop.run_in_executor(None, _create_geo)
        result["log"].append("Surface mesh created")

        # Step 5: Reverse projection (most time-consuming step)
        await update_progress(0.3, "projecting", "Reverse projecting image...")

        def _reverse_proj() -> "pd.DataFrame":
            from alproj.project import reverse_proj
            return reverse_proj(target_img, geo.vert, geo.ind, params_dict, geo.offsets)

        df = await loop.run_in_executor(None, _reverse_proj)
        result["log"].append(f"Reverse projection complete: {len(df)} points")

        # Step 6: Write GeoTIFF (also time-consuming)
        await update_progress(0.7, "writing", "Writing GeoTIFF...")

        def _write_geotiff() -> None:
            from alproj.project import to_geotiff
            effective_max_dist = max_dist if max_dist is not None else resolution
            to_geotiff(
                df,
                output_path,
                resolution=resolution,
                crs=crs,
                bands=["R", "G", "B"],
                interpolate=interpolate,
                max_dist=effective_max_dist,
                agg_func="mean",
            )

        await loop.run_in_executor(None, _write_geotiff)
        result["log"].append("GeoTIFF written")

        # Step 7: Finalize
        await update_progress(0.95, "finalizing", "Finalizing...")

        if project.process_result is not None:
            project.process_result.geotiff_path = output_path
            save_project(project)

        result["path"] = output_path
        result["log"].append("Export complete")

        await update_progress(1.0, "complete", "Export complete")

        logger.info(f"GeoTIFF export complete: {output_path}")
        return result

    except asyncio.CancelledError:
        result["log"].append("Export cancelled by user")
        raise
    except Exception as e:
        result["log"].append(f"Error: {e}")
        logger.exception("GeoTIFF export failed")
        raise


async def export_geotiff(
    project_id: str,
    output_path: str,
    resolution: float = 1.0,
    crs: str = "EPSG:6690",
    interpolate: bool = True,
    max_dist: float | None = None,
    surface_distance: float = 3000.0,
    template_path: str | None = None,
) -> str:
    """Export georectified result as GeoTIFF (legacy synchronous wrapper).

    This is kept for backwards compatibility. Use run_export_job for
    background processing with progress reporting.

    Args:
        project_id: Project UUID string.
        output_path: Destination file path.
        resolution: Output resolution in meters per pixel.
        crs: Output coordinate reference system.
        interpolate: Whether to interpolate for smoother output.
        max_dist: Maximum interpolation distance (meters). Defaults to resolution.
        surface_distance: Surface extraction distance from camera.
        template_path: Optional template raster path.

    Returns:
        Path to exported file.
    """
    result = await run_export_job(
        project_id=project_id,
        output_path=output_path,
        resolution=resolution,
        crs=crs,
        interpolate=interpolate,
        max_dist=max_dist,
        surface_distance=surface_distance,
        template_path=template_path,
        job=None,
    )
    return result["path"]


# =============================================================================
# Partial Reprocessing
# =============================================================================


async def reprocess_from_step(
    project: "Project",
    from_step: str,
    options: "ProcessOptions | None",
    progress_callback: "ProgressCallback",
) -> dict[str, Any]:
    """Reprocess from a specific step.

    This function allows partial reprocessing of a project from a specified step,
    reusing previous results where appropriate.

    Args:
        project: Project to reprocess.
        from_step: Step to start from ("matching", "optimization", or "export").
        options: Processing options override.
        progress_callback: Async callback for progress updates (progress, step, message).

    Returns:
        Processing result dict with GCPs, metrics, etc.

    Raises:
        ValueError: If step is invalid.
        ProcessingError: If reprocessing fails.
    """
    valid_steps = {"matching", "optimization", "export"}
    if from_step not in valid_steps:
        raise ValueError(f"Invalid step: {from_step}. Must be one of {valid_steps}")

    result: dict[str, Any] = {
        "gcps": [],
        "metrics": None,
        "geotiff_path": None,
        "log": [],
    }

    try:
        # Determine which steps to run based on from_step
        run_matching = from_step == "matching"
        run_optimization = from_step in ("matching", "optimization")
        run_export = from_step in ("matching", "optimization", "export")

        result["log"].append(f"Reprocessing from step: {from_step}")

        # Step 1: Feature matching (if needed)
        if run_matching:
            await progress_callback(0.0, "matching", "Starting feature matching...")

            # Simulate feature matching
            for i in range(5):
                await asyncio.sleep(0.2)
                progress = 0.1 + (i + 1) * 0.08
                await progress_callback(progress, "matching", f"Matching features... ({(i+1)*20}%)")

            result["log"].append("Feature matching complete")
        else:
            # Reuse existing GCPs from project
            if project.process_result and project.process_result.gcps:
                result["gcps"] = [gcp.model_dump() for gcp in project.process_result.gcps]
                result["log"].append(f"Reusing {len(result['gcps'])} existing GCPs")
            await progress_callback(0.5, "matching", "Skipped (reusing existing GCPs)")

        # Step 2: Optimization (if needed)
        if run_optimization:
            await progress_callback(0.5, "optimizing", "Starting optimization...")

            # Filter enabled GCPs for optimization
            if project.process_result and project.process_result.gcps:
                enabled_gcps = [
                    gcp for gcp in project.process_result.gcps if gcp.enabled
                ]
                result["log"].append(f"Optimizing with {len(enabled_gcps)} enabled GCPs")

            # Simulate optimization iterations
            for i in range(3):
                await asyncio.sleep(0.3)
                progress = 0.5 + (i + 1) * 0.1
                await progress_callback(
                    progress, "optimizing", f"Optimization iteration {i+1}..."
                )

            # Generate optimized GCPs (simulated)
            result["gcps"] = [
                {
                    "id": 1,
                    "image_x": 100.0,
                    "image_y": 200.0,
                    "geo_x": 500000.0,
                    "geo_y": 4000000.0,
                    "geo_z": 1500.0,
                    "residual": 1.8,  # Improved residual
                    "enabled": True,
                },
                {
                    "id": 2,
                    "image_x": 300.0,
                    "image_y": 400.0,
                    "geo_x": 500100.0,
                    "geo_y": 4000100.0,
                    "geo_z": 1600.0,
                    "residual": 1.2,  # Improved residual
                    "enabled": True,
                },
            ]

            result["metrics"] = {
                "rmse": 1.5,  # Improved RMSE
                "gcp_count": 2,
                "gcp_total": 2,
                "residual_mean": 1.5,
                "residual_std": 0.3,
                "residual_max": 1.8,
            }

            result["log"].append("Optimization complete")
        else:
            # Reuse existing metrics
            if project.process_result and project.process_result.metrics:
                result["metrics"] = project.process_result.metrics.model_dump()
            await progress_callback(0.8, "optimizing", "Skipped (reusing existing optimization)")

        # Step 3: Export (if needed)
        if run_export:
            await progress_callback(0.8, "exporting", "Preparing export...")

            await asyncio.sleep(0.2)
            await progress_callback(0.9, "exporting", "Generating output...")

            # In real implementation, this would call the export function
            result["log"].append("Export preparation complete")

        # Finalize
        await progress_callback(1.0, "complete", "Reprocessing complete")
        result["log"].append("Reprocessing finished successfully")

        return result

    except asyncio.CancelledError:
        result["log"].append("Reprocessing cancelled by user")
        raise
    except Exception as e:
        result["log"].append(f"Error: {e}")
        logger.exception("Reprocessing failed")
        raise ProcessingError(
            f"Reprocessing failed at step '{from_step}': {e}",
            step=from_step,
        ) from e


# Type alias for progress callback
if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from app.schemas import Project

    ProgressCallback = Callable[[float, str, str], Awaitable[None]]


# =============================================================================
# Helper functions for matching validation
# =============================================================================


def validate_matching_result(
    points_found: int,
    min_points_required: int = 4,
    algorithm: str = "SIFT",
) -> None:
    """Validate that sufficient matching points were found.

    Args:
        points_found: Number of matching points found.
        min_points_required: Minimum required points for valid matching.
        algorithm: Matching algorithm used.

    Raises:
        MatchingError: If insufficient points were found.
    """
    if points_found < min_points_required:
        suggestions = [
            "Adjust initial camera parameters closer to the actual shooting position",
            (
                f"Try a different matching algorithm (current: {algorithm}). "
                "Options: SuperPoint-LightGlue, AKAZE, SIFT, MINIMA-ROMA, Tiny-ROMA"
            ),
            "Verify that the target image is within the DSM/orthophoto coverage area",
            "Increase the search distance from the camera position",
            "Check image quality - blurry or overexposed images may have fewer features",
        ]
        raise MatchingError(
            "Image matching failed: insufficient corresponding points",
            points_found=points_found,
            min_points_required=min_points_required,
            suggestions=suggestions,
        )


def estimate_memory_requirement(
    dsm_path: str,
    distance: float,
    resolution: float,
) -> dict[str, float]:
    """Estimate memory requirement for processing.

    Args:
        dsm_path: Path to DSM file.
        distance: Processing distance from camera.
        resolution: Surface mesh resolution.

    Returns:
        Dict with estimated_mb, recommended_resolution, and area_sq_km.
    """
    # Estimate based on area and resolution
    area_meters = (2 * distance) ** 2  # Square area around camera
    pixels = area_meters / (resolution ** 2)

    # Rough estimate: each vertex needs ~100 bytes (position, color, etc.)
    estimated_mb = (pixels * 100) / (1024 * 1024)

    # If estimated > 4GB, suggest higher resolution
    recommended_resolution = resolution
    if estimated_mb > 4000:
        # Calculate resolution needed for ~2GB
        target_pixels = 2000 * 1024 * 1024 / 100
        recommended_resolution = (area_meters / target_pixels) ** 0.5

    return {
        "estimated_mb": estimated_mb,
        "recommended_resolution": recommended_resolution,
        "area_sq_km": area_meters / 1_000_000,
    }
