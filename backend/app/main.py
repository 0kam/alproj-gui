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
from app.core.model_cache import configure_model_cache_environment


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
        active_weights_dir = configure_model_cache_environment(bundle_dir)
        print(f"[BUNDLE_CONFIG] active_weights_dir={active_weights_dir}", flush=True)

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
