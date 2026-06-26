# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for macOS Apple Silicon (arm64) — MakeAGIF v3.1.8
#
# Build: pyinstaller --noconfirm MakeAGIF_v3.1.8_mac.spec
# Output: dist/MakeAGIF v3.1.8.app
#
# Tools in ./tools/ (arm64, no .exe): ffmpeg, ffprobe, gifski, img2webp
# Run ./ci_bundle_mac_tools.sh if tools/ is empty.

import os

block_cipher = None

_icon = "MakeAGIF.icns" if os.path.isfile("MakeAGIF.icns") else None

a = Analysis(
    ["MakeAGIF_v3.1.8_DND_Prototype.py"],
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
    name="MakeAGIF v3.1.8",
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
    name="MakeAGIF v3.1.8",
)
app = BUNDLE(
    coll,
    name="MakeAGIF v3.1.8.app",
    icon=_icon,
    bundle_identifier="com.matias.makeagif.v3-1-8",
    info_plist={
        "CFBundleName": "MakeAGIF v3.1.8",
        "CFBundleDisplayName": "MakeAGIF v3.1.8",
        "CFBundleShortVersionString": "3.1.8",
        "CFBundleVersion": "3.1.8",
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
