# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for macOS Apple Silicon (arm64).
#
# Build ON A MAC (arm64). Cross-compiling a .app from Windows is not supported.
#
#   cd V3
#   ./build_mac_arm64.sh
#
# Or manually:
#   pip install -r requirements.txt
#   pyinstaller --noconfirm MakeAGIF_v3.1.1_mac.spec
#
# Output:
#   dist/MakeAGIF v3.1.1.app
#
# Prerequisites:
#   1. Python 3.11+ for arm64 (native: `python3 -c "import platform; print(platform.machine())"` → arm64)
#   2. arm64 CLI tools in ./tools/ (no .exe suffix):
#        ffmpeg, ffprobe, gifski  (+ optional magick)
#      chmod +x tools/ffmpeg tools/ffprobe tools/gifski
#   3. MakeAGIF.ico next to this spec (window icon; run _make_icon.py on any OS)
#   4. Optional: MakeAGIF.icns for Finder icon (run _make_icns_mac.sh on macOS)
#
# Distribution: codesign + notarization recommended for Gatekeeper; personal
# use can Right-click → Open the first time.

import os

block_cipher = None

_icon = "MakeAGIF.icns" if os.path.isfile("MakeAGIF.icns") else None

a = Analysis(
    ["MakeAGIF_v3.1.1_DND_Prototype.py"],
    pathex=[],
    binaries=[("tools", "tools")],
    datas=[("MakeAGIF.ico", ".")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MakeAGIF v3.1.1",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MakeAGIF v3.1.1",
)
app = BUNDLE(
    coll,
    name="MakeAGIF v3.1.1.app",
    icon=_icon,
    bundle_identifier="com.matias.makeagif.v3-1-1",
    info_plist={
        "CFBundleName": "MakeAGIF v3.1.1",
        "CFBundleDisplayName": "MakeAGIF v3.1.1",
        "CFBundleShortVersionString": "3.1.1",
        "CFBundleVersion": "3.1.1",
        "NSHighResolutionCapable": True,
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Video",
                "CFBundleTypeRole": "Viewer",
                "LSItemContentTypes": [
                    "public.movie",
                    "public.video",
                    "com.apple.quicktime-movie",
                    "public.mpeg-4",
                ],
            }
        ],
    },
)
