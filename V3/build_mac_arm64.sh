#!/usr/bin/env bash
# Build MakeAGIF v3.1.2 for macOS Apple Silicon (.app bundle).
# Run from the V3 folder on an arm64 Mac:
#   chmod +x build_mac_arm64.sh ci_bundle_mac_tools.sh && ./build_mac_arm64.sh

set -euo pipefail
cd "$(dirname "$0")"

echo "==> Python arch: $(python3 -c 'import platform; print(platform.machine())')"
if [[ "$(uname -m)" != "arm64" ]]; then
  echo "WARNING: This host is not arm64. For native Apple Silicon, build on an M-series Mac."
fi

if [[ ! -x tools/ffmpeg || ! -x tools/ffprobe || ! -x tools/gifski || ! -x tools/magick ]]; then
  echo "==> tools/ incomplete — installing macOS bundles (ffmpeg, gifski, imagemagick)..."
  chmod +x ci_bundle_mac_tools.sh
  ./ci_bundle_mac_tools.sh
fi

if [[ ! -f MakeAGIF.ico ]]; then
  echo "NOTE: MakeAGIF.ico not found — window icon may be generic until you run: python3 _make_icon.py"
fi

python3 -m pip install -q -r requirements.txt
python3 -m PyInstaller --noconfirm MakeAGIF_v3.1.2_mac.spec

echo ""
echo "Done: dist/MakeAGIF v3.1.2.app"
echo "Bundled tools: ffmpeg, ffprobe, gifski, magick (parity with Windows tools/)"
echo "Test: open \"dist/MakeAGIF v3.1.2.app\""
