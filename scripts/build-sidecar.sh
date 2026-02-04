#!/bin/bash
# Build the Python backend as a standalone sidecar binary
# Uses PyInstaller --onedir mode for macOS compatibility (avoids dyld issues on macOS 15+)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
TAURI_DIR="$PROJECT_ROOT/src-tauri"
BINARIES_DIR="$TAURI_DIR/binaries"
RESOURCES_DIR="$TAURI_DIR/resources"

echo "==================================="
echo "Building backend sidecar"
echo "==================================="
echo "Project root: $PROJECT_ROOT"
echo "Backend dir: $BACKEND_DIR"
echo ""

# Ensure output directories exist
mkdir -p "$BINARIES_DIR"
mkdir -p "$RESOURCES_DIR"

# Navigate to backend directory
cd "$BACKEND_DIR"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv first."
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if PyInstaller is available in the virtual environment
if ! uv run python -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    uv add pyinstaller --dev
fi

# Detect platform for sidecar naming
case "$(uname -s)" in
    Darwin)
        case "$(uname -m)" in
            arm64)
                PLATFORM="aarch64-apple-darwin"
                ;;
            x86_64)
                PLATFORM="x86_64-apple-darwin"
                ;;
        esac
        ;;
    Linux)
        case "$(uname -m)" in
            aarch64)
                PLATFORM="aarch64-unknown-linux-gnu"
                ;;
            x86_64)
                PLATFORM="x86_64-unknown-linux-gnu"
                ;;
        esac
        ;;
    MINGW*|MSYS*|CYGWIN*)
        PLATFORM="x86_64-pc-windows-msvc"
        ;;
    *)
        echo "Error: Unknown platform"
        exit 1
        ;;
esac

echo "Building for platform: $PLATFORM"
echo ""

# Clean previous builds
rm -rf "$BACKEND_DIR/build" "$BACKEND_DIR/dist" "$BACKEND_DIR/*.spec"

# Download and prepare bundled models
echo "Preparing bundled models..."
if [ ! -d "$BACKEND_DIR/models/huggingface" ] || [ ! -d "$BACKEND_DIR/models/torch" ]; then
    echo "Downloading models (this may take a while)..."
    uv run python "$BACKEND_DIR/scripts/download_models.py"
else
    echo "Models already downloaded, skipping..."
fi

# Copy models to imm package's model_weights directory
# imm expects models in imm/model_weights, not a separate models directory
echo "Copying models to imm package model_weights..."
IMM_MODEL_WEIGHTS=$(uv run python -c "import imm; import os; print(os.path.join(os.path.dirname(imm.__file__), 'model_weights'))")
echo "IMM model_weights dir: $IMM_MODEL_WEIGHTS"

# Copy HuggingFace models
if [ -d "$BACKEND_DIR/models/huggingface" ]; then
    cp -r "$BACKEND_DIR/models/huggingface" "$IMM_MODEL_WEIGHTS/"
    echo "  Copied huggingface models"
fi

# Copy Torch models
if [ -d "$BACKEND_DIR/models/torch" ]; then
    cp -r "$BACKEND_DIR/models/torch" "$IMM_MODEL_WEIGHTS/"
    echo "  Copied torch models"
fi

echo ""

# Get PROJ and GDAL data directories for bundling
# Use rasterio's bundled data instead of pyproj's - they have compatible versions
echo "Finding PROJ and GDAL data directories..."
RASTERIO_PROJ_DATA=$(uv run python -c "import rasterio; import os; print(os.path.join(os.path.dirname(rasterio.__file__), 'proj_data'))")
RASTERIO_GDAL_DATA=$(uv run python -c "import rasterio; import os; print(os.path.join(os.path.dirname(rasterio.__file__), 'gdal_data'))")
echo "PROJ data dir (from rasterio): $RASTERIO_PROJ_DATA"
echo "GDAL data dir (from rasterio): $RASTERIO_GDAL_DATA"

# Build with PyInstaller (using --onedir for macOS 15+ compatibility)
# Note: --onefile causes dyld cache issues on newer macOS versions
echo "Running PyInstaller (onedir mode)..."
uv run pyinstaller \
    --onedir \
    --name "backend-sidecar" \
    --clean \
    --noconfirm \
    --noupx \
    --log-level WARN \
    --add-data "$RASTERIO_PROJ_DATA:proj_data" \
    --add-data "$RASTERIO_GDAL_DATA:gdal_data" \
    --collect-all "PIL" \
    --collect-all "pillow_heif" \
    --hidden-import "PIL._imaging" \
    --hidden-import "PIL._imagingft" \
    --hidden-import "app" \
    --hidden-import "uvicorn" \
    --hidden-import "uvicorn.logging" \
    --hidden-import "uvicorn.loops" \
    --hidden-import "uvicorn.loops.auto" \
    --hidden-import "uvicorn.protocols" \
    --hidden-import "uvicorn.protocols.http" \
    --hidden-import "uvicorn.protocols.http.auto" \
    --hidden-import "uvicorn.protocols.websockets" \
    --hidden-import "uvicorn.protocols.websockets.auto" \
    --hidden-import "uvicorn.lifespan" \
    --hidden-import "uvicorn.lifespan.on" \
    --hidden-import "fastapi" \
    --hidden-import "pydantic" \
    --hidden-import "rasterio" \
    --hidden-import "rasterio.sample" \
    --hidden-import "rasterio.vrt" \
    --hidden-import "rasterio.crs" \
    --hidden-import "rasterio.transform" \
    --hidden-import "rasterio.warp" \
    --hidden-import "rasterio.features" \
    --hidden-import "rasterio.mask" \
    --hidden-import "rasterio.merge" \
    --hidden-import "rasterio.plot" \
    --hidden-import "rasterio.rio" \
    --hidden-import "rasterio._io" \
    --hidden-import "rasterio._features" \
    --hidden-import "rasterio._warp" \
    --collect-submodules "rasterio" \
    --hidden-import "numpy" \
    --hidden-import "cv2" \
    --hidden-import "imm" \
    --collect-all "imm" \
    --hidden-import "torch" \
    --hidden-import "torchvision" \
    --hidden-import "kornia" \
    --hidden-import "huggingface_hub" \
    --add-data "app:app" \
    app/main.py

# Check if build was successful (onedir creates a directory)
if [ ! -d "$BACKEND_DIR/dist/backend-sidecar" ]; then
    echo "Error: Build failed - output directory not found"
    exit 1
fi

if [ ! -f "$BACKEND_DIR/dist/backend-sidecar/backend-sidecar" ]; then
    echo "Error: Build failed - output binary not found"
    exit 1
fi

# Copy to Tauri binaries directory
# For --onedir mode, we need to keep binary and _internal together
# So we copy the entire dist directory structure to binaries/
OUTPUT_NAME="backend-sidecar-$PLATFORM"
SIDECAR_DIR="$BINARIES_DIR/sidecar-$PLATFORM"
echo ""
echo "Setting up sidecar directory: $SIDECAR_DIR"
rm -rf "$SIDECAR_DIR"
mkdir -p "$SIDECAR_DIR"

# Copy everything from the onedir output
cp -r "$BACKEND_DIR/dist/backend-sidecar/"* "$SIDECAR_DIR/"

# Rename the binary with platform suffix for Tauri
mv "$SIDECAR_DIR/backend-sidecar" "$SIDECAR_DIR/$OUTPUT_NAME"
chmod +x "$SIDECAR_DIR/$OUTPUT_NAME"

# Also create a symlink in binaries/ root for Tauri to find
# (Tauri looks for binaries/backend-sidecar-{platform})
ln -sf "sidecar-$PLATFORM/$OUTPUT_NAME" "$BINARIES_DIR/$OUTPUT_NAME"

# Clean up build artifacts
rm -rf "$BACKEND_DIR/build" "$BACKEND_DIR/*.spec"

echo ""
echo "==================================="
echo "Build complete!"
echo "==================================="
echo "Sidecar dir: $SIDECAR_DIR"
echo "Binary: $SIDECAR_DIR/$OUTPUT_NAME"
echo "Symlink: $BINARIES_DIR/$OUTPUT_NAME -> sidecar-$PLATFORM/$OUTPUT_NAME"
echo ""

# Show file info
ls -lh "$SIDECAR_DIR/$OUTPUT_NAME"
echo ""
echo "Sidecar directory total size:"
du -sh "$SIDECAR_DIR"

# Test the binary
echo ""
echo "Testing binary..."
if [ -x "$SIDECAR_DIR/$OUTPUT_NAME" ]; then
    echo "✓ Binary is executable"
    file "$SIDECAR_DIR/$OUTPUT_NAME"
else
    echo "✗ Binary is not executable"
    exit 1
fi
