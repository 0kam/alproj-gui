"""API routes for georectification operations.

Provides:
- POST /api/georectify/simulate: Generate simulation preview image
- POST /api/georectify/match: Run image matching step
- POST /api/georectify/estimate: Run camera parameter estimation step
- POST /api/georectify/process: Start georectification processing job
- POST /api/georectify/export: Export GeoTIFF file
- WebSocket /api/jobs/{jobId}/ws: Real-time progress notifications
"""

from __future__ import annotations

import asyncio
import base64
import logging
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from PIL import Image, ImageDraw

from app.api.deps import ProcessingError, ValidationError, get_job_queue_dep
from app.core.config import settings
from app.core.jobs import Job, JobProgress, JobQueue
from app.core.model_cache import configure_imm_runtime
from app.schemas.camera import SimulationRequest, SimulationResponse
from app.schemas.georectify import (
    EstimateRequest,
    EstimateResponse,
    MatchRequest,
    MatchResponse,
)
from app.schemas.job import ExportRequest, JobStatus, ProcessRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/georectify", tags=["georectify"])


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
# Response Models
# =============================================================================


class ExportResponse(BaseModel):
    """Response for GeoTIFF export."""

    path: str = Field(..., description="Path to exported GeoTIFF file")


class ProcessJobResponse(BaseModel):
    """Response for starting a processing job (202 Accepted)."""

    id: UUID = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Initial job status")
    created_at: str = Field(..., description="Job creation timestamp (ISO 8601)")


def _placeholder_png(message: str) -> bytes:
    """Generate a simple placeholder PNG with a message."""
    img = Image.new("RGB", (800, 600), color=(240, 242, 246))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (799, 599)], outline=(200, 205, 210), width=2)
    draw.text((24, 24), message, fill=(55, 65, 81))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


def _encode_plot(plot: Any) -> bytes:
    """Encode a plot object (numpy array or PIL image) into PNG bytes."""
    if isinstance(plot, Image.Image):
        buffer = BytesIO()
        plot.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()

    try:
        import numpy as np
        import cv2

        if isinstance(plot, np.ndarray):
            success, encoded = cv2.imencode(".png", plot)
            if success:
                return bytes(encoded.tobytes())
    except Exception:
        pass

    return _placeholder_png("Matching plot unavailable (fallback)")


# =============================================================================
# Simulation Endpoint
# =============================================================================


@router.post(
    "/simulate",
    response_model=SimulationResponse,
    summary="Generate simulation image",
    description="Generate a preview image showing what the camera would see with the given parameters.",
)
async def simulate(request: SimulationRequest) -> SimulationResponse:
    """Generate a simulation image from DSM/ortho with camera parameters.

    This endpoint renders a preview of what the target photograph should look like
    based on the DSM, orthophoto, and camera parameters. Used for visual alignment
    before running the full georectification process.

    Args:
        request: Simulation parameters including file paths and camera settings.

    Returns:
        Base64-encoded PNG image.

    Raises:
        ValidationError: If input files are invalid.
        ProcessingError: If simulation fails.
    """
    try:
        # Import georectify service lazily to avoid circular imports
        from app.services.georectify import generate_simulation_image

        image_bytes = await generate_simulation_image(
            dsm_path=request.dsm_path,
            ortho_path=request.ortho_path,
            target_image_path=request.target_image_path,
            camera_params=request.camera_params,
            max_size=request.max_size,
            surface_distance=request.surface_distance,
        )

        # Encode to base64
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        return SimulationResponse(image_base64=image_base64)

    except FileNotFoundError as e:
        raise ValidationError(f"File not found: {e}") from e
    except ValueError as e:
        raise ValidationError(str(e)) from e
    except Exception as e:
        logger.exception("Simulation failed")
        raise ProcessingError(f"Simulation failed: {e}", step="simulation") from e


# =============================================================================
# Matching Endpoint
# =============================================================================


@router.post(
    "/match",
    response_model=MatchResponse,
    summary="Run image matching step",
    description="Generate a matching plot image for the initial parameters.",
)
async def match_images(request: MatchRequest) -> MatchResponse:
    """Run image matching and return a plot image."""
    import cv2

    from app.services.georectify import (
        create_geo_object_with_auto_adjust,
        generate_simulation,
        _camera_params_to_dict,
    )
    from app.core.match_cache import store_match

    log: list[str] = []
    match_count: int | None = None
    match_id: str | None = None

    try:
        # Get target image dimensions for full-size simulation
        target_img = cv2.imread(request.target_image_path)
        if target_img is None:
            raise ValidationError(f"Cannot read target image: {request.target_image_path}")
        target_h, target_w = target_img.shape[:2]

        log.append(f"Target image size: {target_w}x{target_h}")
        log.append("Creating GeoObject...")

        # Create GeoObject with auto-adjustment if distance is too large
        geo, actual_distance = create_geo_object_with_auto_adjust(
            dsm_path=request.dsm_path,
            ortho_path=request.ortho_path,
            camera_x=request.camera_params.x,
            camera_y=request.camera_params.y,
            distance=request.surface_distance,
            resolution=1.0,  # Use full resolution for matching
        )
        if actual_distance != request.surface_distance:
            log.append(
                f"Surface distance adjusted: {request.surface_distance}m -> {actual_distance:.1f}m"
            )

        log.append("Generating full-size simulation image...")

        # Generate simulation at full target image size (like example.py)
        sim_img = generate_simulation(
            geo=geo,
            camera_params=request.camera_params,
            target_width=target_w,
            target_height=target_h,
            min_distance=request.simulation_min_distance,  # Mask closer area to prevent mismatch
        )

        # Save simulation image to temp file
        settings.temp_dir.mkdir(parents=True, exist_ok=True)
        sim_path = settings.temp_dir / f"sim_match_{uuid4().hex}.png"
        cv2.imwrite(str(sim_path), sim_img)

        try:
            active_weights_dir = configure_imm_runtime()
            log.append(f"Model cache: {active_weights_dir}")
            from alproj.gcp import image_match

            # Build params dict with correct image dimensions
            params_dict = _camera_params_to_dict(
                request.camera_params,
                target_w,
                target_h,
            )

            log.append(f"Running image_match ({request.matching_method})...")
            resize_value = _normalize_resize(request.matching_method, request.resize)
            if isinstance(resize_value, str) and resize_value.lower() == "none":
                resize_value = max(target_w, target_h)
            kwargs: dict[str, Any] = {
                "method": request.matching_method,
                "plot_result": True,
                "params": params_dict,
                "resize": resize_value,
                "threshold": request.threshold,
            }
            if request.outlier_filter:
                kwargs["outlier_filter"] = request.outlier_filter
            if request.spatial_thin_grid:
                kwargs["spatial_thin_grid"] = request.spatial_thin_grid
            if request.spatial_thin_selection:
                kwargs["spatial_thin_selection"] = request.spatial_thin_selection

            match, plot = image_match(
                request.target_image_path,
                str(sim_path),
                **kwargs,
            )
            match_count = len(match) if hasattr(match, "__len__") else None
            log.append(f"Found {match_count} matching points")
            plot_bytes = _encode_plot(plot)
            try:
                match_id = store_match(
                    match,
                    {
                        "target_image_path": request.target_image_path,
                        "params_dict": params_dict,
                        "matching_method": request.matching_method,
                        "resize": resize_value,
                        "threshold": request.threshold,
                        "outlier_filter": request.outlier_filter,
                        "spatial_thin_grid": request.spatial_thin_grid,
                        "spatial_thin_selection": request.spatial_thin_selection,
                        "surface_distance": request.surface_distance,
                        "actual_distance": actual_distance,
                        "simulation_min_distance": request.simulation_min_distance,
                        "target_w": target_w,
                        "target_h": target_h,
                    },
                )
                log.append(f"Cached matches: {match_id}")
            except Exception as e:
                logger.warning(f"Failed to cache matches: {e}")
        except BrokenPipeError as e:
            # BrokenPipeError often occurs with large models (minima-roma)
            # due to subprocess communication issues
            logger.error(f"BrokenPipeError during image_match: {e}", exc_info=True)
            log.append(f"image_match error: {e} (BrokenPipeError - this may occur with large models like minima-roma)")
            plot_bytes = _placeholder_png(f"Matching failed: {e}\n\nTry using a different matching method.")
        except OSError as e:
            # Catch other OS-level errors (EPIPE, etc.)
            logger.error(f"OSError during image_match: {e}", exc_info=True)
            log.append(f"image_match error: {e}")
            plot_bytes = _placeholder_png(f"Matching failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during image_match: {e}", exc_info=True)
            log.append(f"image_match error: {e}")
            plot_bytes = _placeholder_png(f"Matching failed: {e}")
        finally:
            try:
                sim_path.unlink(missing_ok=True)
            except Exception:
                pass

        return MatchResponse(
            match_plot_base64=base64.b64encode(plot_bytes).decode("utf-8"),
            match_count=match_count,
            match_id=match_id,
            log=log,
        )

    except FileNotFoundError as e:
        raise ValidationError(f"File not found: {e}") from e
    except ValueError as e:
        raise ValidationError(str(e)) from e
    except Exception as e:
        logger.exception("Image matching failed")
        raise ProcessingError(f"Matching failed: {e}", step="matching") from e


# =============================================================================
# Estimation Endpoint
# =============================================================================


@router.post(
    "/estimate",
    response_model=EstimateResponse,
    summary="Run camera parameter estimation step",
    description="Estimate camera parameters using CMA-ES or Least Squares optimization.",
)
async def estimate_camera(request: EstimateRequest) -> EstimateResponse:
    """Run camera parameter estimation and return optimized params + simulation image.

    This endpoint performs the full optimization pipeline:
    1. Generate simulation from initial parameters
    2. Match features between target and simulation
    3. Set and filter GCPs
    4. Optimize camera parameters (Phase 1: position, orientation, FOV)
    5. If two_stage enabled: re-match and optimize distortion (Phase 2)
    """
    try:
        from app.services.georectify import run_estimation

        sim_bytes, optimized_params, log = await run_estimation(
            dsm_path=request.dsm_path,
            ortho_path=request.ortho_path,
            target_image_path=request.target_image_path,
            camera_params=request.camera_params,
            matching_method=request.matching_method,
            optimizer=request.optimizer,
            max_generations=request.max_generations,
            min_gcp_distance=request.min_gcp_distance,
            match_id=request.match_id,
            two_stage=request.two_stage,
            outlier_filter=request.outlier_filter,
            spatial_thin_grid=request.spatial_thin_grid,
            spatial_thin_selection=request.spatial_thin_selection,
            resize=request.resize,
            threshold=request.threshold,
            surface_distance=request.surface_distance,
            simulation_min_distance=request.simulation_min_distance,
            optimize_position=request.optimize_position,
            optimize_orientation=request.optimize_orientation,
            optimize_fov=request.optimize_fov,
            optimize_distortion=request.optimize_distortion,
        )

        return EstimateResponse(
            simulation_base64=base64.b64encode(sim_bytes).decode("utf-8"),
            optimized_params=optimized_params,
            log=log,
        )

    except FileNotFoundError as e:
        raise ValidationError(f"File not found: {e}") from e
    except ValueError as e:
        raise ValidationError(str(e)) from e
    except Exception as e:
        logger.exception("Estimation failed")
        raise ProcessingError(f"Estimation failed: {e}", step="estimation") from e


# =============================================================================
# Process Endpoint
# =============================================================================


@router.post(
    "/process",
    response_model=ProcessJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start georectification processing",
    description="Submit a georectification job for background processing.",
)
async def process(
    request: ProcessRequest,
    job_queue: JobQueue = Depends(get_job_queue_dep),
) -> ProcessJobResponse:
    """Start a georectification processing job.

    This endpoint submits the processing task to the job queue and returns
    immediately with the job ID. Use the WebSocket endpoint or GET /api/jobs/{id}
    to monitor progress.

    Args:
        request: Processing request with project ID and options.
        job_queue: Job queue dependency.

    Returns:
        Job information including ID for status tracking.

    Raises:
        ValidationError: If project or parameters are invalid.
    """
    try:
        # Import services lazily
        from app.services.georectify import run_georectification

        # Define the job function
        async def georectify_job(job: Job) -> dict[str, Any]:
            """Execute georectification as a background job."""
            return await run_georectification(
                project_id=str(request.project_id),
                options=request.options,
                job=job,
            )

        # Submit job to queue
        job = await job_queue.submit(georectify_job)

        logger.info(f"Submitted georectification job {job.id} for project {request.project_id}")

        return ProcessJobResponse(
            id=job.id,
            status=JobStatus(job.status.value),
            created_at=job.created_at.isoformat(),
        )

    except Exception as e:
        logger.exception("Failed to submit georectification job")
        raise ValidationError(f"Failed to start processing: {e}") from e


# =============================================================================
# Export Endpoint (Background Job)
# =============================================================================


class ExportJobResponse(BaseModel):
    """Response for starting an export job (202 Accepted)."""

    id: UUID = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Initial job status")
    created_at: str = Field(..., description="Job creation timestamp (ISO 8601)")


@router.post(
    "/export",
    response_model=ExportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Export GeoTIFF (background job)",
    description="Start a GeoTIFF export job. Monitor progress via WebSocket at /api/jobs/{id}/ws.",
)
async def export_geotiff(
    request: ExportRequest,
    job_queue: JobQueue = Depends(get_job_queue_dep),
) -> ExportJobResponse:
    """Start a GeoTIFF export job.

    This endpoint submits the export task to the job queue and returns
    immediately with the job ID. Use the WebSocket endpoint or GET /api/jobs/{id}
    to monitor progress.

    Args:
        request: Export parameters including output path and settings.
        job_queue: Job queue dependency.

    Returns:
        Job information including ID for status tracking.

    Raises:
        ValidationError: If project hasn't been processed.
    """
    try:
        # Import georectify service lazily
        from app.services.georectify import run_export_job

        # Define the job function
        async def export_job(job: Job) -> dict[str, Any]:
            """Execute GeoTIFF export as a background job."""
            return await run_export_job(
                project_id=str(request.project_id),
                output_path=request.output_path,
                target_image_path=request.target_image_path,
                target_image_paths=request.target_image_paths,
                output_dir=request.output_dir,
                output_name_template=request.output_name_template,
                resolution=request.resolution,
                crs=request.crs,
                interpolate=request.interpolate,
                max_dist=request.max_dist,
                surface_distance=request.surface_distance,
                template_path=request.template_path,
                job=job,
            )

        # Submit job to queue
        job = await job_queue.submit(export_job)

        logger.info(f"Submitted export job {job.id} for project {request.project_id}")

        return ExportJobResponse(
            id=job.id,
            status=JobStatus(job.status.value),
            created_at=job.created_at.isoformat(),
        )

    except Exception as e:
        logger.exception("Failed to submit export job")
        raise ValidationError(f"Failed to start export: {e}") from e


# =============================================================================
# WebSocket Progress Endpoint
# =============================================================================


# Note: WebSocket endpoint is placed in a separate router to avoid prefix conflicts
# The actual path will be /api/jobs/{job_id}/ws
ws_router = APIRouter(tags=["jobs"])


@ws_router.websocket("/api/jobs/{job_id}/ws")
async def job_progress_websocket(
    websocket: WebSocket,
    job_id: UUID,
    job_queue: JobQueue = Depends(get_job_queue_dep),
) -> None:
    """WebSocket endpoint for real-time job progress updates.

    Connect to receive progress updates for a specific job. Messages are sent
    in JSON format: {"progress": 0.5, "step": "matching", "message": "..."}

    The connection is closed when:
    - The job completes (with final status message)
    - The job fails (with error message)
    - The client disconnects
    - The job is not found

    Args:
        websocket: WebSocket connection.
        job_id: Job UUID to monitor.
        job_queue: Job queue dependency.
    """
    await websocket.accept()

    # Get the job
    job = await job_queue.get(job_id)
    if job is None:
        await websocket.send_json({"error": "Job not found", "job_id": str(job_id)})
        await websocket.close(code=4004, reason="Job not found")
        return

    # Send initial status
    await websocket.send_json({
        "progress": job.progress,
        "step": job.step or "pending",
        "message": job.message or "Waiting to start...",
        "status": job.status.value,
    })

    # Create a queue for progress updates
    progress_queue: asyncio.Queue[JobProgress | None] = asyncio.Queue()

    async def progress_callback(update: JobProgress) -> None:
        """Callback to receive progress updates from job."""
        await progress_queue.put(update)

    # Register callback
    job.add_progress_callback(progress_callback)

    try:
        while True:
            # Check job status
            job = await job_queue.get(job_id)
            if job is None:
                break

            # Check if job is finished
            if job.status.value in ("completed", "failed", "cancelled"):
                await websocket.send_json({
                    "progress": job.progress,
                    "step": "finished" if job.status.value == "completed" else job.step,
                    "message": job.error if job.status.value == "failed" else "Processing complete",
                    "status": job.status.value,
                    "result": job.result if job.status.value == "completed" else None,
                })
                break

            # Wait for progress update with timeout
            try:
                update = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                if update is not None:
                    await websocket.send_json({
                        "progress": update.progress,
                        "step": update.step,
                        "message": update.message,
                        "status": "running",
                    })
            except TimeoutError:
                # Send heartbeat/current status periodically
                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.exception(f"WebSocket error for job {job_id}")
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
    finally:
        # Remove callback
        if job is not None:
            job.remove_progress_callback(progress_callback)
        try:
            await websocket.close()
        except Exception:
            pass
