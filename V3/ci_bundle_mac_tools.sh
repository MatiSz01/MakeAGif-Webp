#!/usr/bin/env bash
# Install and copy the same CLI tools as the Windows tools/ folder (arm64 macOS).
# Used by GitHub Actions and build_mac_arm64.sh.
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Installing ffmpeg, gifski, imagemagick (Homebrew)..."
brew install ffmpeg gifski imagemagick

mkdir -p tools
FF="$(brew --prefix ffmpeg)"
cp "$FF/bin/ffmpeg" "$FF/bin/ffprobe" tools/

cp "$(command -v gifski)" tools/gifski

MAG_PREFIX="$(brew --prefix imagemagick)"
if [[ -x "$MAG_PREFIX/bin/magick" ]]; then
  cp "$MAG_PREFIX/bin/magick" tools/magick
elif [[ -x "$(command -v magick)" ]]; then
  cp "$(command -v magick)" tools/magick
else
  echo "ERROR: ImageMagick 'magick' not found after brew install imagemagick"
  exit 1
fi

chmod +x tools/ffmpeg tools/ffprobe tools/gifski tools/magick
echo "==> Bundled tools (must be arm64 Mach-O):"
file tools/ffmpeg tools/ffprobe tools/gifski tools/magick
