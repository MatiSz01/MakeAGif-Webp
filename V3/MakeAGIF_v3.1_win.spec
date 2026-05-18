# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Windows (x86_64).
#
# Build:
#   pyinstaller MakeAGIF_v3.1_win.spec
#
# Output:
#   dist/MakeAGIF-WEBP v3.1 Beta.exe   (single-file, portable)
#
# Prerequisites:
#   1. pip install -r requirements.txt
#   2. Drop Windows binaries into ./tools/ next to this spec:
#        - ffmpeg.exe, ffprobe.exe  (https://www.gyan.dev/ffmpeg/builds/)
#        - gifski.exe               (https://gif.ski/)
#        - magick.exe               (optional, ImageMagick)
#   3. MakeAGIF.ico must exist next to this spec (run _make_icon.py
#      once if it doesn't).
#
# Notes:
#   - console=False so no terminal window flashes when launching.
#   - upx=True compresses the bundle. If it ever causes Qt to misbehave
#     (rare but possible), set to False.
#   - The .ico is also bundled as a data file so the running app can
#     find it via sys._MEIPASS for the window/taskbar icon.

a = Analysis(
    ['MakeAGIF_v3.1_DND_Prototype.py'],
    pathex=[],
    binaries=[('tools', 'tools')],
    datas=[('MakeAGIF.ico', '.')],
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
    name='MakeAGIF-WEBP v3.1 Beta',
    icon='MakeAGIF.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX disabled: when UPX (any compression mode) is applied to the
    # bundled Qt6 + ffmpeg DLLs the resulting .exe gets blocked by
    # Windows Smart Screen / Defender on some setups (heuristic flag
    # for "packed executable"). The size penalty is real (~25 MB)
    # but the binary actually launches reliably across machines,
    # which is what matters.
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
