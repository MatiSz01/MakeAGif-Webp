# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for macOS (Apple Silicon, arm64).
#
# Build:
#   pyinstaller MakeAGIF_v3.1_mac.spec
#
# Output:
#   dist/MakeAGIF v3.1.app
#
# Prerequisites (on a Mac with Python 3.11+ for arm64):
#   1. pip install -r requirements.txt
#   2. Drop arm64 binaries into ./tools/ next to this spec:
#        - ffmpeg, ffprobe   (https://evermeet.cx/ffmpeg/  — get arm64 variants)
#        - gifski            (https://gif.ski/             — universal binary)
#      They MUST be extension-less and chmod +x'd:
#        chmod +x tools/ffmpeg tools/ffprobe tools/gifski
#   3. (optional) For distribution outside the Mac App Store, set up
#      codesign + notarization. For personal use it's not required, but
#      Gatekeeper will warn the first time the user opens the .app —
#      they can right-click → Open to bypass.
#
# Notes:
#   - target_arch='arm64' produces a NATIVE arm64 binary (no Rosetta).
#     If you also want Intel support, build a separate spec with 'x86_64'
#     and lipo-merge the two binaries.
#   - argv_emulation=True is required for drag-and-drop onto the .app
#     icon (Finder passes file paths as Apple Events, not argv).
#   - BUNDLE wraps everything into a proper .app structure so it shows up
#     as a single double-clickable icon in Finder.

block_cipher = None

a = Analysis(
    ['MakeAGIF_v3.1_DND_Prototype.py'],
    pathex=[],
    binaries=[('tools', 'tools')],
    datas=[],
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
    name='MakeAGIF v3.1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # UPX often breaks Qt frameworks on macOS
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,       # see header notes
    target_arch='arm64',       # native Apple Silicon
    codesign_identity=None,    # set to "Developer ID Application: <you>" to sign
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MakeAGIF v3.1',
)
app = BUNDLE(
    coll,
    name='MakeAGIF v3.1.app',
    icon=None,                 # set to 'icon.icns' once you have one
    bundle_identifier='com.matias.makeagif.v3-1',
    info_plist={
        'CFBundleName': 'MakeAGIF v3.1',
        'CFBundleDisplayName': 'MakeAGIF v3.1',
        'CFBundleShortVersionString': '3.1.0',
        'CFBundleVersion': '3.1.0',
        'NSHighResolutionCapable': True,
        # Drag-and-drop: Finder will pass any file the user drops on the
        # icon as an Apple Event → argv (because argv_emulation=True).
        'CFBundleDocumentTypes': [{
            'CFBundleTypeName': 'Video',
            'CFBundleTypeRole': 'Viewer',
            'LSItemContentTypes': [
                'public.movie', 'public.video',
                'com.apple.quicktime-movie',
                'public.mpeg-4',
            ],
        }],
        # Required by macOS 10.14+ if any subprocess accesses the user's
        # microphone/camera/etc. We only spawn ffmpeg, so this is empty —
        # but if you ever add audio capture, declare it here.
    },
)
