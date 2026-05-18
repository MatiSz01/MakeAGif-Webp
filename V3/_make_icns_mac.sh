#!/usr/bin/env bash
# Build MakeAGIF.icns for the macOS .app bundle (run on macOS only).
# Requires icon_512.png (from _make_icon.py) in this folder.

set -euo pipefail
cd "$(dirname "$0")"

SRC="icon_512.png"
if [[ ! -f "$SRC" ]]; then
  echo "Missing $SRC — run: python3 _make_icon.py"
  exit 1
fi

ICONSET="MakeAGIF.iconset"
rm -rf "$ICONSET"
mkdir -p "$ICONSET"

sips -z 16 16     "$SRC" --out "$ICONSET/icon_16x16.png"      >/dev/null
sips -z 32 32     "$SRC" --out "$ICONSET/icon_16x16@2x.png"   >/dev/null
sips -z 32 32     "$SRC" --out "$ICONSET/icon_32x32.png"      >/dev/null
sips -z 64 64     "$SRC" --out "$ICONSET/icon_32x32@2x.png"   >/dev/null
sips -z 128 128   "$SRC" --out "$ICONSET/icon_128x128.png"    >/dev/null
sips -z 256 256   "$SRC" --out "$ICONSET/icon_128x128@2x.png" >/dev/null
sips -z 256 256   "$SRC" --out "$ICONSET/icon_256x256.png"    >/dev/null
sips -z 512 512   "$SRC" --out "$ICONSET/icon_256x256@2x.png" >/dev/null
sips -z 512 512   "$SRC" --out "$ICONSET/icon_512x512.png"    >/dev/null
cp "$SRC" "$ICONSET/icon_512x512@2x.png"

iconutil -c icns "$ICONSET" -o MakeAGIF.icns
rm -rf "$ICONSET"
echo "OK: MakeAGIF.icns"
