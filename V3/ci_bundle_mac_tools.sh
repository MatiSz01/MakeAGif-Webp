#!/usr/bin/env bash
# Install and copy the same CLI tools as the Windows tools/ folder (arm64 macOS).
# Used by GitHub Actions and build_mac_arm64.sh.
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Installing gifski (Homebrew)..."
brew install gifski

mkdir -p tools
cp "$(command -v gifski)" tools/gifski

# ffmpeg/ffprobe must be relocatable. Homebrew's binaries dlopen libraries
# from /opt/homebrew, so on a Mac without Homebrew every import dies before
# ffprobe can read the file ("Could not analyze", empty console). These
# release builds are static arm64 binaries.
fetch_static() {
  local name="$1"
  local url="https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/${name}.zip"
  local tmp bin
  tmp="$(mktemp -d)"
  echo "==> Fetching static ${name} (${url})..."
  curl -fL --retry 3 --retry-delay 2 -o "${tmp}/${name}.zip" "$url"
  unzip -q "${tmp}/${name}.zip" -d "${tmp}/unz"
  bin="$(find "${tmp}/unz" -type f -name "${name}" | head -1)"
  if [[ -z "${bin}" ]]; then
    echo "Could not find ${name} inside the zip:" >&2
    find "${tmp}/unz" -type f >&2
    exit 1
  fi
  cp "${bin}" "tools/${name}"
  chmod +x "tools/${name}"
  rm -rf "${tmp}"
}
fetch_static ffmpeg
fetch_static ffprobe

if otool -L tools/ffmpeg tools/ffprobe | grep -E '/opt/homebrew|/usr/local/(opt|Cellar)'; then
  echo "ERROR: ffmpeg/ffprobe still depend on Homebrew libraries" >&2
  exit 1
fi

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
echo "==> ffmpeg/ffprobe self-check:"
tools/ffmpeg -hide_banner -version | head -1
tools/ffprobe -hide_banner -version | head -1
echo "==> img2webp self-check:"
tools/img2webp -version
