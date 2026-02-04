"""FastAPI application entry point for alproj-gui backend.

This module initializes the FastAPI application with:
- CORS middleware for frontend communication
- Exception handlers for consistent error responses
- Lifespan management for startup/shutdown events
- Health check endpoint
"""

from __future__ import annotations

import logging
import os
import sys

# Configure environment variables for PyInstaller bundled app
# This must be done BEFORE importing pyproj/rasterio/gdal/imm
def _configure_bundled_app() -> None:
    """Set environment variables for bundled PyInstaller app."""
    is_frozen = getattr(sys, 'frozen', False)
    print(f"[BUNDLE_CONFIG] frozen={is_frozen}", flush=True)

    if is_frozen:
        # Running as bundled executable
        bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        print(f"[BUNDLE_CONFIG] bundle_dir={bundle_dir}", flush=True)

        # === Configure PROJ and GDAL data ===
        proj_data_dir = os.path.join(bundle_dir, 'proj_data')
        gdal_data_dir = os.path.join(bundle_dir, 'gdal_data')

        if os.path.exists(proj_data_dir):
            os.environ['PROJ_LIB'] = proj_data_dir
            os.environ['PROJ_DATA'] = proj_data_dir
            os.environ['PROJ_NETWORK'] = 'OFF'
            print(f"[BUNDLE_CONFIG] Set PROJ_LIB={proj_data_dir}", flush=True)

            try:
                import pyproj.datadir
                pyproj.datadir.set_data_dir(proj_data_dir)
            except Exception as e:
                print(f"[BUNDLE_CONFIG] Failed to set pyproj.datadir: {e}", flush=True)

        if os.path.exists(gdal_data_dir):
            os.environ['GDAL_DATA'] = gdal_data_dir
            print(f"[BUNDLE_CONFIG] Set GDAL_DATA={gdal_data_dir}", flush=True)

        # === Configure HuggingFace and Torch cache for bundled models ===
        # imm package uses these environment variables to find model weights
        imm_weights_dir = os.path.join(bundle_dir, 'imm', 'model_weights')
        print(f"[BUNDLE_CONFIG] imm_weights_dir={imm_weights_dir}", flush=True)
        print(f"[BUNDLE_CONFIG] imm_weights_dir exists={os.path.exists(imm_weights_dir)}", flush=True)

        if os.path.exists(imm_weights_dir):
            # Set HuggingFace cache - must set before importing huggingface_hub
            hf_cache = os.path.join(imm_weights_dir, 'huggingface')
            if os.path.exists(hf_cache):
                os.environ['HF_HOME'] = hf_cache
                os.environ['HUGGINGFACE_HUB_CACHE'] = os.path.join(hf_cache, 'hub')
                os.environ['HF_HUB_OFFLINE'] = '1'  # Disable network access
                print(f"[BUNDLE_CONFIG] Set HF_HOME={hf_cache}", flush=True)

            # Set Torch cache - environment variables must be set BEFORE importing torch
            # but torch may already be loaded by PyInstaller, so we also set torch.hub directly
            torch_cache = os.path.join(imm_weights_dir, 'torch')
            torch_hub_dir = os.path.join(torch_cache, 'hub')
            if os.path.exists(torch_hub_dir):
                os.environ['TORCH_HOME'] = torch_cache
                print(f"[BUNDLE_CONFIG] Set TORCH_HOME={torch_cache}", flush=True)

                # Explicitly set torch.hub directory (works even after torch is imported)
                try:
                    import torch.hub
                    torch.hub.set_dir(torch_hub_dir)
                    print(f"[BUNDLE_CONFIG] Set torch.hub.set_dir({torch_hub_dir})", flush=True)
                    print(f"[BUNDLE_CONFIG] Verify torch.hub.get_dir()={torch.hub.get_dir()}", flush=True)
                except Exception as e:
                    print(f"[BUNDLE_CONFIG] Failed to set torch.hub dir: {e}", flush=True)

                # Also check checkpoints directory
                checkpoints_dir = os.path.join(torch_hub_dir, 'checkpoints')
                if os.path.exists(checkpoints_dir):
                    print(f"[BUNDLE_CONFIG] checkpoints_dir exists: {checkpoints_dir}", flush=True)
                    try:
                        files = os.listdir(checkpoints_dir)[:5]
                        print(f"[BUNDLE_CONFIG] checkpoints contents: {files}", flush=True)
                    except Exception as e:
                        print(f"[BUNDLE_CONFIG] Failed to list checkpoints: {e}", flush=True)

            # List imm weights contents for debugging
            try:
                contents = os.listdir(imm_weights_dir)
                print(f"[BUNDLE_CONFIG] imm_weights contents: {contents}", flush=True)
            except Exception as e:
                print(f"[BUNDLE_CONFIG] Failed to list imm_weights: {e}", flush=True)

        # List bundle_dir top-level contents for debugging
        try:
            top_contents = [d for d in os.listdir(bundle_dir) if os.path.isdir(os.path.join(bundle_dir, d))][:15]
            print(f"[BUNDLE_CONFIG] bundle_dir directories: {top_contents}", flush=True)
        except Exception as e:
            print(f"[BUNDLE_CONFIG] Failed to list bundle_dir: {e}", flush=True)

_configure_bundled_app()
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import register_exception_handlers
from app.api.routes.files import router as files_router
from app.api.routes.georectify import router as georectify_router
from app.api.routes.georectify import ws_router as jobs_ws_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.projects import router as projects_router
from app.api.routes.recovery import router as recovery_router
from app.core.config import settings
from app.core.jobs import init_job_queue

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager for startup and shutdown events.

    Args:
        app: The FastAPI application instance.

    Yields:
        None after startup, before shutdown.
    """
    # Startup
    logger.info("Starting alproj-gui backend...")

    # Initialize job queue
    init_job_queue(max_concurrent=settings.max_concurrent_jobs)

    # Ensure temp directory exists
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Temp directory: {settings.temp_dir}")

    logger.info(f"Server ready at http://{settings.host}:{settings.port}")

    yield

    # Shutdown
    logger.info("Shutting down alproj-gui backend...")


# Create FastAPI application
app = FastAPI(
    title="alproj-gui Backend",
    description="Backend API server for alproj georectification GUI",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Register API routers
app.include_router(files_router)
app.include_router(georectify_router)
app.include_router(jobs_router)
app.include_router(jobs_ws_router)
app.include_router(projects_router)
app.include_router(recovery_router)


# =============================================================================
# Root and Health Endpoints
# =============================================================================


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning API information."""
    return {"message": "alproj-gui Backend API", "version": "0.1.0"}


@app.get("/api/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint.

    Returns:
        Status object indicating the server is running.
    """
    return {"status": "ok"}


# =============================================================================
# Server Entry Point
# =============================================================================


def main() -> None:
    """Run the server with CLI argument support.

    Supports --host and --port arguments for Tauri sidecar integration.
    Falls back to settings defaults if not provided.
    """
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="alproj-gui Backend Server")
    parser.add_argument(
        "--host",
        type=str,
        default=settings.host,
        help=f"Server bind host (default: {settings.host})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help=f"Server bind port (default: {settings.port})",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.debug,
        help="Enable auto-reload (for development)",
    )

    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
