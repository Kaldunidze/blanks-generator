#!/usr/bin/env bash
# build-linux.sh — builds a portable single-file Linux executable
set -e

echo "==> Installing dependencies..."
python3 -m pip install --break-system-packages dearpygui typst pillow pyinstaller 2>/dev/null \
    || python3 -m pip install dearpygui typst pillow pyinstaller

# Optional: bundle a Cyrillic UI font
FONT_SRC="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
if [ -f "$FONT_SRC" ]; then
    mkdir -p assets
    cp "$FONT_SRC" assets/font.ttf
    FONT_FLAG="--add-data assets/font.ttf:assets"
    echo "==> Bundling Cyrillic font from $FONT_SRC"
else
    FONT_FLAG=""
fi

echo "==> Building with PyInstaller..."
python3 -m PyInstaller \
    --onefile \
    --noconsole \
    --collect-all dearpygui \
    --collect-all typst \
    --collect-all PIL \
    $FONT_FLAG \
    app.py

echo ""
echo "Done!  →  dist/app"
