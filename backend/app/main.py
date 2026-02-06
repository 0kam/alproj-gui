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
from pathlib import Path

# Configure environment variables for PyInstaller bundled app
# This must be done BEFORE importing pyproj/rasterio/gdal/imm
def _get_runtime_model_weights_dir() -> Path:
    """Return user-writable runtime directory for imm model weights."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "alproj-gui" / "imm" / "model_weights"


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

        # === Configure model cache (bundled if present, otherwise user cache) ===
        bundled_weights_dir = Path(bundle_dir) / 'imm' / 'model_weights'
        use_bundled_weights = bundled_weights_dir.exists()
        runtime_weights_dir = _get_runtime_model_weights_dir()
        active_weights_dir = bundled_weights_dir if use_bundled_weights else runtime_weights_dir

        print(f"[BUNDLE_CONFIG] bundled_weights_dir={bundled_weights_dir}", flush=True)
        print(f"[BUNDLE_CONFIG] use_bundled_weights={use_bundled_weights}", flush=True)
        print(f"[BUNDLE_CONFIG] runtime_weights_dir={runtime_weights_dir}", flush=True)
        print(f"[BUNDLE_CONFIG] active_weights_dir={active_weights_dir}", flush=True)

        try:
            active_weights_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[BUNDLE_CONFIG] Failed to create active weights dir: {e}", flush=True)

        hf_cache = active_weights_dir / 'huggingface'
        hf_hub_cache = hf_cache / 'hub'
        torch_cache = active_weights_dir / 'torch'
        torch_hub_dir = torch_cache / 'hub'

        hf_hub_cache.mkdir(parents=True, exist_ok=True)
        torch_hub_dir.mkdir(parents=True, exist_ok=True)

        os.environ['HF_HOME'] = str(hf_cache)
        os.environ['HUGGINGFACE_HUB_CACHE'] = str(hf_hub_cache)
        os.environ['TORCH_HOME'] = str(torch_cache)
        if use_bundled_weights:
            os.environ['HF_HUB_OFFLINE'] = '1'
        else:
            # Runtime download mode: do not force offline.
            os.environ.pop('HF_HUB_OFFLINE', None)

        print(f"[BUNDLE_CONFIG] Set HF_HOME={hf_cache}", flush=True)
        print(f"[BUNDLE_CONFIG] Set HUGGINGFACE_HUB_CACHE={hf_hub_cache}", flush=True)
        print(f"[BUNDLE_CONFIG] Set TORCH_HOME={torch_cache}", flush=True)

        # Align torch.hub and imm.WEIGHTS_DIR with the selected model cache location.
        try:
            import torch.hub

            torch.hub.set_dir(str(torch_hub_dir))
            print(f"[BUNDLE_CONFIG] Set torch.hub.set_dir({torch_hub_dir})", flush=True)
            print(f"[BUNDLE_CONFIG] Verify torch.hub.get_dir()={torch.hub.get_dir()}", flush=True)
        except Exception as e:
            print(f"[BUNDLE_CONFIG] Failed to set torch.hub dir: {e}", flush=True)

        try:
            import imm

            imm.WEIGHTS_DIR = active_weights_dir
            imm.WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
            print(f"[BUNDLE_CONFIG] Set imm.WEIGHTS_DIR={imm.WEIGHTS_DIR}", flush=True)
        except Exception as e:
            print(f"[BUNDLE_CONFIG] Failed to configure imm.WEIGHTS_DIR: {e}", flush=True)

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
