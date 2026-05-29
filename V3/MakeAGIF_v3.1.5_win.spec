# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Windows (x86_64).
#
# Build:
#   pyinstaller --noconfirm MakeAGIF_v3.1.5_win.spec
#
# Output:
#   dist/MakeAGIF-WEBP v3.1.5.exe   (one-file)
#
# Bundled tools/ (Windows): ffmpeg.exe, ffprobe.exe, gifski.exe, magick.exe

a = Analysis(
    ["MakeAGIF_v3.1.5_DND_Prototype.py"],
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
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MakeAGIF-WEBP v3.1.5",
    icon="MakeAGIF.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
