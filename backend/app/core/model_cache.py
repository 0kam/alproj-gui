"""Model cache configuration for bundled and development runtimes."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def configure_ssl_certificates() -> Path | None:
    """Configure CA bundle environment variables for HTTPS downloads."""
    try:
        import certifi

        ca_bundle = Path(certifi.where())
        if not ca_bundle.exists():
            return None

        os.environ.setdefault("SSL_CERT_FILE", str(ca_bundle))
        os.environ.setdefault("REQUESTS_CA_BUNDLE", str(ca_bundle))
        os.environ.setdefault("CURL_CA_BUNDLE", str(ca_bundle))
        return ca_bundle
    except Exception as exc:
        logger.warning("Failed to configure SSL certificates: %s", exc)
        return None


def get_runtime_model_weights_dir() -> Path:
    """Return user-writable runtime directory for imm model weights."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "alproj-gui" / "imm" / "model_weights"


def resolve_model_weights_dir(bundle_dir: str | Path | None = None) -> tuple[Path, bool]:
    """Resolve active model weights directory and whether bundled weights are used."""
    if bundle_dir is not None:
        bundle_path = Path(bundle_dir)
    elif getattr(sys, "frozen", False):
        bundle_path = Path(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
    else:
        bundle_path = None

    if bundle_path is not None:
        bundled_weights_dir = bundle_path / "imm" / "model_weights"
        if bundled_weights_dir.exists():
            return bundled_weights_dir, True

    return get_runtime_model_weights_dir(), False


def configure_model_cache_environment(bundle_dir: str | Path | None = None) -> Path:
    """Configure cache-related environment variables and return active weights directory."""
    active_weights_dir, use_bundled_weights = resolve_model_weights_dir(bundle_dir)
    active_weights_dir.mkdir(parents=True, exist_ok=True)

    hf_cache = active_weights_dir / "huggingface"
    hf_hub_cache = hf_cache / "hub"
    torch_cache = active_weights_dir / "torch"
    torch_hub_dir = torch_cache / "hub"

    hf_hub_cache.mkdir(parents=True, exist_ok=True)
    torch_hub_dir.mkdir(parents=True, exist_ok=True)

    os.environ["HF_HOME"] = str(hf_cache)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hf_hub_cache)
    os.environ["TORCH_HOME"] = str(torch_cache)
    os.environ["ALPROJ_IMM_WEIGHTS_DIR"] = str(active_weights_dir)

    if use_bundled_weights:
        os.environ["HF_HUB_OFFLINE"] = "1"
    else:
        os.environ.pop("HF_HUB_OFFLINE", None)

    return active_weights_dir


def configure_imm_runtime(bundle_dir: str | Path | None = None) -> Path:
    """Configure imm/torch runtime paths and return active weights directory."""
    configure_ssl_certificates()
    active_weights_dir = configure_model_cache_environment(bundle_dir)

    torch_hub_dir = active_weights_dir / "torch" / "hub"
    try:
        import torch.hub

        torch.hub.set_dir(str(torch_hub_dir))
    except Exception as exc:
        logger.warning("Failed to configure torch.hub dir: %s", exc)

    try:
        import imm

        imm.WEIGHTS_DIR = active_weights_dir
        imm.WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        logger.warning("Failed to configure imm.WEIGHTS_DIR: %s", exc)

    return active_weights_dir
