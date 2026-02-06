"""Application configuration using pydantic-settings.

Environment variables can be set directly or via a .env file.
All settings have sensible defaults for development.
"""

from functools import lru_cache
from pathlib import Path
from tempfile import gettempdir
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ALPROJ_",
        case_sensitive=False,
        extra="ignore",
    )

    # Server settings
    host: str = Field(default="127.0.0.1", description="Server bind host")
    port: int = Field(default=8765, description="Server bind port")
    debug: bool = Field(default=False, description="Enable debug mode")

    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:1420", "http://localhost:5173", "tauri://localhost"],
        description="Allowed CORS origins",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )

    # Job queue settings
    max_concurrent_jobs: int = Field(
        default=1, description="Maximum number of concurrent jobs"
    )
    job_timeout_seconds: int = Field(
        default=3600, description="Job timeout in seconds (1 hour)"
    )

    # Temporary files
    temp_dir: Path = Field(
        default=Path(gettempdir()) / "alproj-gui",
        description="Directory for temporary files",
    )

    # API settings
    api_prefix: str = Field(default="/api", description="API route prefix")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: Application settings singleton.
    """
    return Settings()


# Global settings instance
settings = get_settings()
