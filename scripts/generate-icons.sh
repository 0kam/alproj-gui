#!/bin/bash
# Generate app icons from SVG source
# Requires: ImageMagick (convert) or Inkscape

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ICONS_DIR="$PROJECT_ROOT/src-tauri/icons"
SVG_SOURCE="$ICONS_DIR/icon.svg"

echo "Generating icons from $SVG_SOURCE..."

# Check for conversion tool
if command -v convert &> /dev/null; then
    CONVERTER="imagemagick"
elif command -v inkscape &> /dev/null; then
    CONVERTER="inkscape"
elif command -v rsvg-convert &> /dev/null; then
    CONVERTER="rsvg"
else
    echo "Error: No SVG to PNG converter found."
    echo "Please install one of: ImageMagick, Inkscape, or librsvg"
    exit 1
fi

echo "Using converter: $CONVERTER"

# Function to convert SVG to PNG
convert_svg() {
    local size=$1
    local output=$2

    case $CONVERTER in
        imagemagick)
            convert -background none -density 300 -resize ${size}x${size} "$SVG_SOURCE" "$output"
            ;;
        inkscape)
            inkscape --export-type=png --export-filename="$output" -w "$size" -h "$size" "$SVG_SOURCE"
            ;;
        rsvg)
            rsvg-convert -w "$size" -h "$size" "$SVG_SOURCE" -o "$output"
            ;;
    esac
}

# Generate PNG icons at required sizes
echo "Generating 32x32.png..."
convert_svg 32 "$ICONS_DIR/32x32.png"

echo "Generating 128x128.png..."
convert_svg 128 "$ICONS_DIR/128x128.png"

echo "Generating 128x128@2x.png..."
convert_svg 256 "$ICONS_DIR/128x128@2x.png"

echo "Generating 512x512.png (for icns)..."
convert_svg 512 "$ICONS_DIR/512x512.png"

# Generate ICO for Windows
if command -v convert &> /dev/null; then
    echo "Generating icon.ico..."
    convert_svg 16 "$ICONS_DIR/icon-16.png"
    convert_svg 32 "$ICONS_DIR/icon-32.png"
    convert_svg 48 "$ICONS_DIR/icon-48.png"
    convert_svg 64 "$ICONS_DIR/icon-64.png"
    convert_svg 256 "$ICONS_DIR/icon-256.png"

    convert "$ICONS_DIR/icon-16.png" "$ICONS_DIR/icon-32.png" "$ICONS_DIR/icon-48.png" \
            "$ICONS_DIR/icon-64.png" "$ICONS_DIR/icon-256.png" "$ICONS_DIR/icon.ico"

    rm -f "$ICONS_DIR/icon-16.png" "$ICONS_DIR/icon-32.png" "$ICONS_DIR/icon-48.png" \
          "$ICONS_DIR/icon-64.png" "$ICONS_DIR/icon-256.png"
fi

# Generate ICNS for macOS
if command -v iconutil &> /dev/null; then
    echo "Generating icon.icns..."
    ICONSET="$ICONS_DIR/icon.iconset"
    mkdir -p "$ICONSET"

    convert_svg 16 "$ICONSET/icon_16x16.png"
    convert_svg 32 "$ICONSET/icon_16x16@2x.png"
    convert_svg 32 "$ICONSET/icon_32x32.png"
    convert_svg 64 "$ICONSET/icon_32x32@2x.png"
    convert_svg 128 "$ICONSET/icon_128x128.png"
    convert_svg 256 "$ICONSET/icon_128x128@2x.png"
    convert_svg 256 "$ICONSET/icon_256x256.png"
    convert_svg 512 "$ICONSET/icon_256x256@2x.png"
    convert_svg 512 "$ICONSET/icon_512x512.png"
    convert_svg 1024 "$ICONSET/icon_512x512@2x.png"

    iconutil -c icns "$ICONSET" -o "$ICONS_DIR/icon.icns"
    rm -rf "$ICONSET"
fi

echo "Icon generation complete!"
ls -la "$ICONS_DIR/"
