#!/usr/bin/env bash
# Install and copy the same CLI tools as the Windows tools/ folder (arm64 macOS).
# Used by GitHub Actions and build_mac_arm64.sh.
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Installing ffmpeg, gifski (Homebrew)..."
brew install ffmpeg gifski

mkdir -p tools
FF="$(brew --prefix ffmpeg)"
cp "$FF/bin/ffmpeg" "$FF/bin/ffprobe" tools/

cp "$(command -v gifski)" tools/gifski

# WebP encoder: use Google's official, STATICALLY-LINKED libwebp tool (img2webp)
# instead of Homebrew's ImageMagick. The copied `magick` binary is NOT portable
# — on a Mac without Homebrew it can't find delegates.xml / its coder modules
# and fails with "NoDecodeDelegateForThisImageFormat" even for PNG. img2webp is
# self-contained, handles alpha, and gives exact millisecond frame timing.
WEBP_VER="1.6.0"
WEBP_PKG="libwebp-${WEBP_VER}-mac-arm64"
echo "==> Fetching official static img2webp (${WEBP_PKG})..."
curl -fsSL "https://storage.googleapis.com/downloads.webmproject.org/releases/webp/${WEBP_PKG}.tar.gz" -o "${WEBP_PKG}.tar.gz"
tar -xzf "${WEBP_PKG}.tar.gz"
cp "${WEBP_PKG}/bin/img2webp" tools/img2webp
rm -rf "${WEBP_PKG}" "${WEBP_PKG}.tar.gz"

chmod +x tools/ffmpeg tools/ffprobe tools/gifski tools/img2webp
echo "==> Bundled tools (must be arm64 Mach-O):"
file tools/ffmpeg tools/ffprobe tools/gifski tools/img2webp
echo "==> img2webp self-check:"
tools/img2webp -version
