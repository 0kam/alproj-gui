#!/usr/bin/env python3
"""
Download and prepare models for bundling.

This script downloads the required image matching models and copies them
to the backend/models directory for bundling with the desktop app.

Usage:
    uv run python scripts/download_models.py
"""

import shutil
import sys
from pathlib import Path

# Models to bundle (excluding UFM due to size)
BUNDLED_MODELS = [
    "tiny-roma",
    "superpoint-lightglue",
    "minima-roma",
    "rdd",
]


def get_cache_paths() -> tuple[Path, Path]:
    """Get HuggingFace and Torch cache paths."""
    home = Path.home()
    hf_cache = home / ".cache" / "huggingface" / "hub"
    torch_cache = home / ".cache" / "torch" / "hub"
    return hf_cache, torch_cache


def download_models() -> None:
    """Download models by initializing them."""
    import imm

    device = "cpu"

    for model_name in BUNDLED_MODELS:
        print(f"Downloading {model_name}...")
        try:
            _ = imm.get_matcher(model_name, device=device)
            print(f"  ✓ {model_name} downloaded")
        except Exception as e:
            print(f"  ✗ Failed to download {model_name}: {e}")
            sys.exit(1)


def copy_models_to_bundle_dir(bundle_dir: Path) -> dict[str, list[Path]]:
    """
    Copy downloaded models to the bundle directory.

    Returns a dict mapping model names to their copied paths.
    """
    hf_cache, torch_cache = get_cache_paths()
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # HuggingFace model mappings
    hf_models = {
        "superpoint-lightglue": "models--image-matching-models--superpoint-lightglue",
        "tiny-roma": "models--image-matching-models--tiny-roma",
        "minima-roma": "models--image-matching-models--minima",  # minima-roma uses minima
        "rdd": "models--image-matching-models--rdd",
    }

    # Torch checkpoint files needed for each model
    torch_checkpoints = {
        "superpoint-lightglue": [
            "superpoint_v1.pth",
            "superpoint_lightglue_v0-1_arxiv.pth",
        ],
        "tiny-roma": [
            "tiny_roma_v1_outdoor.pth",
            "xfeat.pt",
        ],
        "minima-roma": [
            "roma_outdoor.pth",
        ],
        "rdd": [
            "resnet50-0676ba61.pth",
        ],
    }

    # Torch hub directories needed
    torch_hub_dirs = [
        "facebookresearch_dinov2_main",
        "verlab_accelerated_features_main",
    ]

    copied_files: dict[str, list[Path]] = {}

    # Copy HuggingFace models
    # Use symlinks=False to resolve symlinks and copy actual files
    # This is important for PyInstaller bundling
    hf_bundle_dir = bundle_dir / "huggingface" / "hub"
    hf_bundle_dir.mkdir(parents=True, exist_ok=True)

    for model_name in BUNDLED_MODELS:
        copied_files[model_name] = []
        hf_model_name = hf_models.get(model_name)

        if hf_model_name:
            src = hf_cache / hf_model_name
            dst = hf_bundle_dir / hf_model_name

            if src.exists():
                if dst.exists():
                    shutil.rmtree(dst)
                # Resolve symlinks (symlinks=False) to copy actual files
                # This ensures files work when bundled with PyInstaller
                shutil.copytree(src, dst, symlinks=False)
                copied_files[model_name].append(dst)
                print(f"  Copied HF model: {hf_model_name}")
            else:
                print(f"  ⚠ HF model not found: {src}")

    # Copy Torch checkpoints
    torch_bundle_dir = bundle_dir / "torch" / "hub" / "checkpoints"
    torch_bundle_dir.mkdir(parents=True, exist_ok=True)

    torch_checkpoints_src = torch_cache / "checkpoints"

    for model_name, checkpoints in torch_checkpoints.items():
        for ckpt in checkpoints:
            src = torch_checkpoints_src / ckpt
            dst = torch_bundle_dir / ckpt

            if src.exists():
                shutil.copy2(src, dst)
                copied_files.setdefault(model_name, []).append(dst)
                print(f"  Copied checkpoint: {ckpt}")
            else:
                print(f"  ⚠ Checkpoint not found: {src}")

    # Copy Torch hub directories (for DINOv2, etc.)
    torch_hub_bundle_dir = bundle_dir / "torch" / "hub"

    for hub_dir in torch_hub_dirs:
        src = torch_cache / hub_dir
        dst = torch_hub_bundle_dir / hub_dir

        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            # Preserve symlinks if any
            shutil.copytree(src, dst, symlinks=True)
            print(f"  Copied hub dir: {hub_dir}")
        else:
            print(f"  ⚠ Hub dir not found: {src}")

    return copied_files


def calculate_bundle_size(bundle_dir: Path) -> int:
    """Calculate total size of bundled models in bytes."""
    total = 0
    for f in bundle_dir.rglob("*"):
        if f.is_file() and not f.is_symlink():
            total += f.stat().st_size
    return total


def main() -> None:
    """Main entry point."""
    # Get paths
    backend_dir = Path(__file__).parent.parent
    bundle_dir = backend_dir / "models"

    print("=" * 60)
    print("ALPROJ Model Bundler")
    print("=" * 60)
    print(f"\nModels to bundle: {', '.join(BUNDLED_MODELS)}")
    print(f"Bundle directory: {bundle_dir}")
    print()

    # Step 1: Download models
    print("Step 1: Downloading models...")
    download_models()
    print()

    # Step 2: Copy to bundle directory
    print("Step 2: Copying models to bundle directory...")
    copied = copy_models_to_bundle_dir(bundle_dir)
    print()

    # Step 3: Calculate size
    total_size = calculate_bundle_size(bundle_dir)
    print(f"Total bundle size: {total_size / 1024 / 1024:.1f} MB")
    print()

    print("✓ Models prepared for bundling")
    print(f"  Location: {bundle_dir}")


if __name__ == "__main__":
    main()
