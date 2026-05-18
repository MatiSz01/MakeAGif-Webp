#!/usr/bin/env bash
# Build MakeAGIF v3.1.1 for macOS Apple Silicon (.app bundle).
# Run from the V3 folder on an arm64 Mac:
#   chmod +x build_mac_arm64.sh && ./build_mac_arm64.sh

set -euo pipefail
cd "$(dirname "$0")"

echo "==> Python arch: $(python3 -c 'import platform; print(platform.machine())')"
if [[ "$(uname -m)" != "arm64" ]]; then
  echo "WARNING: This host is not arm64. For native Apple Silicon, build on an M-series Mac."
fi

missing=()
for bin in ffmpeg ffprobe gifski; do
  if [[ ! -x "tools/${bin}" ]]; then
    missing+=("tools/${bin}")
  fi
done
if [[ ${#missing[@]} -gt 0 ]]; then
  echo "ERROR: Missing or non-executable bundled tools:"
  printf '  %s\n' "${missing[@]}"
  echo "See tools/README_MAC_TOOLS.md"
  exit 1
fi

if [[ ! -f MakeAGIF.ico ]]; then
  echo "NOTE: MakeAGIF.ico not found — window icon may be generic until you run: python3 _make_icon.py"
fi

python3 -m pip install -q -r requirements.txt
python3 -m PyInstaller --noconfirm MakeAGIF_v3.1.1_mac.spec

echo ""
echo "Done: dist/MakeAGIF v3.1.1.app"
echo "Test: open \"dist/MakeAGIF v3.1.1.app\""
