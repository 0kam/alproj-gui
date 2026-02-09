# ALPROJ GUI

A desktop application for georectifying mountain photographs using Digital Surface Models (DSM) and aerial imagery. It produces georeferenced GeoTIFF outputs suitable for GIS analysis.

## Overview

ALPROJ GUI provides a wizard-style interface for transforming mountain photographs into geographically referenced images. The application guides users through:

1. **Data Input** - Loading DSM, aerial orthophotos, and target mountain photos
2. **Camera Parameter Setup** - Interactive map-based configuration of camera position, direction, and field of view
3. **Processing** - Automated image matching and camera parameter optimization
4. **Export** - Generating GeoTIFF files with embedded coordinate information

## Tech Stack

### Frontend
- **SvelteKit** - Web application framework
- **Svelte 4** - UI component framework
- **TypeScript 5** - Type-safe JavaScript
- **Tailwind CSS 3** - Utility-first CSS framework
- **MapLibre GL** - Interactive map rendering
- **Vite 5** - Build tool and dev server

### Backend
- **Python 3.11** - Runtime environment
- **FastAPI** - Async web framework
- **Pydantic 2** - Data validation
- **uvicorn** - ASGI server
- **[alproj](https://github.com/0kam/alproj)** - Core georectification library
- **rasterio** - Geospatial raster I/O
- **OpenCV** - Image processing
- **NumPy** - Numerical computing

### Desktop
- **Tauri 2** - Desktop application framework
- **Rust** - Backend runtime for Tauri

### Package Managers
- **uv** - Python package manager
- **npm** - Node.js package manager
- **Cargo** - Rust package manager

## Project Structure

```
alproj_gui/
├── backend/           # FastAPI backend (Python)
│   ├── app/           # Application code
│   └── .venv/         # Virtual environment
├── frontend/          # SvelteKit frontend (TypeScript)
│   └── src/           # Source code
├── src-tauri/         # Tauri desktop app (Rust)
│   └── binaries/      # Sidecar binaries
├── scripts/           # Development scripts
├── devel_data/        # Sample data for development
└── specs/             # Feature specifications
```

## Installation

Download the latest release from the [Releases](../../releases) page.

### macOS

1. Download the `.dmg` file:
   - **Apple Silicon (M1/M2/M3)**: `ALPROJ.GUI_x.x.x_aarch64.dmg`
   - Intel macOS build is not provided in the current release workflow.

2. Open the `.dmg` and drag the app to Applications folder

3. **First launch** (app is not code-signed):
   - Right-click the app → Select **Open**
   - Click **Open** in the dialog

   Or via Terminal:
   ```bash
   xattr -cr /Applications/ALPROJ\ GUI.app
   ```

### Windows

1. Download `ALPROJ.GUI_x.x.x_x64-setup.exe` or `ALPROJ.GUI_x.x.x_x64_en-US.msi`

2. Run the installer

3. **First launch** (app is not code-signed):
   - If SmartScreen appears, click **More info**
   - Click **Run anyway**

### Linux

1. Download `ALPROJ.GUI_x.x.x_linux_x86_64.tar.gz`

2. Extract and install:
   ```bash
   tar -xzf ALPROJ.GUI_x.x.x_linux_x86_64.tar.gz
   cd alproj-gui-linux-x86_64
   ./install.sh
   ```

---

## Development Setup

### Prerequisites

- [Node.js](https://nodejs.org/) (v20+)
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [Rust](https://rustup.rs/) (for Tauri builds)

### Running in Development Mode (Browser)

The easiest way to start both servers:

```bash
./scripts/dev.sh
```

Or start them separately:

```bash
# Backend (port 8765)
cd backend && uv run uvicorn app.main:app --reload --port 8765

# Frontend (port 5173)
cd frontend && npm run dev
```

**URLs:**
- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8765/docs

### Running as Tauri Desktop App

For development with hot reload (run from project root):

```bash
cargo tauri dev
```

This automatically starts both the frontend and backend servers.

## Building for Production

### Build the Tauri Desktop App

1. **Build the Python backend sidecar** (required before release build):

   ```bash
   ./scripts/build-sidecar.sh
   ```

   This creates a standalone executable from the Python backend using PyInstaller.

2. **Build the Tauri application** (run from project root):

   ```bash
   cargo tauri build
   ```

   The built application will be in `src-tauri/target/release/bundle/`.

### Platform-specific Notes

- **macOS**: Minimum version 10.15 (Catalina)
- **Linux**: Requires `libwebkit2gtk-4.1-0` and `libgtk-3-0`
- **Windows**: Built as MSVC target

## Code Quality

### Type Checking & Linting

```bash
# Frontend
cd frontend && npm run check && npm run lint

# Backend
cd backend && uv run mypy . && uv run ruff check .
```

### Testing

```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && npm run test
```

## License

MIT
