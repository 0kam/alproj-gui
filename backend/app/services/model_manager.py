"""
Model manager for bundled image matching models.

This module handles:
- Detecting bundled vs cached models
- Setting up environment variables for model paths
- Providing model availability information
"""

import os
import sys
from pathlib import Path
from typing import NamedTuple


class ModelInfo(NamedTuple):
    """Information about a model."""

    name: str
    available: bool
    bundled: bool
    size_mb: float


# Models bundled with the app
BUNDLED_MODELS = [
    "tiny-roma",
    "superpoint-lightglue",
    "minima-roma",
    "rdd",
]

# Models that require download (not bundled due to size)
DOWNLOADABLE_MODELS = [
    "ufm",
]


def get_bundle_dir() -> Path | None:
    """
    Get the bundled models directory.

    Returns None if running in development mode without bundled models.
    """
    # Check if running as a PyInstaller bundle
    if getattr(sys, "frozen", False):
        # Running as compiled executable
        bundle_dir = Path(sys._MEIPASS) / "models"  # type: ignore[attr-defined]
        if bundle_dir.exists():
            return bundle_dir

    # Check for models directory relative to the backend
    # Development mode or sidecar mode
    backend_dir = Path(__file__).parent.parent.parent
    models_dir = backend_dir / "models"

    if models_dir.exists() and any(models_dir.iterdir()):
        return models_dir

    return None


def setup_model_environment() -> dict[str, str]:
    """
    Set up environment variables to use bundled models.

    This should be called before importing imm or torch.

    Returns the environment variables that were set.
    """
    bundle_dir = get_bundle_dir()
    env_vars: dict[str, str] = {}

    if bundle_dir is None:
        # No bundled models, use default cache locations
        return env_vars

    # Set HuggingFace cache
    hf_cache = bundle_dir / "huggingface"
    if hf_cache.exists():
        os.environ["HF_HOME"] = str(hf_cache)
        os.environ["HUGGINGFACE_HUB_CACHE"] = str(hf_cache / "hub")
        env_vars["HF_HOME"] = str(hf_cache)
        env_vars["HUGGINGFACE_HUB_CACHE"] = str(hf_cache / "hub")

    # Set Torch cache
    torch_cache = bundle_dir / "torch"
    if torch_cache.exists():
        os.environ["TORCH_HOME"] = str(torch_cache)
        env_vars["TORCH_HOME"] = str(torch_cache)

    return env_vars


def get_model_info(model_name: str) -> ModelInfo:
    """Get information about a specific model."""
    bundle_dir = get_bundle_dir()
    bundled = bundle_dir is not None and model_name in BUNDLED_MODELS

    # Approximate sizes in MB
    sizes = {
        "tiny-roma": 11,
        "superpoint-lightglue": 50,
        "minima-roma": 557,
        "rdd": 270,
        "ufm": 3400,
    }

    # Check if model is available (either bundled or in cache)
    available = bundled  # For now, only bundled models are available

    if not bundled and model_name in DOWNLOADABLE_MODELS:
        # Check user cache for downloadable models
        available = _check_model_in_cache(model_name)

    return ModelInfo(
        name=model_name,
        available=available,
        bundled=bundled,
        size_mb=sizes.get(model_name, 0),
    )


def _check_model_in_cache(model_name: str) -> bool:
    """Check if a model exists in the user's cache."""
    home = Path.home()
    hf_cache = home / ".cache" / "huggingface" / "hub"

    # Map model names to HuggingFace repo names
    hf_repos = {
        "ufm": ["models--infinity1096--UFM-Base", "models--infinity1096--UFM-Refine"],
    }

    repos = hf_repos.get(model_name, [])
    return all((hf_cache / repo).exists() for repo in repos)


def list_available_models() -> list[ModelInfo]:
    """List all available models with their status."""
    all_models = BUNDLED_MODELS + DOWNLOADABLE_MODELS
    return [get_model_info(name) for name in all_models]


def get_matcher(model_name: str) -> "BaseMatcher":  # type: ignore[name-defined]
    """
    Get a matcher instance for the specified model.

    This is a wrapper around imm.get_matcher that ensures
    the model environment is set up correctly.
    """
    # Ensure environment is set up
    setup_model_environment()

    # Import imm after setting up environment
    import imm

    model_info = get_model_info(model_name)
    if not model_info.available:
        raise ValueError(
            f"Model '{model_name}' is not available. "
            f"Bundled: {model_info.bundled}, Size: {model_info.size_mb}MB"
        )

    return imm.get_matcher(model_name)
