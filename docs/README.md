# ALPROJ GUI Documentation

ALPROJ GUI is a desktop application for georectifying mountain photographs using Digital Surface Models (DSM) and aerial imagery. It produces georeferenced GeoTIFF outputs suitable for GIS analysis.

## Quick Start

### System Requirements

- **Operating System**:
  - macOS 10.15+ (Apple Silicon only; Intel Mac is not currently supported)
  - Windows 10+
  - Linux x86_64 (glibc-based distributions)
- **Memory**: 8GB RAM minimum, 16GB recommended for large datasets
- **Storage**: 1GB for application, plus space for data files

### Installation

Download assets from the release page and install per platform:

1. **macOS (Apple Silicon)**  
   Download `ALPROJ.GUI_x.x.x_aarch64.dmg`, drag `ALPROJ GUI.app` into Applications, then launch with:
   - Right-click app icon -> **Open** (first run)
   - If needed, run `xattr -cr /Applications/ALPROJ\ GUI.app`

2. **Windows**  
   Download `ALPROJ.GUI_x.x.x_x64-setup.exe` or `ALPROJ.GUI_x.x.x_x64_en-US.msi`, run installer, and allow launch via SmartScreen if prompted.

3. **Linux**  
   Download `ALPROJ.GUI_x.x.x_linux_x86_64.tar.gz`, then:
   ```bash
   tar -xzf ALPROJ.GUI_x.x.x_linux_x86_64.tar.gz
   cd alproj-gui-linux-x86_64
   ./install.sh
   ```

### First Run

1. **Start the Application**: Launch ALPROJ GUI
2. **Create a New Project**: Click "New Project" on the home screen
3. **Follow the Wizard**: The application will guide you through:
   - Data Input (DSM, orthophoto, target image)
   - Camera Setup (position, orientation, FOV)
   - Processing (automatic georectification)
   - Result Review (accuracy metrics)
   - Export (GeoTIFF output)

## Required Data

### Digital Surface Model (DSM)
- Format: GeoTIFF
- Content: Elevation data covering the photographed area
- Resolution: Higher resolution yields better results (1-5m recommended)

### Orthophoto / Aerial Image
- Format: GeoTIFF with georeference
- Content: Aerial or satellite imagery of the same area
- Must overlap with DSM coverage

### Target Mountain Photograph
- Format: JPEG, PNG, or TIFF
- Content: The photograph you want to georectify
- Best results with EXIF data (GPS coordinates, focal length)

## Basic Workflow

```
1. Input Data     -> Select DSM, orthophoto, and target image
2. Camera Setup   -> Set initial camera position and orientation
3. Processing     -> Run automatic optimization
4. Review         -> Check accuracy metrics and GCPs
5. Export         -> Save as GeoTIFF
```

## Features

- **Wizard-based Interface**: Step-by-step guidance through the georectification process
- **Interactive Map**: Set camera position and view area on OpenStreetMap
- **Real-time Preview**: See simulation images as you adjust parameters
- **Automatic Optimization**: Uses image matching to refine camera parameters
- **GCP Management**: View, edit, and exclude ground control points
- **Multiple Export Options**: Configure resolution and coordinate system

## File Formats

### Input
| Type | Formats | Notes |
|------|---------|-------|
| DSM | GeoTIFF (.tif, .tiff) | Must have CRS defined |
| Orthophoto | GeoTIFF (.tif, .tiff) | Must have CRS defined |
| Target Image | JPEG, PNG, TIFF | EXIF data helpful |

### Output
| Type | Format | Notes |
|------|--------|-------|
| Georectified Image | GeoTIFF | Configurable resolution and CRS |
| Project File | .alproj | JSON-based, reopenable |
| Report | JSON or Text | Processing parameters and metrics |

## Getting Help

- See [tutorial.md](./tutorial.md) for a detailed walkthrough
- Check the tooltips in the application for parameter explanations
- Report issues on the project's issue tracker

## Development

### Running from Source

```bash
# Clone the repository
git clone https://github.com/your-org/alproj-gui.git
cd alproj-gui

# Start development servers
./scripts/dev.sh
```

### Building

```bash
# Build the backend sidecar
./scripts/build-sidecar.sh

# Build the Tauri application
cd src-tauri && cargo tauri build
```

## License

See LICENSE file in the repository root.
