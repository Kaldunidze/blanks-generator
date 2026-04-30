#!/usr/bin/env bash
# build-linux.sh — builds a portable single-file Linux executable
set -e

echo "==> Installing dependencies..."
python3 -m pip install --break-system-packages dearpygui typst pillow pyinstaller 2>/dev/null \
    || python3 -m pip install dearpygui typst pillow pyinstaller

# Optional: bundle a Cyrillic UI font
FONT_SRC=""
for CAND in \
    /usr/share/fonts/noto/NotoSans-Regular.ttf \
    /usr/share/fonts/truetype/noto/NotoSans-Regular.ttf \
    /usr/share/fonts/TTF/DejaVuSans.ttf \
    /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
    /usr/share/fonts/liberation/LiberationSans-Regular.ttf \
    /usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf \
    /usr/share/fonts/truetype/freefont/FreeSans.ttf
do
    if [ -f "$CAND" ]; then
        FONT_SRC="$CAND"
        break
    fi
done

if [ -n "$FONT_SRC" ]; then
    mkdir -p assets
    cp "$FONT_SRC" assets/font.ttf
    FONT_FLAG="--add-data assets/font.ttf:assets"
    echo "==> Bundling Cyrillic font from $FONT_SRC"
else
    FONT_FLAG=""
    echo "==> No system Cyrillic font found; build will rely on target machine fonts"
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
