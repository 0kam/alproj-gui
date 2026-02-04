# ALPROJ GUI Tutorial

This tutorial walks you through a complete georectification workflow using sample data.

## Overview

Georectification is the process of assigning geographic coordinates to a photograph. This allows the photograph to be used in GIS applications, overlaid on maps, or combined with other geospatial data.

ALPROJ GUI automates this process for mountain photographs using:
- A Digital Surface Model (DSM) for terrain elevation
- An orthophoto for visual reference
- Image matching algorithms to find corresponding points

## Prerequisites

Before starting, ensure you have:

1. **DSM file**: A GeoTIFF containing elevation data
2. **Orthophoto**: A georeferenced aerial or satellite image
3. **Target photograph**: The mountain photo you want to georectify

For this tutorial, we'll use the sample data in `devel_data/`.

## Step 1: Creating a New Project

1. Launch ALPROJ GUI
2. On the home screen, click **"New Project"**
3. Enter a project name (e.g., "Mountain Test")
4. Click **"Create"**

The wizard will open at the Data Input step.

## Step 2: Data Input

### Loading the DSM

1. In the **DSM** section, click **"Select File"**
2. Navigate to your DSM file (e.g., `devel_data/dsm.tif`)
3. The application will display:
   - File path
   - Coordinate Reference System (CRS)
   - Bounding box
   - Resolution

### Loading the Orthophoto

1. In the **Orthophoto** section, click **"Select File"**
2. Navigate to your orthophoto file (e.g., `devel_data/ortho.tif`)
3. Verify the CRS matches the DSM (or is compatible)

### Loading the Target Image

1. In the **Target Image** section, click **"Select File"**
2. Navigate to your mountain photograph
3. If EXIF data is available, the application will show:
   - GPS coordinates (if present)
   - Camera model
   - Focal length

### CRS Verification

If the DSM and orthophoto have different CRS, you'll see a warning. The files should ideally use the same projected coordinate system.

Click **"Next"** to proceed to Camera Setup.

## Step 3: Camera Setup

This step establishes the initial camera position and orientation.

### Setting Camera Position

**Using the Map:**
1. The map shows the DSM coverage area
2. Click on the map to set the camera position
3. A marker will appear at the clicked location

**Using EXIF Data:**
If your image has GPS coordinates:
1. Click **"Auto-detect from EXIF"**
2. The camera position will be set automatically

**Manual Entry:**
1. Enter X, Y coordinates in the input fields
2. Enter the camera elevation (Z)

### Setting Camera Orientation

**Pan (Horizontal Direction):**
- 0° = North
- 90° = East
- 180° = South
- 270° = West

Drag the direction indicator on the map or enter a value directly.

**Tilt (Vertical Angle):**
- 0° = Horizontal
- Negative = Looking down
- Positive = Looking up

**Roll (Rotation):**
- Usually 0° for a level camera
- Adjust if the horizon is tilted

### Field of View (FOV)

The FOV determines how wide the camera's view is.

**Auto-calculate from EXIF:**
If focal length and sensor size are available, click "Auto-detect" to estimate FOV.

**Manual Entry:**
Enter the FOV in degrees (typically 40-80° for standard lenses).

### Preview

The **Simulation Preview** panel shows what the camera should see with the current parameters. Adjust until the preview roughly matches your target photograph.

Click **"Next"** to proceed to Processing.

## Step 4: Processing

This step runs the automatic georectification algorithm.

### Starting Processing

1. Review the processing options (or use defaults)
2. Click **"Start Processing"**

### Processing Steps

The algorithm performs these steps:

1. **Surface Generation**: Creates a 3D mesh from DSM and orthophoto
2. **Feature Matching**: Finds corresponding points between the target image and simulation
3. **Optimization**: Refines camera parameters to minimize error
4. **GCP Generation**: Creates Ground Control Points with coordinates

### Progress Monitoring

- The progress bar shows overall completion
- The current step is displayed below
- A log shows detailed messages

### Cancellation

Click **"Cancel"** to stop processing. Partial results will be available.

When processing completes, click **"Next"** to view results.

## Step 5: Result Review

Review the georectification quality before exporting.

### Accuracy Metrics

| Metric | Meaning | Good Value |
|--------|---------|------------|
| RMSE | Root Mean Square Error in pixels | < 5 pixels |
| GCP Count | Number of valid ground control points | > 10 |
| Residual Max | Worst individual error | < 15 pixels |

### Image Comparison

Use the comparison slider to compare:
- Original target photograph
- Georectified result

### GCP Review (Advanced)

Click **"Show GCPs"** to view ground control points:

1. **GCP Table**: Lists all points with coordinates and residuals
2. **GCP Map**: Shows point locations on the map
3. **Enable/Disable**: Toggle individual GCPs

If a GCP has high residual, you can disable it and re-run optimization.

Click **"Next"** to proceed to Export.

## Step 6: Export

Save the georectified result.

### Export Settings

**Resolution:**
- Enter meters per pixel (e.g., 1.0 for 1m/pixel)
- Lower values = higher quality but larger files

**Output CRS:**
- Select the coordinate reference system for the output
- Default matches the input DSM CRS

**Output Path:**
- Click "Browse" to select destination
- File will be saved as GeoTIFF (.tif)

### Exporting

1. Configure settings
2. Click **"Export"**
3. Wait for export to complete

### Export Report

Optionally, export a processing report containing:
- All parameters used
- Accuracy metrics
- GCP details

Choose JSON or Text format.

## Step 7: Saving the Project

Save your project for future reference:

1. Go to **File > Save** (or press Ctrl+S / Cmd+S)
2. Choose a location and filename
3. The project is saved as `.alproj` format

You can later reopen the project to:
- Review results
- Adjust parameters and reprocess
- Export with different settings

## Tips for Better Results

### Image Selection
- Choose images with clear features (ridgelines, peaks)
- Avoid heavily overexposed or blurry images
- Images taken on clear days work best

### Camera Position
- Get as accurate an initial position as possible
- If no GPS, use known landmarks to estimate location
- Ensure the camera position is within the DSM coverage

### Processing
- If matching fails, try adjusting initial parameters
- Consider using a different matching algorithm
- Ensure sufficient overlap between target area and data

### Memory Issues
- For large DSM files, increase the resolution value
- Process smaller areas if needed
- Close other applications to free memory

## Troubleshooting

### "Matching failed: insufficient points"
- Initial camera parameters are too far from actual
- Try adjusting position or orientation
- Try a different matching algorithm

### "Memory error"
- DSM or orthophoto is too large
- Increase resolution value (e.g., from 1.0 to 5.0)
- Reduce processing distance

### "CRS mismatch warning"
- DSM and orthophoto use different coordinate systems
- Ideally reproject files to match
- The application can handle some differences

### Poor RMSE
- Initial parameters may be inaccurate
- Try disabling outlier GCPs
- Consider re-shooting with GPS enabled

## Next Steps

- Try processing your own photographs
- Experiment with different matching algorithms
- Learn about GCP editing for fine-tuning results
- Export reports for documentation

For more information, see the [README](./README.md) or contact support.
