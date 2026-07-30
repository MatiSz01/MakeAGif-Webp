# =============================================================================
# MakeAGIF v3.1.10 — DND Prototype (NLE trim/playhead + frame-exact preview)
# =============================================================================
# Forked from v3.1.4. Performance pass — UI responsiveness, no engine changes.
# v3.1.10 changelog:
#   * FIX — persistent settings actually persist now in the packaged build.
#     v3.1.9 wrote app_settings.json next to __file__, which inside a PyInstaller
#     one-file .exe is the throwaway _MEIxxxx temp folder (deleted on exit), so the
#     last-used parameters were saved to a location that vanished and every launch
#     fell back to the defaults. The settings file now lives next to the executable
#     (Windows/Linux) or in ~/Library/Application Support/MakeAGIF (macOS .app),
#     the same persistent spot the presets use. Same fix covers cache dir + chart
#     toggle persistence.
#
# v3.1.9 changelog:
#   * Persistent settings (single mode) — the last-used parameters now stick.
#     1) They're saved to app_settings.json on render AND on app close
#        (key "last_single_vals"), and restored on the next launch instead of
#        snapping back to the hard-coded defaults.
#     2) Loading a new clip no longer resets the panel to defaults — it inherits
#        the current parameters (format, mode, fps/quality, dimensions, flags…);
#        only the trim is cleared since it's specific to each source.
#     3) The encoding-mode tab (Iterative/Manual) is no longer force-reset to
#        Iterative on import, so "where you left off" is preserved.
#     Trim is intentionally NOT restored on a fresh boot (set_vals only applies
#     a trim when a source is loaded), so no stale TC range ever reappears.
#
# v3.1.8 changelog:
#   * FIX (macOS) — WebP export, take 2. v3.1.7 routed macOS WebP to the bundled
#     ImageMagick, but Homebrew's `magick` is NOT relocatable: copied on its own
#     it can't find delegates.xml / its coder modules and dies with
#     "NoDecodeDelegateForThisImageFormat" — it couldn't even read the PNG
#     frames. We now bundle Google's official, STATICALLY-LINKED libwebp tool
#     `img2webp` (self-contained, no config/coder deps) and make it the
#     preferred WebP encoder on macOS. It handles alpha natively and uses EXACT
#     millisecond frame timing (no more centisecond quantisation). The broken
#     `magick` is no longer bundled on macOS. Windows is untouched: it has no
#     img2webp, so it still uses ffmpeg (non-alpha) / magick (alpha) exactly as
#     before.
#
# v3.1.7 changelog:
#   * FIX (macOS) — WebP export. The bundled macOS ffmpeg (Homebrew default)
#     ships WITHOUT the libwebp encoder, so `-c:v libwebp` died with "Unknown
#     encoder 'libwebp'". We now probe the encoder once at startup
#     (FFMPEG_HAS_LIBWEBP) and route WebP through the already-bundled ImageMagick
#     when it's missing (or when alpha is requested, as before). Windows ffmpeg
#     has libwebp, so its WebP path is byte-for-byte unchanged. NOTE: the magick
#     fallback uses centisecond frame delays, so macOS WebP fps is slightly
#     quantised vs ffmpeg's exact rate — acceptable; GIFs (gifski) stay exact.
#   * About box — the version line now self-identifies the OS at runtime
#     (macOS/Windows/Linux build) instead of hardcoding "Windows build". Credits
#     corrected: gifski = all GIFs, ImageMagick = WebP (alpha + libwebp-less
#     fallback), ffmpeg source notes both gyan.dev (Win) and Homebrew (mac).
#
# v3.1.6 changelog (supersedes the never-shipped v3.1.5 macOS build):
#   * FIX (macOS) — frame glob expansion. v3.1.5 correctly dropped shell=True
#     but assumed gifski expands "*.png" itself; on Unix it does NOT (the shell
#     normally does that), so a shell-less run would hand gifski a literal
#     "*.png" → 0 frames. run_cmd now expands "*.png"/"f_*.png" into an explicit
#     sorted file list on macOS/Linux, while Windows keeps the literal pattern
#     (gifski/magick expand it there + it dodges the ~32 KB command-line limit
#     on long clips). Windows behaviour is byte-for-byte unchanged.
#
# v3.1.5 changelog:
#   * PR1 — Trim thumbnails (trimmer IN/OUT, drop-zone strip, batch strip) now
#     decode OFF the UI thread via _AsyncThumbLoader. SET IN/OUT and editing the
#     trim fields no longer freeze the window. Per-label generation counter
#     cancels stale/hidden decodes. Same frame-exact path as before (no drift).
#   * PR2 — get_video_specs() probes metadata with a SINGLE ffprobe JSON call
#     (was ffmpeg -i + 2× ffprobe = 3 processes). Legacy path kept as fallback.
#   * FIX (macOS) — gifski/magick encode failed with a bogus
#     "--fps: .../MakeAGIF: No such file or directory" because run_cmd used
#     shell=True for the "*.png" frame glob. On POSIX that runs
#     `/bin/sh -c argv[0] ...`, so only argv[0] (the executable path, which is
#     inside "MakeAGIF vX.app" and HAS a space) was the command — /bin/sh
#     word-split it and failed. Now always shell=False. (Glob expansion was
#     finished in v3.1.6 — see above.)
#   * UX (single mode) — after a render a modal result WINDOW (English) now
#     states the winning params (Q / FPS / size) and clearly flags when the
#     result was REUSED from a previous run (Smart Match cache hit) instead of
#     freshly searched — so an instant cache copy no longer looks like "nothing
#     happened". Being modal + non-inline, the message is gone the moment the
#     user runs again. A "Search Again" action (dialog + drop-zone button)
#     forces a fresh search ignoring saved iterations for that run, WITHOUT
#     toggling "Keep iterations" (one-shot `force_reencode` param; cache still
#     saved).
#   * Cross-platform pass — "Open output folder" used os.startfile (Windows-only,
#     silently failed on macOS) → now uses open_path_in_os(). Alpha-tester page
#     opened via a malformed "file:///"+path URI on POSIX → now Path.as_uri().
#     Monospace UI bits hardcoded "Consolas" (Windows-only) → added 'Menlo' /
#     monospace fallback so numbers/log stay aligned on macOS; UI font gained a
#     macOS-friendly fallback too.
#   * Iterative search ALGORITHM, export pipeline and scene detection UNCHANGED
#     (force_reencode only skips the cache READ side; warm-start math intact).
#
# v3.1.4 changelog:
#   * Phase 2 optimization: direct FPS scaling from size factor (fewer redundant encodes).
#   * Trim UI closure: OUT shown/edited as last INCLUDED frame (TC + t_end + thumbs);
#     engine/storage stay exclusive [IN, OUT). Combined ffmpeg seek for preview.
#   * Trim dialog: OUT = exact user frame (inclusive); scene cuts +1 (next plan);
#     IN/OUT thumb ffmpeg seek fix at t≈0.
#   * Trim preview: ½ res Qt PLAY proxy + fast scrub decode; exact frame on pause/I/O.
#     NLE TC fields; scene cache clear; frame-step ←/→.
#
# v3.1 changelog (inherited from v3.1; growing as features land):
#   * Timeline auto-follows playhead during playback when zoomed in (NLE-style
#     paging — no more losing the cursor offscreen at high zoom).
#   * Snap-halo visual feedback on the timeline: hovering near a scene cut
#     paints a yellow halo so the user sees WYSIWYG that "click here = snap".
#     Snap also engages during drag-scrub (was click-only).
#   * Horizontal scrollbar under the timeline that activates when zoomed in.
#     Bidirectional sync with the wheel/Shift+wheel viewport so any input
#     path (drag handle, wheel, +/-/FIT buttons) keeps everything coherent.
#   * VFR (variable framerate) detection via ffprobe. When the source is VFR,
#     a yellow warning banner above the timeline tells the user that frame-
#     perfect trim may drift, and recommends re-encoding to CFR. Detection
#     compares r_frame_rate vs avg_frame_rate with a 1.5% tolerance so
#     clean 23.976/24/29.97/30 sources don't false-positive.
#   * Trim transport: explicit "GO TO IN" / "GO TO OUT" buttons + Shift+I /
#     Shift+O shortcuts (Premiere/Resolve convention).
#   * Polish: CrossCursor in SEG MODE, live tooltip on volume drag, scene
#     detector now reports "Analyzing X% (N cuts)" with a slim progress bar,
#     cut markers fade to alpha 60 once there are >200 cuts so they don't
#     saturate the timeline, MIN_VIEW_SPAN now adapts to total_frames so
#     "1 frame visible" is the real zoom floor on long clips.
#   * Iterative engine telemetry: WorkerSignals now exposes iter_started /
#     iter_step / iter_finished. A new IterChartWidget under the progress
#     bar plots the live trajectory of (iteration, file_size) against the
#     target band so users can see convergence behavior in real time.
#     The chart includes an always-visible compact trajectory line of the
#     last attempts AND a hover tooltip with the full attempt history (Q,
#     FPS, size, bracket status) — no console expansion needed.
#   * Iter chart can be hidden/shown via a small disclosure button; the
#     preference is persisted in app_settings.json (key: show_iter_chart).
#   * Console no longer auto-pops on MAKE press — the user controls when
#     to expand the log panel.
#   * Cross-platform readiness: tool paths now go through _exe()/get_tool_path
#     so 'ffmpeg' / 'ffmpeg.exe' resolve correctly on macOS/Linux/Windows.
#     All 'open this folder/file' UI actions route through open_path_in_os(),
#     which handles os.startfile / 'open' / 'xdg-open' uniformly.
#     PyInstaller specs for Windows AND macOS Apple Silicon shipped under
#     MakeAGIF_v3.1.1_win.spec (Windows) / MakeAGIF_v3.1.2_mac.spec (macOS arm64).
#     See MACOS_BUILD.md — GitHub Actions builds the .app without a local Mac.
#
# v3.1.2 (macOS-focused release):
#   * Same as v3.1.1 plus explicit version bump for Apple builds.
#   * Bundled tools match Windows: ffmpeg, ffprobe, gifski, magick (arm64).
#   * MAGICK_PATH only when magick exists on disk (WebP+alpha parity).
#
# v3.1.3 (trim / NLE semantics):
#   * Scene cuts frame-aligned to source fps before markers/snap (WYSIWYG with export).
#   * Unified playhead frame index (_park_at_frame_index) for scrub, I/O, goto, steps.
#   * Precise preview uses same frame index as TC/playhead (removed 0.4/fps QMedia bias).
#   * SET OUT parks on last *included* frame; goto OUT still shows exclusive boundary.
#   * _quantize_to_source_frame clamps to last source frame index.
#   * Scene cuts: fix frame-align dropping all cuts when t_frames/duration wrong;
#     use QMediaPlayer duration; clearer label when 0 cuts after detect.
#   * Frame-perfect trim: shared frame-index helpers, ffprobe nb_frames/r_fps,
#     preview/thumbs/scene cuts via ffmpeg -accurate_seek (same path as export).
#
# v3.1.1 patch (included):
#   * Trim dialog async frame preview; debounced timeline scrub.
#
# Inherits everything from v3.0:
#   - Iterative search engine with persistent knowledge cache
#   - Scene detection + persistent scene cache (RAM + disk, content-keyed)
#   - NLE-style segment selection (Shift+Click range fill, SEG MODE toggle)
#   - Frame-perfect trim (symmetric integer-FPS timecode parsing)
#   - Timeline zoom + pan, multimedia-style volume control
# =============================================================================

import sys
import os
import subprocess
import re
import math
import time
import shutil
import tempfile
import hashlib
import json
import threading
import queue
import base64
import webbrowser
import copy
import glob
from pathlib import Path
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
from datetime import datetime

from PySide6.QtWidgets import (QApplication, QScrollArea, QScrollBar, QDialog, QDialogButtonBox, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QFrame, QTabWidget,
                               QSlider, QGroupBox, QPushButton, QComboBox,
                               QCheckBox, QStackedWidget, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QSpinBox, QDoubleSpinBox, QTextEdit, QButtonGroup,
                               QAbstractItemView, QFileDialog, QMessageBox, QSizePolicy, QProgressBar, QLineEdit, QMenu, QToolTip,
                               QStyle, QStyleOptionSlider)
from PySide6.QtCore import Qt, QUrl, QSize, QThread, Signal, QObject, Slot, QTimer, QItemSelection, QItemSelectionModel, QRect
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
# from PySide6.QtGui import QColor, QFont, QPalette, QIcon, QDragEnterEvent, QDropEvent # (Unused imports commented out for cleanliness)
from PySide6.QtGui import QIcon, QColor, QImage, QPixmap, QShortcut, QKeySequence, QColor, QCursor, QPainter

# --- Premiere Pro Studio Style (v3.0 Ultra-Dark matches v2.7) ---
COLOR_BG = "#080808"           # Negro casi absoluto
COLOR_PANEL = "#111111"        # Paneles secundarios (Inputs)
COLOR_ACCENT = "#25a0ff"       # Azul vibrante de Premiere
COLOR_ACCENT_HOVER = "#40a9ff"
COLOR_TEXT = "#bbbbbb"         # Gris claro
COLOR_TEXT_BRIGHT = "#ffffff"  # Blanco puro
COLOR_BORDER = "#1a1a1a"       # Bordes sutiles
COLOR_SELECT = "#1e3a8c"       # Selección Azul Profundo
COLOR_DANGER = "#ff4444"
COLOR_SUCCESS = "#00c853"
COLOR_WARNING = "#ffab00"
COLOR_STATE_INFO = "#1e3a8c"

# --- Constants ---
SCRIPT_VERSION = "v3.1.10"
APP_AUTHOR = "Matias Szteinberg"
APP_TITLE = f"MakeAGIF/WEBP v3.1.10 — By {APP_AUTHOR}"
INPROGRESS_SUFFIX = "_INPROGRESS"
DEFAULT_CACHE_DIR = os.path.join(tempfile.gettempdir(), "gif_tool_py_frame_cache")
# Scene-detection cache lives in its own folder, intentionally NOT under the
# user-configurable frame cache. Reasons:
#   - It's tiny (one small JSON per source) so it doesn't fill the SSD.
#   - It survives the "Purge Cache" button (purging frames shouldn't force the
#     user to re-detect scenes — that's a slower, more expensive operation).
#   - Keyed by content hash (size + sha1 of first 1 MB), so renaming/moving the
#     source still hits the cache.
SCENE_CACHE_DIR = os.path.join(tempfile.gettempdir(), "gif_tool_scene_cache")
_SCENE_RAM_CACHE = {}  # content-key (str) -> {threshold(float): list[float]}

def _video_content_key(path):
    """Fingerprint a video file by its size + sha1 of the first 1 MB. Robust
    to renames/moves (no path involvement) and fast on multi-GB files. Returns
    None if the file can't be read."""
    try:
        size = os.path.getsize(path)
        h = hashlib.sha1()
        h.update(str(size).encode("utf-8"))
        with open(path, "rb") as f:
            h.update(f.read(1024 * 1024))  # first 1 MiB
        return h.hexdigest()
    except Exception:
        return None

def _scene_cache_path(content_key, threshold):
    """Disk location for one (content, threshold) cache entry."""
    safe_thr = f"{float(threshold):.3f}".replace(".", "_")
    return os.path.join(SCENE_CACHE_DIR, f"{content_key}__t{safe_thr}.json")

def load_scene_cache(content_key, threshold):
    """Return cached scene data or None.

    v4: ``{"ver": 4, "cuts_fi": [...]}`` — first frame of each new scene (+1 aligned).
    v3: legacy without +1 — migrated +1 on load.  v2/v1: legacy formats.
    """
    if not content_key:
        return None
    ram = _SCENE_RAM_CACHE.get(content_key, {})
    if threshold in ram:
        hit = ram[threshold]
        if isinstance(hit, list):
            return {"ver": 1, "cuts_sec": [float(c) for c in hit]}
        return dict(hit)
    p = _scene_cache_path(content_key, threshold)
    try:
        if os.path.isfile(p):
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
            ver = int(data.get("ver", 1))
            cuts_fi = [
                int(x) for x in (data.get("cuts_fi") or [])
                if isinstance(x, (int, float))
            ]
            if ver >= 4 and cuts_fi:
                payload = {"ver": 4, "cuts_fi": sorted(set(cuts_fi))}
            elif ver == 3 and cuts_fi:
                payload = {
                    "ver": 4,
                    "cuts_fi": sorted(set(max(1, int(x) + 1) for x in cuts_fi)),
                }
            elif ver == 2 and cuts_fi:
                payload = {"ver": 4, "cuts_fi": sorted(set(cuts_fi))}
            else:
                cuts = [
                    float(c) for c in (data.get("cuts") or [])
                    if isinstance(c, (int, float))
                ]
                payload = {"ver": 1, "cuts_sec": sorted(set(cuts))}
            _SCENE_RAM_CACHE.setdefault(content_key, {})[threshold] = dict(payload)
            return payload
    except Exception:
        pass
    return None


def save_scene_cache(content_key, threshold, cuts_fi, src_path=None):
    """Persist frame-index scene cuts (v4) to RAM + disk."""
    if not content_key:
        return
    cuts_fi = sorted(set(int(x) for x in cuts_fi if int(x) > 0))
    payload = {"ver": 4, "cuts_fi": cuts_fi}
    _SCENE_RAM_CACHE.setdefault(content_key, {})[threshold] = dict(payload)
    try:
        os.makedirs(SCENE_CACHE_DIR, exist_ok=True)
        with open(_scene_cache_path(content_key, threshold), 'w', encoding='utf-8') as f:
            json.dump({
                "ver": 4,
                "cuts_fi": cuts_fi,
                "threshold": float(threshold),
                "src_seen": src_path or "",
                "saved_at": time.time(),
            }, f)
    except Exception:
        pass


def clear_scene_cache(content_key=None, threshold=None):
    """Remove scene-detection cache (RAM + disk).

    *content_key* — fingerprint for one source file (``None`` = entire cache).
    *threshold* — if set with *content_key*, only that sensitivity; else all
    thresholds saved for that clip (clears legacy v1/v2 JSON files).

    Returns ``(ram_cleared, disk_files_removed)``.
    """
    ram_cleared = 0
    disk_removed = 0
    if content_key:
        bucket = _SCENE_RAM_CACHE.get(content_key)
        if bucket:
            if threshold is not None:
                if threshold in bucket:
                    del bucket[threshold]
                    ram_cleared = 1
            else:
                ram_cleared = len(bucket)
                _SCENE_RAM_CACHE.pop(content_key, None)
        try:
            os.makedirs(SCENE_CACHE_DIR, exist_ok=True)
            prefix = f"{content_key}__t"
            safe_thr = (
                f"{float(threshold):.3f}".replace(".", "_")
                if threshold is not None else None
            )
            for name in os.listdir(SCENE_CACHE_DIR):
                if not name.endswith(".json") or not name.startswith(prefix):
                    continue
                if safe_thr is not None and f"__t{safe_thr}.json" not in name:
                    continue
                try:
                    os.remove(os.path.join(SCENE_CACHE_DIR, name))
                    disk_removed += 1
                except OSError:
                    pass
        except OSError:
            pass
        return (ram_cleared, disk_removed)

    _SCENE_RAM_CACHE.clear()
    ram_cleared = 1
    try:
        if os.path.isdir(SCENE_CACHE_DIR):
            for name in os.listdir(SCENE_CACHE_DIR):
                if not name.endswith(".json"):
                    continue
                try:
                    os.remove(os.path.join(SCENE_CACHE_DIR, name))
                    disk_removed += 1
                except OSError:
                    pass
    except OSError:
        pass
    return (ram_cleared, disk_removed)


def clear_scene_cache_on_app_startup():
    """Wipe RAM + disk scene cache every launch (fresh DETECT per session)."""
    return clear_scene_cache()


PREVIEW_PROXY_DIR = os.path.join(tempfile.gettempdir(), "gif_tool_preview_proxy")


def should_offer_half_res_playback(src_w, src_h):
    """True when a ½-res Qt playback proxy is worth building (large sources)."""
    try:
        w, h = int(src_w or 0), int(src_h or 0)
    except (TypeError, ValueError):
        return False
    if w <= 0 or h <= 0:
        return False
    return (w * h) >= 640 * 360 or max(w, h) >= 720


def preview_decode_dimensions(vw, vh, *, exact=False):
    """Pixel size for ffmpeg frame grab.

    * exact=False — scrubbing (½ UI size, faster decode).
    * exact=True  — paused / I/O / park (full UI, matches export).
    """
    vw, vh = max(32, int(vw)), max(32, int(vh))
    if exact:
        tw = min(vw, 1280)
        th = min(vh, 720)
    else:
        tw = max(320, vw // 2)
        th = max(180, vh // 2)
        long_edge = max(tw, th)
        if long_edge > 640:
            scale = 640.0 / long_edge
            tw = max(160, int(tw * scale))
            th = max(90, int(th * scale))
    return max(32, tw), max(32, th)


def build_playback_proxy_path(content_key):
    if not content_key:
        return None
    return os.path.join(PREVIEW_PROXY_DIR, f"{content_key}_half.mp4")


def build_playback_proxy(source_path, content_key, src_w, src_h):
    """Build (or reuse) a half-resolution H.264 proxy for smooth Qt PLAY."""
    if not content_key or not os.path.isfile(source_path):
        return None
    try:
        w, h = int(src_w or 0), int(src_h or 0)
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0:
        return None
    out = build_playback_proxy_path(content_key)
    if os.path.isfile(out) and os.path.getsize(out) > 2048:
        return out
    tw = max(2, (w // 2) & ~1)
    th = max(2, (h // 2) & ~1)
    try:
        os.makedirs(PREVIEW_PROXY_DIR, exist_ok=True)
    except OSError:
        return None
    fd, tmp = tempfile.mkstemp(suffix=".mp4", prefix="magif_ppx_", dir=PREVIEW_PROXY_DIR)
    os.close(fd)
    try:
        cmd = [
            FFMPEG_PATH, "-y", "-nostdin",
            "-i", source_path,
            "-an",
            "-vf", f"scale={tw}:{th}",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-movflags", "+faststart",
            tmp,
        ]
        flags = 0x08000000 if os.name == "nt" else 0
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
            timeout=600,
        )
        if proc.returncode != 0 or not os.path.isfile(tmp):
            return None
        try:
            if os.path.isfile(out):
                os.remove(out)
        except OSError:
            pass
        os.replace(tmp, out)
        return out
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return None


# App-level settings live alongside the script (next to /presets/) so the user's
# choice of cache folder, etc. survives across runs without polluting their
# preset library. Falls back silently to defaults on any I/O error.
def _app_settings_path():
    """Location of app_settings.json.

    CRITICAL (v3.1.10): this must live next to the PERSISTENT user data, NOT next
    to ``__file__``. In a PyInstaller one-file build ``__file__`` resolves to the
    temporary ``_MEIxxxx`` extraction folder, which is wiped when the app exits —
    so anything written there (last-used settings, cache dir, chart toggle) never
    survives a restart and the app always boots back to the hard-coded defaults.

    We mirror the presets location instead:
      * Windows / Linux: right next to the executable (or the .py in dev).
      * macOS frozen .app: ~/Library/Application Support/MakeAGIF (writing inside
        the .app bundle is read-only / hidden once installed or signed).
    """
    try:
        if getattr(sys, "frozen", False):
            if sys.platform == "darwin":
                base = os.path.expanduser("~/Library/Application Support/MakeAGIF")
            else:
                base = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(base, exist_ok=True)
    except Exception:
        base = os.getcwd()
    return os.path.join(base, "app_settings.json")

def load_app_settings():
    try:
        p = _app_settings_path()
        if os.path.isfile(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}

def save_app_settings(data):
    try:
        with open(_app_settings_path(), 'w', encoding='utf-8') as f:
            json.dump(data or {}, f, indent=2)
    except Exception:
        pass


# --- Alpha Tester (HTML transparency inspector, ported from v2.7 Lite) ---
#
# Self-contained HTML page that renders a GIF/WebP/video against four
# different backgrounds (checkerboard, black, white, magenta) so the user
# can spot ghosting, halo edges, and alpha-blend artifacts at a glance.
# Each card is click-to-zoom with pan/scroll/keyboard zoom support.
#
# Two injection points kept verbatim from v2.7 so we can pre-load the
# rendered file without hitting browser file:// security: the HTML is
# written to %TEMP% with a base64 data URI baked into the script, plus
# RAW_PATH/RAW_NAME for the "Copy Folder Path" button. When opened with
# no file (open_alpha_tester(None)), the upload box is shown for manual
# drag-and-drop in the browser.
ALPHA_TESTER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transparency Reality Tester - v12 (ELITE INSPECTOR)</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #1a1a1a;
            color: #f0f0f0;
            margin: 0;
            padding: 40px;
            text-align: center;
        }

        h1 { margin-bottom: 10px; color: #fff; font-weight: 300; }
        p { color: #888; margin-bottom: 40px; }

        .upload-container {
            background: #252525;
            padding: 30px;
            border-radius: 12px;
            display: inline-block;
            margin-bottom: 40px;
            border: 2px dashed #444;
            transition: all 0.3s;
        }
        .upload-container:hover { border-color: #666; background: #2a2a2a; }

        /* Custom File Input Styling to avoid OS language default */
        #fileInput { display: none; }
        .custom-file-upload {
            display: inline-block;
            padding: 12px 24px;
            cursor: pointer;
            background-color: #444;
            color: #fff;
            border-radius: 6px;
            font-weight: 600;
            transition: background 0.2s;
        }
        .custom-file-upload:hover { background-color: #555; }
        #file-name {
            display: block;
            margin-top: 10px;
            font-size: 0.8rem;
            color: #888;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 30px;
            max-width: 1600px;
            margin: 0 auto;
        }

        .card {
            background: #222;
            border: 1px solid #333;
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }

        .card-header {
            background: #2d2d2d;
            padding: 12px;
            font-weight: 600;
            font-size: 0.85rem;
            color: #aaa;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid #333;
        }

        .canvas-area {
            height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }

        .canvas-area img, .canvas-area video {
            max-width: 90%;
            max-height: 90%;
            object-fit: contain;
            filter: drop-shadow(0 0 10px rgba(0,0,0,0.5));
        }

        /* backgrounds */
        .bg-checker {
            background-color: #fff;
            background-image:
              linear-gradient(45deg, #eee 25%, transparent 25%),
              linear-gradient(-45deg, #eee 25%, transparent 25%),
              linear-gradient(45deg, transparent 75%, #eee 75%),
              linear-gradient(-45deg, transparent 75%, #eee 75%);
            background-size: 20px 20px;
            background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
        }
        .bg-black { background-color: #000; }
        .bg-white { background-color: #fff; }
        .bg-magenta { background-color: #ff00ff; }

        /* Fullscreen Modal */
        #modal {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.95);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            cursor: zoom-out;
        }
        #modal.active { display: flex; }
        #modal .modal-content-wrapper {
            width: 90%;
            height: 80%;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 16px;
            box-shadow: 0 0 100px rgba(0,0,0,0.9);
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.1);
        }
        #modal .modal-content-wrapper img, #modal .modal-content-wrapper video {
            max-width: 95%;
            max-height: 95%;
            object-fit: contain;
            filter: drop-shadow(0 0 20px rgba(0,0,0,0.5));
            transition: transform 0.1s ease-out;
        }
        #modal-header {
            position: absolute;
            top: 30px;
            color: #fff;
            font-size: 1.1rem;
            text-transform: uppercase;
            letter-spacing: 3px;
            background: rgba(0,0,0,0.6);
            padding: 8px 20px;
            border-radius: 50px;
            backdrop-filter: blur(10px);
            z-index: 1001;
        }

        .zoom-controls {
            position: absolute;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            padding: 12px 25px;
            border-radius: 50px;
            display: flex;
            align-items: center;
            gap: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            z-index: 1002;
        }
        .zoom-slider-container { display: flex; flex-direction: column; align-items: center; width: 250px; }
        .zoom-slider { width: 100%; cursor: pointer; }
        .zoom-labels { display: flex; justify-content: space-between; width: 100%; font-size: 0.7rem; color: #666; margin-top: 5px; }
        .zoom-value {
            min-width: 60px; font-family: monospace; font-size: 0.9rem; color: #4CAF50;
            cursor: pointer; border-bottom: 1px dashed #4CAF50;
            padding: 2px 4px; border-radius: 4px;
        }
        .zoom-value:hover { background: rgba(76, 175, 80, 0.1); }
        .btn-reset {
            background: #333; border: none; color: #eee; padding: 6px 15px;
            border-radius: 20px; cursor: pointer; font-size: 0.8rem;
            transition: background 0.2s;
        }
        .btn-reset:hover { background: #444; color: #fff; }

        #modal .modal-content-wrapper {
            cursor: grab;
        }
        #modal .modal-content-wrapper:active {
            cursor: grabbing;
        }

        #zoomed-element {
            transform-origin: center;
        }

        /* Tick mark for 100% */
        .slider-wrapper { position: relative; width: 100%; }
        .tick-100 {
            position: absolute;
            top: 50%; left: 50%;
            width: 2px; height: 10px;
            background: rgba(255,255,255,0.3);
            transform: translate(-50%, -50%);
            pointer-events: none;
        }

        .path-banner {
            background: #222;
            padding: 10px 20px;
            border-radius: 8px;
            margin: 20px auto 40px;
            display: none; /* Hidden by default */
            align-items: center;
            gap: 15px;
            border: 1px solid #333;
            max-width: 80%;
        }
        .path-text { color: #666; font-family: monospace; font-size: 0.85rem; word-break: break-all; }
        .btn-copy {
            background: #444; border: none; color: #fff; padding: 5px 12px;
            border-radius: 4px; cursor: pointer; font-size: 0.75rem;
        }
        .btn-copy:hover { background: #555; }

        .card {
            cursor: zoom-in;
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
        }
        .card:hover { transform: scale(1.02); box-shadow: 0 15px 40px rgba(0,0,0,0.7); }
        .card::after {
            content: 'Click to Zoom';
            position: absolute;
            bottom: 10px; right: 10px;
            font-size: 0.65rem;
            color: rgba(255,255,255,0.3);
            text-transform: uppercase;
            letter-spacing: 1px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
        }
        .card:hover::after { opacity: 1; }
    </style>
</head>
<body>

    <h1>Transparency & Ghosting Tester</h1>
    <p>Inspecting borders and alpha blending against different contexts.</p>

    <div class="path-banner">
        <div style="text-align: left;">
            <div id="file-name" style="font-weight: bold; margin-bottom: 4px; color: #4CAF50;">No file loaded</div>
            <div id="file-path" class="path-text" style="opacity: 0.6">Folder: ---</div>
        </div>
        <button class="btn-copy" onclick="copyPath()">Copy Folder Path</button>
    </div>

    <div class="upload-container" style="display:none" id="upload-box">
        <label for="fileInput" class="custom-file-upload">
            Choose File (WebP/GIF)
        </label>
        <input type="file" id="fileInput" accept="image/*,video/*">
    </div>

    <div class="grid">
        <div class="card" onclick="maximize(this, 'checker')">
            <div class="card-header">Checkerboard (Transparency)</div>
            <div class="canvas-area bg-checker" id="container-checker"></div>
        </div>
        <div class="card" onclick="maximize(this, 'black')">
            <div class="card-header">Pure Black (Check for white halos)</div>
            <div class="canvas-area bg-black" id="container-black"></div>
        </div>
        <div class="card" onclick="maximize(this, 'white')">
            <div class="card-header">Pure White (Check for dark edges)</div>
            <div class="canvas-area bg-white" id="container-white"></div>
        </div>
        <div class="card" onclick="maximize(this, 'magenta')">
            <div class="card-header">High-Contrast Magenta (Check for edge artifacts)</div>
            <div class="canvas-area bg-magenta" id="container-magenta"></div>
        </div>
    </div>

    <div id="modal" onclick="closeModal(event)">
        <div id="modal-header"><span id="bg-name">None</span></div>
        <div id="modal-content-area" class="modal-content-wrapper"></div>

        <div class="zoom-controls" onclick="event.stopPropagation()">
            <div class="zoom-value" id="zoom-text">100%</div>
            <div class="zoom-slider-container">
                <div class="slider-wrapper">
                    <input type="range" min="0" max="200" value="100" class="zoom-slider" id="zoomSlider">
                    <div class="tick-100"></div>
                </div>
                <div class="zoom-labels">
                    <span>25%</span>
                    <span>100%</span>
                    <span>400%</span>
                </div>
            </div>
            <button class="btn-reset" onclick="resetZoom()">Reset 100%</button>
        </div>
    </div>

    <script>
        const fileInput = document.getElementById('fileInput');
        const containers = [
            document.getElementById('container-checker'),
            document.getElementById('container-black'),
            document.getElementById('container-white'),
            document.getElementById('container-magenta')
        ];

        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;

            const objectUrl = URL.createObjectURL(file);
            const isVideo = file.type.startsWith('video');

            containers.forEach(c => c.innerHTML = '');
            containers.forEach(container => {
                let element;
                if (isVideo) {
                    element = document.createElement('video');
                    element.src = objectUrl;
                    element.autoplay = true; element.loop = true; element.muted = true;
                    element.playsInline = true; element.controls = true;
                } else {
                    element = document.createElement('img');
                    element.src = objectUrl;
                }
                container.appendChild(element);
            });

            document.getElementById('file-name').textContent = file.name;
        });

        const modal = document.getElementById('modal');
        const modalContentArea = document.getElementById('modal-content-area');
        const bgName = document.getElementById('bg-name');
        const zoomSlider = document.getElementById('zoomSlider');
        const zoomText = document.getElementById('zoom-text');

        let isDragging = false;
        let startX, startY;
        let currentScale = 1.0;
        let translateX = 0, translateY = 0;

        function maximize(card, bg) {
            const original = card.querySelector('img, video');
            const header = card.querySelector('.card-header').textContent;
            if (!original) return;

            modalContentArea.innerHTML = '';
            modalContentArea.className = 'modal-content-wrapper bg-' + bg;

            const clone = original.cloneNode(true);
            clone.id = 'zoomed-element';
            modalContentArea.appendChild(clone);

            modal.classList.add('active');
            bgName.textContent = header;
            resetZoom();
        }

        function closeModal(e) {
            if (e.target === modal || e.target === modalContentArea) {
                modal.classList.remove('active');
            }
        }

        function updateDisplay() {
            const element = document.getElementById('zoomed-element');
            if (element) {
                element.style.transform = `translate(${translateX}px, ${translateY}px) scale(${currentScale})`;
            }
            zoomText.textContent = Math.round(currentScale * 100) + '%';

            // Sync slider (using the biased scale logic)
            const ds = currentScale * 100;
            let sliderVal;
            if (ds <= 100) {
                sliderVal = (ds - 25) / 0.75;
            } else {
                sliderVal = 100 + ((ds - 100) / 300) * 100;
            }
            zoomSlider.value = sliderVal;
        }

        zoomSlider.addEventListener('input', function() {
            const val = parseInt(this.value);
            if (val <= 100) {
                currentScale = (25 + (val/100) * 75) / 100;
            } else {
                currentScale = (100 + ((val-100)/100) * 300) / 100;
            }
            updateDisplay();
        });

        // Mouse Wheel Zoom
        modal.addEventListener('wheel', function(e) {
            if (!modal.classList.contains('active')) return;
            e.preventDefault();
            const delta = e.deltaY > 0 ? -0.1 : 0.1;
            currentScale = Math.min(Math.max(0.01, currentScale + delta), 4.0);
            updateDisplay();
        }, { passive: false });

        // Pan and Drag
        modalContentArea.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX - translateX;
            startY = e.clientY - translateY;
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            translateX = e.clientX - startX;
            translateY = e.clientY - startY;
            updateDisplay();
        });

        window.addEventListener('mouseup', () => {
            isDragging = false;
        });

        // Keyboard Entry
        zoomText.addEventListener('click', () => {
            const newVal = prompt("Enter zoom percentage (1-400):", Math.round(currentScale * 100));
            if (newVal !== null) {
                const parsed = parseInt(newVal);
                if (!isNaN(parsed)) {
                    currentScale = Math.min(Math.max(1, parsed), 400) / 100;
                    updateDisplay();
                }
            }
        });

        function resetZoom() {
            currentScale = 1.0;
            translateX = 0;
            translateY = 0;
            updateDisplay();
        }

        function copyPath() {
            let pathValue = "{{RAW_PATH}}";
            if (pathValue && pathValue !== "{{" + "RAW_PATH" + "}}") {
                // Extract directory only
                const parts = pathValue.split('/');
                parts.pop(); // Remove filename
                const dirPath = parts.join('/');
                navigator.clipboard.writeText(dirPath);
                alert("Folder path copied to clipboard!");
            }
        }

        function loadFileFromPath(path) {
            const statusLabel = document.getElementById('file-name');
            const pathLabel = document.getElementById('file-path');
            const pathBanner = document.querySelector('.path-banner');

            try {
                const isData = path.startsWith('data:');
                let isVideo = false;

                if (isData) {
                    isVideo = path.includes('data:video');
                    // Show banner only if we have a real path injected
                    const realPath = "{{RAW_PATH}}";
                    if (realPath && realPath !== "{{" + "RAW_PATH" + "}}") {
                        const parts = realPath.split('/');
                        parts.pop();
                        pathLabel.textContent = "Folder: " + parts.join('/');
                        pathBanner.style.display = 'inline-flex';
                    } else {
                        pathBanner.style.display = 'none';
                    }
                } else {
                    isVideo = path.toLowerCase().endsWith('.webm') || path.toLowerCase().endsWith('.mp4') || path.toLowerCase().endsWith('.mov');
                    pathBanner.style.display = 'none'; // Default for non-Python loads
                }

                containers.forEach(c => {
                    c.innerHTML = '<span style="color:#555">Loading Asset...</span>';
                });

                containers.forEach(container => {
                    let element;
                    if (isVideo) {
                        element = document.createElement('video');
                        element.onerror = (e) => { statusLabel.textContent = "Error: Video load failed."; };
                        element.oncanplay = () => { finishLoad(); };
                        element.src = path;
                        element.autoplay = true; element.loop = true; element.muted = true;
                        element.playsInline = true; element.controls = true;
                    } else {
                        element = document.createElement('img');
                        element.onerror = (e) => { statusLabel.textContent = "Error: Image load failed."; };
                        element.onload = () => { finishLoad(); };
                        element.src = path;
                    }
                    container.innerHTML = '';
                    container.appendChild(element);
                });

                function finishLoad() {
                    statusLabel.textContent = (isData ? "File successfully inlined via Base64" : path.split('/').pop()) + " (Auto-loaded)";
                    statusLabel.style.color = "#4CAF50";
                    if (isData) {
                       const actualName = "{{RAW_NAME}}";
                       if(actualName && actualName !== "{{" + "RAW_NAME" + "}}") statusLabel.textContent = actualName;
                    }
                }
            } catch (e) {
                statusLabel.textContent = "Loader Error: " + e.message;
            }
        }

        // AUTO_LOAD_TRIGGER
        window.addEventListener('load', () => {
             // Show upload box only if no auto-load
            const TARGET = "###INJECT_BASE64_URI###";
            if (TARGET && TARGET !== "###" + "INJECT_BASE64_URI" + "###" && TARGET.length > 10) {
                loadFileFromPath(TARGET);
            } else {
                document.getElementById('upload-box').style.display = 'inline-block';
            }
        });

        // drag-and-drop support
        document.body.addEventListener('dragover', e => e.preventDefault());
        document.body.addEventListener('drop', e => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if (file) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
                fileInput.dispatchEvent(new Event('change'));
            }
        });
    </script>
</body>
</html>"""


def open_alpha_tester(filepath=None):
    """Generate the transparency-test HTML in %TEMP% and open it in the
    user's default browser. If ``filepath`` points at an existing GIF /
    WebP, we inline-encode it as base64 and bake it into the page so the
    browser doesn't trip on file:// CORS — the same trick v2.7 used. With
    no file we leave the manual upload box visible.

    Returns ``True`` on success, ``False`` if anything went wrong (which
    we surface via QMessageBox in the caller). The function NEVER raises:
    a failed alpha tester should not crash the main app."""
    try:
        temp_dir = tempfile.gettempdir()
        tester_path = os.path.join(temp_dir, "MakeAGIF_AlphaTester.html")
        html_content = ALPHA_TESTER_HTML

        if filepath and os.path.exists(filepath):
            ext = os.path.splitext(filepath)[1].lower()
            mime = "image/webp" if ext == ".webp" else (
                "image/gif" if ext == ".gif" else "video/webm"
            )
            with open(filepath, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")
            data_uri = f"data:{mime};base64,{b64_data}"
            html_content = html_content.replace("###INJECT_BASE64_URI###", data_uri)

            raw_path = filepath.replace("\\", "/")
            html_content = html_content.replace("{{RAW_PATH}}", raw_path)
            html_content = html_content.replace("{{RAW_NAME}}", os.path.basename(filepath))

        with open(tester_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Path.as_uri() builds a correct file:// URI on every platform
        # (Windows drive letters AND POSIX absolute paths) — avoids the
        # "file:///" + path hack that produced a malformed file:////... URI
        # for macOS/Linux absolute paths.
        webbrowser.open(Path(tester_path).as_uri())
        return True
    except Exception:
        return False


# --- Stylesheet ---
GLOBAL_STYLE = f"""
    QMainWindow {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; }}
    QWidget {{ font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; font-size: 11px; color: {COLOR_TEXT}; }}
    
    QGroupBox {{ 
        color: {COLOR_ACCENT}; 
        font-weight: bold; 
        border: 1px solid {COLOR_BORDER}; 
        margin-top: 20px; 
        border-radius: 4px; 
        padding-top: 15px;
        background: {COLOR_BG}; 
    }}
    QGroupBox::title {{ 
        subcontrol-origin: margin; 
        subcontrol-position: top left; 
        left: 10px; 
        padding: 0 5px; 
        background-color: {COLOR_BG}; 
    }}

    /* Buttons - Premiere Style Flat */
    QPushButton {{ 
        background-color: {COLOR_PANEL}; 
        color: {COLOR_TEXT_BRIGHT}; 
        border: 1px solid #333; 
        border-radius: 3px; 
        padding: 5px 15px; 
        font-weight: 600; 
    }}
    QPushButton:hover {{ 
        background-color: #333; 
        border-color: #555; 
    }}
    QPushButton:pressed {{ 
        background-color: {COLOR_ACCENT}; 
        border: 1px solid {COLOR_ACCENT}; 
        color: white; 
    }}
    QPushButton:disabled {{ 
        background-color: {COLOR_BG}; 
        color: #333; 
        border-color: #222; 
    }}
    
    /* Toggle Buttons (Radio-like behavior) */
    QPushButton:checked {{ 
        background-color: {COLOR_ACCENT}; 
        color: white; 
        border: 1px solid {COLOR_ACCENT_HOVER}; 
    }}

    QLineEdit, QSpinBox, QDoubleSpinBox {{ 
        background-color: {COLOR_PANEL}; 
        color: {COLOR_TEXT_BRIGHT}; 
        border: 1px solid #333; 
        border-radius: 2px; 
        padding: 4px; 
        selection-background-color: {COLOR_ACCENT}; 
    QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background-color: {COLOR_BG};
        color: #555;
        border: 1px solid #222;
    }}

    /* Checkboxes — Standardized SQUARE indicators across the whole app */
    QCheckBox {{ color: {COLOR_TEXT_BRIGHT}; spacing: 8px; font-weight: bold; font-size: 12px; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border-radius: 3px;
        border: 2px solid #ddd;
        background-color: #333;
    }}
    QCheckBox::indicator:hover {{ border-color: {COLOR_ACCENT}; }}
    QCheckBox::indicator:checked {{
        background-color: {COLOR_ACCENT};
        border: 2px solid #fff;
    }}
    QCheckBox::indicator:disabled {{
        background-color: #1a1a1a;
        border: 2px solid #333;
    }}

    /* Tabs */
    QTabWidget::pane {{ border: 1px solid {COLOR_BORDER}; background: {COLOR_BG}; }}
    QTabBar::tab {{ 
        background: {COLOR_BG}; 
        color: {COLOR_TEXT}; 
        padding: 8px 20px; 
        border-bottom: 2px solid {COLOR_BORDER}; 
        font-weight: 600; 
    }}
    QTabBar::tab:selected {{ 
        color: {COLOR_TEXT_BRIGHT}; 
        border-bottom: 2px solid {COLOR_ACCENT}; 
        background: {COLOR_PANEL}; 
    }}
    
    /* Table */
    QTableWidget {{ 
        background-color: {COLOR_PANEL}; 
        gridline-color: {COLOR_BORDER}; 
        color: {COLOR_TEXT_BRIGHT}; 
        border: none;
        selection-background-color: {COLOR_SELECT}; 
        selection-color: {COLOR_TEXT_BRIGHT};
    }}
    /* Keep the row highlight visible even when the table loses focus
       (e.g. user clicks the right-side settings panel) so it's always
       clear which task is being edited. */
    QTableWidget::item:selected {{ 
        background-color: {COLOR_SELECT}; 
        color: {COLOR_TEXT_BRIGHT};
    }}
    QTableWidget::item:selected:!active {{ 
        background-color: {COLOR_SELECT}; 
        color: {COLOR_TEXT_BRIGHT};
    }}
    QTableWidget::item:selected:!focus {{ 
        background-color: {COLOR_SELECT}; 
        color: {COLOR_TEXT_BRIGHT};
    }}
    QHeaderView::section {{ 
        background-color: #1f1f1f; 
        color: {COLOR_TEXT}; 
        padding: 5px; 
        border: none; 
        border-right: 1px solid #333;
        font-weight: bold; 
        text-transform: uppercase; 
        font-size: 10px; 
    }}
    QScrollBar:vertical {{ 
        background: {COLOR_BG}; 
        width: 10px; 
        margin: 0px; 
    }}
    QScrollBar::handle:vertical {{ 
        background: #333; 
        min-height: 20px; 
        border-radius: 5px; 
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    
    QProgressBar {{
        border: 1px solid #444;
        border-radius: 2px;
        text-align: center;
        color: white;
        background: #111;
    }}
    /* Format Buttons Specific - Stronger Visuals */
    QPushButton#fmt_btn {{ font-size: 12px; height: 30px; border: 1px solid #444; }}
    QPushButton#fmt_btn:checked {{ 
        background-color: {COLOR_ACCENT}; 
        color: white; 
        border: 2px solid white; 
        font-weight: 900;
    }}
    
    /* Small Tool Buttons */
    QPushButton#tool_btn {{
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 2px;
        padding: 2px;
        font-size: 14px;
        color: #888;
    }}
    QPushButton#tool_btn:hover {{ background-color: #333; color: white; border: 1px solid #555; }}
    QPushButton#tool_btn:pressed {{ background-color: {COLOR_ACCENT}; color: white; }}
"""

# --- Helpers ---
def _exe(name):
    """Append the .exe suffix on Windows only. Bundled Mac/Linux binaries
    are extension-less ('ffmpeg', not 'ffmpeg.exe'), so hardcoding '.exe'
    breaks the cross-platform tools/ folder convention."""
    return f"{name}.exe" if os.name == "nt" else name


def _bundle_root():
    """Folder that holds the running app entry (script, .exe, or .app MacOS binary)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _user_presets_dir():
    """Where the editable preset library lives.

    * Windows / Linux: next to the executable (portable) or the script (dev),
      so the user can find and share presets right beside the app.
    * macOS frozen .app: writing inside ``Foo.app/Contents/MacOS`` is hidden
      from Finder and read-only once the app is in /Applications or signed,
      so we use the standard per-user location instead.
    """
    if getattr(sys, "frozen", False) and sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/MakeAGIF")
        return os.path.join(base, "presets")
    return os.path.join(_bundle_root(), "presets")


def get_tool_path(name):
    """Locate an external CLI tool, preferring a bundled copy under
    ./tools/ (or PyInstaller's MEIPASS / .app MacOS folder when frozen),
    falling back to PATH lookup. `name` should be the EXTENSION-LESS base
    name; we add platform-correct suffix via _exe()."""
    fname = _exe(name)
    candidates = [os.path.join(_bundle_root(), "tools", fname)]
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, "tools", fname))
    for p in candidates:
        if os.path.isfile(p):
            return p
    return fname


def get_optional_tool_path(name):
    """Like get_tool_path but returns None if the tool is not bundled/found on disk.

    Use for optional tools (ImageMagick) so we never treat the bare name
    'magick' as available when only PATH might resolve it inconsistently."""
    p = get_tool_path(name)
    return p if os.path.isfile(p) else None


def open_path_in_os(path):
    """Cross-platform "open this folder/file in the OS file manager / default
    app". Centralized so we don't sprinkle os.name/sys.platform branches
    every time we want to launch something. Returns True on success."""
    try:
        if os.name == 'nt':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


FFMPEG_PATH = get_tool_path("ffmpeg")
FFPROBE_PATH = get_tool_path("ffprobe")  # used for VFR detection (ffmpeg
                                          # stderr doesn't expose r/avg
                                          # frame rate separately)
GIFSKI_PATH = get_tool_path("gifski")
MAGICK_PATH = get_optional_tool_path("magick")  # WebP+alpha (Windows bundle)
# macOS WebP encoder: the official, statically-linked libwebp tool. Unlike the
# Homebrew `magick` binary (which needs external delegates.xml + coder modules
# that don't ship with a copied binary), img2webp is fully self-contained and
# also gives exact millisecond frame timing.
IMG2WEBP_PATH = get_optional_tool_path("img2webp")


def _ffmpeg_has_encoder(name):
    """Return True if the bundled ffmpeg advertises the given encoder.

    The macOS Homebrew ffmpeg we bundle is NOT always built with
    --enable-libwebp, so `-c:v libwebp` dies with "Unknown encoder 'libwebp'".
    We probe once at startup so the WebP path can fall back to ImageMagick when
    the encoder is missing. Windows ffmpeg ships libwebp, so this stays True
    there and the encode path is byte-for-byte unchanged."""
    try:
        flags = 0x08000000 if os.name == 'nt' else 0
        out = subprocess.run(
            [FFMPEG_PATH, "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=15, creationflags=flags,
        )
        return name in (out.stdout or "")
    except Exception:
        return False


# Probed once: does THIS ffmpeg build have the libwebp encoder? Drives the
# WebP fallback to ImageMagick on builds that don't (notably the macOS bundle).
FFMPEG_HAS_LIBWEBP = _ffmpeg_has_encoder("libwebp")


def _parse_rational(s):
    """Parse ffprobe's "num/den" rational strings into a float, returning
    None on garbage (negative denominator, '0/0' which ffprobe emits for
    unknown rates, etc.)."""
    if not s or "/" not in s:
        try:
            v = float(s)
            return v if v > 0 else None
        except (TypeError, ValueError):
            return None
    try:
        num, den = s.split("/", 1)
        num = int(num); den = int(den)
        if den <= 0 or num <= 0:
            return None
        return num / den
    except (ValueError, TypeError):
        return None


def _probe_vfr(path):
    """Return (is_vfr: bool, r_frame_rate: float|None, avg_frame_rate: float|None)
    by asking ffprobe directly. We compare:
      - r_frame_rate  : the declared / nominal stream rate
      - avg_frame_rate: total_frames / duration computed from packets
    Significant divergence (>1.5%) means the source is variable-framerate
    and ALL frame-perfect math (1/fps step, frame quantization, NLE TC) is
    inherently approximate. We don't try to fix it — just flag it so the
    user knows their trim may drift by a frame or two on long clips.

    Falls back silently to (False, None, None) if ffprobe is missing or
    fails — better to skip the warning than to block the dialog."""
    if not os.path.exists(path):
        return (False, None, None)
    try:
        cmd = [
            FFPROBE_PATH, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate,avg_frame_rate",
            "-of", "default=noprint_wrappers=1",
            path,
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=8,
            creationflags=0x08000000 if os.name == 'nt' else 0,
        )
        if proc.returncode != 0:
            return (False, None, None)
        out = proc.stdout
        m_r = re.search(r"r_frame_rate\s*=\s*(\S+)", out)
        m_a = re.search(r"avg_frame_rate\s*=\s*(\S+)", out)
        r_fps = _parse_rational(m_r.group(1)) if m_r else None
        a_fps = _parse_rational(m_a.group(1)) if m_a else None
        if r_fps is None or a_fps is None:
            return (False, r_fps, a_fps)
        # Threshold: 1.5% relative diff. Tighter than 1% (which catches
        # 23.976 vs 24 cleanly as VFR, false positive) and looser than 3%
        # (which would miss subtle drift). 1.5% gracefully handles the
        # 29.97 ↔ 30 / 23.976 ↔ 24 cases as CFR while still catching real
        # mobile-cam VFR which usually shows >>5% divergence.
        diff = abs(r_fps - a_fps) / max(r_fps, a_fps)
        return (diff > 0.015, r_fps, a_fps)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return (False, None, None)
    except Exception:
        return (False, None, None)


def _probe_stream_frame_stats(path):
    """ffprobe: r_frame_rate, nb_frames, stream duration (best-effort)."""
    if not os.path.exists(path):
        return (None, 0, 0.0)
    try:
        cmd = [
            FFPROBE_PATH, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate,nb_frames,duration",
            "-of", "default=noprint_wrappers=1",
            path,
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=8,
            creationflags=0x08000000 if os.name == 'nt' else 0,
        )
        if proc.returncode != 0:
            return (None, 0, 0.0)
        out = proc.stdout
        m_r = re.search(r"r_frame_rate\s*=\s*(\S+)", out)
        m_nb = re.search(r"nb_frames\s*=\s*(\d+)", out)
        m_d = re.search(r"duration\s*=\s*([\d.]+)", out)
        r_fps = _parse_rational(m_r.group(1)) if m_r else None
        nb = int(m_nb.group(1)) if m_nb else 0
        dur = float(m_d.group(1)) if m_d else 0.0
        return (r_fps, nb, dur)
    except Exception:
        return (None, 0, 0.0)


def _probe_specs_json(path):
    """PR2: gather every spec we need in ONE ffprobe JSON call instead of the
    legacy ``ffmpeg -i`` + 2× ffprobe (three processes). Returns a fully
    populated specs dict on success, or None to fall back to the legacy path.

    VFR detection uses the same r_frame_rate vs avg_frame_rate comparison
    (>1.5% divergence) as _probe_vfr, so the warning banner behaves identically.
    """
    if not os.path.exists(path):
        return None
    try:
        cmd = [
            FFPROBE_PATH, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,duration"
            ":format=duration",
            "-of", "json",
            path,
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
            creationflags=0x08000000 if os.name == 'nt' else 0,
        )
        if proc.returncode != 0 or not proc.stdout:
            return None
        data = json.loads(proc.stdout)
        streams = data.get("streams") or []
        if not streams:
            return None
        st = streams[0]
        w = int(st.get("width") or 0)
        h = int(st.get("height") or 0)
        r_fps = _parse_rational(st.get("r_frame_rate"))
        a_fps = _parse_rational(st.get("avg_frame_rate"))
        fps = r_fps or a_fps
        if w <= 0 or h <= 0 or not fps or fps <= 0:
            return None
        # Duration: prefer container/format, fall back to the stream entry.
        dur = 0.0
        fmt = data.get("format") or {}
        for cand in (fmt.get("duration"), st.get("duration")):
            try:
                dv = float(cand)
            except (TypeError, ValueError):
                continue
            if dv > 0:
                dur = dv
                break
        # Frame count: real nb_frames if present, else derive from duration.
        try:
            nb = int(st.get("nb_frames") or 0)
        except (TypeError, ValueError):
            nb = 0
        t_frames = nb if nb > 0 else (int(round(dur * fps)) if dur > 0 else 0)
        is_vfr = False
        if r_fps and a_fps and max(r_fps, a_fps) > 0:
            is_vfr = (abs(r_fps - a_fps) / max(r_fps, a_fps)) > 0.015
        if dur > 0:
            m, s = divmod(int(dur), 60)
            h_, m = divmod(m, 60)
            dur_str = f"{h_:02d}:{m:02d}:{s:02d}"
        else:
            dur_str = "0:00"
        return {
            "w": w, "h": h, "fps": float(fps),
            "dur": dur_str, "duration": dur, "t_frames": t_frames,
            "err": False, "is_vfr": is_vfr, "r_fps": r_fps, "avg_fps": a_fps,
            "fps_display": format_fps_for_display(fps),
        }
    except Exception:
        return None


def get_video_specs(path):
    specs = {"w": 0, "h": 0, "fps": 0.0, "dur": "0:00", "duration": 0.0,
             "t_frames": 0, "err": True,
             # VFR detection results — populated below; kept on specs so
             # downstream code (trim dialog, engine logs) can read them
             # without re-probing.
             "is_vfr": False, "r_fps": None, "avg_fps": None}
    if not os.path.exists(path): return specs

    # PR2 fast path: a single ffprobe JSON call. Falls through to the legacy
    # ffmpeg+ffprobe pipeline below if ffprobe is missing or returns nothing
    # usable (keeps robustness on odd containers ffprobe can't summarise).
    fast = _probe_specs_json(path)
    if fast is not None:
        return fast

    proc = None
    try:
        cmd = [FFMPEG_PATH, "-hide_banner", "-i", path]
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, creationflags=0x08000000 if os.name == 'nt' else 0)
        try:
            # Hard timeout so a corrupt file or hung ffmpeg can't lock the UI thread.
            _, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
                proc.communicate(timeout=2)
            except Exception:
                pass
            return specs
        m_r = re.search(r",\s*(\d{2,})x(\d{2,})", err)
        if m_r: specs["w"], specs["h"] = int(m_r.group(1)), int(m_r.group(2))
        m_f = re.search(r"(\d+(?:\.\d+)?)\s*fps", err)
        if m_f: specs["fps"] = float(m_f.group(1))
        m_d = re.search(r"Duration:\s*(\d{2}:\d{2}:\d{2})\.(\d{2})", err)
        if m_d:
            specs["dur"] = m_d.group(1)
            h, m, s = map(int, m_d.group(1).split(':'))
            dur_sec = h*3600 + m*60 + s + int(m_d.group(2))/100
            specs["duration"] = dur_sec
            specs["t_frames"] = int(dur_sec * specs["fps"])
        if specs["w"] > 0: specs["err"] = False
    except Exception:
        # Ensure no zombie ffmpeg lingers on unexpected failures.
        if proc and proc.poll() is None:
            try: proc.kill()
            except Exception: pass

    # VFR check is best-effort — failures here don't invalidate specs, we
    # just leave is_vfr=False (and the trim dialog won't show the banner).
    if not specs["err"]:
        is_vfr, r_fps, a_fps = _probe_vfr(path)
        specs["is_vfr"] = is_vfr
        specs["r_fps"] = r_fps
        specs["avg_fps"] = a_fps
        pr_fps, pr_nb, pr_dur = _probe_stream_frame_stats(path)
        if pr_fps and pr_fps > 0:
            specs["fps"] = pr_fps
        if pr_nb > 0:
            specs["t_frames"] = pr_nb
        if pr_dur > 0:
            if specs["duration"] <= 0 or abs(specs["duration"] - pr_dur) > 0.25:
                specs["duration"] = pr_dur
                if pr_nb <= 0 and specs["fps"] > 0:
                    specs["t_frames"] = int(round(pr_dur * specs["fps"]))
        if specs["fps"] > 0:
            specs["fps_display"] = format_fps_for_display(specs["fps"])
    return specs

def parse_trim_to_seconds(val, default=0.0, fps=None):
    """Parse a trim value to float seconds. Accepts:
      - plain seconds ('5.234')
      - HH:MM:SS[.ms]  ('00:00:05.20')
      - HH:MM:SS:FF    ('00:00:05:12') — NLE-style, requires `fps`
      - MM:SS variants
    Returns `default` if unparseable."""
    if val is None: return default
    s = str(val).strip()
    if not s: return default
    try:
        return float(s)
    except ValueError:
        pass
    parts = s.split(":")
    try:
        if len(parts) == 4:
            # NLE timecode HH:MM:SS:FF. We treat HH:MM:SS as INTEGER-fps TC (i.e.
            # 30 seconds at 29.97 fps == 30*30 = 900 frames, NOT 30*29.97 = 899.1
            # frames). This MUST mirror format_seconds_as_tc_frames exactly,
            # otherwise the format→parse round-trip drifts by ~2-3 frames at
            # non-integer framerates and ffmpeg seeks to the wrong PTS — which
            # is precisely the "leaked frame" trim bug.
            if fps and float(fps) > 0:
                fps_f = float(fps)
                fps_int = nle_tc_fps_int(fps_f)
                h, m, sec, ff = parts
                total_frames = (int(h) * 3600 + int(m) * 60 + int(sec)) * fps_int + int(ff)
                return total_frames / fps_f
            # Otherwise treat trailing as fractional seconds (best-effort fallback).
            h, m, sec, ff = parts
            return int(h) * 3600 + int(m) * 60 + int(sec) + int(ff) / 100.0
        if len(parts) == 3:
            h, m, sec = parts
            return int(h) * 3600 + int(m) * 60 + float(sec)
        if len(parts) == 2:
            m, sec = parts
            return int(m) * 60 + float(sec)
    except ValueError:
        pass
    return default

def format_seconds_as_tc(sec):
    """Render float seconds as HH:MM:SS.uuuuuu (microseconds, 6 decimals).
    Returns '' for None/invalid. This is the storage format passed verbatim to
    ffmpeg `-ss/-to`. Microsecond precision is needed because frame-quantized
    values at non-integer framerates fall between milliseconds — e.g. for
    29.97 fps each frame is 33.3667 ms wide and millisecond-rounding can drift
    the seek by enough to land in the previous/next frame, producing an
    off-by-one on the first or last extracted frame."""
    if sec is None: return ""
    try: sec = float(sec)
    except (ValueError, TypeError): return ""
    if sec <= 0: return "00:00:00"
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    # Width = 9 (e.g. "09.869800"), precision = 6.
    return f"{int(h):02d}:{int(m):02d}:{s:09.6f}"

def format_seconds_as_tc_frames(sec, fps):
    """Render float seconds as HH:MM:SS:FF (NLE-style timecode using frames).
    Used for ALL user-facing display — table column, manual In/Out fields, dialog labels.
    Returns '' for None/invalid. Falls back to centisecond format if fps is missing/zero."""
    if sec is None: return ""
    try:
        sec = float(sec)
        fps_f = float(fps or 0)
    except (ValueError, TypeError):
        return ""
    if fps_f <= 0:
        return format_seconds_as_tc(sec)
    if sec <= 0: return "00:00:00:00"
    total_frames = int(round(sec * fps_f))
    fps_int = nle_tc_fps_int(fps_f)
    ff = total_frames % fps_int
    total_seconds = total_frames // fps_int
    s = total_seconds % 60
    m = (total_seconds // 60) % 60
    h = total_seconds // 3600
    return f"{h:02d}:{m:02d}:{s:02d}:{ff:02d}"


def source_frame_index_from_sec(sec, fps, max_idx=None, *, rounding="round"):
    """0-based source frame index for *sec*.

    rounding:
      - ``round`` — default; TC round-trip and export alignment.
      - ``floor`` — QMediaPlayer ms → frame (never round *into* the next frame).
    """
    if not fps or float(fps) <= 0:
        return 0
    x = float(sec) * float(fps)
    if rounding == "floor":
        fi = int(math.floor(x + 1e-9))
    else:
        fi = int(round(x))
    if max_idx is not None:
        fi = max(0, min(fi, int(max_idx)))
    return fi


def format_fps_for_display(fps):
    """Human/NLE fps label (23.98, 29.97, 24…). Math keeps full ``fps`` precision."""
    if fps is None or float(fps) <= 0:
        return "?"
    f = float(fps)
    standards = (
        (23.976, "23.98"),
        (24.0, "24"),
        (25.0, "25"),
        (29.97, "29.97"),
        (30.0, "30"),
        (48.0, "48"),
        (50.0, "50"),
        (59.94, "59.94"),
        (60.0, "60"),
    )
    label, ref = min(
        ((lbl, r) for r, lbl in standards),
        key=lambda pair: abs(pair[1] - f),
    )
    if abs(ref - f) / max(f, 0.001) < 0.02:
        return label
    if abs(f - round(f)) < 0.05:
        return str(int(round(f)))
    return f"{f:.2f}".rstrip("0").rstrip(".")


def nle_tc_fps_int(fps):
    """Integer fps for HH:MM:SS:FF fields (23.976 → 24, 29.97 → 30)."""
    if fps is None or float(fps) <= 0:
        return 24
    f = float(fps)
    pairs = (
        (23.976, 24), (24.0, 24), (25.0, 25), (29.97, 30), (30.0, 30),
        (48.0, 48), (50.0, 50), (59.94, 60), (60.0, 60),
    )
    ref, tc = min(pairs, key=lambda p: abs(p[0] - f))
    if abs(ref - f) / max(f, 0.001) < 0.02:
        return tc
    return max(1, int(round(f)))


def format_frame_index_as_tc(fi, fps):
    """HH:MM:SS:FF from a 0-based source frame index (NLE integer-fps TC grid)."""
    if fps is None or float(fps) <= 0:
        return "00:00:00:00"
    fps_int = nle_tc_fps_int(fps)
    fi = max(0, int(fi))
    ff = fi % fps_int
    total_seconds = fi // fps_int
    s = total_seconds % 60
    m = (total_seconds // 60) % 60
    h = total_seconds // 3600
    return f"{h:02d}:{m:02d}:{s:02d}:{ff:02d}"


def sec_from_source_frame_index(fi, fps):
    """PTS at the start of source frame *fi* (export / preview use this)."""
    if not fps or float(fps) <= 0:
        return float(fi)
    return int(fi) / float(fps)


def ms_start_of_frame(fi, fps):
    """QMediaPlayer position (ms) at the start of source frame *fi*."""
    if not fps or float(fps) <= 0:
        return max(0, int(fi))
    # floor — round() can map adjacent source frames to the same integer ms.
    return int(math.floor(sec_from_source_frame_index(fi, fps) * 1000.0 + 1e-6))


def ms_last_included_frame(fi, fps):
    """Last ms that still belongs to included frame *fi* (before *fi+1*)."""
    if not fps or float(fps) <= 0:
        return max(0, int(fi))
    next_ms = ms_start_of_frame(int(fi) + 1, fps)
    return max(0, next_ms - 1)


def exclusive_out_sec_from_included_frame(last_incl_fi, fps, cap_sec=None):
    """Exclusive OUT for [IN, OUT) when *last_incl_fi* is the last kept frame."""
    out_sec = sec_from_source_frame_index(int(last_incl_fi) + 1, fps)
    if cap_sec is not None:
        out_sec = min(out_sec, float(cap_sec))
    return out_sec


def last_included_frame_index_from_out(out_sec, fps, max_idx=None):
    """Last included frame index from an exclusive OUT timestamp."""
    if not fps or float(fps) <= 0:
        return 0
    # out_sec = (last_incl + 1) / fps — ceil finds the exclusive boundary frame.
    out_excl = int(math.ceil(float(out_sec) * float(fps) - 1e-9))
    last_fi = max(0, out_excl - 1)
    if max_idx is not None:
        last_fi = min(last_fi, int(max_idx))
    return last_fi


def inclusive_display_sec_from_exclusive_out(out_sec, fps, max_idx=None):
    """PTS of the last included frame (what the user expects as 'OUT')."""
    fi = last_included_frame_index_from_out(out_sec, fps, max_idx)
    return sec_from_source_frame_index(fi, fps)


def parse_trim_end_display_to_exclusive(sec_display, fps, cap_sec=None):
    """Convert UI/manual OUT (last included frame) → exclusive OUT for ffmpeg."""
    if sec_display is None:
        return None
    fi = source_frame_index_from_sec(sec_display, fps)
    return exclusive_out_sec_from_included_frame(fi, fps, cap_sec)


def out_exclusive_frame_index(out_sec, fps, max_idx=None):
    """Frame index at the red OUT marker (first frame NOT in the trim)."""
    fi = source_frame_index_from_sec(out_sec, fps, max_idx)
    if max_idx is not None:
        fi = min(fi, int(max_idx))
    return max(0, fi)


def scene_cut_frame_index_from_detection(sec, fps, max_idx=None):
    """Map ffmpeg scene-detection PTS → first frame of the *next* plan (NLE marker).

    ``select=gt(scene)`` + ``showinfo`` typically fires on the last frame of the
    outgoing shot. NLE markers belong on the first frame of the incoming shot (+1).
    Uses floor (not round) so 23.976 does not drift forward a frame.
    """
    if not fps or float(fps) <= 0:
        return 0
    fi = int(math.floor(float(sec) * float(fps) + 1e-6))
    fi += 1
    if max_idx is not None:
        fi = min(fi, int(max_idx))
    return max(1, fi)


def frame_index_from_tc_text(text, fps, max_idx=None):
    """Parse strict ``HH:MM:SS:FF`` (NLE grid) → 0-based source frame index, or None."""
    if text is None:
        return None
    raw = str(text).strip().replace(";", ":")
    m = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2}):(\d{2})", raw)
    if not m:
        return None
    h, mi, s, ff = (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
    if mi > 59 or s > 59:
        return None
    if not fps or float(fps) <= 0:
        return None
    fps_int = nle_tc_fps_int(fps)
    if ff >= fps_int:
        return None
    fi = (h * 3600 + mi * 60 + s) * fps_int + ff
    if max_idx is not None:
        fi = max(0, min(int(fi), int(max_idx)))
    return fi


class NLETimecodeEdit(QLineEdit):
    """Fixed ``HH:MM:SS:FF`` field (Premiere-style). Enter commits; invalid → revert."""

    commit_requested = Signal()

    def __init__(self, parent=None, fps=25.0, text="00:00:00:00"):
        super().__init__(parent)
        self._fps = float(fps or 25)
        self._max_idx = None
        self._last_committed = "00:00:00:00"
        self.setInputMask("00:00:00:00;1")
        self.setAlignment(Qt.AlignCenter)
        self.setCursorPosition(0)
        self.set_committed_text(text)

    def set_fps(self, fps, max_idx=None):
        self._fps = float(fps or 25)
        self._max_idx = max_idx

    def set_committed_text(self, text):
        tc = text if frame_index_from_tc_text(text, self._fps, self._max_idx) is not None else "00:00:00:00"
        self._last_committed = tc
        self.blockSignals(True)
        self.setText(tc)
        self.blockSignals(False)

    def revert(self):
        self.set_committed_text(self._last_committed)

    def release_keyboard_focus(self):
        """Leave the masked field so ←/→, Space, JKL, and timeline work again."""
        self.deselect()
        self.clearFocus()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.commit_requested.emit()
            self.release_keyboard_focus()
            event.accept()
            return
        if event.key() == Qt.Key_Escape:
            self.revert()
            self.release_keyboard_focus()
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        # Defer so the click target receives focus first (click-outside works).
        QTimer.singleShot(0, self._deferred_focus_out)
        super().focusOutEvent(event)

    def _deferred_focus_out(self):
        if self.hasFocus():
            return
        txt = self.text()
        if txt == self._last_committed:
            return
        if frame_index_from_tc_text(txt, self._fps, self._max_idx) is not None:
            self.commit_requested.emit()
        else:
            self.revert()


def calculate_target_dims(specs, vals):
    w_src, h_src = specs.get('w', 0), specs.get('h', 0)
    if w_src == 0: return 0, 0
    ar = w_src / h_src
    
    mode = vals.get("dim_mode", "Original")
    
    if mode == "Original": return w_src, h_src
    
    if mode == "Percentage (%)":
        p = max(0.01, float(vals.get("dim_perc", 100)) / 100.0)
        return max(1, round(w_src * p)), max(1, round(h_src * p))
        
    if mode == "Lock Width":
        tw = max(1, int(vals.get("dim_w", 640)))
        return tw, max(1, round(tw / ar))
        
    if mode == "Lock Height":
        th = max(1, int(vals.get("dim_h", 360)))
        return max(1, round(th * ar)), th
        
    if mode == "Manual WxH":
        return max(1, int(vals.get("dim_w", 640))), max(1, int(vals.get("dim_h", 360)))
        
    return w_src, h_src

# --- Worker Signals ---
class WorkerSignals(QObject):
    log = Signal(str)
    progress = Signal(int)       # 0-100
    status_text = Signal(str)    # Main status label
    step = Signal(str, str)      # (Icon, Text) for process step
    task_started = Signal(object)
    task_finished = Signal(object, bool, str)
    finished = Signal()
    error = Signal(str)
    # Iterative search telemetry: emitted ONCE per attempt during
    # run_iterative_search. A subscribing chart can plot the trajectory
    # of (size vs. target) over iterations to show convergence behavior.
    # Tuple shape: dict{
    #   "iter": int,             1-based attempt index
    #   "size": int,             produced file size in bytes
    #   "target": int,           target_size_bytes
    #   "lower": int, "upper": int,  acceptance bracket
    #   "fps": int, "quality": int,  encode params for that attempt
    #   "phase": str             "P1" or "P2" (for marker color in chart)
    # }
    iter_step = Signal(dict)
    # Lifecycle markers so the chart can clear/lock between runs.
    iter_started = Signal(dict)   # {"target": int, "lower": int, "upper": int}
    iter_finished = Signal(dict)  # {"winner": dict|None, "iterations": int}
    # Fired right BEFORE each encode begins, so the chart can announce
    # which configuration is currently being tested while the encode
    # runs (instead of only updating after the result lands via iter_step).
    # {
    #   "iter":  int,           cumulative attempt index (matches iter_step)
    #   "q":     int,           quality being tested
    #   "fps":   int,           framerate being tested
    #   "w":     int, "h": int, target output dims
    #   "phase": "P1" | "P2",   which search phase
    #   "via":   "bisect" | "secant" | "warm-cache",  how mid_q was picked
    # }
    iter_attempt_started = Signal(dict)

# --- Engine ---
class ConversionEngine:
    """Encapsulates all the heavy lifting logic, decoupled from UI widgets."""
    def __init__(self, signals, cancel_event):
        self.signals = signals
        self.cancel_event = cancel_event
        self.current_proc = None

    def log(self, msg): self.signals.log.emit(msg)

    def check_cancel(self):
        if self.cancel_event.is_set():
            if self.current_proc:
                try: self.current_proc.terminate(); self.current_proc.wait(0.5)
                except: pass
            raise InterruptedError("Cancelled by user")

    def run_cmd(self, cmd):
        # Normalize: drop None, stringify, then log the ORIGINAL command (with
        # the "*.png" pattern intact) so the console stays readable instead of
        # dumping hundreds of expanded frame paths.
        cmd = [str(x) for x in cmd if x is not None]
        cmd_str = ' '.join(f'"{x}"' if ' ' in x else x for x in cmd)
        self.log(f"  CMD: {cmd_str}")
        flags = 0x08000000 if os.name == 'nt' else 0
        # NEVER use shell=True here: on POSIX, Popen(list, shell=True) runs
        # `/bin/sh -c <list[0]> ...`, so only list[0] is the command — and the
        # bundled executable lives inside "MakeAGIF vX.app" (path WITH a space),
        # which /bin/sh would word-split → "No such file or directory". With
        # shell=False the argv is passed verbatim, so spaces are safe.
        #
        # Wildcard frame args ("*.png" for gifski, "f_*.png" for magick) need
        # platform-specific handling because WITHOUT a shell nobody expands them:
        #   * Windows  — gifski/magick expand the pattern THEMSELVES, and keeping
        #     the literal pattern keeps the command line short (avoids the
        #     ~32 KB CreateProcess limit on long clips). Pass it through.
        #   * macOS/Linux — gifski does NOT expand globs (its author confirms the
        #     shell normally does it), so we expand here into an explicit, sorted
        #     file list. POSIX ARG_MAX (~1 MB+) easily holds thousands of frames.
        run_list = cmd
        if os.name != 'nt':
            expanded = []
            for x in cmd:
                base = os.path.basename(x)
                if '*' in base or '?' in base:
                    d = os.path.dirname(x)
                    pattern = os.path.join(glob.escape(d), base) if d else base
                    matches = sorted(glob.glob(pattern))
                    expanded.extend(matches if matches else [x])
                else:
                    expanded.append(x)
            run_list = expanded
        self.current_proc = subprocess.Popen(
            run_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', creationflags=flags
        )
        
        while True:
            self.check_cancel()
            line = self.current_proc.stdout.readline()
            if not line and self.current_proc.poll() is not None: break
            if line: self.log(f"    {line.strip()}")
            
        rc = self.current_proc.poll()
        self.current_proc = None
        return rc

    @staticmethod
    def _settings_filename_suffix(fps, q, w, h, mode=None, prio=None, target_mb=None):
        """Compact, human-readable tag for the actual encode params.

        Leads with the optimization mode + priority + target-size
        prefix so re-encodes of the same source are immediately
        distinguishable when listed side by side. Format::

            _<MODE><TARGET>_Q<q>_F<fps>_<w>x<h>

        where ``<MODE>`` is one of:
          - ``BAL`` – AUTO + Balanced priority
          - ``QP``  – AUTO + Quality priority
          - ``FP``  – AUTO + FPS priority
          - ``MAN`` – MANUAL (fixed Q/F)

        ``<TARGET>`` is the AUTO mode target in MB (e.g. ``16M``,
        ``8M5`` for 8.5 MB) and is only emitted for AUTO modes.

        Examples:
          AUTO/Balanced @ 16 MB →  ``_BAL16M_Q72_F18_960x540``
          AUTO/Quality @ 8 MB   →  ``_QP8M_Q85_F12_960x540``
          AUTO/FPS @ 4 MB       →  ``_FP4M_Q70_F25_960x540``
          MANUAL                →  ``_MAN_Q90_F25_1920x1080``

        Backwards-compatible: if ``mode``/``prio``/``target_mb`` are
        omitted (older callers), the old ``_Q72_F18_960x540`` shape is
        produced — no MODE prefix at all."""
        # --- 1. MODE / PRIO / TARGET prefix --------------------------------
        prefix = None
        m = (mode or "").strip().upper()
        if m == "MANUAL":
            prefix = "MAN"
        elif m == "ITERATIVE":
            prio_code = "BAL"
            if prio:
                pl = str(prio).strip().lower()
                if pl in ("quality", "qual", "q", "qprio", "qp"):
                    prio_code = "QP"
                elif pl in ("fps", "f", "fprio", "fp"):
                    prio_code = "FP"
                elif pl in ("balanced", "bal", "mixed"):
                    prio_code = "BAL"
            if target_mb is not None:
                try:
                    tmb = float(target_mb)
                except (TypeError, ValueError):
                    tmb = None
                if tmb is not None and tmb > 0:
                    # Emit "16M" for ints, "8M5" for half-MB targets.
                    # Avoiding "." keeps the tag visually compact and
                    # filesystem-friendly (no special meaning).
                    if abs(tmb - round(tmb)) < 1e-3:
                        prefix = f"{prio_code}{int(round(tmb))}M"
                    else:
                        whole = int(tmb)
                        frac = round(tmb - whole, 2)
                        frac_s = f"{frac:.2f}".split(".", 1)[1].rstrip("0") or "0"
                        prefix = f"{prio_code}{whole}M{frac_s}"
                else:
                    prefix = prio_code
            else:
                prefix = prio_code

        # --- 2. Q / FPS / WxH (always) -------------------------------------
        try: fps_i = int(round(float(fps)))
        except Exception: fps_i = 0
        try: q_i = int(round(float(q)))
        except Exception: q_i = 0
        try: w_i = int(w); h_i = int(h)
        except Exception: w_i, h_i = 0, 0

        parts = []
        if prefix: parts.append(prefix)
        if q_i > 0: parts.append(f"Q{q_i}")
        if fps_i > 0: parts.append(f"F{fps_i}")
        if w_i > 0 and h_i > 0: parts.append(f"{w_i}x{h_i}")
        return ("_" + "_".join(parts)) if parts else ""

    def _inject_settings_suffix(self, path, fps, q, w, h, mode=None, prio=None, target_mb=None):
        """Return ``path`` with the settings suffix inserted before the
        extension. Idempotent: if the suffix is already present (e.g. the user
        re-runs the same task) we don't double-append. Collisions with an
        existing file get a ``_N`` disambiguator appended after the suffix."""
        suffix = self._settings_filename_suffix(fps, q, w, h, mode=mode, prio=prio, target_mb=target_mb)
        if not suffix:
            return path
        d = os.path.dirname(path)
        base, ext = os.path.splitext(os.path.basename(path))
        # Strip a trailing "_Optimized" base tag from
        # ``get_output_path`` so the final name reads cleanly as
        # ``clip_BAL16M_Q72_F18_960x540.webp`` instead of
        # ``clip_Optimized_BAL16M_...``. The MODE prefix in the suffix
        # already conveys "this was optimized".
        if base.endswith("_Optimized"):
            base = base[: -len("_Optimized")]
        # Idempotency: drop any pre-existing instance of the same suffix from
        # the base, so re-runs don't produce ``foo_BAL16M_Q72_..._BAL16M_Q72_...``.
        if base.endswith(suffix):
            base = base[: -len(suffix)]
        candidate = os.path.join(d, base + suffix + ext)
        # If the destination is the exact same file we already wrote, return
        # it as-is so the caller can no-op the rename.
        if os.path.normcase(os.path.abspath(candidate)) == os.path.normcase(os.path.abspath(path)):
            return path
        c = 1
        final = candidate
        while os.path.exists(final):
            final = os.path.join(d, f"{base}{suffix}_{c}{ext}")
            c += 1
        return final

    def get_output_path(self, inp, fmt, force_dir=None):
        fmt_upper = fmt.upper()
        ext = ".gif" if fmt_upper == "GIF" else ".webp"
        # If force_dir is a FULL file path (with .gif/.webp), the user picked an
        # explicit name in the Save-As dialog — use it verbatim. Auto-suffix
        # only if a file with that exact name already exists, to avoid clobbering.
        if force_dir:
            forced_ext = os.path.splitext(force_dir)[1].lower()
            if forced_ext in (".gif", ".webp"):
                # Coerce to the user's currently-active format if mismatched
                # (e.g. they picked a path before flipping GIF↔WebP).
                if forced_ext != ext:
                    force_dir = os.path.splitext(force_dir)[0] + ext
                base, _ = os.path.splitext(force_dir)
                final = force_dir
                c = 1
                while os.path.exists(final):
                    final = f"{base}_{c}{ext}"
                    c += 1
                return final
        d = force_dir if force_dir else os.path.dirname(inp)
        n = os.path.splitext(os.path.basename(inp))[0]
        c = 1
        fn = f"{n}_Optimized{ext}"
        while os.path.exists(os.path.join(d, fn)):
            fn = f"{n}_Optimized_{c}{ext}"
            c += 1
        return os.path.join(d, fn)
        
    def start_task(self, task):
        try:
            self.signals.progress.emit(0)
            self.log(f"Starting Task: {task.filename}")
            
            p = task.vals
            tw, th = calculate_target_dims(task.specs, p)
            self.log(f"  Target Resolution: {tw}x{th}")
            
            target_mb = p.get("target", 16.0)
            low_m = p.get("low", 1.5)
            up_m = p.get("up", 0.5)
            
            out_path = self.get_output_path(task.path, p["format"], force_dir=p.get("_force_out_dir"))
            dest_dir = os.path.dirname(out_path)
            base_name = os.path.splitext(os.path.basename(task.path))[0]
            keep_iter = bool(p.get("keep_iterations", False))
            # When the user opts in to "keep iterations", we use a stable, predictable
            # folder next to the source so the next run can discover and reuse files.
            # Otherwise we use an ephemeral temp folder that is wiped after the task.
            # Read-only source locations (e.g. mounted drives, network shares
            # without write perms) would crash os.makedirs. We fall back to
            # a temp folder there and downgrade keep_iter so the post-job
            # cleanup branch wipes it — better than hard-failing the render.
            if keep_iter:
                iter_folder = os.path.join(dest_dir, f"{base_name}_ITERATIONS")
                try:
                    os.makedirs(iter_folder, exist_ok=True)
                except OSError as e:
                    self.log(f"  ⚠ Could not create '{iter_folder}' ({e}). Falling back to temp folder; cache disabled this run.")
                    iter_folder = tempfile.mkdtemp(prefix=f"{base_name}_iter_")
                    keep_iter = False
            else:
                iter_folder = tempfile.mkdtemp(prefix=f"{base_name}_iter_")
            
            common = {
                "input_path": task.path,
                "source_basename_no_ext": base_name,
                "output_format": p["format"].upper(),  # normalize to uppercase (GIF/WEBP)
                "has_alpha": p.get("alpha", False),
                "play_once": p.get("play_once", False),
                "faster_encode": p.get("fast", False),
                "webp_lossless": p.get("lossless", False),
                "iter_attempts_main_folder": iter_folder, 
                "iter_keep": keep_iter,
                # Short hash that namespaces iteration filenames so the
                # knowledge cache never confuses samples from different
                # trim / alpha / lossless configs of the same source.
                # Computed from the same param dict so the iter loop
                # below and `_build_knowledge_cache` agree on the tag.
                "attempt_signature": self._attempt_signature({
                    "trim_start":   p.get("trim_start", ""),
                    "trim_end":     p.get("trim_end", ""),
                    "has_alpha":    p.get("alpha", False),
                    "webp_lossless": p.get("lossless", False),
                }),
                # User-overridable cache root (Advanced → Cache Folder). Falls back
                # to the OS temp directory when nothing is configured. We tolerate
                # an unwritable override by reverting silently to the default.
                "cache_dir": (lambda d: d if d and os.path.isdir(d) else DEFAULT_CACHE_DIR)(p.get("_force_cache_dir")),
                # Forwarded for downstream sanity checks / logs. Trim math itself
                # uses exclusive OUT (duration = out - in), no padding.
                "source_fps": float(task.specs.get("fps", 0) or 0),
                "target_mb": target_mb,
                "strict_lower_bound": (target_mb - low_m) * 1024 * 1024,
                "strict_upper_bound": (target_mb + up_m) * 1024 * 1024,
                "target_size_bytes": target_mb * 1024 * 1024,
                # Trim points must propagate so generate_animation can pass -ss/-to to ffmpeg
                # AND so the cache key below distinguishes trimmed vs full-source extractions.
                "trim_start": p.get("trim_start", ""),
                "trim_end": p.get("trim_end", ""),
            }
            
            final_res = None
            
            self.log(f"  Mode: {p['mode']}  Format: {p.get('format','?').upper()}")
            if p["mode"] == "ITERATIVE":
                final_res = self.run_iterative_search(p, tw, th, common, task.specs, out_path)
            else:
                res = self.generate_animation({**common, "fps": p["fps"], "quality": p["qual"], "width": tw, "height": th, "output_path_for_iter": out_path})
                if res["status"] == "Success": final_res = res
            
            # Cleanup iteration folder ONLY when we created an ephemeral temp dir.
            # If keep_iter is on, the folder lives next to the source for future
            # warm-starts and we leave it intact.
            if not common.get("iter_keep"):
                try: shutil.rmtree(common["iter_attempts_main_folder"])
                except: pass
            
            if final_res:
                # v2.7-style: stamp the actual encode params (Q / FPS / WxH)
                # into the filename. Done here so BOTH iterative and manual
                # paths get the same treatment, and we always use the WINNER's
                # values, not the requested ones (which may differ when the
                # iterative engine drops FPS to hit the target).
                if p.get("name_settings", True):
                    try:
                        # Pass mode + priority + target so the filename
                        # leads with e.g. ``_BAL16M_…`` / ``_QP8M_…`` /
                        # ``_MAN_…``, making variants of the same source
                        # self-describing on disk.
                        new_path = self._inject_settings_suffix(
                            final_res['file_path'],
                            final_res.get('fps'), final_res.get('quality'),
                            final_res.get('width'), final_res.get('height'),
                            mode=p.get("mode"),
                            prio=p.get("prio"),
                            target_mb=p.get("target"),
                        )
                        if new_path != final_res['file_path']:
                            os.rename(final_res['file_path'], new_path)
                            final_res['file_path'] = new_path
                    except Exception as e:
                        # Non-fatal: keep the original filename if the rename
                        # fails (e.g. permission glitch on a network share).
                        self.log(f"  Filename tagging failed, keeping plain name: {e}")
                # Stash the winning params on the task so the single-mode UI can
                # show the user exactly what won — and whether it was reused from
                # a previous iteration (cache hit) vs freshly searched.
                try:
                    task.result_from_cache = bool(final_res.get("from_cache"))
                    task.result_quality = final_res.get("quality")
                    task.result_fps = final_res.get("fps")
                    task.result_size = final_res.get("file_size")
                    task.result_mode = p.get("mode")
                except Exception:
                    pass
                self.signals.status_text.emit(f"DONE: {os.path.basename(final_res['file_path'])}")
                self.signals.progress.emit(100)
                return True, final_res['file_path']
            else:
                self.signals.error.emit("Failed to generate file matching criteria.")
                return False, ""
                
        except InterruptedError:
            self.log("Task Cancelled.")
            return False, ""
        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")
            self.signals.error.emit(str(e))
            return False, ""

    def generate_animation(self, params):
        res = {"status": "Error", "file_path": None, "file_size": 0}
        out_fmt = params.get("output_format", "GIF")
        ext = ".webp" if out_fmt == "WEBP" else ".gif"
        
        dest = params["output_path_for_iter"]
        base, _ = os.path.splitext(dest); dest = base + ext
        tmp_out = base + INPROGRESS_SUFFIX + ext
        
        self.check_cancel()
        if os.path.exists(dest): os.remove(dest)
        if os.path.exists(tmp_out): os.remove(tmp_out)

        fps, q, w, h = params["fps"], params["quality"], params["width"], params["height"]
        # Cache key must include trim points: extracting frames from a trimmed range
        # produces a different frame set than extracting the full source.
        trim_s = params.get("trim_start", "") or ""
        trim_e = params.get("trim_end", "") or ""
        # CACHE_VER bump:
        #   v2 — pipeline rewrite (-t over -to, fps=N:round=down, -frames:v cap,
        #        -fps_mode cfr) to fix off-by-one boundary frames.
        #   v3 — sub-millisecond -ss/-t precision (6 decimals) so frame-quantized
        #        timestamps at non-integer fps survive the storage round-trip
        #        without drifting onto the wrong source frame.
        #   v4 — symmetric HH:MM:SS:FF parse/format (integer-fps TC math), fixing
        #        the ~2-frame leak at trim boundaries on 29.97/23.976 fps sources
        #        when get_vals re-derived storage from the display field.
        #   v5 — (revoked) Tried NLE-style INCLUSIVE OUT but that conflicted
        #        with what the user sees in the preview / scene-segment math.
        #   v6 — back to EXCLUSIVE OUT: duration = out - in.
        #   v7 — boundary-frame leak fix. When OUT is quantized to a source
        #        frame START (the common case after snap-to-cut or frame-
        #        precise TC entry), `-t duration` lands EXACTLY on that
        #        frame's PTS and ffmpeg includes it in the trimmed stream.
        #        The fps filter then maps that boundary frame into the
        #        last output slot via `floor(T*out_fps)`, producing a
        #        single-frame "flash" of source content past OUT. Two
        #        complementary fixes:
        #         a) shave duration by 1 ms so -t never reaches the
        #            boundary frame's PTS,
        #         b) compute expected_frames with math.floor (not round)
        #            so -frames:v never pads past the natural output
        #            count of the (now sub-boundary) source range.
        CACHE_VER = "v7"
        ckey = hashlib.md5(
            f"{CACHE_VER}|{params['input_path']}_{fps}_{w}_{h}_{params.get('has_alpha', False)}_{trim_s}_{trim_e}".encode()
        ).hexdigest()
        cpath = os.path.join(params["cache_dir"], f"cache_{ckey}")
        marker = os.path.join(cpath, "_SUCCESS.txt")
        
        # Parse trim points in seconds — single source of truth, used both to
        # build the ffmpeg command AND to verify the result post-extraction.
        in_sec_v  = parse_trim_to_seconds(trim_s, default=0.0)  if trim_s else 0.0
        out_sec_v = parse_trim_to_seconds(trim_e, default=None) if trim_e else None
        # EXCLUSIVE OUT: the output covers [IN, OUT). The frame whose PTS == OUT
        # is NOT included — this matches what the user sees when scrubbing the
        # preview AND aligns naturally with segment selection (a cut at PTS T
        # is the FIRST frame of the next segment, so selecting up to T must
        # not bleed into it).
        raw_duration_sec = (out_sec_v - in_sec_v) if (out_sec_v is not None) else None
        if raw_duration_sec is not None and raw_duration_sec <= 0:
            raw_duration_sec = None  # treat as "no end" (full source from in_sec)

        # ---- Boundary-frame epsilon (v7 fix) ----
        # When OUT is frame-quantized (snap-to-cut, manual TC entry, scene
        # selection), `out_sec_v` lands EXACTLY on a source frame's PTS,
        # making the duration land on that frame's PTS too. -t with that
        # exact value pulls the boundary frame into the trimmed stream,
        # which the fps filter then maps to the LAST output slot and
        # produces a single-frame "flash" past OUT. Shaving 1 ms is well
        # below half-frame at any common rate (≥ 8.3 ms @ 120 fps) so it
        # never excludes a frame the user actually wanted; it just nudges
        # -t below the boundary so the boundary frame is excluded.
        BOUNDARY_EPSILON_S = 0.001
        if raw_duration_sec is not None:
            duration_sec = max(BOUNDARY_EPSILON_S, raw_duration_sec - BOUNDARY_EPSILON_S)
        else:
            duration_sec = None

        # ---- Expected frame count (v7 fix) ----
        # Use math.floor(duration * fps), NOT round(). The trimmed source
        # window is [IN, OUT), so output_frames * (1/fps) must be ≤ duration
        # to stay within it. round() can exceed when the fractional part is
        # ≥ .5 (e.g. 5.572 s × 22 fps = 122.59 → round=123 → 5.59 s of
        # playback, 19 ms past OUT). With floor we get the largest integer
        # count that fits inside the window AND it matches what the fps
        # filter naturally emits from the (already-shaved) source range, so
        # `-frames:v` doesn't have to pad with a duplicate frame.
        expected_frames = (
            max(0, int(math.floor(raw_duration_sec * float(fps))))
            if raw_duration_sec is not None else None
        )

        if not (os.path.exists(cpath) and os.path.exists(marker)):
            self.signals.step.emit("⚙️", "Extracting Frames...")
            if os.path.exists(cpath): shutil.rmtree(cpath)
            os.makedirs(cpath, exist_ok=True)
            # fps=N:round=down stabilizes the boundary rounding so we don't
            # gain a half-frame at the head or tail.
            vf = [f"fps={fps}:round=down"]
            if w > 0 and h > 0: vf.append(f"scale={w}:{h}:flags=lanczos")
            elif w > 0: vf.append(f"scale={w}:-2:flags=lanczos")
            elif h > 0: vf.append(f"scale=-2:{h}:flags=lanczos")
            if params.get("has_alpha"): vf.append("format=rgba")
            
            # Frame-accurate trim: -ss BEFORE -i for fast keyframe seek, then
            # -accurate_seek (explicit) decodes forward to the exact in_sec.
            # We use -t DURATION (relative) instead of -to ABSOLUTE because
            # -to is INCLUSIVE in many ffmpeg builds — it would let one extra
            # frame slip past the OUT mark. -frames:v hard-caps the post-fps
            # count to the math we computed in Python. -fps_mode cfr disables
            # any duplication/drop heuristics that could insert ghost frames.
            ff_cmd = [FFMPEG_PATH, "-y", "-accurate_seek"]
            if in_sec_v > 1e-6:
                # 6 decimals = microsecond precision. Critical at non-integer
                # framerates (e.g. 29.97) where each frame is 33.3667 ms wide
                # and 3-decimal rounding can land in the wrong source frame.
                ff_cmd.extend(["-ss", f"{in_sec_v:.6f}"])
            if duration_sec is not None:
                ff_cmd.extend(["-t", f"{duration_sec:.6f}"])
            ff_cmd.extend(["-i", params["input_path"], "-vf", ",".join(vf)])
            if expected_frames is not None and expected_frames > 0:
                ff_cmd.extend(["-frames:v", str(expected_frames)])
            ff_cmd.extend(["-fps_mode", "cfr"])
            ff_cmd.append(os.path.join(cpath, "f_%06d.png"))

            if self.run_cmd(ff_cmd) != 0: return res
            with open(marker, 'w') as f: f.write('ok')

        # ---- Frame-accuracy verification ----
        # Compare actual extracted frame count against the expected count.
        # Logged so the user can validate the trim landed exactly even on a
        # cache hit. After the -frames:v cap, expected==got should be exact;
        # we still tolerate ±1 to be safe across ffmpeg builds.
        try:
            extracted = sum(1 for n in os.listdir(cpath) if n.startswith("f_") and n.endswith(".png"))
            if expected_frames is not None:
                marker_label = "OK" if abs(extracted - expected_frames) <= 1 else "DRIFT"
                # Δ shows the user-visible trim duration (OUT - IN), not the
                # internally-shaved -t value. The 1 ms epsilon is a pipeline
                # detail and would only confuse anyone reading the log.
                self.log(
                    f"  Trim verify: in={in_sec_v:.3f}s out={out_sec_v:.3f}s (excl) "
                    f"(Δ={raw_duration_sec:.3f}s @ {fps}fps) → expected={expected_frames} frames, got {extracted} [{marker_label}]"
                )
            else:
                self.log(f"  Trim verify: from {in_sec_v:.3f}s to END → got {extracted} frames")
        except Exception:
            pass

        self.signals.step.emit("💎", f"Encoding {out_fmt}...")
        if out_fmt == "GIF":
            cmd = [GIFSKI_PATH, "--fps", str(fps), "--quality", str(q)]
            if w > 0: cmd.extend(["--width", str(w)])
            if params.get("play_once"): cmd.append("--once")
            if params.get("faster_encode"): cmd.append("--fast")
            cmd.extend(["-o", tmp_out, os.path.join(cpath, "*.png")])
        else:
            # ---- WEBP encoder selection (priority order) ----
            # 1) img2webp — bundled on macOS. Official libwebp tool, statically
            #    linked (works on any Mac, unlike Homebrew's magick which needs
            #    external config + coder modules). Handles alpha natively and
            #    uses EXACT millisecond frame timing.
            # 2) ImageMagick — the Windows alpha path (unchanged), plus any build
            #    whose ffmpeg lacks libwebp where a relocatable magick exists.
            #    Uses centisecond -delay (fps slightly quantised).
            # 3) ffmpeg libwebp — the original Windows non-alpha path (exact).
            # NOTE: img2webp/magick are absent on Windows, so Windows always
            # lands on the magick(alpha)/ffmpeg(non-alpha) branches — unchanged.
            if IMG2WEBP_PATH:
                ms = max(1, int(round(1000.0 / fps)))
                cmd = [IMG2WEBP_PATH, "-loop", "1" if params.get("play_once") else "0", "-d", str(ms)]
                if params.get("faster_encode"): cmd.extend(["-m", "1"])
                # img2webp defaults to LOSSLESS, so request lossy explicitly for
                # the quality-controlled path.
                if params.get("webp_lossless"): cmd.append("-lossless")
                else: cmd.extend(["-lossy", "-q", str(q)])
                cmd.append(os.path.join(cpath, "f_*.png"))
                cmd.extend(["-o", tmp_out])
            elif bool(MAGICK_PATH) and (params.get("has_alpha") or not FFMPEG_HAS_LIBWEBP):
                delay = max(1, int(round(100.0 / fps)))
                cmd = [MAGICK_PATH, "-delay", str(delay), os.path.join(cpath, "f_*.png")]
                if params.get("has_alpha"): cmd.extend(["-dispose", "Background"])
                cmd.extend(["-loop", "1" if params.get("play_once") else "0"])
                if params.get("webp_lossless"): cmd.extend(["-define", "webp:lossless=true"])
                else: cmd.extend(["-quality", str(q)])
                cmd.append(tmp_out)
            else:
                cmd = [FFMPEG_PATH, "-y", "-f", "image2", "-framerate", str(fps), "-i", os.path.join(cpath, "f_%06d.png"), "-c:v", "libwebp"]
                if params.get("has_alpha"): cmd.extend(["-pix_fmt", "bgra", "-preset", "drawing"])
                cmd.extend(["-loop", "1" if params.get("play_once") else "0"])
                if params.get("webp_lossless"): cmd.append("-lossless")
                else: cmd.extend(["-q:v", str(q)])
                cmd.extend(["-compression_level", "0" if params.get("faster_encode") else "4", tmp_out])

        if self.run_cmd(cmd) == 0 and os.path.exists(tmp_out):
            os.rename(tmp_out, dest)
            # Echo the params used so the caller (start_task) can inject them
            # into the filename without having to keep separate bookkeeping.
            res.update({
                "status": "Success", "file_path": dest, "file_size": os.path.getsize(dest),
                "fps": params.get("fps"), "quality": params.get("quality"),
                "width": params.get("width"), "height": params.get("height"),
            })
            self.signals.step.emit("✅", f"{out_fmt} Rendered!")
        return res

    # ---------- Knowledge cache (warm-start support) ----------
    @staticmethod
    def _attempt_signature(p):
        """Hash the parameters that materially affect output file size at a
        given (q, fps, w, h) so the iteration filename can carry a unique
        tag. The knowledge cache uses the tag to keep samples from
        different runs cleanly separated.

        We hash four inputs:
        - ``trim_start`` / ``trim_end``: a longer clip means a bigger
          file at every Q. Sharing a folder with a different trim and
          NOT distinguishing here would cause Tier-1 to copy the wrong
          file as the user's output.
        - ``has_alpha``: transparency adds an alpha channel and roughly
          adds 10–25% to the size, so samples are not interchangeable.
        - ``webp_lossless``: lossless WebP is multiple times bigger than
          lossy at the same Q; it must be its own bucket.

        Format/extension is implicit in the filename's ``ext`` already,
        so we don't include it in the hash. Same for play_once / faster_encode
        which don't change size meaningfully.

        Returns a short 8-char hex tag — collision-safe enough for the
        handful of variants a single source ever sees in practice and
        keeps filenames readable.
        """
        raw = "|".join([
            str(p.get("trim_start", "") or ""),
            str(p.get("trim_end", "") or ""),
            "a1" if p.get("has_alpha") else "a0",
            "ll1" if p.get("webp_lossless") else "ll0",
        ])
        return hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]

    def _build_knowledge_cache(self, iter_dir, base, w, h, ext, signature):
        """Scan a persistent iterations folder and build {(fps, q, w, h): {size, path}}.
        Filenames are expected in the form
        ``tmp_p{PHASE}_q{Q}_fps{F}_dim{W}x{H}_sig{SIG}{ext}``
        where PHASE is ``1``, ``1u`` (FPS upscale), or ``2`` (FPS downscale).

        We filter by ``signature`` so samples from a previous run with a
        different trim / alpha / lossless config don't pollute the
        warm-start hints (an old sample at the same Q/fps/dim would
        report the wrong size, leading Tier-1 to copy the wrong file
        as the final output and ``_seed_q_from_cache`` to seed a poor
        starting Q). Legacy unsigned filenames from earlier v3.1 runs
        are ignored on purpose — they belong to an unknown trim
        configuration so reusing them is unsafe.
        """
        cache = {}
        if not iter_dir or not os.path.isdir(iter_dir): return cache
        dim_str = f"{w}x{h}"
        pat = re.compile(
            rf"^tmp_p(?:1u?|2)_q(\d+)_fps(\d+)_dim{re.escape(dim_str)}_sig([0-9a-f]+){re.escape(ext)}$",
            re.IGNORECASE,
        )
        found = []
        skipped_legacy = 0
        legacy_pat = re.compile(
            rf"^tmp_p[12]_q\d+_fps\d+_dim{re.escape(dim_str)}{re.escape(ext)}$",
            re.IGNORECASE,
        )
        try:
            entries = os.listdir(iter_dir)
        except OSError:
            return cache
        for f in entries:
            if INPROGRESS_SUFFIX in f: continue
            m = pat.match(f)
            if not m:
                if legacy_pat.match(f):
                    skipped_legacy += 1
                continue
            q_v, f_v, sig_v = int(m.group(1)), int(m.group(2)), m.group(3).lower()
            if sig_v != signature.lower():
                # Same source/dim but different trim or alpha — not a
                # valid hint for the current run.
                continue
            path = os.path.join(iter_dir, f)
            try: sz = os.path.getsize(path)
            except OSError: continue
            cache[(f_v, q_v, w, h)] = {"size": sz, "path": path}
            found.append(f"[Cache] Q{q_v} F{f_v} {sz/(1024*1024):.2f}MB → {f}")
        if found:
            self.log(f"--- Knowledge cache: found {len(found)} prior iteration(s) for {base} @ {dim_str} (sig {signature}) ---")
            for line in found: self.log(line)
        elif skipped_legacy:
            self.log(f"--- Knowledge cache: ignored {skipped_legacy} legacy unsigned iteration(s) (incompatible filename format) ---")
        return cache

    def _proactive_cache_scan(self, cache, target_size, low_b, high_b, target_fps):
        """If cache contains a file already in size bracket AND at an acceptable
        FPS, return it directly so we can skip the search entirely.

        FPS acceptance: any FPS >= target_fps is acceptable (P1.5 upscale
        results are strictly better — same size, smoother animation). Also
        accept up to 2 FPS below target to tolerate small rounding gaps."""
        if not cache: return None
        candidates = []
        for (f_v, q_v, w_v, h_v), info in cache.items():
            sz = info["size"]
            in_bracket = low_b <= sz <= high_b
            fps_ok = f_v >= target_fps or (target_fps - f_v) <= 2
            if in_bracket and fps_ok:
                candidates.append({
                    "file_path": info["path"], "size": sz,
                    "fps": f_v, "quality": q_v,
                    "diff": abs(sz - target_size),
                })
        if not candidates: return None
        candidates.sort(key=lambda c: (abs(c["fps"] - target_fps) * 1000, -c["quality"], c["diff"]))
        return candidates[0]

    def _seed_q_from_cache(self, cache, fps, w, h, target_size, low_q, high_q):
        """If cache has prior attempts at the same (fps, w, h), interpolate the
        Q most likely to land near target_size and return it (clamped to current
        binary-search window). Returns None if no useful hint."""
        same_axis = [
            {"q": q_v, "sz": info["size"]}
            for (f_v, q_v, w_v, h_v), info in cache.items()
            if f_v == fps and w_v == w and h_v == h
        ]
        if not same_axis: return None
        # Linear interpolation between the two samples that bracket target_size.
        below = [s for s in same_axis if s["sz"] <= target_size]
        above = [s for s in same_axis if s["sz"] >= target_size]
        if below and above:
            lo = max(below, key=lambda s: s["sz"])
            hi = min(above, key=lambda s: s["sz"])
            if hi["sz"] != lo["sz"]:
                t = (target_size - lo["sz"]) / (hi["sz"] - lo["sz"])
                guess = int(round(lo["q"] + t * (hi["q"] - lo["q"])))
            else:
                guess = lo["q"]
        else:
            # Fallback: nearest sample by size.
            nearest = min(same_axis, key=lambda s: abs(s["sz"] - target_size))
            guess = nearest["q"]
        return max(low_q, min(high_q, guess))

    def _secant_q_from_live(self, samples, fps, target_size, low_q, high_q):
        """Pick the next Q to test using a safeguarded SECANT step over the
        in-run samples accumulated so far at the same FPS. Returns an
        integer Q in [low_q, high_q] that has not been tested yet at
        this FPS, or None if the data isn't usable.

        Why secant beats blind bisection here:
        the size-vs-Q curve is approximately monotonic and smooth on
        most content. Once we have ONE sample below target and ONE
        above (often by attempt 3), linear interpolation between them
        usually predicts the size-target Q within ±2, whereas bisect
        takes the bracket midpoint regardless of where the curve
        crosses target. On smooth content this saves an attempt; on
        chunky content it is no worse than bisect because we always
        clamp the guess to the current bracket and bracket updates are
        unchanged.

        Safeguards (all critical for "no regression vs bisect"):
        - Filter to ``fps``-matched samples — mixing curves across
          frame-rates would produce nonsense, since size scales roughly
          with fps.
        - Need at least one sample on each side of target. With only
          one side we return None and let bisect drive.
        - Reject degenerate cases where the bracketing samples have
          equal size or equal Q (zero-slope or zero-domain → division
          by zero / vertical secant).
        - Clamp the guess to the current bisection bracket so we never
          extend the search outside it. This preserves the worst-case
          attempt count (≤ ~log2(60) ≈ 6 for Q ∈ [40, 100]).
        - Never repeat a Q already tested at this FPS — falls back to
          bisect to make forward progress instead of wasting an encode.
        """
        same = [s for s in samples if s["fps"] == fps]
        below = [s for s in same if s["sz"] <= target_size]
        above = [s for s in same if s["sz"] >= target_size]
        if not (below and above):
            return None
        lo = max(below, key=lambda s: s["sz"])
        hi = min(above, key=lambda s: s["sz"])
        if hi["sz"] == lo["sz"] or hi["q"] == lo["q"]:
            return None
        t = (target_size - lo["sz"]) / float(hi["sz"] - lo["sz"])
        guess = int(round(lo["q"] + t * (hi["q"] - lo["q"])))
        guess = max(low_q, min(high_q, guess))
        if any(s["q"] == guess for s in same):
            return None
        return guess

    def run_iterative_search(self, ui_vals, w, h, common, specs, final_out_path):
        prio = ui_vals.get("prio", "Balanced").lower()
        src_fps = specs.get('fps', 25)
        
        # Determine intent FPS (v2.7 parity)
        if prio == "fps": target_fps = min(50, int(round(src_fps)))
        elif prio == "quality": target_fps = max(8, min(15, int(round(src_fps * 0.6))))
        else: target_fps = max(12, min(22, int(round(src_fps * 0.8))))
        
        min_fps = max(8, min(12, target_fps)) # basic floor
        
        ext = ".webp" if common["output_format"] == "WEBP" else ".gif"

        # ---- Knowledge cache (only meaningful when 'Keep iterations' is ON) ----
        # Pass the attempt signature so the cache only returns samples
        # generated under the same trim / alpha / lossless config —
        # mixing trims would produce wrong sizes and (worse) Tier-1
        # could copy the wrong file as the final output.
        # "Force re-iterate" (the drop-zone button): ignore the read side of the
        # cache for THIS run so the search runs fresh, without the user having to
        # turn off "Keep iterations". New iterations are still written to disk.
        force_re = bool(ui_vals.get("force_reencode"))
        if common.get("iter_keep") and not force_re:
            cache = self._build_knowledge_cache(
                common["iter_attempts_main_folder"], common["source_basename_no_ext"],
                w, h, ext, common["attempt_signature"],
            )
        else:
            cache = {}
            if force_re and common.get("iter_keep"):
                self.log("  Force re-iterate: ignoring cached iterations — running a fresh search.")

        # Tier-1 perfect match: skip search entirely if a previous run already
        # produced a file in the size bracket AND matching the target FPS intent.
        tier1 = self._proactive_cache_scan(
            cache, common["target_size_bytes"],
            common["strict_lower_bound"], common["strict_upper_bound"], target_fps,
        )
        if tier1:
            self.log(f"  Smart Match (Tier 1): Q{tier1['quality']} F{tier1['fps']} "
                     f"({tier1['size']/(1024*1024):.2f}MB) — skipping search.")
            if os.path.exists(final_out_path): os.remove(final_out_path)
            shutil.copy2(tier1["file_path"], final_out_path)
            # Surface the WINNER's params so the caller can rename the file
            # to include them. For Tier-1 the winner = the cached file we hit.
            return {
                "status": "Success", "file_path": final_out_path, "file_size": tier1["size"],
                "fps": tier1.get("fps"), "quality": tier1.get("quality"),
                "width": w, "height": h,
                "from_cache": True,
            }

        # Ceiling FPS: the absolute highest FPS worth trying (source rate,
        # integer-rounded, never below target_fps).
        max_fps = max(target_fps, min(50, int(round(src_fps))))

        # Tier-2 ceiling shortcut: if the cache already proves Q100 at the
        # MAX possible FPS still can't reach the target, accept the best
        # cached Q100 immediately — no point re-encoding anything.
        cache_q100_at_max = None
        cache_q100_best = None  # best (highest fps) Q100 in cache
        for (f_v, q_v, w_v, h_v), info in cache.items():
            if q_v == 100 and w_v == w and h_v == h:
                if f_v == max_fps:
                    cache_q100_at_max = info
                if cache_q100_best is None or f_v > cache_q100_best[0]:
                    cache_q100_best = (f_v, info)
        if cache_q100_at_max and cache_q100_at_max["size"] < common["strict_lower_bound"]:
            self.log(f"  Ceiling shortcut: cached Q100 F{max_fps} ({cache_q100_at_max['size']/(1024*1024):.2f}MB)"
                     f" < target {common['target_mb']}MB — accepting as best possible.")
            if os.path.exists(final_out_path): os.remove(final_out_path)
            shutil.copy2(cache_q100_at_max["path"], final_out_path)
            return {
                "status": "Success", "file_path": final_out_path, "file_size": cache_q100_at_max["size"],
                "quality": 100, "fps": max_fps, "width": w, "height": h,
                "from_cache": True,
            }

        low_q, high_q = 40, 100
        best_res = None
        closest_any = {'file_path': None, 'size': 0, 'diff': float('inf')}
        successful = []
        # Tolerance for early-stop: 3% of the target size. If a result lands in
        # bracket AND within this tolerance, accept and break (avoid wasting more
        # encodes refining a result that's already "good enough").
        tol_bytes = max(1, int(round(common["target_size_bytes"] * 0.03)))
        
        self.signals.step.emit("🔎", "Phase I: Quality Search...")
        self.log(f"--- P1: Quality Binary Search (Target: {common['target_mb']}MB, FPS: {target_fps}) ---")

        # Telemetry: tell any subscribed chart that a new search has started
        # so it can clear stale data points and lock its target/bracket axes.
        self.signals.iter_started.emit({
            "target": int(common["target_size_bytes"]),
            "lower":  int(common["strict_lower_bound"]),
            "upper":  int(common["strict_upper_bound"]),
        })

        attempts = 0
        total_attempts = 0   # counter that spans both phases for telemetry
        max_attempts = 10
        fps = target_fps
        seed_used = False  # we only seed mid_q on the very first attempt
        # In-run sample log for the safeguarded-secant step. Each entry:
        # {"q": int, "sz": int (bytes), "fps": int}. Populated AFTER each
        # successful encode below; consumed at the top of the next loop
        # iteration to interpolate the next mid_q. Stays empty when bisect
        # is the right call (e.g. only one sample, or samples on the same
        # side of target).
        live_samples = []
        
        # Phase 1: Binary Search on Quality
        while low_q <= high_q and attempts < max_attempts:
            self.check_cancel(); attempts += 1
            # mid_q selection — three sources, in priority order:
            #   1) First-attempt warm-start from the persistent disk cache
            #      (only when 'Keep iterations' is on AND a prior run hit
            #      this fps/dim).
            #   2) Live-secant interpolation from in-run samples once we
            #      have one above and one below the target at this fps.
            #   3) Plain bisection midpoint (fallback / first-attempt
            #      when neither source applies).
            chose_via = "bisect"
            if not seed_used:
                hint = self._seed_q_from_cache(cache, fps, w, h, common["target_size_bytes"], low_q, high_q)
                if hint is not None:
                    mid_q = hint
                    chose_via = "warm-cache"
                    self.log(f"    Warm-start: seeding Q{mid_q} from prior iterations.")
                else:
                    mid_q = (low_q + high_q) // 2
                seed_used = True
            else:
                secant_guess = self._secant_q_from_live(
                    live_samples, fps, common["target_size_bytes"], low_q, high_q,
                )
                if secant_guess is not None:
                    mid_q = secant_guess
                    chose_via = "secant"
                else:
                    mid_q = (low_q + high_q) // 2
            
            self.signals.progress.emit(int((attempts/15)*100))
            if chose_via == "secant":
                self.log(f"  > Attempt {attempts}: Testing Q{mid_q} (secant from live samples).")
            else:
                self.log(f"  > Attempt {attempts}: Testing Q{mid_q}...")

            # Tell the chart which config we're about to test BEFORE
            # the encode starts, so the user sees a clear "currently
            # testing Q{q} F{fps}" banner while the encode is in flight
            # (vs. only updating retroactively when the size is known).
            # `total_attempts + 1` matches the index iter_step will
            # emit a few lines down — keeping them aligned makes the
            # chart's "running" highlight unambiguous.
            self.signals.iter_attempt_started.emit({
                "iter":  total_attempts + 1,
                "q":     int(mid_q),
                "fps":   int(fps),
                "w":     int(w), "h": int(h),
                "phase": "P1",
                "via":   chose_via,
            })
            
            # Filename embeds the params actually tried (q, fps, dim) AND
            # the run's attempt signature (trim/alpha/lossless hash) so
            # the next run can rebuild the knowledge cache deterministically
            # without confusing samples across configurations.
            sig = common["attempt_signature"]
            fname = f"tmp_p1_q{mid_q}_fps{fps}_dim{w}x{h}_sig{sig}"
            opath = os.path.join(common["iter_attempts_main_folder"], fname + ext)
            
            # Reuse a prior iteration file if it exists — avoids a redundant
            # gifski encode when 'Keep iterations' is on and a previous run
            # already produced this exact (Q, FPS, dim, sig) combination.
            if os.path.exists(opath):
                sz = os.path.getsize(opath)
                self.log(f"    (reusing cached iteration: {sz/(1024*1024):.2f}MB)")
                res = {"status": "Success", "file_size": sz, "file_path": opath}
            else:
                params = {**common, "fps": fps, "quality": mid_q, "width": w, "height": h, "output_path_for_iter": opath}
                res = self.generate_animation(params)
            if res["status"] != "Success": break
            
            sz = res["file_size"]
            res_obj = {'file_path': opath, 'size': sz, 'fps': fps, 'quality': mid_q, 'diff': abs(sz - common['target_size_bytes'])}
            
            if res_obj['diff'] < closest_any['diff']: closest_any = res_obj

            # Feed the live-secant log. Recorded BEFORE the
            # in-bracket/break check below so that even the winning
            # attempt is logged — this matters when the same source
            # is queued twice in the batch and the second run wants
            # to reuse this attempt's data point.
            live_samples.append({"q": mid_q, "sz": int(sz), "fps": int(fps)})

            # Telemetry: this attempt is "complete" — emit before the
            # break/continue logic below so the chart sees every iteration
            # including the winning one.
            total_attempts += 1
            self.signals.iter_step.emit({
                "iter":    total_attempts,
                "size":    int(sz),
                "target":  int(common["target_size_bytes"]),
                "lower":   int(common["strict_lower_bound"]),
                "upper":   int(common["strict_upper_bound"]),
                "fps":     int(fps),
                "quality": int(mid_q),
                "phase":   "P1",
            })

            in_bracket = common['strict_lower_bound'] <= sz <= common['strict_upper_bound']
            if in_bracket:
                successful.append(res_obj)
                best_res = res_obj
                if res_obj['diff'] <= tol_bytes:
                    self.log(f"    Early-stop: diff {res_obj['diff']/(1024*1024):.2f}MB ≤ tol {tol_bytes/(1024*1024):.2f}MB — accepting.")
                    break
                # Even if not within tolerance, in-bracket is success: stop.
                break
            elif sz > common['strict_upper_bound']: high_q = mid_q - 1
            else: low_q = mid_q + 1
            
        # Phase 1.5: FPS Upscale — if Q100 at target_fps is BELOW the target,
        # there's headroom to spend on smoother animation. Binary-search on
        # FPS (at Q100) between target_fps+1 and source fps.
        if not best_res and closest_any['file_path']:
            if closest_any.get('quality', 0) >= 100 and closest_any['size'] < common['target_size_bytes'] and max_fps > target_fps:
                self.signals.step.emit("📈", "Phase 1.5: FPS Upscale...")
                lo_fps, hi_fps = target_fps + 1, max_fps
                self.log(f"--- P1.5: FPS Upscale at Q100 (range F{lo_fps}–F{hi_fps}) ---")
                upscale_best = closest_any  # fallback: the Q100@target_fps result
                attempts_up = 0
                max_attempts_up = 6
                while lo_fps <= hi_fps and attempts_up < max_attempts_up:
                    self.check_cancel(); attempts_up += 1
                    try_fps = (lo_fps + hi_fps) // 2
                    self.log(f"  > Attempt {total_attempts + 1}: Testing Q100 @ F{try_fps}...")
                    sig = common["attempt_signature"]
                    fname = f"tmp_p1u_q100_fps{try_fps}_dim{w}x{h}_sig{sig}"
                    opath = os.path.join(common["iter_attempts_main_folder"], fname + ext)
                    self.signals.iter_attempt_started.emit({
                        "iter":  total_attempts + 1,
                        "q":     100,
                        "fps":   int(try_fps),
                        "w":     int(w), "h": int(h),
                        "phase": "P1.5",
                        "via":   "fps-bisect",
                    })
                    if os.path.exists(opath):
                        sz = os.path.getsize(opath)
                        self.log(f"    (reusing cached iteration: {sz/(1024*1024):.2f}MB)")
                        res = {"status": "Success", "file_size": sz, "file_path": opath}
                    else:
                        params = {**common, "fps": try_fps, "quality": 100, "width": w, "height": h, "output_path_for_iter": opath}
                        res = self.generate_animation(params)
                    if res["status"] != "Success": break
                    sz = res["file_size"]
                    res_obj = {'file_path': opath, 'size': sz, 'fps': try_fps, 'quality': 100, 'diff': abs(sz - common['target_size_bytes'])}
                    if res_obj['diff'] < upscale_best['diff']:
                        upscale_best = res_obj

                    total_attempts += 1
                    self.signals.iter_step.emit({
                        "iter":    total_attempts,
                        "size":    int(sz),
                        "target":  int(common["target_size_bytes"]),
                        "lower":   int(common["strict_lower_bound"]),
                        "upper":   int(common["strict_upper_bound"]),
                        "fps":     int(try_fps),
                        "quality": 100,
                        "phase":   "P1.5",
                    })

                    if common['strict_lower_bound'] <= sz <= common['strict_upper_bound']:
                        successful.append(res_obj)
                        best_res = res_obj
                        break
                    elif sz > common['strict_upper_bound']:
                        hi_fps = try_fps - 1
                    else:
                        lo_fps = try_fps + 1

                if not best_res:
                    if upscale_best['diff'] < closest_any['diff']:
                        closest_any = upscale_best

        # Phase 2: FPS step-down with Q re-search at each tier.
        # Only enters when P1 overshot (file too big even at Q40). Tries
        # progressively lower FPS tiers until an in-bracket result is found
        # or we hit the floor. Skipped when the problem is a ceiling hit
        # (Q100 still under target) since lower FPS would only shrink the file.
        p2_skip = (closest_any.get('quality', 0) >= 100
                   and closest_any['size'] < common['target_size_bytes'])
        if not best_res and closest_any['file_path'] and not p2_skip and target_fps > min_fps:
            self.signals.step.emit("📉", "Phase II: FPS Adjust...")
            
            # --- PRIORITY 1 OPTIMIZATION: DIRECT FPS SCALING ---
            current_fps = closest_any['fps']
            current_size = closest_any['size']
            target_size = common['target_size_bytes']
            
            # Using 0.93 safety margin to absorb header overhead
            fps_ratio = (target_size / current_size) * 0.93
            estimated_fps = int(round(current_fps * fps_ratio))
            tier_fps = max(min_fps, min(current_fps - 1, estimated_fps))
            
            self.log(f"  [Optimizer] Phase 1 overshot: smallest size at F{current_fps} was {current_size/(1024*1024):.2f}MB (target {common['target_mb']}MB).")
            self.log(f"  [Optimizer] Direct scaling ratio: {fps_ratio:.3f} -> Estimated FPS: {estimated_fps}")
            self.log(f"  [Optimizer] Selected Target FPS: {tier_fps} (Floor: {min_fps})")
            
            fps_tiers = [tier_fps]
            if tier_fps > min_fps:
                fps_tiers.append(min_fps) # Add min_fps as a robust fallback
            
            max_p2_total = 12
            p2_used = 0
            for tier_fps in fps_tiers:
                if best_res or p2_used >= max_p2_total: break
                self.log(f"--- P2: Quality Binary Search at FPS={tier_fps} ---")
                low_q2, high_q2 = 40, 100
                while low_q2 <= high_q2 and p2_used < max_p2_total:
                    self.check_cancel(); p2_used += 1
                    mid_q2 = (low_q2 + high_q2) // 2
                    self.log(f"  > Attempt {total_attempts + 1}: Testing Q{mid_q2} @ F{tier_fps}...")
                    sig = common["attempt_signature"]
                    fname = f"tmp_p2_q{mid_q2}_fps{tier_fps}_dim{w}x{h}_sig{sig}"
                    opath = os.path.join(common["iter_attempts_main_folder"], fname + ext)
                    self.signals.iter_attempt_started.emit({
                        "iter":  total_attempts + 1,
                        "q":     int(mid_q2),
                        "fps":   int(tier_fps),
                        "w":     int(w), "h": int(h),
                        "phase": "P2",
                        "via":   "bisect",
                    })
                    if os.path.exists(opath):
                        sz = os.path.getsize(opath)
                        self.log(f"    (reusing cached iteration: {sz/(1024*1024):.2f}MB)")
                        res = {"status": "Success", "file_size": sz, "file_path": opath}
                    else:
                        params = {**common, "fps": tier_fps, "quality": mid_q2, "width": w, "height": h, "output_path_for_iter": opath}
                        res = self.generate_animation(params)
                    if res["status"] != "Success": break
                    sz = res["file_size"]
                    res_obj = {'file_path': opath, 'size': sz, 'fps': tier_fps, 'quality': mid_q2, 'diff': abs(sz - common['target_size_bytes'])}
                    if res_obj['diff'] < closest_any['diff']: closest_any = res_obj

                    total_attempts += 1
                    self.signals.iter_step.emit({
                        "iter":    total_attempts,
                        "size":    int(sz),
                        "target":  int(common["target_size_bytes"]),
                        "lower":   int(common["strict_lower_bound"]),
                        "upper":   int(common["strict_upper_bound"]),
                        "fps":     int(tier_fps),
                        "quality": int(mid_q2),
                        "phase":   "P2",
                    })

                    if common['strict_lower_bound'] <= sz <= common['strict_upper_bound']:
                        successful.append(res_obj)
                        best_res = res_obj
                        break
                    elif sz > common['strict_upper_bound']: high_q2 = mid_q2 - 1
                    else: low_q2 = mid_q2 + 1

        # Finalize
        winner = None
        if successful:
             if prio == "fps":
                 # FPS priority: prefer highest FPS, then highest quality, then closest to target.
                 def p_sort(item): return (-item['fps'], -item['quality'], item['diff'])
             elif prio == "quality":
                 # Quality priority: prefer highest quality, then lowest FPS (saves budget), then closest.
                 def p_sort(item): return (-item['quality'], item['fps'], item['diff'])
             else:
                 # Balanced: prefer FPS closest to target intent, then highest quality, then closest.
                 def p_sort(item): return (abs(item['fps'] - target_fps) * 1000, -item['quality'], item['diff'])
             successful.sort(key=p_sort)
             winner = successful[0]
        else:
             winner = closest_any

        # Telemetry: announce search end so the chart can stop animating
        # and lock the rendered trajectory until the next run starts.
        self.signals.iter_finished.emit({
            "winner": (
                {"size": int(winner["size"]),
                 "fps":  int(winner["fps"]),
                 "quality": int(winner["quality"])}
                if winner and winner.get("file_path") else None
            ),
            "iterations": total_attempts,
        })

        if winner and winner.get('file_path') and os.path.exists(winner['file_path']):
             self.log(f"  WINNER: Q{winner['quality']} F{winner['fps']} ({winner['size']/(1024*1024):.2f}MB)")
             if os.path.exists(final_out_path): os.remove(final_out_path)
             shutil.copy2(winner['file_path'], final_out_path)
             return {
                "status": "Success", "file_path": final_out_path, "file_size": winner['size'],
                "fps": winner.get("fps"), "quality": winner.get("quality"),
                "width": w, "height": h,
             }

        return None

class Worker(QThread):
    def __init__(self, queue_items):
        super().__init__()
        self.items = queue_items
        self.signals = WorkerSignals()
        self.cancel_event = threading.Event()
        
    def run(self):
        engine = ConversionEngine(self.signals, self.cancel_event)
        for i, task in enumerate(self.items):
            if self.cancel_event.is_set(): break
            self.signals.log.emit(f"--- Processing Task {i+1}/{len(self.items)} ---")
            self.signals.task_started.emit(task)
            success, dest_path = engine.start_task(task)
            self.signals.task_finished.emit(task, success, dest_path)
        self.signals.finished.emit()

    def cancel(self):
        self.cancel_event.set()


class SceneDetectorWorker(QThread):
    """Run FFmpeg's `select='gt(scene,T)'` filter and parse pts_time of each detected
    scene change. Emits `cuts` (list[float] seconds) when finished, plus periodic
    progress (pct 0-100, cuts_so_far) parsed from ffmpeg's `time=HH:MM:SS.ss`
    lines so the UI can show partial counts mid-scan instead of just a %.

    Cancellable mid-run; cleans up the spawned ffmpeg process."""
    cuts_ready = Signal(list)        # list[int] — first frame index of each new scene
    progress = Signal(int, int)      # (pct 0-100, cuts_so_far)
    failed = Signal(str)

    _re_pts = re.compile(r"pts_time:(\d+(?:\.\d+)?)")
    # Capture sub-second too so short clips (<10s) get smooth updates instead
    # of jumping in 1s integer steps.
    _re_time = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?")

    def __init__(self, video_path, duration_sec, threshold=0.30, fps=25.0, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.duration_sec = max(0.001, float(duration_sec or 0))
        self.threshold = float(threshold)
        self.fps = float(fps or 0)
        self._cancel = False
        self._proc = None

    def cancel(self):
        self._cancel = True
        proc = self._proc
        if proc is not None:
            try: proc.terminate()
            except Exception: pass

    def run(self):
        cut_frame_indices = set()
        last_pct = -1  # throttle: only emit when pct actually changes
        try:
            cmd = [
                FFMPEG_PATH, "-hide_banner", "-nostats",
                "-i", self.video_path,
                "-vf", f"select='gt(scene,{self.threshold})',showinfo",
                "-an", "-f", "null", "-",
            ]
            flags = 0x08000000 if os.name == 'nt' else 0
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace', creationflags=flags,
            )
            assert self._proc.stderr is not None
            for line in iter(self._proc.stderr.readline, ''):
                if self._cancel:
                    break
                m_pts = self._re_pts.search(line)
                if m_pts:
                    try:
                        t = float(m_pts.group(1))
                        if self.fps > 0:
                            max_fi = max(
                                1, int(round(self.duration_sec * self.fps)) - 1
                            )
                            fi = scene_cut_frame_index_from_detection(
                                t, self.fps, max_fi
                            )
                            cut_frame_indices.add(fi)
                        elif t > 0:
                            cut_frame_indices.add(t)  # unused path; kept for safety
                    except ValueError:
                        pass
                m_t = self._re_time.search(line)
                if m_t and self.duration_sec > 0:
                    cur = (int(m_t.group(1))*3600 + int(m_t.group(2))*60
                           + int(m_t.group(3)))
                    if m_t.group(4):
                        # Parse "ss" or "sss" suffix as a fractional second.
                        frac = m_t.group(4)
                        cur += int(frac) / (10 ** len(frac))
                    pct = int(min(100, max(0, (cur / self.duration_sec) * 100)))
                    if pct != last_pct:
                        last_pct = pct
                        self.progress.emit(pct, len(cut_frame_indices))
            try: self._proc.wait(timeout=2)
            except Exception: pass
            if self._cancel:
                return
            self.progress.emit(100, len(cut_frame_indices))
            cuts_fi = sorted(int(x) for x in cut_frame_indices if int(x) > 0)
            self.cuts_ready.emit(cuts_fi)
        except FileNotFoundError:
            self.failed.emit("FFmpeg not found")
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            if self._proc and self._proc.poll() is None:
                try: self._proc.kill()
                except Exception: pass



class IterChartWidget(QWidget):
    """Live mini-chart of the iterative search trajectory.

    Subscribes to ConversionEngine's iter_started / iter_step / iter_finished
    signals via the dialog/window connect path. Each emitted iteration plots
    one dot at (iteration_idx, file_size) with the acceptance bracket drawn
    as a horizontal green band and the target as a bright line.

    The widget is tiny (full-width × 64 px) — designed to live next to the
    main progress bar so the user gets glanceable convergence info without
    a separate window. Idle state shows a hint label inside the widget.

    Painting is pure QPainter (no plotting deps). All drawing math is in
    SOURCE units (bytes, iteration index) → screen px via small helpers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Height bumped to fit a second footer line that lists the recent
        # attempts as compact text — that's the "always-visible, no console
        # required" channel for users who want to see what's been tried.
        # The first footer line keeps the per-iteration status; the new
        # trajectory line is the historical recap.
        # Bumped to 100 px to host a top "currently testing" banner that
        # announces (Q, FPS, W×H, phase, via) of the in-flight encode
        # before its size lands as a data point. Chart body shrinks
        # accordingly via pad_t.
        self.setFixedHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        # Search state. None when idle (no run yet, or cleared).
        self._target = None        # int bytes
        self._lower  = None        # int bytes (acceptance bracket lower)
        self._upper  = None        # int bytes (acceptance bracket upper)
        self._points = []          # list[dict] each with size/iter/phase/fps/q
        self._running = False      # True between iter_started and iter_finished
        self._winner = None        # set after iter_finished
        # In-flight attempt — populated by iter_attempt_started, cleared
        # by iter_step (the result landed) or iter_finished (search ended
        # without producing a final iter_step, e.g. cancelled).
        # When set, the chart paints a top banner like
        # "🔍 Testing #3: Q72 / F22 / 1920×1080 · P1 · secant".
        self._current_attempt = None
        self._refresh_tooltip()

    # --- API consumed by the main window via signal connections -------------

    @Slot(dict)
    def on_iter_started(self, info):
        self._target = int(info.get("target") or 0)
        self._lower  = int(info.get("lower")  or 0)
        self._upper  = int(info.get("upper")  or 0)
        self._points = []
        self._running = True
        self._winner = None
        self._current_attempt = None
        self._refresh_tooltip()
        self.update()

    @Slot(dict)
    def on_iter_attempt_started(self, info):
        """Engine signaled it is about to start an encode. Stash the
        config so paintEvent can render the banner. Doesn't append to
        ``_points`` — that happens later via on_iter_step when the
        encode finishes and the size is known."""
        self._current_attempt = dict(info)
        self.update()

    @Slot(dict)
    def on_iter_step(self, pt):
        if not self._running:
            # Defensive: a stray step before iter_started — initialize
            # bracket from the point itself so we still render something.
            self._target = int(pt.get("target") or 0)
            self._lower  = int(pt.get("lower")  or 0)
            self._upper  = int(pt.get("upper")  or 0)
            self._running = True
        self._points.append(dict(pt))
        # The encode for the announced attempt has finished (its result
        # is now a data point), so clear the "currently testing" banner.
        # iter_attempt_started will fire again before the next encode
        # begins.
        self._current_attempt = None
        self._refresh_tooltip()
        self.update()

    @Slot(dict)
    def on_iter_finished(self, info):
        self._running = False
        self._winner = info.get("winner")
        self._current_attempt = None
        self._refresh_tooltip()
        self.update()

    def clear(self):
        self._target = None
        self._lower = None
        self._upper = None
        self._points = []
        self._running = False
        self._winner = None
        self._current_attempt = None
        self._refresh_tooltip()
        self.update()

    # --- Tooltip (full attempt history on hover) -----------------------

    def _arrow_for(self, pt):
        """Compact status arrow for an attempt vs. its acceptance bracket.
        Returns (arrow_text, descriptive_text) so callers can pick whichever
        fits — paintEvent uses the short form, tooltip uses the long form."""
        if pt['size'] > pt['upper']:
            return ("↑", "over")
        if pt['size'] < pt['lower']:
            return ("↓", "under")
        return ("✓", "in bracket")

    def _refresh_tooltip(self):
        """Build a multi-line tooltip listing every attempted (Q, FPS, size)
        so the user can hover the chart and see the full search history at
        a glance — no need to expand the console.

        Uses a monospace formatting via fixed-width fields so columns align
        in Qt's tooltip default font. Header summarizes the target band;
        each row shows iteration index, phase, encode params, output size,
        and bracket status. Winner gets a final ★ row when known."""
        if not self._points:
            self.setToolTip(
                "Iterative engine telemetry.\n\n"
                "Once a search starts, every attempt (FPS, quality, "
                "produced file size, bracket status) will be listed here."
            )
            return
        target_mb = (self._target or 0) / (1024.0 * 1024.0)
        lo_mb    = (self._lower  or 0) / (1024.0 * 1024.0)
        up_mb    = (self._upper  or 0) / (1024.0 * 1024.0)
        lines = [
            f"Target: {target_mb:.2f} MB     Bracket: {lo_mb:.2f} – {up_mb:.2f} MB",
            "─" * 46,
            f"{'#':>2}  {'Phase':<5} {'FPS':>3} {'Q':>3}  {'Size (MB)':>9}   Status",
            "─" * 46,
        ]
        for p in self._points:
            sz = p['size'] / (1024.0 * 1024.0)
            arrow, desc = self._arrow_for(p)
            lines.append(
                f"{p['iter']:>2}  {p['phase']:<5} {p['fps']:>3} {p['quality']:>3}"
                f"   {sz:>7.2f}    {arrow} {desc}"
            )
        if self._winner and not self._running:
            wmb = self._winner['size'] / (1024.0 * 1024.0)
            lines.append("─" * 46)
            lines.append(f"★ WINNER: Q{self._winner['quality']} "
                         f"F{self._winner['fps']} → {wmb:.2f} MB")
        elif self._running:
            lines.append("─" * 46)
            lines.append("…searching")
        self.setToolTip("\n".join(lines))

    # --- Painting -----------------------------------------------------------

    def _y_range(self):
        """Pick a Y-axis [min, max] that comfortably shows the target band
        AND every observed point. Padded ±15% so dots near the boundary
        don't kiss the edge."""
        candidates = [self._target or 0, self._upper or 0]
        candidates += [p["size"] for p in self._points]
        if not any(candidates):
            return (0, 1)
        hi = max(candidates) * 1.15
        # Don't anchor to 0 if all data is huge — gives finer resolution
        # near the target. But keep at least a 50% bottom margin so the
        # acceptance band isn't clipped against the floor.
        lo = max(0, min(candidates) - hi * 0.05)
        if lo == hi:
            hi = lo + 1
        return (lo, hi)

    # --- "Currently testing" banner ---------------------------------------
    # The banner sits in the top strip of the widget (above the chart body)
    # and shows what config the engine is encoding RIGHT NOW. We render
    # it whenever ``_current_attempt`` is set — independent of whether
    # any data points have landed yet, so the very first attempt also
    # shows up here while it's running.

    BANNER_H = 18  # px reserved at the top for the announcement strip

    def _draw_current_attempt_banner(self, p, w, attempt):
        from PySide6.QtGui import QBrush, QPen
        # Background pill — bright blue when in P1, orange in P2 to match
        # the dot color scheme below (so the eye associates banner with
        # the corresponding dot). A subtle gradient + 1px border keeps it
        # visually distinct from idle chrome.
        is_p2 = (attempt.get("phase") == "P2")
        accent = QColor("#ff9800") if is_p2 else QColor("#4a90e2")
        bg = QColor(accent); bg.setAlpha(35)
        p.setBrush(QBrush(bg))
        pen = QPen(accent); pen.setWidth(1)
        p.setPen(pen)
        p.drawRoundedRect(2, 2, w - 4, self.BANNER_H - 2, 4, 4)

        # Compose "🔍 Testing #N: Q{q} / F{fps} / W×H · P1 · via". The
        # arrow icon makes the running state unmistakable. Truncate the
        # `via` chip on narrow widths so the rest of the banner stays.
        q     = int(attempt.get("q") or 0)
        fps_v = int(attempt.get("fps") or 0)
        w_v   = int(attempt.get("w") or 0)
        h_v   = int(attempt.get("h") or 0)
        phase = attempt.get("phase") or "P1"
        via   = attempt.get("via") or "bisect"
        i_v   = int(attempt.get("iter") or (len(self._points) + 1))

        dim_str = f"{w_v}×{h_v}" if (w_v and h_v) else "—"
        via_label = {
            "secant":     "secant",
            "warm-cache": "warm cache",
            "bisect":     "bisect",
        }.get(via, via)

        # Bright text for the configuration (high contrast against pill).
        font = p.font(); font.setPointSize(8); font.setBold(True); font.setItalic(False)
        p.setFont(font)
        p.setPen(QColor("#ffffff"))
        primary = f"🔍 Testing  #{i_v}:  Q{q}  /  F{fps_v}  /  {dim_str}"
        # Sidekick text in muted color showing phase + via.
        font2 = p.font(); font2.setBold(False); font2.setItalic(True); font2.setPointSize(8)

        # Try to fit primary + secondary on one line; if not, drop the
        # secondary suffix entirely so the primary always reads cleanly.
        fm = p.fontMetrics()
        secondary = f"   ·   {phase}   ·   {via_label}"
        avail = w - 16
        primary_w = fm.horizontalAdvance(primary)
        if primary_w + fm.horizontalAdvance(secondary) <= avail:
            p.drawText(8, self.BANNER_H - 4, primary)
            p.setFont(font2)
            p.setPen(QColor("#cdd9eb"))
            p.drawText(8 + primary_w, self.BANNER_H - 4, secondary)
        else:
            p.drawText(8, self.BANNER_H - 4, primary)

    def paintEvent(self, ev):
        from PySide6.QtGui import QPainter, QBrush, QPen
        from PySide6.QtCore import QPoint
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        p.setBrush(QBrush(QColor("#0d0d18")))
        p.setPen(Qt.NoPen)
        p.drawRect(0, 0, w, h)
        # 1px border so the chart is visually distinct from surrounding panels
        p.setPen(QColor("#222"))
        p.drawRect(0, 0, w - 1, h - 1)

        # If there's an attempt in flight, paint the banner FIRST so it's
        # visible even in the idle pre-data state (the very first encode
        # starts before any iter_step lands).
        if self._current_attempt is not None:
            self._draw_current_attempt_banner(p, w, self._current_attempt)

        # Idle state — render a centered hint and bail. Skip when a banner
        # already explains "we're testing the first attempt"; in that case
        # we just leave the chart body empty until iter_step lands.
        if self._target is None or self._target <= 0 or not self._points:
            if self._current_attempt is None:
                p.setPen(QColor("#555"))
                p.setBrush(Qt.NoBrush)
                font = p.font(); font.setPointSize(8); font.setItalic(True); p.setFont(font)
                msg = ("Iterative engine: chart will render here during search."
                       if not self._running else "Searching… first iteration coming.")
                p.drawText(self.rect(), Qt.AlignCenter, msg)
            return

        # Drawing area (small inner padding so axes/labels don't kiss edges).
        # pad_t leaves room for the banner above the chart body. pad_b
        # reserves room for TWO footer lines below the chart:
        #   - line 1: per-iteration status (last completed attempt summary)
        #   - line 2: compact trajectory of the last few attempts
        # so the user gets the prior-attempt history without expanding the
        # console.
        pad_l, pad_r, pad_t, pad_b = 28, 8, self.BANNER_H + 4, 28
        gx0, gy0 = pad_l, pad_t
        gx1, gy1 = w - pad_r, h - pad_b
        gw, gh = gx1 - gx0, gy1 - gy0
        if gw <= 0 or gh <= 0:
            return

        y_lo, y_hi = self._y_range()
        y_span = max(1.0, y_hi - y_lo)
        # Iteration axis goes 0..N+1 so the first dot isn't pasted to the
        # left edge and the most-recent has space to breathe.
        max_iter = max(self._points[-1]["iter"], 4)

        def to_x(iteration):
            return int(gx0 + (iteration / float(max_iter + 1)) * gw)
        def to_y(size):
            # Inverted Y — bigger size goes higher (more familiar than the
            # image-coord convention).
            return int(gy1 - ((size - y_lo) / y_span) * gh)

        # Acceptance band (semi-transparent green) — the "good" zone.
        if self._upper and self._lower:
            band_top = to_y(self._upper)
            band_bot = to_y(self._lower)
            band_col = QColor("#2e7d32"); band_col.setAlpha(70)
            p.setBrush(QBrush(band_col))
            p.setPen(Qt.NoPen)
            p.drawRect(gx0, band_top, gw, max(2, band_bot - band_top))

        # Target line (bright green dashed)
        target_y = to_y(self._target)
        pen = QPen(QColor("#66bb6a")); pen.setWidth(1); pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        p.drawLine(gx0, target_y, gx1, target_y)

        # Trajectory line (gray) connecting consecutive iterations.
        if len(self._points) >= 2:
            pen = QPen(QColor("#555")); pen.setWidth(1)
            p.setPen(pen)
            prev = self._points[0]
            for cur in self._points[1:]:
                p.drawLine(to_x(prev["iter"]), to_y(prev["size"]),
                           to_x(cur["iter"]),  to_y(cur["size"]))
                prev = cur

        # Iteration dots — color-coded by phase.
        # P1 = primary quality search (azure)
        # P2 = fps fallback phase (orange)
        # The last point gets a halo if the run is still active so the
        # eye is drawn to the latest data point.
        for i, pt in enumerate(self._points):
            x = to_x(pt["iter"]); y = to_y(pt["size"])
            in_bracket = (self._lower <= pt["size"] <= self._upper) if self._lower and self._upper else False
            if pt.get("phase") == "P2":
                col = QColor("#ff9800")
            else:
                col = QColor("#4a90e2")
            # Highlight the winning point if we know it (post-iter_finished).
            is_winner = (not self._running and self._winner is not None
                         and pt["size"] == self._winner.get("size")
                         and pt["fps"] == self._winner.get("fps")
                         and pt["quality"] == self._winner.get("quality"))
            if is_winner:
                col = QColor("#00e676")
            # Halo on the latest live point
            if self._running and i == len(self._points) - 1:
                halo = QColor(col); halo.setAlpha(80)
                p.setBrush(QBrush(halo)); p.setPen(Qt.NoPen)
                p.drawEllipse(QPoint(x, y), 7, 7)
            p.setBrush(QBrush(col))
            p.setPen(QColor("#0d0d18"))
            r = 5 if (in_bracket or is_winner) else 4
            p.drawEllipse(QPoint(x, y), r, r)

        # Axis labels (tiny). Y: target in MB; X: iteration count.
        p.setPen(QColor("#888"))
        font = p.font(); font.setPointSize(7); font.setItalic(False); p.setFont(font)
        target_mb = (self._target or 0) / (1024.0 * 1024.0)
        p.drawText(2, target_y + 4, f"{target_mb:.1f}MB")
        p.drawText(2, gy0 + 8, "Mb")
        last = self._points[-1]
        last_mb = last["size"] / (1024.0 * 1024.0)
        status = "WIN" if (not self._running and self._winner is not None) else f"#{last['iter']}"
        p.setPen(QColor("#aaa"))
        p.drawText(gx0, gy1 + 12,
                   f"{status}  ·  last: {last_mb:.2f}MB  Q{last['quality']} F{last['fps']}  ·  {len(self._points)} iter")

        # --- Trajectory line: compact recap of the last N attempts -----
        # Always visible, no hover required. This is the "see what was tried
        # without opening the console" channel. Truncated to whatever fits
        # the available width so the strip never wraps onto a new line.
        # Format per chip: "#3 Q72/F18 1.42↑". Color is muted (single tone)
        # for readability; per-phase coloring would split into multiple
        # drawText calls and add complexity for little gain — the dots above
        # already convey phase visually.
        traj_y = gy1 + 26
        p.setPen(QColor("#7a8aa0"))
        font = p.font(); font.setPointSize(7); font.setItalic(False); p.setFont(font)
        # Build chip strings for ALL points, then truncate from the LEFT
        # (so the most recent attempts are always visible) until they fit.
        chips = []
        for pt in self._points:
            arrow, _ = self._arrow_for(pt)
            sz = pt["size"] / (1024.0 * 1024.0)
            chips.append(f"#{pt['iter']} Q{pt['quality']}/F{pt['fps']} {sz:.2f}{arrow}")
        if self._winner and not self._running:
            wmb = self._winner['size'] / (1024.0 * 1024.0)
            chips.append(f"★ Q{self._winner['quality']}/F{self._winner['fps']} {wmb:.2f}MB")
        sep = "   "
        text = sep.join(chips)
        # Drop chips from the left until it fits the available width.
        fm = p.fontMetrics()
        avail = w - gx0 - 4
        while chips and fm.horizontalAdvance(text) > avail:
            chips.pop(0)
            text = ("…" + sep + sep.join(chips)) if chips else ""
        if text:
            p.drawText(gx0, traj_y, text)


class TimelineWidget(QWidget):
    """Custom timeline bar that draws In/Out markers and scrub position."""
    seeked = Signal(float)  # 0.0-1.0
    # Emitted when a segment (or run of consecutive segments) is selected via
    # the segment-select gesture. Carries (start_ratio, end_ratio) in 0-1
    # source-time units. The OUT ratio is EXCLUSIVE: it equals the cut PTS
    # that ends the segment (= first frame of the NEXT segment) so the
    # engine's [in, out) trim math doesn't bleed an extra frame.
    segment_selected = Signal(float, float)
    # Emitted whenever the visible viewport changes. Carries the current zoom
    # factor (1.0 = full duration, 2.0 = half visible, etc.) so external UI
    # (TrimDialog) can update the zoom indicator label.
    zoom_changed = Signal(float)

    # Tightest allowed view span. Default = ~0.1% of source for clips with
    # unknown frame count; once the dialog calls set_total_frames(N) we
    # tighten to "1 frame visible" = max(1/N, 0.0001), so users can zoom
    # right down to a single source frame on long clips without the floor
    # capping them prematurely. Floored at 0.0001 to avoid float-precision
    # weirdness at extreme zooms.
    MIN_VIEW_SPAN = 0.001

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)  # +8px so the new ruler tick band fits without
                                 # overlapping the active region.
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        # Hover preview needs mouse moves WITHOUT a button held.
        self.setMouseTracking(True)
        self.pos_ratio = 0.0   # current playhead 0-1
        self.in_ratio  = 0.0   # in point 0-1
        self.out_ratio = 1.0   # out point 0-1
        self.cut_ratios = []   # list[float 0-1] — detected scene cuts
        # When False, cut markers and snap halo are NOT drawn AND _nearest_
        # snap_cut_idx returns None (so clicks/drags don't snap). The
        # actual cut data is preserved in self.cut_ratios so toggling back
        # ON instantly re-enables snap without re-running detection. Owned
        # by TrimDialog's "view cuts" toggle button.
        self.cuts_visible = True
        # Segment-select state. None = no segment selection (free trim mode);
        # otherwise (start_idx, end_idx) inclusive, indexed against the segment
        # list built from boundaries [0, *cut_ratios, 1].
        self.sel_seg_range = None
        # Anchor for range-fill: the index of the FIRST segment chosen in the
        # current selection cycle. Subsequent shift-clicks extend from this
        # anchor up to the clicked index, filling everything in between (NLE /
        # file-explorer convention). Reset to None when the user breaks the
        # selection (clear, manual I/O, new cuts list, plain click in select mode).
        self.sel_anchor_idx = None
        # Soft-green hover preview: the would-be selection if the user clicked
        # at the current cursor position. Computed in mouseMoveEvent and only
        # active while the user is "in select gesture" (Shift held OR select
        # mode toggled on).
        self.hover_seg_range = None
        # When True, plain left clicks on the timeline behave as segment-select
        # (no Shift required). Toggled by an external button in TrimDialog.
        self.select_mode = False
        # Cut index that's currently within snap range under the cursor.
        # When non-None, paintEvent draws a halo around that cut so the user
        # gets WYSIWYG feedback that "click here = land on this cut". Reset
        # on leave / on segment-select gesture (which has its own preview).
        self.snap_hover_idx = None
        # Pixel snap threshold — single source of truth used by both the
        # mousePress click-snap and the hover halo, so they always agree on
        # what counts as "near a cut".
        self._snap_px = 6
        # Per-instance min view span; the class constant above is the safe
        # floor used until the dialog hands us the source's total frame
        # count via set_total_frames().
        self._min_view_span = self.MIN_VIEW_SPAN
        # Visible viewport in SOURCE-RATIO space. (0.0, 1.0) = whole clip; any
        # zoom-in narrows this to a sub-range that gets stretched across the
        # widget width. ALL paint and click math goes through _src_to_x /
        # _x_to_src to translate between source ratios and screen pixels —
        # don't reach into the raw `* w` math anywhere else.
        self.view_start_r = 0.0
        self.view_end_r = 1.0

    # --- Viewport math ----------------------------------------------------
    # Every screen-space conversion goes through these two helpers so adding /
    # changing zoom semantics doesn't require auditing the entire paint path.

    def _view_span(self):
        return max(self._min_view_span, self.view_end_r - self.view_start_r)

    def _src_to_x(self, src_r, w):
        """Source ratio (0..1) → screen x in pixels. May fall outside [0, w]
        when the source point is outside the visible viewport; callers that
        draw lines/rects should clip or skip as appropriate."""
        return int((src_r - self.view_start_r) / self._view_span() * w)

    def _x_to_src(self, x, w):
        """Screen x → source ratio. Clamped to [0, 1] so clicks at the very
        edges of the viewport still resolve to a legal source position."""
        if w <= 0:
            return 0.0
        r = self.view_start_r + (x / w) * self._view_span()
        return max(0.0, min(1.0, r))

    def _x_in_view(self, x, w):
        return 0 <= x <= w

    def paintEvent(self, ev):
        from PySide6.QtGui import QPainter, QLinearGradient, QBrush
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Track background
        p.setBrush(QBrush(QColor("#1a1a2a")))
        p.setPen(Qt.NoPen)
        p.drawRect(0, 0, w, h)

        # Ruler band (top 8px) — when zoomed in we draw a faint shaded strip
        # showing what fraction of the source is currently visible. This is
        # the "minimap"-style cue NLEs use so the user never loses context.
        if self.view_start_r > 0.0 or self.view_end_r < 1.0:
            ruler_h = 6
            # Underlay: full source range (dim).
            p.setBrush(QBrush(QColor("#0d0d18")))
            p.drawRect(0, 0, w, ruler_h)
            # Highlight: visible viewport mapped against the FULL source.
            vx_s = int(self.view_start_r * w)
            vx_e = int(self.view_end_r   * w)
            p.setBrush(QBrush(QColor("#3949ab")))
            p.drawRect(vx_s, 0, max(2, vx_e - vx_s), ruler_h)

        # Active region (between in-out). Painted GREEN when the user has an
        # active segment selection so they can tell at a glance "this trim is
        # segment-aligned" vs. a free trim. Manual I/O changes drop
        # sel_seg_range back to None → blue.
        x_in  = self._src_to_x(self.in_ratio,  w)
        x_out = self._src_to_x(self.out_ratio, w)
        # Clip the rectangle to the widget so a partially-offscreen trim
        # doesn't paint outside its bounds (or compute a negative width).
        rx_in  = max(0, min(w, x_in))
        rx_out = max(0, min(w, x_out))
        active_color = "#1e7d32" if self.sel_seg_range is not None else "#1e3a8c"
        p.setBrush(QBrush(QColor(active_color)))
        p.drawRect(rx_in, 0, max(0, rx_out - rx_in), h)

        # Hover preview (softer green, semi-transparent). Drawn ABOVE the
        # active region but BELOW the cut ticks/markers so the user can still
        # see their existing selection underneath while previewing the new one.
        if self.hover_seg_range is not None:
            bounds = self._segment_bounds()
            s_idx, e_idx = self.hover_seg_range
            if 0 <= s_idx < len(bounds) - 1 and 0 <= e_idx < len(bounds) - 1:
                x_s = max(0, min(w, self._src_to_x(bounds[s_idx],     w)))
                x_e = max(0, min(w, self._src_to_x(bounds[e_idx + 1], w)))
                hover_col = QColor("#66bb6a"); hover_col.setAlpha(110)
                p.setBrush(QBrush(hover_col))
                p.drawRect(x_s, 0, max(0, x_e - x_s), h)

        # Scene cut marks (orange, semi-transparent vertical lines).
        # Drawn UNDER markers/playhead so the manual in/out and scrub head stay readable.
        # Skipped entirely when cuts_visible is off — the cuts list is
        # still preserved in memory so toggling back on doesn't re-detect.
        if self.cut_ratios and self.cuts_visible:
            # Adaptive alpha: with hundreds of cuts the bars overlap into a
            # solid orange band that hides the underlying region color and
            # the in/out markers. Scale alpha down past 200 cuts so density
            # reads as "many" without saturating the timeline. Floor at 60
            # so individual cuts never disappear entirely.
            n = len(self.cut_ratios)
            if n <= 200:
                alpha = 180
            else:
                alpha = max(60, 180 - int((n - 200) * 0.4))
            cut_color = QColor("#ffab00"); cut_color.setAlpha(alpha)
            p.setPen(cut_color)
            for cr in self.cut_ratios:
                # Skip cuts outside the visible viewport — drawing them would
                # paint at negative x or past the right edge and waste cycles.
                if not (self.view_start_r <= cr <= self.view_end_r):
                    continue
                xc = self._src_to_x(cr, w)
                p.drawLine(xc, 4, xc, h - 4)

        # Snap halo — when the cursor hovers within snap distance of a cut
        # (and we're NOT mid segment-select gesture), draw a wider, brighter
        # vertical band around it as a "click here = snap" preview. Cheap
        # WYSIWYG feedback so users don't wonder why their click suddenly
        # jumped a few pixels. Only painted when a click would actually land
        # on the cut, so it's never ambiguous.
        if (self.cuts_visible
                and self.snap_hover_idx is not None
                and 0 <= self.snap_hover_idx < len(self.cut_ratios)):
            cr = self.cut_ratios[self.snap_hover_idx]
            if self.view_start_r <= cr <= self.view_end_r:
                xc = self._src_to_x(cr, w)
                halo = QColor("#ffd54f"); halo.setAlpha(110)
                p.setBrush(QBrush(halo))
                p.setPen(Qt.NoPen)
                p.drawRect(xc - 4, 2, 8, h - 4)
                # Bright core line on top so the exact landing point is unmistakable.
                p.setPen(QColor("#fff176"))
                p.drawLine(xc, 2, xc, h - 2)

        # In marker (green) — only paint if visible.
        if self._x_in_view(x_in, w):
            p.setPen(QColor("#00c853"))
            p.setBrush(QBrush(QColor("#00c853")))
            p.drawRect(x_in, 0, 3, h)

        # Out marker (red) — only paint if visible.
        if self._x_in_view(x_out, w):
            p.setPen(QColor("#ff4444"))
            p.setBrush(QBrush(QColor("#ff4444")))
            p.drawRect(x_out - 3, 0, 3, h)

        # Playhead (white). When zoomed in, the playhead may be outside the
        # viewport — skip drawing in that case rather than clipping to an
        # edge and giving a misleading position cue.
        x_ph = self._src_to_x(self.pos_ratio, w)
        if self._x_in_view(x_ph, w):
            p.setPen(QColor("#ffffff"))
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawRect(x_ph - 1, 0, 2, h)
            from PySide6.QtGui import QPolygon
            from PySide6.QtCore import QPoint
            tri = QPolygon([QPoint(x_ph-5, 0), QPoint(x_ph+5, 0), QPoint(x_ph, 8)])
            p.drawPolygon(tri)

    def _segment_bounds(self):
        """Return the sorted list of segment boundary ratios: [0, *cuts, 1].
        With N internal cuts there are N+1 segments, segment k spans
        bounds[k] .. bounds[k+1]."""
        bounds = sorted(set([0.0] + [c for c in self.cut_ratios if 0.0 < c < 1.0] + [1.0]))
        return bounds

    def _segment_index_at(self, ratio):
        """Return the segment index that contains `ratio`, or -1 if none."""
        bounds = self._segment_bounds()
        for i in range(len(bounds) - 1):
            if bounds[i] <= ratio < bounds[i+1]:
                return i
        # Right edge — clamp to last segment so a click at exactly 1.0 still works.
        if ratio >= 1.0 and len(bounds) >= 2:
            return len(bounds) - 2
        return -1

    def _has_segments(self):
        return len(self._segment_bounds()) >= 2

    def _emit_segment_range(self):
        """Translate sel_seg_range into (start_ratio, end_ratio) and emit. End
        is the cut PTS of the segment after `end_idx`, so the engine's
        exclusive OUT lands exactly on the next scene's first frame."""
        if self.sel_seg_range is None:
            return
        s_idx, e_idx = self.sel_seg_range
        bounds = self._segment_bounds()
        if not (0 <= s_idx < len(bounds) - 1) or not (0 <= e_idx < len(bounds) - 1):
            return
        self.segment_selected.emit(bounds[s_idx], bounds[e_idx + 1])

    def _compute_target_range(self, idx, shift_held):
        """Given a clicked segment `idx` and whether Shift is currently held,
        return the (start, end) range that should be selected/previewed.

        Rule (NLE / Explorer style):
          - Shift WITH an existing anchor → fill from anchor to idx (inclusive
            both ends), regardless of how many segments lie between.
          - Otherwise → single-segment selection (idx, idx). The next non-shift
            click in select mode RESETS the anchor; that's how you start a new
            multi-select from scratch."""
        if shift_held and self.sel_anchor_idx is not None:
            a = self.sel_anchor_idx
            return (min(a, idx), max(a, idx))
        return (idx, idx)

    def mousePressEvent(self, e):
        w = self.width()
        if w <= 0:
            return

        # Right-click is a dedicated "deselect segment" gesture. It clears the
        # green selection + anchor without needing to toggle SEG MODE off, and
        # without touching IN/OUT (so the user keeps their trim values). This
        # is the missing escape hatch the user asked for: once a green range
        # is painted, you can drop it instantly with right-click.
        if e.button() == Qt.RightButton:
            if (self.sel_seg_range is not None
                    or self.sel_anchor_idx is not None
                    or self.hover_seg_range is not None):
                self.sel_seg_range = None
                self.sel_anchor_idx = None
                self.hover_seg_range = None
                self.update()
            return

        ratio = self._x_to_src(e.x(), w)
        shift = bool(e.modifiers() & Qt.ShiftModifier)

        # Segment-select gesture: triggered by Shift+Click anywhere, OR by a
        # plain click while select_mode is on (user toggled the SEG MODE button).
        do_segment = (shift or self.select_mode) and self._has_segments()
        if do_segment:
            idx = self._segment_index_at(ratio)
            if idx >= 0:
                # Shift extends from the existing anchor; non-shift starts a new
                # selection and resets the anchor. This mirrors how Explorer's
                # "click + shift+click" works.
                if not shift:
                    self.sel_anchor_idx = idx
                self.sel_seg_range = self._compute_target_range(idx, shift)
                # Hover preview is now equal to the actual selection — refresh
                # so the cursor doesn't have to move to repaint the right shade.
                self.hover_seg_range = self.sel_seg_range
                self._emit_segment_range()
                self.update()
                return

        # Plain click → scrub with click-snap to nearby cuts. We do NOT clear
        # sel_seg_range here so the green selection persists while the user
        # scrubs; only manual I/O changes invalidate it.
        # Snap distance is in PIXELS so it stays consistent regardless of
        # current zoom level — at higher zoom you can land on a cut without
        # being pixel-perfect, but the source-time threshold scales down
        # accordingly (good — the user can also scrub off-cut more precisely).
        snap_idx = self._nearest_snap_cut_idx(ratio, w)
        if snap_idx is not None:
            ratio = self.cut_ratios[snap_idx]
        self.seeked.emit(ratio)

    def mouseMoveEvent(self, e):
        w = self.width()
        if w <= 0:
            return
        ratio = self._x_to_src(e.x(), w)
        shift = bool(e.modifiers() & Qt.ShiftModifier)
        in_select_gesture = shift or self.select_mode

        # Hover preview: only when the user is "in segment-select gesture"
        # (Shift held OR select_mode toggled on) AND we have segments to pick.
        new_hover = None
        if in_select_gesture and self._has_segments():
            idx = self._segment_index_at(ratio)
            if idx >= 0:
                new_hover = self._compute_target_range(idx, shift)
        if new_hover != self.hover_seg_range:
            self.hover_seg_range = new_hover
            self.update()

        # Snap halo — only meaningful for plain scrub. While the user is
        # composing a segment selection the green hover preview already
        # signals the click target, so layering a snap halo on top would be
        # noisy (and the click won't snap-to-cut anyway in that path).
        new_snap = None if in_select_gesture else self._nearest_snap_cut_idx(ratio, w)
        if new_snap != self.snap_hover_idx:
            self.snap_hover_idx = new_snap
            self.update()

        # Drag-scrub: only when left button is held AND we're not in a select
        # gesture, otherwise dragging would emit spurious seeks while the user
        # is composing a Shift+Click range.
        if (e.buttons() & Qt.LeftButton) and not in_select_gesture:
            # Snap during drag too, so dragging near a cut also lands on it.
            scrub_ratio = (self.cut_ratios[new_snap]
                           if new_snap is not None else ratio)
            self.seeked.emit(scrub_ratio)

    def wheelEvent(self, e):
        """Mouse-wheel interactions on the timeline:
          - plain wheel  → ZOOM (centered on cursor x)
          - Shift+wheel  → PAN horizontally (one notch ≈ 10% of visible span)

        The cursor's source position is held constant during zoom so the user
        can drill into the exact frame they're hovering — same convention as
        Premiere/Resolve/Audition. Volume and other widgets in the dialog
        keep their own wheel handlers; Qt routes wheel by hover so they don't
        conflict.
        """
        delta = e.angleDelta().y()
        if delta == 0:
            return
        w = self.width()
        if w <= 0:
            return
        mods = e.modifiers()
        shift = bool(mods & Qt.ShiftModifier)

        try:
            cursor_x = float(e.position().x())
        except AttributeError:
            cursor_x = float(e.x())  # PySide6 < 6.0 fallback

        if shift:
            # Pan: 1 notch = 10% of currently-visible range.
            pan_units = (delta / 120.0) * 0.1
            shift_amt = -pan_units * self._view_span()
            self._set_view(self.view_start_r + shift_amt,
                           self.view_end_r   + shift_amt)
            e.accept()
            return

        # Zoom: 1 notch = 1.2x in/out. Wheel UP (positive delta) zooms IN.
        steps = delta / 120.0
        factor = (1.0 / 1.2) ** steps
        cursor_src = self._x_to_src(cursor_x, w)
        new_span = self._view_span() * factor
        new_span = max(self._min_view_span, min(1.0, new_span))
        # Anchor the cursor's source position at its current screen x so the
        # frame under the cursor doesn't visually slide during zoom.
        anchor_frac = cursor_x / w
        new_start = cursor_src - anchor_frac * new_span
        self._set_view(new_start, new_start + new_span)
        e.accept()

    def _nearest_snap_cut_idx(self, ratio, w):
        """Return the index of the closest cut to `ratio` if it falls within
        snap_px pixels at the current zoom, else None. Centralized so click,
        drag, and hover-halo all agree on what "snap-eligible" means.

        We compute the threshold in PIXEL space (`px / w * span`) so zooming
        in tightens the source-time tolerance — at high zoom the user can
        scrub off-cut precisely, while at low zoom a soft 6px window keeps
        snapping forgiving."""
        if not self.cut_ratios or not self.cuts_visible:
            return None
        span = self._view_span()
        # When the timeline is collapsed (w==0 during early layout) bail.
        if w <= 0:
            return None
        thr_src = (self._snap_px / w) * span
        # min() over (distance, idx) so ties go to the lowest-indexed cut
        # deterministically.
        nearest_idx = min(range(len(self.cut_ratios)),
                          key=lambda i: abs(self.cut_ratios[i] - ratio))
        if abs(self.cut_ratios[nearest_idx] - ratio) <= thr_src:
            return nearest_idx
        return None

    def leaveEvent(self, e):
        # Drop the hover overlay when the cursor leaves the timeline so the
        # widget doesn't keep a stale ghost rectangle.
        dirty = False
        if self.hover_seg_range is not None:
            self.hover_seg_range = None
            dirty = True
        if self.snap_hover_idx is not None:
            self.snap_hover_idx = None
            dirty = True
        if dirty:
            self.update()

    def set_position(self, ratio):
        self.pos_ratio = ratio; self.update()

    def set_in(self, ratio, manual=True):
        # `manual=True` (the default) means this came from a user I press or
        # the initial restore; that invalidates any segment-selection overlay
        # AND its anchor so the visual stays truthful. `manual=False` is used
        # by the segment-select flow itself to move I/O without nuking state.
        self.in_ratio = ratio
        if manual:
            self.sel_seg_range = None
            self.sel_anchor_idx = None
        self.update()

    def set_out(self, ratio, manual=True):
        self.out_ratio = ratio
        if manual:
            self.sel_seg_range = None
            self.sel_anchor_idx = None
        self.update()

    def set_cuts(self, ratios):
        # Cut list changed → any prior segment indices are no longer valid.
        self.cut_ratios = list(ratios or [])
        self.sel_seg_range = None
        self.sel_anchor_idx = None
        self.hover_seg_range = None
        self.snap_hover_idx = None
        self.update()

    def set_cuts_visible(self, on):
        """Show/hide the orange cut markers + snap halo on the timeline.
        When False, ``_nearest_snap_cut_idx`` returns None so clicks and
        drags don't snap either — single switch covers both visual and
        behavioral aspects so the timeline can read truly "clean" when
        the user wants to ignore detected scenes."""
        self.cuts_visible = bool(on)
        # Drop any stale halo state so we don't briefly flash a snap hint
        # when toggling back on (it'll be recomputed on the next mouse move).
        self.snap_hover_idx = None
        self.update()

    def set_select_mode(self, on):
        """Toggle 'always-on' segment select. When on, plain left clicks pick
        the segment under the cursor (no Shift required). Shift+Click still
        works the same way regardless.

        Toggling OFF *also* clears the active green selection AND its anchor —
        otherwise the green range would linger on the timeline with no way to
        get rid of it (the toggle was effectively one-way before). The IN/OUT
        markers themselves stay put: dropping the visual cue doesn't undo the
        user's trim work. Use CLEAR TRIM to reset trim entirely.

        Cursor swap: CrossCursor when select_mode is ON so the user gets a
        proprioceptive cue that "click here = pick a region", instead of the
        regular scrub PointingHandCursor.
        """
        self.select_mode = bool(on)
        if not self.select_mode:
            self.sel_seg_range = None
            self.sel_anchor_idx = None
            self.hover_seg_range = None
        self.setCursor(Qt.CrossCursor if self.select_mode else Qt.PointingHandCursor)
        self.update()

    def clear_segment_selection(self):
        if self.sel_seg_range is not None or self.sel_anchor_idx is not None:
            self.sel_seg_range = None
            self.sel_anchor_idx = None
            self.update()

    # --- Zoom / pan API -------------------------------------------------
    # External UI (zoom +/- buttons, FIT button) drives the viewport through
    # these. _set_view does the clamping so the rest of the code can be
    # naive about over/underflow.

    def _set_view(self, start_r, end_r):
        """Apply (start_r, end_r) as the new viewport, clamping to [0,1] and
        enforcing a minimum span. Repaints + emits zoom_changed only if the
        view actually changed."""
        span = max(self._min_view_span, min(1.0, end_r - start_r))
        # Re-derive end from the (possibly-clamped) span first, then slide
        # the pair into legal range. Sliding (instead of independently
        # clamping start/end) preserves the requested span — important when
        # zooming in near an edge.
        if start_r < 0.0:
            start_r = 0.0
        if start_r + span > 1.0:
            start_r = 1.0 - span
        end_r = start_r + span
        if (start_r, end_r) == (self.view_start_r, self.view_end_r):
            return
        self.view_start_r = start_r
        self.view_end_r = end_r
        self.update()
        self.zoom_changed.emit(self.zoom_factor())

    def zoom_factor(self):
        """Current zoom expressed as a multiplier. 1.0 = full source visible."""
        return 1.0 / self._view_span()

    def reset_view(self):
        """FIT the entire source into view (zoom = 1x)."""
        self._set_view(0.0, 1.0)

    def set_total_frames(self, n):
        """Tighten the zoom-in floor to "exactly 1 source frame visible".

        Without this, MIN_VIEW_SPAN=0.001 caps zoom at 1000× regardless of
        clip length — fine for short clips, but on a 10-minute video that
        means the tightest visible window is ~0.6s = 18 frames at 30fps,
        which isn't fine enough to land on a specific frame visually.
        Setting this to total_frames lets users zoom right down to a single
        frame's width on long clips. Floored at 0.0001 to keep float math
        well-conditioned at extreme zooms."""
        try:
            n = int(n)
        except (TypeError, ValueError):
            return
        if n <= 0:
            return
        self._min_view_span = max(0.0001, 1.0 / n)
        # If we're currently zoomed past the new floor (e.g. user changed
        # source mid-session), nudge the view to comply.
        if self._view_span() < self._min_view_span:
            self._set_view(self.view_start_r,
                           self.view_start_r + self._min_view_span)

    def zoom_in(self, factor=1.25):
        """Programmatic zoom in centered on the playhead — used by the +
        button so the keyboard/button flow doesn't depend on mouse position."""
        center = max(self.view_start_r, min(self.view_end_r, self.pos_ratio))
        new_span = max(self._min_view_span, self._view_span() / factor)
        self._set_view(center - new_span / 2.0, center + new_span / 2.0)

    def zoom_out(self, factor=1.25):
        center = max(self.view_start_r, min(self.view_end_r, self.pos_ratio))
        new_span = min(1.0, self._view_span() * factor)
        self._set_view(center - new_span / 2.0, center + new_span / 2.0)

    def follow_playhead(self):
        """Auto-pan the viewport so the playhead stays visible during
        playback. NLE convention: when the playhead leaves the visible
        range, "page" the view so that:
          - if it crossed the RIGHT edge → reposition the playhead at ~10%
            from the left, exposing the next ~90% of upcoming content.
          - if it crossed the LEFT edge (rewind / J-key)  → reposition at
            ~90% from the left, exposing the prior ~90%.

        Only acts when actually zoomed in (view span < 1.0). At 1× the whole
        clip is visible and there's nothing to follow. Caller is responsible
        for deciding WHEN to invoke this (e.g. only during PlayingState) so
        manual scrubs don't yank the viewport.

        Returns True if the view was actually moved (useful for tests / log
        diagnostics)."""
        span = self._view_span()
        if span >= 1.0:
            return False
        if self.view_start_r <= self.pos_ratio <= self.view_end_r:
            return False
        if self.pos_ratio > self.view_end_r:
            new_start = self.pos_ratio - span * 0.1   # show what's coming
        else:
            new_start = self.pos_ratio - span * 0.9   # show what just passed
        prev_start, prev_end = self.view_start_r, self.view_end_r
        self._set_view(new_start, new_start + span)
        return (self.view_start_r, self.view_end_r) != (prev_start, prev_end)


class _PrecisePreviewBridge(QObject):
    """Background decode → main thread via queued Signal (Qt thread-safe)."""
    decode_done = Signal(object, int, int, int, bool, int)  # png, gen, vw, vh, exact, fi
    playback_proxy_ready = Signal(str)  # path or ""


class TrimDialog(QDialog):
    """NLE-style trim dialog. Returns in_sec / out_sec (float seconds, framerate-agnostic)."""
    def __init__(self, task, parent=None, initial_in_sec=0.0, initial_out_sec=None):
        super().__init__(parent)
        # Before any installEventFilter — layout/resize can call eventFilter early.
        self._tc_app_filter = False
        self._precise_shutdown = False
        self.task = task
        self.setWindowTitle(f"✂️ Trim — {task.filename}")
        self.setMinimumSize(800, 600)
        self.resize(1024, 768)
        self.setStyleSheet(GLOBAL_STYLE)

        self.fps = float(task.specs.get('fps', 25) or 25)
        duration = float(task.specs.get('duration', 0) or 0)
        if duration <= 0:
            duration = task.specs.get('t_frames', 1) / self.fps

        self.duration_sec = max(duration, 1.0)

        # Source frame count — same discrete timeline the encoder uses with
        # fps=source_fps:round=down.  `t_frames` from ffprobe when present;
        # otherwise derive from duration so the last steppable frame is
        # N-1, not N (avoids int(duration*fps) off-by-one).
        tf_probe = int(task.specs.get("t_frames") or 0)
        approx_tf = (
            max(1, int(round(self.duration_sec * self.fps)))
            if self.fps > 0 else 1
        )
        self._total_source_frames = tf_probe if tf_probe > 0 else approx_tf
        if self.fps > 0:
            self._max_frame_idx = max(0, self._total_source_frames - 1)
            self._default_out_sec = self._total_source_frames / self.fps
        else:
            self._max_frame_idx = 0
            self._default_out_sec = self.duration_sec

        # Internal pointers stored as SECONDS (framerate-agnostic)
        self.in_sec = float(initial_in_sec or 0.0)
        self.out_sec = (
            float(initial_out_sec)
            if initial_out_sec is not None
            else self._default_out_sec
        )
        self.current_sec = 0.0
        # Logical frame tracker.  QMediaPlayer's setPosition() seeks to the
        # nearest keyframe and reports integer-ms positions, so repeated
        # arrow-key steps can drift or stick.  When this is not None,
        # _step_sec and _displayed_frame_sec use it instead of re-deriving
        # from the player's imprecise position.  Reset to None on any
        # non-stepping action (play, scrub, JKL shuttle, timeline click).
        self._step_frame_idx = None
        # Last frame the user chose as OUT (inclusive). Avoids float out_sec ↔ fi drift.
        self._out_incl_fi = None
        self._loop_play_fi = None
        self._loop_playing = False
        self._loop_seek_guard = False
        self._loop_last_shown_fi = None
        self._tc_edit_block = False
        self._precise_display_fi = None
        self._frame_png_cache = {}
        self._frame_cache_order = []
        self._frame_cache_max = 48
        self._thumb_loader = _AsyncThumbLoader(self)  # PR1: async IN/OUT thumbs
        self.cuts_fi = []
        self.jkl_speed = 0.0       # current JKL shuttle speed (neg=reverse)
        self._jkl_speeds = [1.0, 2.0, 4.0, 8.0]
        self._k_held = False       # True while K is physically held
        self._k_step_timer = QTimer(self)
        self._k_step_timer.setInterval(80)
        self._k_step_timer.timeout.connect(self._k_step_tick)
        self._k_step_dir = 0       # -1 or +1 when K+J / K+L active
        self._rev_timer = QTimer(self)
        self._rev_timer.timeout.connect(self._rev_tick)
        self._loop_timer = QTimer(self)
        self._loop_timer.timeout.connect(self._loop_frame_tick)
        self._stutter_wall_t0 = 0.0
        self._stutter_pos_t0 = 0
        self._stutter_samples = []    # recent (wall_delta, pos_delta) pairs
        self._stutter_state = False   # True when stutter is detected

        # Scene detection state
        self.cuts_sec = []          # list[float] — detected scene-change times
        self.scene_worker = None    # active SceneDetectorWorker, if any
        self.snap_threshold_sec = 0.30  # max distance to snap-correct in/out to a cut
        self._scene_threshold = 0.30
        # Content-fingerprint key for the persistent scene cache (RAM + disk).
        # Computed once in __init__ so cache reads/writes don't re-hash on every
        # detect cycle. May be None if we can't read the file.
        self._scene_content_key = _video_content_key(task.path)
        self._source_media_path = task.path
        self._playback_proxy_path = None
        self._proxy_build_running = False
        self._pending_playback_pos_ms = None
        src_w = int(task.specs.get("w") or 0)
        src_h = int(task.specs.get("h") or 0)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # --- Video Widget ---
        self.video_widget = QVideoWidget()
        self.video_widget.setFocusPolicy(Qt.StrongFocus)
        self.video_widget.setStyleSheet("background: black;")
        # Native video surfaces on Windows can swallow wheel events before
        # they bubble up to the dialog; an event filter routes them into
        # _adjust_volume_by_wheel so wheel-over-video still adjusts volume.
        self.video_widget.installEventFilter(self)
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_widget)
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(task.path))
        self.player.durationChanged.connect(self._on_player_duration_changed)
        self.audio_output.setVolume(0.0)
        layout.addWidget(self.video_widget, 1)

        # --- Frame-exact preview overlay (paused only) ---
        # QVideoWidget / QMediaPlayer seek to keyframes and report coarse ms
        # positions — they cannot match NLE surgical accuracy.  While paused,
        # we paint the exact frame from cv2/ffmpeg on top so what you see is
        # what I/O will capture.
        self._precise_frame = QLabel(self.video_widget)
        self._precise_frame.setAlignment(Qt.AlignCenter)
        self._precise_frame.setStyleSheet("background: #000000;")
        self._precise_frame.setScaledContents(False)
        self._precise_frame.hide()

        # Async frame-exact preview: decode off the UI thread + debounced timeline
        # seeks so scrubbing stays responsive. Results coalesce if decode lags.
        self._precise_bridge = _PrecisePreviewBridge(self)
        self._precise_bridge.decode_done.connect(self._on_precise_decode_finished)
        self._precise_bridge.playback_proxy_ready.connect(self._on_playback_proxy_ready)
        self._preview_gen = 0
        self._precise_lock = threading.Lock()
        self._precise_worker_busy = False
        self._precise_coalesce = None  # (gen, path, fi, fps, tw, th, vw, vh, exact)
        self._precise_seek_timer = QTimer(self)
        self._precise_seek_timer.setSingleShot(True)
        self._precise_seek_timer.setInterval(75)
        self._precise_seek_timer.timeout.connect(self._debounced_scrub_preview_flush)
        self._precise_resize_timer = QTimer(self)
        self._precise_resize_timer.setSingleShot(True)
        self._precise_resize_timer.setInterval(120)
        self._precise_resize_timer.timeout.connect(self._debounced_scrub_preview_flush)

        # --- Playback speed overlay (floats over bottom of video, no layout push) ---
        self._lbl_speed = QLabel("", self.video_widget)
        self._lbl_speed.setAlignment(Qt.AlignCenter)
        self._lbl_speed.setStyleSheet(
            "color: #ccc; font-size: 10px; font-weight: bold; "
            "background: rgba(0, 0, 0, 160); border: none; "
            "padding: 3px 10px; border-radius: 3px;"
        )
        self._lbl_speed.setFixedHeight(20)
        self._lbl_speed.hide()

        # --- VFR warning banner (only shown when source is variable framerate) ---
        # ffprobe-detected variable-framerate sources break frame-perfect
        # trim assumptions (1/fps is no longer constant, NLE TC drifts).
        # We don't try to silently fix it (re-encoding to CFR is a destructive
        # decision the user should make explicitly) — we just flag it loudly
        # right above the timeline so it's the first thing they see.
        if task.specs.get("is_vfr"):
            r_fps = task.specs.get("r_fps")
            a_fps = task.specs.get("avg_fps")
            detail = ""
            if r_fps and a_fps:
                detail = (
                    f" (declared {format_fps_for_display(r_fps)} fps"
                    f" · measured avg {format_fps_for_display(a_fps)} fps)"
                )
            vfr_banner = QLabel(
                f"⚠ Variable framerate detected{detail}. Frame-perfect trim "
                "may drift by 1–2 frames on long clips. For frame-accurate "
                "results, re-encode the source to constant framerate first."
            )
            vfr_banner.setWordWrap(True)
            vfr_banner.setStyleSheet(
                "background: #3a2a10; color: #ffd54f; border: 1px solid #b07a00; "
                "border-radius: 3px; padding: 6px 10px; font-size: 11px; font-weight: bold;"
            )
            layout.addWidget(vfr_banner)

        # --- Custom Timeline ---
        self.timeline = TimelineWidget()
        # Tell the timeline how many source frames there are so its zoom-in
        # floor lets the user reach "1 frame visible" on long clips. Falls
        # back to the conservative class default if we have no count.
        total_frames = self._total_source_frames
        if total_frames > 0:
            self.timeline.set_total_frames(total_frames)
        layout.addWidget(self.timeline)

        # --- Viewport scrollbar (only visible when zoomed in) ---
        # Source-ratio space is mapped to a 0..SCROLL_RES integer range so
        # QScrollBar's native model fits cleanly: pageStep = visible span,
        # value = view_start. Hidden at 1× to avoid visual clutter when
        # there's nothing to scroll. Sync goes both ways through
        # _on_timeline_scroll / _sync_scrollbar with blockSignals to break
        # the would-be feedback loop (set_view → zoom_changed → sync →
        # setValue → valueChanged → set_view → ...).
        self.SCROLL_RES = 10000  # 4 decimal places of precision over [0, 1]
        self.timeline_scroll = QScrollBar(Qt.Horizontal)
        self.timeline_scroll.setMinimum(0)
        self.timeline_scroll.setMaximum(0)         # updated by _sync_scrollbar
        self.timeline_scroll.setPageStep(self.SCROLL_RES)
        self.timeline_scroll.setSingleStep(int(self.SCROLL_RES * 0.02))
        self.timeline_scroll.setVisible(False)     # 1× = full clip, no scrollbar
        self.timeline_scroll.setStyleSheet(
            "QScrollBar:horizontal { height: 10px; background: #1a1a2a; border: 0; }"
            "QScrollBar::handle:horizontal { background: #3949ab; min-width: 20px; border-radius: 4px; }"
            "QScrollBar::handle:horizontal:hover { background: #4a90e2; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }"
            "QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }"
        )
        self.timeline_scroll.valueChanged.connect(self._on_timeline_scroll)
        layout.addWidget(self.timeline_scroll)

        # --- Zoom controls (thin row right under the timeline) ---
        # Wheel-on-timeline is the primary zoom path; these are the
        # discoverable / accessible counterpart so users who don't think to
        # spin the wheel still find them. The "Zoom:" prefix and the live %
        # readout double as a hint that the timeline IS zoomable.
        zoom_row = QHBoxLayout()
        zoom_row.setSpacing(4)
        zoom_row.setContentsMargins(0, 0, 0, 0)
        zoom_btn_style = (
            "QPushButton { background: #2a2a3a; color: #ccc; font-weight: bold; "
            "font-size: 11px; padding: 2px 8px; border-radius: 3px; "
            "border: 1px solid #333; min-width: 22px; } "
            "QPushButton:hover { background: #3a3a4a; color: #fff; } "
            "QPushButton:disabled { color: #555; }"
        )
        lbl_zoom_caption = QLabel("Zoom:")
        lbl_zoom_caption.setStyleSheet("color: #888; font-size: 10px;")
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_in  = QPushButton("+")
        self.btn_zoom_fit = QPushButton("FIT")
        for b in (self.btn_zoom_out, self.btn_zoom_in, self.btn_zoom_fit):
            b.setStyleSheet(zoom_btn_style)
            b.setFocusPolicy(Qt.NoFocus)  # don't steal arrow-key focus from JKL
        self.btn_zoom_out.setToolTip("Zoom out (or scroll wheel down on timeline)")
        self.btn_zoom_in.setToolTip("Zoom in (or scroll wheel up on timeline)")
        self.btn_zoom_fit.setToolTip("Reset zoom to fit the entire clip (1:1)")
        self.lbl_zoom = QLabel("1.0×")
        self.lbl_zoom.setStyleSheet("color: #4a90e2; font-size: 11px; font-weight: bold; min-width: 44px;")
        zoom_hint = QLabel("wheel = zoom · Shift+wheel = pan")
        zoom_hint.setStyleSheet("color: #555; font-size: 10px; font-style: italic;")
        zoom_row.addWidget(lbl_zoom_caption)
        zoom_row.addWidget(self.btn_zoom_out)
        zoom_row.addWidget(self.btn_zoom_in)
        zoom_row.addWidget(self.btn_zoom_fit)
        zoom_row.addWidget(self.lbl_zoom)
        zoom_row.addStretch(1)
        zoom_row.addWidget(zoom_hint)
        layout.addLayout(zoom_row)

        self.btn_zoom_in.clicked.connect(lambda: self.timeline.zoom_in())
        self.btn_zoom_out.clicked.connect(lambda: self.timeline.zoom_out())
        self.btn_zoom_fit.clicked.connect(self.timeline.reset_view)
        self.timeline.zoom_changed.connect(self._on_timeline_zoom_changed)

        nle_hint = QLabel(
            "Preview res: dropdown (Full / ½). LOOP = frame-exact overlay.  "
            "←/→ = one frame. Home/End = first/last frame. IN/OUT TC + Enter.  "
            f"TC grid {nle_tc_fps_int(self.fps)} fps ({format_fps_for_display(self.fps)})."
        )
        nle_hint.setWordWrap(True)
        nle_hint.setStyleSheet(
            "color: #5a7a5a; font-size: 10px; font-style: italic; padding: 0 2px;"
        )
        layout.addWidget(nle_hint)

        # --- Timecode + In/Out Labels + Trim thumbnails ---
        tc_row = QHBoxLayout()
        tc_row.setSpacing(6)
        _trim_thumb_style = (
            "background: #0e0e0e; border: 1px solid #1e1e1e; border-radius: 3px;"
        )
        self._trim_thumb_in = QLabel()
        self._trim_thumb_in.setFixedSize(106, 60)
        self._trim_thumb_in.setAlignment(Qt.AlignCenter)
        self._trim_thumb_in.setStyleSheet(_trim_thumb_style)
        self._trim_thumb_in.setVisible(False)

        _tc_edit_style = (
            "font-size: 13px; font-family: Consolas, 'Menlo', monospace; font-weight: bold; "
            "padding: 2px 6px; border: 1px solid #333; border-radius: 3px; "
            "background: #1a1a2a;"
        )
        lbl_in_tag = QLabel("IN")
        lbl_in_tag.setStyleSheet("font-size: 11px; font-weight: bold; color: #00c853;")
        self.edit_in = NLETimecodeEdit(self, fps=self.fps, text="00:00:00:00")
        self.edit_in.setFocusPolicy(Qt.ClickFocus)
        self.edit_in.setFixedWidth(108)
        self.edit_in.setStyleSheet(_tc_edit_style + " color: #00c853;")
        self.edit_in.setToolTip(
            "IN timecode HH:MM:SS:FF (fixed format). Enter to apply — does not close trim."
        )
        self.lbl_tc = QLabel("00:00:00:00")
        self.lbl_tc.setStyleSheet(
            "font-size: 14px; font-family: Consolas, 'Menlo', monospace; font-weight: bold; color: #4a90e2;"
        )
        lbl_out_tag = QLabel("OUT")
        lbl_out_tag.setStyleSheet("font-size: 11px; font-weight: bold; color: #ff4444;")
        self.edit_out = NLETimecodeEdit(self, fps=self.fps, text="00:00:00:00")
        self.edit_out.setFocusPolicy(Qt.ClickFocus)
        self.edit_out.setFixedWidth(108)
        self.edit_out.setStyleSheet(_tc_edit_style + " color: #ff4444;")
        self.edit_out.setToolTip(
            "OUT timecode — last frame included. Enter to apply — does not close trim."
        )
        self.edit_in.set_fps(self.fps, self._max_frame_idx)
        self.edit_out.set_fps(self.fps, self._max_frame_idx)
        self.edit_in.commit_requested.connect(self._commit_in_tc_edit)
        self.edit_out.commit_requested.connect(self._commit_out_tc_edit)

        self._trim_thumb_out = QLabel()
        self._trim_thumb_out.setFixedSize(106, 60)
        self._trim_thumb_out.setAlignment(Qt.AlignCenter)
        self._trim_thumb_out.setStyleSheet(_trim_thumb_style)
        self._trim_thumb_out.setVisible(False)

        tc_row.addWidget(self._trim_thumb_in)
        tc_row.addWidget(lbl_in_tag)
        tc_row.addWidget(self.edit_in)
        tc_row.addStretch()
        tc_row.addWidget(self.lbl_tc)
        tc_row.addStretch()
        tc_row.addWidget(lbl_out_tag)
        tc_row.addWidget(self.edit_out)
        tc_row.addWidget(self._trim_thumb_out)
        layout.addLayout(tc_row)

        # --- Controls ---
        ctrl_row = QHBoxLayout()
        btn_style = "background: #2a2a3a; font-weight: bold; font-size: 12px; padding: 6px 12px; border-radius: 3px; border: 1px solid #333;"

        self.btn_play = QPushButton("▶ PLAY")
        self.btn_in   = QPushButton("[ SET IN  (I)")
        self.btn_out  = QPushButton("SET OUT ] (O)")
        self.btn_clr  = QPushButton("↺ CLEAR TRIM")
        self.btn_goto_in  = QPushButton("⇤ GO TO IN")
        self.btn_goto_out = QPushButton("GO TO OUT ⇥")
        self.btn_loop = QPushButton("🔁 LOOP")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setChecked(False)
        self._loop_active = False
        for b in [self.btn_play, self.btn_in, self.btn_out, self.btn_clr,
                  self.btn_goto_in, self.btn_goto_out, self.btn_loop]:
            b.setStyleSheet(btn_style)
        self.btn_in.setStyleSheet(btn_style + " color: #00c853;")
        self.btn_out.setStyleSheet(btn_style + " color: #ff4444;")
        self.btn_goto_in.setStyleSheet(btn_style + " color: #00c853;")
        self.btn_goto_out.setStyleSheet(btn_style + " color: #ff4444;")
        self.btn_loop.setStyleSheet(
            btn_style + " color: #aaa;"
            "QPushButton:checked { background: #1e3a8c; color: #40a9ff; border-color: #40a9ff; }"
        )
        self.btn_goto_in.setToolTip("Jump playhead to IN point (Shift+I)")
        self.btn_goto_out.setToolTip("Jump playhead to OUT point (Shift+O)")
        self.btn_loop.setToolTip(
            "Loop preview between IN and OUT (smooth Qt playback). "
            "Press PLAY. Paused view uses frame-exact overlay."
        )
        
        # --- Volume cluster (multimedia-player style: icon + slider + %) ---
        # Replaces the old "Mute Audio" checkbox. Behavior:
        #   - speaker icon = mute toggle (icon morphs by current level: 🔇/🔈/🔉/🔊)
        #   - slider 0..100 with native wheel handling (Qt does this for free)
        #   - moving the slider while muted automatically un-mutes (player UX)
        #   - last non-zero level is remembered for unmute restore
        # _is_muted is the source of truth for the audible state; the slider
        # value tracks the *intended* level so muting+unmuting brings you back
        # to where you were, not to a hard-coded default.
        self._is_muted = True
        self._last_volume = 70  # 0..100, restored on unmute

        self.btn_mute = QPushButton("🔇")
        self.btn_mute.setCheckable(False)  # we manage state manually so the
                                           # icon can react to volume == 0
        self.btn_mute.setFixedWidth(34)
        self.btn_mute.setToolTip("Toggle mute (M)")
        self.btn_mute.setFocusPolicy(Qt.NoFocus)
        self.btn_mute.setStyleSheet(
            "QPushButton { background: #2a2a3a; color: #ccc; font-size: 14px; "
            "padding: 4px; border-radius: 3px; border: 1px solid #333; } "
            "QPushButton:hover { background: #3a3a4a; color: #fff; }"
        )

        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(self._last_volume)
        self.vol_slider.setFixedWidth(96)
        self.vol_slider.setSingleStep(2)
        self.vol_slider.setPageStep(10)
        self.vol_slider.setToolTip("Volume (mouse wheel adjusts)")
        self.vol_slider.setFocusPolicy(Qt.NoFocus)
        self.vol_slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 4px; background: #2a2a3a; border-radius: 2px; }"
            "QSlider::sub-page:horizontal { background: #4a90e2; border-radius: 2px; }"
            "QSlider::handle:horizontal { background: #ddd; width: 12px; height: 12px; "
            "margin: -5px 0; border-radius: 6px; border: 1px solid #777; }"
            "QSlider::handle:horizontal:hover { background: #fff; }"
        )

        self.lbl_vol = QLabel("muted")
        self.lbl_vol.setFixedWidth(46)
        self.lbl_vol.setStyleSheet("color: #888; font-size: 11px; font-family: Consolas, 'Menlo', monospace;")
        self.lbl_vol.setAlignment(Qt.AlignCenter)

        self.btn_mute.clicked.connect(self._on_mute_clicked)
        self.vol_slider.valueChanged.connect(self._on_volume_slider)
        # sliderMoved fires ONLY on real user interaction (drag), not on
        # programmatic setValue() — perfect for the live tooltip without
        # spamming when wheel/keyboard updates the slider too quickly.
        self.vol_slider.sliderMoved.connect(self._show_volume_tooltip)

        # JKL hint label
        hint = QLabel(
            "◀◀ J · K Stop · L ▶▶  (ramp speed)   |   K+J / K+L = slow step      "
            "←/→ frame · Shift ×10      "
            "I/O set · edit TC + Enter · Shift+I/O go-to      "
            "[ ] or PgUp/Dn = cuts      "
            "+/− zoom · 0 fit · M mute"
        )
        hint.setStyleSheet("color: #555; font-size: 10px;")

        # Order chosen as visual mnemonic: GO TO IN flanks SET IN on its
        # outside (left edge), GO TO OUT flanks SET OUT on its outside
        # (right edge). Reading left→right: "jump to IN, set IN, play
        # through, set OUT, jump to OUT".
        ctrl_row.addWidget(self.btn_goto_in)
        ctrl_row.addWidget(self.btn_in)
        ctrl_row.addWidget(self.btn_play)
        ctrl_row.addWidget(self.btn_out)
        ctrl_row.addWidget(self.btn_goto_out)
        ctrl_row.addWidget(self.btn_clr)
        ctrl_row.addWidget(self.btn_loop)
        # Visual separator between transport and audio cluster
        sep = QFrame(); sep.setFrameShape(QFrame.VLine); sep.setStyleSheet("color: #333; margin: 4px 6px;")
        ctrl_row.addWidget(sep)
        ctrl_row.addWidget(self.btn_mute)
        ctrl_row.addWidget(self.vol_slider)
        ctrl_row.addWidget(self.lbl_vol)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)
        layout.addWidget(hint)

        # --- Scene Detection Row ---
        scene_row = QHBoxLayout()
        scene_row.setSpacing(8)
        self.btn_detect = QPushButton("🎬 DETECT SCENES")
        self.btn_detect.setStyleSheet(btn_style + f" color: {COLOR_ACCENT};")
        self.btn_detect.setToolTip(
            "Auto-detect scene changes via FFmpeg. Cuts appear as orange marks on the timeline.\n"
            "If markers look wrong, use CLEAR SCENE CACHE then detect again."
        )
        self.btn_clear_scene_cache = QPushButton("🗑 CLEAR SCENE CACHE")
        self.btn_clear_scene_cache.setStyleSheet(btn_style + " color: #c77;")
        self.btn_clear_scene_cache.setToolTip(
            "Delete cached scene cuts for THIS clip (RAM + temp folder).\n"
            "Use after upgrading the app or when orange markers look offset.\n"
            "Does not change IN/OUT — only removes detection cache."
        )
        self.chk_snap = QCheckBox("Snap to cuts")
        self.chk_snap.setChecked(True)
        self.chk_snap.setToolTip(
            f"When setting IN/OUT from the timeline or playhead (not after "
            f"arrow frame-step), snap to the nearest detected cut within "
            f"±{self.snap_threshold_sec:.2f}s.  After ←/→ stepping, I/O use "
            f"the exact frame — same as a professional NLE."
        )
        self.chk_snap.setStyleSheet("color: #aaa; font-weight: bold;")

        # Segment-select toggle. Discoverable counterpart to Shift+Click — when
        # ON, plain clicks act as segment-select so users on a trackpad / one
        # hand can still range-select. Visually distinct (rounded chip) so
        # it's clear it's a MODE, not a one-shot action.
        self.btn_seg_mode = QPushButton("◧ SEG MODE")
        self.btn_seg_mode.setCheckable(True)
        self.btn_seg_mode.setStyleSheet(
            "QPushButton { background: #2a2a3a; color: #aaa; font-weight: bold; font-size: 11px; "
            "padding: 5px 10px; border-radius: 3px; border: 1px solid #333; } "
            "QPushButton:checked { background: #1e7d32; color: #fff; border-color: #2e9c3a; }"
        )
        self.btn_seg_mode.setToolTip(
            "Segment Select Mode.\n\n"
            "• Click a segment between two cuts → selects that whole scene (paints green).\n"
            "• Shift+Click another segment → fills the entire range from the first pick "
            "to the click (no skipping; everything in between is included).\n"
            "• While the cursor hovers a segment, a soft green preview shows what would "
            "be selected before you click.\n\n"
            "Deselect:\n"
            "• Right-click on the timeline → clears the green selection (keeps IN/OUT).\n"
            "• Toggle this button OFF → also clears the selection.\n\n"
            "Note: Shift+Click works the same way even with this mode OFF.\n"
            "OUT is exclusive (cut frame = first frame of next scene, not included)."
        )

        self.lbl_scene = QLabel("")
        self.lbl_scene.setStyleSheet(f"color: {COLOR_WARNING}; font-size: 10px; font-style: italic;")

        # Slim inline progress bar — only visible while the scene detector
        # is actively scanning. Doubles up with lbl_scene's text ("Analyzing
        # X% — N cuts found"): the bar is the at-a-glance cue, the text
        # gives the precise count.
        self.scene_progress = QProgressBar()
        self.scene_progress.setRange(0, 100)
        self.scene_progress.setValue(0)
        self.scene_progress.setTextVisible(False)
        self.scene_progress.setFixedHeight(6)
        self.scene_progress.setFixedWidth(120)
        self.scene_progress.setVisible(False)
        self.scene_progress.setStyleSheet(
            "QProgressBar { background: #1a1a2a; border: 1px solid #333; border-radius: 3px; }"
            "QProgressBar::chunk { background: #ffab00; border-radius: 2px; }"
        )

        # Cuts visibility toggle. Hides the orange marks AND disables snap
        # at the same time, so the timeline reads "clean" with one click.
        # The cuts data is preserved internally — re-toggling instantly
        # brings them back, no re-detection needed.
        self.btn_cuts_view = QPushButton("👁 CUTS")
        self.btn_cuts_view.setCheckable(True)
        self.btn_cuts_view.setChecked(True)
        self.btn_cuts_view.setStyleSheet(
            "QPushButton { background: #2a2a2a; color: #888; font-weight: bold; font-size: 11px; "
            "padding: 5px 10px; border-radius: 3px; border: 1px solid #333; } "
            "QPushButton:checked { background: #ffab00; color: #1a1a1a; border-color: #ffc452; }"
        )
        self.btn_cuts_view.setToolTip(
            "Show / hide detected scene cuts on the timeline.\n\n"
            "• ON  → orange marks visible, IN/OUT and scrub snap to nearest cut.\n"
            "• OFF → marks hidden AND snapping disabled (clean timeline).\n\n"
            "The detected cuts stay in memory while hidden — toggling back ON\n"
            "instantly restores them without re-running detection."
        )

        self._play_res_block = False
        self.cmb_play_res = QComboBox()
        self.cmb_play_res.addItem("Preview: Full res", "full")
        self.cmb_play_res.addItem("Preview: ½ res", "half")
        self.cmb_play_res.setStyleSheet(
            "color: #ddd; font-weight: bold; font-size: 11px; "
            "padding: 2px 6px; background: #1a1a2a; border: 1px solid #333;"
        )
        self.cmb_play_res.setToolTip(
            "Monitor + PLAY resolution.\n"
            "• Full — frame-exact overlay + source file for PLAY.\n"
            "• ½ — lighter overlay + half-res proxy for PLAY (built in background).\n"
            "Export always uses full-quality source. Playhead stays put on change."
        )
        self.cmb_play_res.setCurrentIndex(0)
        self._play_res_block = False
        self.cmb_play_res.currentIndexChanged.connect(self._on_play_res_changed)

        scene_row.addWidget(self.btn_detect)
        scene_row.addWidget(self.btn_clear_scene_cache)
        scene_row.addWidget(self.cmb_play_res)
        scene_row.addWidget(self.btn_cuts_view)
        scene_row.addWidget(self.chk_snap)
        scene_row.addWidget(self.btn_seg_mode)
        scene_row.addWidget(self.scene_progress)
        scene_row.addWidget(self.lbl_scene, 1)
        layout.addLayout(scene_row)

        # --- Segment-select hint banner ---
        # In-UI documentation so users don't have to discover the feature via
        # tooltip alone. Subtle (italic, dim) so it doesn't compete with the
        # main controls but readable on the dark theme.
        seg_hint = QLabel(
            "🟢 Segment select: Shift+Click a scene to mark it green. "
            "Shift+Click another to fill the whole range between them. "
            "Or toggle ◧ SEG MODE for plain clicks to do the same. "
            "Right-click the timeline to deselect."
        )
        seg_hint.setStyleSheet("color: #6a8a6a; font-size: 10px; font-style: italic; padding: 0 2px;")
        seg_hint.setWordWrap(True)
        layout.addWidget(seg_hint)

        # --- Dialog buttons ---
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        for role in (QDialogButtonBox.Ok, QDialogButtonBox.Cancel):
            btn = bbox.button(role)
            if btn:
                btn.setAutoDefault(False)
                btn.setDefault(False)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

        # --- Connections ---
        self.timeline.seeked.connect(self._seek_ratio)
        self.timeline.segment_selected.connect(self._on_segment_selected)
        self.btn_seg_mode.toggled.connect(self.timeline.set_select_mode)
        # CUTS toggle: hide markers + disable snap together. We also flip
        # the snap checkbox to OFF when hiding, and to ON when showing
        # (matching default), so the user gets one obvious switch instead
        # of two that need to be kept in sync mentally.
        self.btn_cuts_view.toggled.connect(self._on_cuts_view_toggled)
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_in.clicked.connect(self.set_in)
        self.btn_out.clicked.connect(self.set_out)
        self.btn_goto_in.clicked.connect(self.goto_in)
        self.btn_goto_out.clicked.connect(self.goto_out)
        self.btn_clr.clicked.connect(self.clear_trim)
        self.btn_loop.toggled.connect(self._on_loop_toggled)
        self.btn_detect.clicked.connect(self._toggle_scene_detection)
        self.btn_clear_scene_cache.clicked.connect(self._clear_scene_cache_clicked)
        self.player.positionChanged.connect(self._on_pos_changed)

        # --- Keyboard Shortcuts ---
        QShortcut(QKeySequence("Space"), self, self.toggle_play)
        QShortcut(QKeySequence("I"),     self, self.set_in)
        QShortcut(QKeySequence("O"),     self, self.set_out)
        # NLE convention: Shift+I/O = jump TO the IN/OUT marker (Premiere /
        # Resolve identical bindings).
        QShortcut(QKeySequence("Shift+I"), self, self.goto_in)
        QShortcut(QKeySequence("Shift+O"), self, self.goto_out)
        # J/K/L — NLE shuttle (handled via keyPressEvent/keyReleaseEvent
        # so we can detect K-hold for K+J / K+L slow stepping)
        # Arrow frame stepping
        QShortcut(QKeySequence("Left"),              self, lambda: self._step_frames(-1))
        QShortcut(QKeySequence("Right"),             self, lambda: self._step_frames(1))
        QShortcut(QKeySequence("Shift+Left"),        self, lambda: self._step_frames(-10))
        QShortcut(QKeySequence("Shift+Right"),       self, lambda: self._step_frames(10))
        # Cut navigation (active only after a scene detection has produced cuts).
        # PgUp = prev cut, PgDown = next cut — same direction as scrolling /
        # most NLE timelines (up = backwards, down = forwards).
        QShortcut(QKeySequence("["),                 self, lambda: self._jump_to_cut(-1))
        QShortcut(QKeySequence("]"),                 self, lambda: self._jump_to_cut(+1))
        QShortcut(QKeySequence(Qt.Key_PageUp),       self, lambda: self._jump_to_cut(-1))
        QShortcut(QKeySequence(Qt.Key_PageDown),     self, lambda: self._jump_to_cut(+1))
        QShortcut(QKeySequence(Qt.Key_Home),         self, self.goto_first_frame)
        QShortcut(QKeySequence(Qt.Key_End),          self, self.goto_last_frame)
        # Audio
        QShortcut(QKeySequence("M"),                 self, self._on_mute_clicked)
        # Zoom (NLE-style: = zooms in even without Shift; 0 fits)
        QShortcut(QKeySequence("="),                 self, lambda: self.timeline.zoom_in())
        QShortcut(QKeySequence("+"),                 self, lambda: self.timeline.zoom_in())
        QShortcut(QKeySequence("-"),                 self, lambda: self.timeline.zoom_out())
        QShortcut(QKeySequence("0"),                 self, self.timeline.reset_view)

        # Restore previous trim markers (fast); heavy work after window shows.
        self._sync_out_incl_from_storage()
        self._restore_markers()
        if self.fps > 0:
            in_fi = source_frame_index_from_sec(
                self.in_sec, self.fps, self._max_frame_idx, rounding="floor"
            )
            self._step_frame_idx = in_fi
            self._precise_display_fi = in_fi
            self._refresh_tc(in_fi / self.fps, in_fi)
            self.player.setPosition(ms_start_of_frame(in_fi, self.fps))
        else:
            self._refresh_tc(self.in_sec)
            self.player.setPosition(int(round(self.in_sec * 1000)))
        QTimer.singleShot(0, self._deferred_trim_open)

    # ---- helpers ----

    def _sec_to_tc(self, sec, frame_idx=None):
        if frame_idx is not None and self.fps > 0:
            return format_frame_index_as_tc(frame_idx, self.fps)
        return format_seconds_as_tc_frames(max(0.0, sec), self.fps) or "00:00:00:00"

    def _frame_index_to_timeline_ratio(self, fi):
        """Map a source frame index to 0..1 on the timeline (frame-quantized)."""
        if self._max_frame_idx <= 0:
            return 0.0
        return max(0.0, min(1.0, int(fi) / float(self._max_frame_idx)))

    def _frame_index_from_timeline_ratio(self, ratio, *, mode="floor"):
        """Inverse of ``_frame_index_to_timeline_ratio`` for scrub/segments."""
        if self._max_frame_idx <= 0 or not self.fps:
            return 0
        x = max(0.0, min(1.0, float(ratio))) * self._max_frame_idx
        if mode == "ceil":
            fi = int(math.ceil(x - 1e-9))
        elif mode == "round":
            fi = int(round(x))
        else:
            fi = int(math.floor(x + 1e-9))
        return max(0, min(fi, self._max_frame_idx))

    def _sync_timeline_cuts(self):
        """Orange scene ticks aligned to integer ``cuts_fi`` (not duration drift)."""
        self.timeline.set_cuts(self._cuts_fi_to_timeline_ratios())

    def _cuts_fi_to_timeline_ratios(self):
        if not self.cuts_fi or self._max_frame_idx <= 0:
            return []
        return [
            self._frame_index_to_timeline_ratio(fi)
            for fi in self.cuts_fi
            if 0 < fi <= self._max_frame_idx
        ]

    def _authoritative_paused_fi(self):
        """Frame on screen when paused — overlay / logical index wins."""
        if self._step_frame_idx is not None:
            return int(self._step_frame_idx)
        if self._precise_display_fi is not None:
            return int(self._precise_display_fi)
        return source_frame_index_from_sec(
            self.player.position() / 1000.0,
            self.fps,
            self._max_frame_idx,
            rounding="floor",
        )

    def _authoritative_playhead_ms(self):
        """Playhead ms — logical frame index wins over Qt (often 0 before first PLAY)."""
        if self.fps and self.fps > 0:
            fi = self._authoritative_paused_fi()
            if fi is not None:
                return ms_start_of_frame(fi, self.fps)
        return int(self.player.position())

    def _refresh_tc(self, sec, frame_idx=None):
        if frame_idx is None and self._step_frame_idx is not None and self.fps > 0:
            frame_idx = self._step_frame_idx
        if frame_idx is not None and self.fps > 0:
            sec = frame_idx / self.fps
            ratio = self._frame_index_to_timeline_ratio(frame_idx)
        else:
            ratio = sec / self.duration_sec if self.duration_sec > 0 else 0.0
        self.current_sec = sec
        self.lbl_tc.setText(self._sec_to_tc(sec, frame_idx))
        self.timeline.set_position(ratio)

    def _frame_index_from_sec(self, sec, *, rounding="floor"):
        """Integer source frame index for a timestamp (clamped)."""
        if not self.fps or self.fps <= 0:
            return None
        return source_frame_index_from_sec(
            sec, self.fps, self._max_frame_idx, rounding=rounding
        )

    def _sec_from_frame_index(self, fi):
        if not self.fps or self.fps <= 0:
            return max(0.0, float(fi))
        fi = max(0, min(int(fi), self._max_frame_idx))
        return sec_from_source_frame_index(fi, self.fps)

    def _frame_index_for_io_markers(self):
        """Paused playhead frame — overlay / logical index, not Qt keyframes."""
        return self._authoritative_paused_fi()

    def _player_frame_index(self):
        """Frame under the playhead — logical index wins over QMediaPlayer ms."""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            return source_frame_index_from_sec(
                self.player.position() / 1000.0,
                self.fps,
                self._max_frame_idx,
                rounding="floor",
            )
        return self._frame_index_for_io_markers()

    def _park_at_frame_index(
        self, fi, *, sync_tc_fields=True, preview_exact=True, skip_player_seek=False
    ):
        """Pause and show frame ``fi`` (monitor + TC + timeline agree with export)."""
        if not self.fps or self.fps <= 0:
            sec = max(0.0, min(float(fi), self.duration_sec))
            self._step_frame_idx = None
            self.player.pause()
            self.btn_play.setText("▶ PLAY")
            self._refresh_tc(sec)
            self.player.setPosition(int(round(sec * 1000)))
            self._apply_precise_preview(exact=preview_exact)
            return
        fi = max(0, min(int(fi), self._max_frame_idx))
        self._step_frame_idx = fi
        sec = fi / self.fps
        self.player.pause()
        if not self._loop_playing:
            self.btn_play.setText("▶ PLAY")
        self._refresh_tc(sec, fi)
        if sync_tc_fields:
            self._sync_in_out_tc_fields()
        if not skip_player_seek:
            self.player.setPosition(ms_start_of_frame(fi, self.fps))
        self._precise_display_fi = fi
        self._apply_precise_preview(exact=preview_exact, force_fi=fi)

    def _monitor_size(self):
        """Size of the preview area (valid while looping — do not hide video_widget)."""
        g = self.video_widget.geometry()
        vw, vh = g.width(), g.height()
        if vw >= 32 and vh >= 32:
            return vw, vh
        vw = self.video_widget.width()
        vh = self.video_widget.height()
        if vw >= 32 and vh >= 32:
            return vw, vh
        return max(320, vw or 320), max(180, vh or 180)

    def _uses_playback_proxy(self):
        return self.cmb_play_res.currentData() == "half"

    def _preview_exact_for_monitor(self):
        """Paused / LOOP overlay decode matches Preview dropdown."""
        return self.cmb_play_res.currentData() == "full"

    def _frame_cache_key(self, fi, exact):
        return (int(fi), bool(exact))

    def _frame_cache_get(self, fi, exact):
        return self._frame_png_cache.get(self._frame_cache_key(fi, exact))

    def _refresh_monitor_at_playhead(self):
        """Re-draw monitor at current frame after res / source change."""
        self._cancel_precise_preview_work()
        fi = self._step_frame_idx
        if fi is None:
            fi = self._authoritative_paused_fi()
        if fi is None:
            fi = 0
        exact = self._preview_exact_for_monitor()
        self._set_playback_media(
            self._playback_media_for_play(),
            hold_ms=self._authoritative_playhead_ms(),
        )
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self._pending_playback_pos_ms = ms_start_of_frame(fi, self.fps)
            return
        self._loop_last_shown_fi = None
        self._park_at_frame_index(
            fi,
            sync_tc_fields=False,
            preview_exact=exact,
        )

    def _show_loop_frame(self, fi):
        """LOOP step: frame-exact overlay on top of monitor (video surface stays sized)."""
        fi = max(0, min(int(fi), self._max_frame_idx))
        exact = self._preview_exact_for_monitor()
        cache_key = (fi, exact)
        if self._loop_last_shown_fi == cache_key:
            return
        self._loop_last_shown_fi = cache_key
        self._step_frame_idx = fi
        self._precise_display_fi = fi
        self._refresh_tc(fi / self.fps, fi)
        self._layout_precise_frame_overlay()
        vw, vh = self._monitor_size()
        cached = self._frame_cache_get(fi, exact)
        if cached and self._show_precise_png(cached, vw, vh, exact=exact):
            self._precise_frame.show()
            self._precise_frame.raise_()
            self._lbl_speed.raise_()
            return
        self._apply_precise_preview(exact=exact, force_fi=fi)

    def _park_at_sec(self, sec):
        fi = self._frame_index_from_sec(sec)
        if fi is None:
            self.player.pause()
            self.btn_play.setText("▶ PLAY")
            sec = max(0.0, min(float(sec), self.duration_sec))
            self._step_frame_idx = None
            self._refresh_tc(sec)
            self.player.setPosition(int(round(sec * 1000)))
            self._apply_precise_preview(exact=True)
        else:
            self._park_at_frame_index(fi)

    def _media_duration_sec(self):
        """Best-known clip length: QMediaPlayer when loaded, else probe specs."""
        d_ms = self.player.duration()
        if d_ms and d_ms > 0:
            return max(self.duration_sec, d_ms / 1000.0)
        return self.duration_sec

    def _effective_max_frame_idx_for_cuts(self):
        """Last frame index for scene-cut quantisation (never below duration×fps)."""
        if not self.fps or self.fps <= 0:
            return self._max_frame_idx
        n = max(1, int(round(self._media_duration_sec() * self.fps)))
        return max(self._max_frame_idx, n - 1)

    @Slot(int)
    def _on_player_duration_changed(self, ms):
        """ffprobe duration can be missing/wrong; Qt often has the real length."""
        if not ms or ms <= 0:
            return
        if self._pending_playback_pos_ms is not None:
            self.player.setPosition(self._pending_playback_pos_ms)
            self._pending_playback_pos_ms = None
        media_dur = ms / 1000.0
        if media_dur <= self.duration_sec + 0.05:
            return
        had_no_cuts = not self.cuts_sec
        self.duration_sec = media_dur
        if self.fps > 0:
            tf = max(self._total_source_frames, int(round(media_dur * self.fps)))
            self._total_source_frames = max(1, tf)
            self._max_frame_idx = max(0, self._total_source_frames - 1)
            self._default_out_sec = self._total_source_frames / self.fps
            self.timeline.set_total_frames(self._total_source_frames)
        if had_no_cuts:
            self._try_warm_start_scenes()

    def _apply_scene_cut_frames(self, cut_fis):
        """Store scene markers as integer frame indices (WYSIWYG with export)."""
        if not cut_fis:
            self.cuts_fi = []
            self.cuts_sec = []
            return
        dur = self._media_duration_sec()
        max_fi = self._effective_max_frame_idx_for_cuts()
        seen = set()
        aligned_fi = []
        for raw in cut_fis:
            fi = max(0, min(int(raw), max_fi))
            if fi <= 0 or fi in seen:
                continue
            seen.add(fi)
            aligned_fi.append(fi)
        self.cuts_fi = sorted(aligned_fi)
        if not self.fps or self.fps <= 0:
            self.cuts_sec = [float(fi) for fi in self.cuts_fi]
            return
        self.cuts_sec = []
        for fi in self.cuts_fi:
            sec = sec_from_source_frame_index(fi, self.fps)
            if 0.0 < sec < dur:
                self.cuts_sec.append(sec)
        self.cuts_sec = sorted(set(self.cuts_sec))
        self._sync_timeline_cuts()

    def _restore_markers(self):
        """Apply previous in/out to the visual timeline immediately."""
        if self.fps > 0:
            in_fi = source_frame_index_from_sec(
                self.in_sec, self.fps, self._max_frame_idx, rounding="floor"
            )
            self.timeline.set_in(self._frame_index_to_timeline_ratio(in_fi))
        else:
            self.timeline.set_in(self.in_sec / self.duration_sec)
        self._sync_out_markers_ui()
        self._sync_in_out_tc_fields()

    def _sync_in_out_tc_fields(self):
        """Push current IN/OUT frame indices into editable TC fields."""
        if not self.fps or self.fps <= 0:
            return
        self._tc_edit_block = True
        in_fi = source_frame_index_from_sec(self.in_sec, self.fps, self._max_frame_idx)
        out_fi = self._out_last_included_frame_index()
        self.edit_in.set_fps(self.fps, self._max_frame_idx)
        self.edit_out.set_fps(self.fps, self._max_frame_idx)
        self.edit_in.set_committed_text(format_frame_index_as_tc(in_fi, self.fps))
        self.edit_out.set_committed_text(format_frame_index_as_tc(out_fi, self.fps))
        self._tc_edit_block = False

    def _release_tc_focus(self):
        """Return focus to the trim surface (not stuck in IN/OUT fields)."""
        self.edit_in.release_keyboard_focus()
        self.edit_out.release_keyboard_focus()
        self.video_widget.setFocus(Qt.OtherFocusReason)

    def _try_unfocus_tc_edit(self, event):
        """Click anywhere outside IN/OUT TC fields → commit/revert + release focus."""
        fw = QApplication.focusWidget()
        if fw not in (self.edit_in, self.edit_out):
            return
        try:
            gp = event.globalPosition().toPoint()
        except AttributeError:
            gp = event.globalPos()
        hit = QApplication.widgetAt(gp)
        if hit is fw:
            return
        w = hit
        while w is not None:
            if w is fw:
                return
            w = w.parentWidget()
        fw.clearFocus()

    def _deferred_trim_open(self):
        """Thumbs, overlay, scene cache, proxy — after the dialog is visible."""
        if self._precise_shutdown:
            return
        fi = self._step_frame_idx
        if fi is None and self.fps > 0:
            fi = source_frame_index_from_sec(
                self.in_sec, self.fps, self._max_frame_idx, rounding="floor"
            )
        if fi is not None and self.fps > 0:
            self._park_at_frame_index(
                fi,
                sync_tc_fields=False,
                preview_exact=self._preview_exact_for_monitor(),
            )
        self._update_trim_thumb("in")
        self._update_trim_thumb("out")
        self._try_warm_start_scenes()
        if self._uses_playback_proxy() and self._scene_content_key:
            self._start_playback_proxy_build()
        self._release_tc_focus()

    def showEvent(self, event):
        super().showEvent(event)
        app = QApplication.instance()
        if app and not self._tc_app_filter:
            app.installEventFilter(self)
            self._tc_app_filter = True
        QTimer.singleShot(0, self._release_tc_focus)
        QTimer.singleShot(50, self._repaint_preview_if_needed)

    def _repaint_preview_if_needed(self):
        """Overlay after layout — QVideoWidget stays black until PLAY otherwise."""
        if self._precise_shutdown:
            return
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            return
        if self._precise_frame.isVisible() and self._precise_display_fi is not None:
            return
        fi = self._step_frame_idx
        if fi is None:
            fi = self._authoritative_paused_fi()
        if fi is None:
            fi = 0
        self._apply_precise_preview(
            exact=self._preview_exact_for_monitor(),
            force_fi=fi,
        )

    def hideEvent(self, event):
        app = QApplication.instance()
        if app and self._tc_app_filter:
            app.removeEventFilter(self)
            self._tc_app_filter = False
        super().hideEvent(event)

    def _commit_in_tc_edit(self):
        if self._tc_edit_block or not self.fps or self.fps <= 0:
            return
        fi = frame_index_from_tc_text(
            self.edit_in.text(), self.fps, self._max_frame_idx
        )
        if fi is None:
            self.edit_in.revert()
            self.lbl_scene.setText("Invalid IN — use HH:MM:SS:FF (FF < fps grid)")
            self._release_tc_focus()
            return
        self.edit_in.set_committed_text(self.edit_in.text())
        self.in_sec = self._sec_from_frame_index(fi)
        self.timeline.set_in(self._frame_index_to_timeline_ratio(fi))
        self._update_trim_thumb("in", frame_idx=fi)
        self._park_at_frame_index(fi)
        self._release_tc_focus()

    def _commit_out_tc_edit(self):
        if self._tc_edit_block or not self.fps or self.fps <= 0:
            return
        fi = frame_index_from_tc_text(
            self.edit_out.text(), self.fps, self._max_frame_idx
        )
        if fi is None:
            self.edit_out.revert()
            self.lbl_scene.setText("Invalid OUT — use HH:MM:SS:FF (FF < fps grid)")
            self._release_tc_focus()
            return
        self.edit_out.set_committed_text(self.edit_out.text())
        cap = self._default_out_sec if self.fps > 0 else self.duration_sec
        self._out_incl_fi = fi
        self.out_sec = exclusive_out_sec_from_included_frame(fi, self.fps, cap)
        in_fi = source_frame_index_from_sec(self.in_sec, self.fps, self._max_frame_idx)
        if source_frame_index_from_sec(self.out_sec, self.fps) <= in_fi:
            fi = min(in_fi, self._max_frame_idx)
            self._out_incl_fi = fi
            self.out_sec = exclusive_out_sec_from_included_frame(fi, self.fps, cap)
        self._sync_out_markers_ui()
        self._update_trim_thumb("out", frame_idx=fi)
        self._park_at_frame_index(fi)
        self._release_tc_focus()

    def _out_last_included_frame_index(self):
        """Last source frame the user chose as OUT (included in export)."""
        if self._out_incl_fi is not None:
            return max(0, min(int(self._out_incl_fi), self._max_frame_idx))
        return last_included_frame_index_from_out(
            self.out_sec, self.fps, self._max_frame_idx
        )

    def _sync_out_incl_from_storage(self):
        """Rebuild ``_out_incl_fi`` after load/restore when only ``out_sec`` is known."""
        if self.fps and self.fps > 0:
            self._out_incl_fi = last_included_frame_index_from_out(
                self.out_sec, self.fps, self._max_frame_idx
            )

    def _sync_out_markers_ui(self, manual=True):
        """Timeline + label at the user OUT frame (not the exclusive boundary)."""
        incl_fi = self._out_last_included_frame_index()
        self.timeline.set_out(
            self._frame_index_to_timeline_ratio(incl_fi), manual=manual
        )
        self._tc_edit_block = True
        self.edit_out.set_committed_text(format_frame_index_as_tc(incl_fi, self.fps))
        self._tc_edit_block = False

    def _loop_frame_bounds(self):
        """Integer IN / last-included OUT for loop preview (matches export range)."""
        in_fi = source_frame_index_from_sec(
            self.in_sec, self.fps, self._max_frame_idx
        )
        last_incl_fi = self._out_last_included_frame_index()
        return in_fi, max(in_fi, last_incl_fi)

    def _loop_frame_interval_ms(self):
        if not self.fps or self.fps <= 0:
            return 40
        return max(1, int(round(1000.0 / float(self.fps))))

    def _start_loop_playback(self):
        """Frame-exact IN..OUT loop via timer + overlay (monitor stays visible)."""
        self._cancel_precise_preview_work()
        self.player.pause()
        self.player.setPlaybackRate(1.0)
        self._loop_playing = True
        self._loop_seek_guard = False
        self._loop_last_shown_fi = None
        self._step_frame_idx = None
        self.video_widget.show()
        self._precise_frame.setStyleSheet("background: #000000;")
        self._layout_precise_frame_overlay()
        self._precise_frame.show()
        self._precise_frame.raise_()
        in_fi, _ = self._loop_frame_bounds()
        self._loop_play_fi = in_fi - 1
        self._loop_timer.start(self._loop_frame_interval_ms())
        self.btn_play.setText("⏸ PAUSE")
        self._loop_frame_tick()

    def _stop_loop_playback(self):
        self._loop_timer.stop()
        self._loop_playing = False
        self._loop_seek_guard = False
        self._loop_last_shown_fi = None
        self._layout_precise_frame_overlay()

    def _loop_clear_seek_guard(self):
        self._loop_seek_guard = False

    def _loop_frame_tick(self):
        if not self._loop_active or not self._loop_playing:
            self._stop_loop_playback()
            return
        in_fi, last_incl_fi = self._loop_frame_bounds()
        cur = in_fi if self._loop_play_fi is None else int(self._loop_play_fi) + 1
        if cur > last_incl_fi:
            cur = in_fi
        self._loop_play_fi = cur
        self._show_loop_frame(cur)

    def _loop_wrap_if_needed(self, pos_ms):
        """Keep Qt loop playback inside [IN .. last included frame]."""
        if self._loop_seek_guard:
            return True
        if (not self._loop_active
                or self.player.playbackState() != QMediaPlayer.PlayingState):
            return False
        if not self.fps or self.fps <= 0:
            sec = pos_ms / 1000.0
            eps = 0.04
            if sec >= self.out_sec - eps:
                self._loop_seek_guard = True
                self.player.setPosition(int(round(self.in_sec * 1000)))
                QTimer.singleShot(120, self._loop_clear_seek_guard)
                return True
            if sec < self.in_sec - eps:
                self._loop_seek_guard = True
                last_sec = inclusive_display_sec_from_exclusive_out(
                    self.out_sec, self.fps, self._max_frame_idx
                )
                self.player.setPosition(int(round(last_sec * 1000)))
                QTimer.singleShot(120, self._loop_clear_seek_guard)
                return True
            return False
        in_fi, last_incl_fi = self._loop_frame_bounds()
        in_ms = ms_start_of_frame(in_fi, self.fps)
        out_excl_ms = ms_start_of_frame(last_incl_fi + 1, self.fps)
        p = int(pos_ms)
        if p >= out_excl_ms:
            self._loop_seek_guard = True
            self.player.setPosition(in_ms)
            QTimer.singleShot(120, self._loop_clear_seek_guard)
            return True
        if p < in_ms:
            self._loop_seek_guard = True
            self.player.setPosition(ms_start_of_frame(last_incl_fi, self.fps))
            QTimer.singleShot(120, self._loop_clear_seek_guard)
            return True
        return False

    def _seek_ratio(self, ratio, *, immediate_precise=False):
        ratio = max(0.0, min(1.0, float(ratio)))
        if self.fps > 0:
            fi = self._frame_index_from_sec(
                ratio * self.duration_sec, rounding="floor"
            )
            self._step_frame_idx = fi
            self._precise_display_fi = fi
            self._refresh_tc(fi / self.fps, fi)
            ms = ms_start_of_frame(fi, self.fps)
        else:
            self._precise_display_fi = None
            self._step_frame_idx = None
            ms = int(ratio * self.duration_sec * 1000)
            self._refresh_tc(ms / 1000.0)
        self.player.setPosition(ms)
        exact = True if immediate_precise else self._preview_exact_for_monitor()
        if self.fps > 0:
            self._apply_precise_preview(exact=exact, force_fi=fi)
        else:
            self._apply_precise_preview(exact=exact)

    # ---- Zoom UI ----

    def _on_timeline_zoom_changed(self, factor):
        """Update the zoom indicator + enable/disable buttons. Called every
        time the user wheels, drags, or hits the +/-/FIT buttons. Disabling
        FIT at 1.0× is purely cosmetic — clicking it again is a no-op."""
        # Format: 1.0×, 2.5×, 12×, 100× — drop the decimal once we're past 10x
        # to keep the label width predictable.
        if factor < 10:
            txt = f"{factor:.1f}×"
        else:
            txt = f"{int(round(factor))}×"
        self.lbl_zoom.setText(txt)
        at_fit = abs(factor - 1.0) < 1e-3
        self.btn_zoom_fit.setEnabled(not at_fit)
        # Tint indicator: gray at 1×, blue when zoomed in (visual cue that
        # the timeline is showing a sub-range of the source).
        col = "#888" if at_fit else "#4a90e2"
        self.lbl_zoom.setStyleSheet(f"color: {col}; font-size: 11px; font-weight: bold; min-width: 44px;")
        # Keep the viewport scrollbar in lockstep with the timeline view —
        # zooming, panning, FIT, the auto-follow path, all eventually fire
        # zoom_changed and end up here.
        self._sync_scrollbar()

    def _sync_scrollbar(self):
        """Push the timeline's current view (start_r, end_r) into the
        scrollbar widget. Hides the bar at 1× because there's nothing to
        scroll. Uses blockSignals so this update path doesn't bounce back
        into _on_timeline_scroll → _set_view → zoom_changed → here."""
        span = self.timeline._view_span()
        page = max(1, int(round(span * self.SCROLL_RES)))
        max_val = max(0, self.SCROLL_RES - page)
        val = int(round(self.timeline.view_start_r * self.SCROLL_RES))
        val = max(0, min(max_val, val))
        # < 1.0 (with epsilon) = zoomed in = show bar.
        self.timeline_scroll.setVisible(span < 0.999)
        self.timeline_scroll.blockSignals(True)
        self.timeline_scroll.setPageStep(page)
        self.timeline_scroll.setMaximum(max_val)
        self.timeline_scroll.setValue(val)
        self.timeline_scroll.blockSignals(False)

    def _on_timeline_scroll(self, value):
        """User dragged / wheeled / arrow'd the scrollbar → translate to a
        view shift while preserving span (a scrollbar pans, never zooms)."""
        span = self.timeline._view_span()
        new_start = value / float(self.SCROLL_RES)
        # _set_view will clamp and emit zoom_changed → _sync_scrollbar.
        # That feedback loop is broken by blockSignals inside _sync_scrollbar.
        self.timeline._set_view(new_start, new_start + span)

    # ---- Audio (mute toggle + volume slider) ----

    def _volume_icon(self):
        """Pick the speaker glyph that matches current state. Mirrors how
        VLC / Spotify / system mixers represent audio level so users don't
        have to think about it."""
        if self._is_muted or self._last_volume == 0:
            return "🔇"
        v = self._last_volume
        if v <= 33:  return "🔈"
        if v <= 66:  return "🔉"
        return "🔊"

    def _apply_audio_state(self):
        """Push (_is_muted, _last_volume) into the QAudioOutput and refresh
        the icon + % readout. Single funnel so all entry points (mute click,
        slider drag, programmatic restore) produce a consistent UI."""
        eff = 0.0 if self._is_muted else (self._last_volume / 100.0)
        self.audio_output.setVolume(eff)
        self.btn_mute.setText(self._volume_icon())
        if self._is_muted:
            self.lbl_vol.setText("muted")
            self.lbl_vol.setStyleSheet("color: #777; font-size: 11px; font-family: Consolas, 'Menlo', monospace; font-style: italic;")
        else:
            self.lbl_vol.setText(f"{self._last_volume}%")
            self.lbl_vol.setStyleSheet("color: #ccc; font-size: 11px; font-family: Consolas, 'Menlo', monospace;")

    def _on_mute_clicked(self):
        # Plain icon click toggles mute. We don't use a checkable QPushButton
        # because we want the icon to also reflect "volume is 0 even though
        # not technically muted" — the source of truth is _is_muted.
        self._is_muted = not self._is_muted
        # If unmuting and the slider is at 0, bump to a sensible default so
        # there's actually some audio (otherwise the user un-mutes and hears
        # nothing, which feels broken).
        if not self._is_muted and self._last_volume == 0:
            self._last_volume = 50
            # Block signal so this doesn't recurse into _on_volume_slider.
            self.vol_slider.blockSignals(True)
            self.vol_slider.setValue(self._last_volume)
            self.vol_slider.blockSignals(False)
        self._apply_audio_state()

    def _on_volume_slider(self, val):
        # Moving the slider while muted unmutes — that's the multimedia-player
        # convention everywhere (browser <video>, VLC, etc.).
        self._last_volume = int(val)
        if self._last_volume > 0 and self._is_muted:
            self._is_muted = False
        elif self._last_volume == 0 and not self._is_muted:
            # Dragging to 0 effectively mutes; reflect that in the icon.
            self._is_muted = True
        self._apply_audio_state()

    def _show_volume_tooltip(self, val):
        """Floating "70%" tooltip while the user drags the slider thumb.
        Tracks the cursor (Qt's default tooltip behavior) so the readout is
        always within eye-line of the user's hand. Auto-hides via Qt's
        default tooltip timeout once dragging stops."""
        QToolTip.showText(QCursor.pos(), f"{int(val)}%", self.vol_slider)

    def _adjust_volume_by_wheel(self, e):
        """Centralized wheel→volume mapping. Used by both wheelEvent (catches
        wheel events that propagated up to the dialog) and eventFilter (catches
        wheel events that the QVideoWidget swallowed before they could bubble).

        Setting the slider value via setValue() fires valueChanged →
        _on_volume_slider(), which is the single funnel that updates
        _last_volume / _is_muted / icon / label / actual audio output. We
        deliberately don't poke the audio output directly here, otherwise
        the slider thumb and the audible level would drift apart.

        Steps:
          - plain wheel → ±5%   (~20 notches across the full range)
          - Shift+wheel → ±1%   (fine adjust)
          - Ctrl+wheel  → ±10%  (coarse jump)
        """
        delta = e.angleDelta().y()
        if delta == 0:
            return False
        mods = e.modifiers()
        if mods & Qt.ShiftModifier:
            step = 1
        elif mods & Qt.ControlModifier:
            step = 10
        else:
            step = 5
        direction = 1 if delta > 0 else -1
        new_v = max(0, min(100, self._last_volume + direction * step))
        if new_v != self.vol_slider.value():
            self.vol_slider.setValue(new_v)
        e.accept()
        return True

    def wheelEvent(self, e):
        """Dialog-level wheel handler so spinning the wheel ANYWHERE in the
        trim panel adjusts volume — over the buttons, the labels, empty
        space, etc. The timeline consumes its own wheel events for zoom and
        the volume slider has its native wheel handling, so neither bubbles
        up. The video widget is handled separately via eventFilter (see
        below) because on some platforms its native surface eats the event
        before propagation."""
        if not self._adjust_volume_by_wheel(e):
            super().wheelEvent(e)

    def eventFilter(self, watched, event):
        from PySide6.QtCore import QEvent
        if getattr(self, "_tc_app_filter", False) and self.isVisible():
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._try_unfocus_tc_edit(event)
        if watched is self.video_widget:
            if event.type() == QEvent.Wheel:
                if self._adjust_volume_by_wheel(event):
                    return True
            elif event.type() == QEvent.Resize:
                self._reposition_speed_overlay()
                self._layout_precise_frame_overlay()
                if self.player.playbackState() != QMediaPlayer.PlayingState:
                    self._precise_resize_timer.stop()
                    self._precise_resize_timer.start(90)
        return super().eventFilter(watched, event)

    def _step_frames(self, delta_frames):
        """Step playhead by exact source-frame count (NLE ←/→)."""
        self.player.pause()
        self.btn_play.setText("▶ PLAY")
        if self.fps > 0:
            if self._step_frame_idx is not None:
                cur_frame = int(self._step_frame_idx)
            else:
                cur_frame = self._frame_index_for_io_markers()
            if cur_frame is None:
                cur_frame = 0
            self._park_at_frame_index(cur_frame + int(delta_frames))
            return

    def _step_sec(self, delta):
        self.player.pause()
        self.btn_play.setText("▶ PLAY")
        if self.fps > 0:
            cur_frame = self._player_frame_index()
            if cur_frame is None:
                cur_frame = 0
            step_frames = int(round(delta * self.fps))
            if step_frames == 0:
                step_frames = 1 if delta > 0 else -1
            self._park_at_frame_index(cur_frame + step_frames)
            return
        new_ms = max(0, min(int((self.current_sec + delta) * 1000),
                            int(self.duration_sec * 1000)))
        self._step_frame_idx = None
        self.player.setPosition(new_ms)
        self._apply_precise_preview(exact=True)

    def _on_loop_toggled(self, checked):
        """Enable IN..OUT loop (smooth Qt playback on PLAY)."""
        self._loop_active = checked
        self._loop_play_fi = None
        if not checked:
            self._stop_loop_playback()
            if self.player.playbackState() == QMediaPlayer.PlayingState:
                self.player.pause()
                self.btn_play.setText("▶ PLAY")

    def _on_pos_changed(self, pos_ms):
        if self._loop_timer.isActive():
            return
        if self._step_frame_idx is not None and self.player.playbackState() != QMediaPlayer.PlayingState:
            return
        if self._loop_wrap_if_needed(pos_ms):
            if self._step_frame_idx is not None:
                self._refresh_tc(self._sec_from_frame_index(self._step_frame_idx))
            return

        sec = pos_ms / 1000.0
        playing = self.player.playbackState() == QMediaPlayer.PlayingState
        if self.fps > 0 and playing and not self._loop_playing:
            self._step_frame_idx = None
        elif self.fps > 0 and not playing:
            sec = self._quantize_to_source_frame(sec)
        self._refresh_tc(sec)

        # Auto-follow playhead during playback only.
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.timeline.follow_playhead()
            self._sample_stutter(pos_ms)

    # ---- JKL (NLE shuttle transport) ----
    #
    # Mirrors Premiere / Resolve behaviour:
    #   L        → play forward 1x; successive presses ramp 2x → 4x → 8x
    #   J        → play reverse  1x; successive presses ramp -2x → -4x → -8x
    #   K        → full stop, reset shuttle speed
    #   K held + L → slow-forward frame step (~12 fps feel)
    #   K held + J → slow-reverse frame step
    #   J while playing forward (or L while reverse) → decelerate first

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter) and not event.isAutoRepeat():
            fw = self.focusWidget()
            if fw is self.edit_in:
                self._commit_in_tc_edit()
                event.accept()
                return
            if fw is self.edit_out:
                self._commit_out_tc_edit()
                event.accept()
                return
        if key == Qt.Key_K:
            if not event.isAutoRepeat():
                self._k_held = True
                self._jkl_stop()
            return
        if key == Qt.Key_J:
            if self._k_held:
                self._k_step_dir = -1
                if not self._k_step_timer.isActive():
                    self._k_step_tick()
                    self._k_step_timer.start()
                self._update_speed_indicator()
            else:
                self._jkl_shuttle(-1)
            return
        if key == Qt.Key_L:
            if self._k_held:
                self._k_step_dir = 1
                if not self._k_step_timer.isActive():
                    self._k_step_tick()
                    self._k_step_timer.start()
                self._update_speed_indicator()
            else:
                self._jkl_shuttle(1)
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        key = event.key()
        if key == Qt.Key_K and not event.isAutoRepeat():
            self._k_held = False
            self._k_step_timer.stop()
            self._k_step_dir = 0
            self._update_speed_indicator()
            return
        if key in (Qt.Key_J, Qt.Key_L) and self._k_held:
            self._k_step_timer.stop()
            self._k_step_dir = 0
            self._update_speed_indicator()
            return
        super().keyReleaseEvent(event)

    def _jkl_shuttle(self, direction):
        """Ramp shuttle speed in *direction* (+1 forward, -1 reverse)."""
        self._step_frame_idx = None
        cur = self.jkl_speed
        if direction == 1:
            if cur < 0:
                idx = self._jkl_speeds.index(min(self._jkl_speeds, key=lambda s: abs(s - abs(cur))))
                new_idx = max(0, idx - 1)
                self.jkl_speed = -self._jkl_speeds[new_idx] if new_idx > 0 else 0.0
            else:
                idx = -1
                for i, s in enumerate(self._jkl_speeds):
                    if abs(cur - s) < 0.01:
                        idx = i
                        break
                self.jkl_speed = self._jkl_speeds[min(idx + 1, len(self._jkl_speeds) - 1)]
        else:
            if cur > 0:
                idx = self._jkl_speeds.index(min(self._jkl_speeds, key=lambda s: abs(s - cur)))
                new_idx = max(0, idx - 1)
                self.jkl_speed = self._jkl_speeds[new_idx] if new_idx > 0 else 0.0
            else:
                idx = -1
                for i, s in enumerate(self._jkl_speeds):
                    if abs(abs(cur) - s) < 0.01:
                        idx = i
                        break
                self.jkl_speed = -self._jkl_speeds[min(idx + 1, len(self._jkl_speeds) - 1)]

        if abs(self.jkl_speed) < 0.01:
            self._jkl_stop()
            return

        self._rev_timer.stop()
        rate = self.jkl_speed
        if rate < 0:
            # QMediaPlayer can't play in reverse; simulate with a timer
            # that steps backwards by N frames per tick.
            self.player.pause()
            speed_mult = abs(rate)
            frames_per_tick = max(1, int(speed_mult))
            interval = max(16, int(1000 / self.fps / speed_mult * frames_per_tick))
            self._rev_frames = frames_per_tick
            self._rev_timer.setInterval(interval)
            self._rev_timer.start()
            self.btn_play.setText(f"◀◀ {abs(rate):.0f}x")
        else:
            self._cancel_precise_preview_work()
            self._precise_frame.hide()
            self._reset_stutter()
            self.player.setPlaybackRate(rate)
            self._set_playback_media(
                self._playback_media_for_play(),
                hold_ms=self._authoritative_playhead_ms(),
            )
            self.player.play()
            self.btn_play.setText(f"▶▶ {rate:.0f}x" if rate > 1 else "▶ PLAY")
        self._update_speed_indicator()
        self._apply_precise_preview()

    def _rev_tick(self):
        """Timer callback for simulated reverse playback."""
        delta = -self._rev_frames / self.fps
        new_ms = max(0, int((self.current_sec + delta) * 1000))
        if new_ms <= 0:
            self._rev_timer.stop()
            self.jkl_speed = 0.0
            self.btn_play.setText("▶ PLAY")
            self._update_speed_indicator()
        self.player.setPosition(new_ms)
        if self._loop_wrap_if_needed(new_ms):
            return
        if self.fps > 0:
            sec = self._quantize_to_source_frame(new_ms / 1000.0)
            self._step_frame_idx = max(0, min(int(round(sec * self.fps)), self._max_frame_idx))
            self._refresh_tc(self._step_frame_idx / self.fps)
        self._apply_precise_preview(exact=True)

    def _jkl_stop(self):
        """K = full stop, reset shuttle."""
        self.jkl_speed = 0.0
        self._rev_timer.stop()
        self.player.pause()
        self.player.setPlaybackRate(1.0)
        self.btn_play.setText("▶ PLAY")
        self._stutter_state = False
        self._stutter_samples.clear()
        self._update_speed_indicator()
        fi = self._player_frame_index()
        if fi is not None:
            self._park_at_frame_index(fi)
            return
        self._apply_precise_preview(exact=True)

    def _k_step_tick(self):
        """Single frame step while K is held + J or L pressed."""
        self._step_frames(self._k_step_dir)

    def _update_speed_indicator(self):
        """Show/hide the playback speed overlay on the video monitor."""
        _overlay_base = (
            "font-size: 10px; font-weight: bold; border: none; "
            "padding: 3px 10px; border-radius: 3px;"
        )
        rate = self.jkl_speed
        show = False
        if self._k_held and self._k_step_dir != 0:
            direction = "▶" if self._k_step_dir > 0 else "◀"
            self._lbl_speed.setText(f"{direction}  SLOW STEP (frame-by-frame)")
            self._lbl_speed.setStyleSheet(
                f"color: {COLOR_ACCENT}; background: rgba(0,0,0,180); {_overlay_base}"
            )
            show = True
        elif abs(rate) > 1.01:
            speed = abs(rate)
            direction = "▶▶" if rate > 0 else "◀◀"
            self._lbl_speed.setText(f"{direction}  {speed:.0f}× speed")
            self._lbl_speed.setStyleSheet(
                f"color: {COLOR_WARNING}; background: rgba(0,0,0,180); {_overlay_base}"
            )
            show = True
        elif self._stutter_state and (
            self.player.playbackState() == QMediaPlayer.PlayingState
        ):
            direction = "◀◀" if rate < -0.01 else "▶"
            self._lbl_speed.setText(f"⚠ {direction} Playback is not real-time")
            self._lbl_speed.setStyleSheet(
                f"color: {COLOR_DANGER}; background: rgba(0,0,0,200); {_overlay_base}"
            )
            show = True

        if show:
            self._reposition_speed_overlay()
            self._lbl_speed.raise_()
            self._lbl_speed.show()
        else:
            self._lbl_speed.hide()

    def _reposition_speed_overlay(self):
        """Keep the speed overlay centered at the bottom of the video widget."""
        vw = self.video_widget
        self._lbl_speed.adjustSize()
        w = max(self._lbl_speed.sizeHint().width() + 20, 180)
        self._lbl_speed.setFixedWidth(w)
        x = (vw.width() - w) // 2
        y = vw.height() - self._lbl_speed.height() - 8
        self._lbl_speed.move(x, y)

    def _layout_precise_frame_overlay(self):
        """Stretch the surgical preview label to cover the video surface."""
        vw = self.video_widget
        self._precise_frame.setGeometry(0, 0, vw.width(), vw.height())

    def _cancel_precise_preview_work(self):
        """Drop pending overlay decodes (e.g. before PLAY)."""
        self._precise_seek_timer.stop()
        self._precise_resize_timer.stop()
        self._preview_gen += 1
        with self._precise_lock:
            self._precise_coalesce = None

    def _debounced_scrub_preview_flush(self):
        """Coalesced overlay refresh after timeline drag or monitor resize."""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            return
        fi = self._step_frame_idx
        self._flush_precise_preview_async(
            exact=self._preview_exact_for_monitor(),
            force_fi=fi,
        )

    def _schedule_precise_preview_debounced(self):
        """Timeline scrub: coalesce rapid drags; lower-res decode while dragging."""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            return
        self._precise_seek_timer.start()

    def _apply_precise_preview(self, *, exact=False, force_fi=None):
        """Queue frame-exact overlay (async). Always decodes from full source."""
        self._precise_seek_timer.stop()
        self._precise_resize_timer.stop()
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self._precise_frame.hide()
            return
        self._flush_precise_preview_async(exact=exact, force_fi=force_fi)

    def _remember_frame_cache(self, fi, png_bytes, *, exact=False):
        if not png_bytes:
            return
        key = self._frame_cache_key(fi, exact)
        if key in self._frame_png_cache:
            if key in self._frame_cache_order:
                self._frame_cache_order.remove(key)
            self._frame_cache_order.append(key)
            return
        self._frame_png_cache[key] = png_bytes
        self._frame_cache_order.append(key)
        while len(self._frame_cache_order) > self._frame_cache_max:
            old = self._frame_cache_order.pop(0)
            self._frame_png_cache.pop(old, None)

    def _show_precise_png(self, png_bytes, vw, vh, *, exact=False):
        if not png_bytes:
            self._precise_frame.hide()
            return False
        img = QImage()
        if not img.loadFromData(png_bytes):
            self._precise_frame.hide()
            return False
        pix = QPixmap.fromImage(img)
        if pix.isNull():
            self._precise_frame.hide()
            return False
        if pix.width() != vw or pix.height() != vh:
            mode = Qt.SmoothTransformation if exact else Qt.FastTransformation
            pix = pix.scaled(vw, vh, Qt.KeepAspectRatio, mode)
        self._precise_frame.setPixmap(pix)
        self._precise_frame.show()
        self._precise_frame.raise_()
        self._lbl_speed.raise_()
        return True

    def _flush_precise_preview_async(self, *, exact=False, force_fi=None):
        """Snapshot playhead + widget size and decode in a worker thread."""
        if self._precise_shutdown:
            return
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self._precise_frame.hide()
            return
        if not self.fps or self.fps <= 0:
            self._precise_frame.hide()
            return
        self._layout_precise_frame_overlay()
        vw, vh = self._monitor_size()
        if vw < 32 or vh < 32:
            QTimer.singleShot(
                100,
                lambda: self._apply_precise_preview(exact=exact, force_fi=force_fi),
            )
            return
        if force_fi is not None:
            fi = int(force_fi)
        else:
            fi = self._player_frame_index()
        if fi is None:
            fi = 0
        fi = max(0, min(fi, self._max_frame_idx))
        self._precise_display_fi = fi
        cached = self._frame_cache_get(fi, exact)
        if cached and self._show_precise_png(cached, vw, vh, exact=exact):
            return
        tw, th = preview_decode_dimensions(vw, vh, exact=exact)
        path = self._source_media_path
        fps = self.fps

        self._preview_gen += 1
        gen = self._preview_gen
        with self._precise_lock:
            if self._precise_worker_busy:
                self._precise_coalesce = (
                    gen, path, fi, fps, tw, th, vw, vh, exact
                )
                return
            self._precise_worker_busy = True
        threading.Thread(
            target=self._precise_thread_job,
            args=(gen, path, fi, fps, tw, th, vw, vh, exact),
            daemon=True,
        ).start()

    def _precise_thread_job(
        self, gen, path, frame_idx, fps, tw, th, vw, vh, exact
    ):
        png = None
        try:
            png = _extract_frame_png_bytes(
                path, 0.0, fps, tw, th, frame_index=frame_idx
            )
        except Exception:
            png = None
        self._precise_bridge.decode_done.emit(
            png, gen, vw, vh, bool(exact), int(frame_idx)
        )

    @Slot(object, int, int, int, bool, int)
    def _on_precise_decode_finished(self, png_bytes, gen, vw, vh, exact, frame_idx):
        if self._precise_shutdown:
            with self._precise_lock:
                self._precise_worker_busy = False
                self._precise_coalesce = None
            return
        next_job = None
        with self._precise_lock:
            self._precise_worker_busy = False
            if self._precise_coalesce is not None:
                next_job = self._precise_coalesce
                self._precise_coalesce = None
                self._precise_worker_busy = True

        if (
            gen == self._preview_gen
            and self.player.playbackState() != QMediaPlayer.PlayingState
        ):
            want_fi = self._step_frame_idx
            if want_fi is None:
                want_fi = self._precise_display_fi
            if want_fi is not None and int(frame_idx) != int(want_fi):
                pass
            else:
                if png_bytes:
                    self._remember_frame_cache(frame_idx, png_bytes, exact=exact)
                if self._show_precise_png(png_bytes, vw, vh, exact=exact):
                    self._precise_display_fi = int(frame_idx)

        if next_job is not None and not self._precise_shutdown:
            gen2, path2, fi2, fps2, tw2, th2, vw2, vh2, ex2 = next_job
            threading.Thread(
                target=self._precise_thread_job,
                args=(gen2, path2, fi2, fps2, tw2, th2, vw2, vh2, ex2),
                daemon=True,
            ).start()

    def _playback_media_for_play(self):
        """Qt player path during PLAY (proxy when ready, else source)."""
        if (
            self._uses_playback_proxy()
            and self._playback_proxy_path
            and os.path.isfile(self._playback_proxy_path)
        ):
            return self._playback_proxy_path
        return self._source_media_path

    def _set_playback_media(self, path, *, hold_ms=None):
        """Swap QMediaPlayer source; restore playhead after duration loads."""
        if not path or not os.path.isfile(path):
            return
        cur = ""
        src = self.player.source()
        if src.isLocalFile():
            cur = src.toLocalFile()
        if os.path.normcase(cur) == os.path.normcase(path):
            return
        if hold_ms is None:
            hold_ms = self._authoritative_playhead_ms()
        self._pending_playback_pos_ms = int(hold_ms)
        self.player.setSource(QUrl.fromLocalFile(path))

    def _start_playback_proxy_build(self):
        if self._precise_shutdown or not self._uses_playback_proxy():
            return
        key = self._scene_content_key
        if not key:
            return
        existing = build_playback_proxy_path(key)
        if existing and os.path.isfile(existing):
            self._on_playback_proxy_ready(existing)
            return
        if self._proxy_build_running:
            return
        src_w = int(self.task.specs.get("w") or 0)
        src_h = int(self.task.specs.get("h") or 0)
        self._proxy_build_running = True
        self.lbl_scene.setText("Building ½ res playback proxy…")

        def _job():
            out = build_playback_proxy(
                self._source_media_path, key, src_w, src_h
            )
            self._precise_bridge.playback_proxy_ready.emit(out or "")

        threading.Thread(target=_job, daemon=True).start()

    @Slot(str)
    def _on_playback_proxy_ready(self, path):
        self._proxy_build_running = False
        if self._precise_shutdown:
            return
        if not self._uses_playback_proxy():
            return
        if path and os.path.isfile(path):
            self._playback_proxy_path = path
            if self.lbl_scene.text().startswith("Building ½ res"):
                self.lbl_scene.setText("½ res preview proxy ready")
            if self.player.playbackState() == QMediaPlayer.PlayingState:
                self._set_playback_media(
                    path, hold_ms=self._authoritative_playhead_ms()
                )
            else:
                self._refresh_monitor_at_playhead()
        elif self.lbl_scene.text().startswith("Building ½ res"):
            self.lbl_scene.setText("½ res proxy failed — using full source")

    def _on_play_res_changed(self, _index=0):
        """Preview Full / ½ — refresh monitor; playhead frame unchanged."""
        if self._play_res_block or self._precise_shutdown:
            return
        was_playing = (
            self.player.playbackState() == QMediaPlayer.PlayingState
        )
        self._cancel_precise_preview_work()
        self._frame_png_cache.clear()
        self._frame_cache_order.clear()
        self._loop_last_shown_fi = None
        if self._uses_playback_proxy():
            self._start_playback_proxy_build()
        elif self.lbl_scene.text().startswith(("Building ½ res", "½ res")):
            self.lbl_scene.setText("")
        self._refresh_monitor_at_playhead()
        if was_playing:
            self.player.play()

    def _reset_stutter(self):
        """Reset stutter tracking — call when playback starts or mode changes."""
        self._stutter_wall_t0 = time.monotonic()
        self._stutter_pos_t0 = self.player.position()
        self._stutter_samples.clear()
        self._stutter_state = False

    def _sample_stutter(self, pos_ms):
        """Compare wall-clock elapsed vs video position elapsed to detect
        stutter during forward playback at 1× rate."""
        rate = self.player.playbackRate()
        if rate < 0.5 or rate > 1.5:
            return
        now = time.monotonic()
        wall_delta = (now - self._stutter_wall_t0) * 1000.0
        pos_delta = pos_ms - self._stutter_pos_t0
        if wall_delta < 300:
            return
        self._stutter_wall_t0 = now
        self._stutter_pos_t0 = pos_ms
        if wall_delta > 0:
            ratio = pos_delta / (wall_delta * rate)
            self._stutter_samples.append(ratio)
            if len(self._stutter_samples) > 8:
                self._stutter_samples.pop(0)
        if len(self._stutter_samples) >= 3:
            avg = sum(self._stutter_samples) / len(self._stutter_samples)
            was = self._stutter_state
            self._stutter_state = avg < 0.80
            if was != self._stutter_state:
                self._update_speed_indicator()

    # ---- Actions ----

    def toggle_play(self):
        self._rev_timer.stop()
        self.jkl_speed = 0.0
        self.player.setPlaybackRate(1.0)
        self._stop_loop_playback()

        if self.player.playbackState() == QMediaPlayer.PlayingState:
            hold_ms = self.player.position()
            hold_fi = None
            if self.fps > 0:
                if self._step_frame_idx is not None:
                    hold_fi = self._step_frame_idx
                else:
                    hold_fi = source_frame_index_from_sec(
                        hold_ms / 1000.0,
                        self.fps,
                        self._max_frame_idx,
                        rounding="floor",
                    )
            self.player.pause()
            self.btn_play.setText("▶ PLAY")
            self._stutter_state = False
            if hold_fi is not None:
                self._park_at_frame_index(
                    hold_fi,
                    preview_exact=self._preview_exact_for_monitor(),
                )
            else:
                self._apply_precise_preview(
                    exact=self._preview_exact_for_monitor()
                )
        else:
            self._cancel_precise_preview_work()
            self._precise_frame.hide()
            self._step_frame_idx = None
            self._loop_seek_guard = False
            if self._loop_active and self.fps > 0:
                in_fi, last_fi = self._loop_frame_bounds()
                cur_fi = source_frame_index_from_sec(
                    self.player.position() / 1000.0,
                    self.fps,
                    self._max_frame_idx,
                    rounding="floor",
                )
                if cur_fi < in_fi or cur_fi > last_fi:
                    self.player.setPosition(ms_start_of_frame(in_fi, self.fps))
            self._reset_stutter()
            self._set_playback_media(
                self._playback_media_for_play(),
                hold_ms=self._authoritative_playhead_ms(),
            )
            self.player.play()
            self.btn_play.setText("⏸ PAUSE")
        self._update_speed_indicator()

    def _displayed_frame_sec(self):
        """Return the PTS of the frame currently displayed on screen.

        Uses the same frame index as the frame-exact overlay and export
        quantisation — no QMediaPlayer forward bias while paused."""
        fi = self._player_frame_index()
        if fi is not None:
            return fi / self.fps
        return self._quantize_to_source_frame(self.player.position() / 1000.0)

    def _quantize_to_source_frame(self, sec):
        """Snap a timestamp to the nearest source-frame boundary (1/fps)."""
        if not self.fps or self.fps <= 0:
            return sec
        sec = max(0.0, min(float(sec), self.duration_sec))
        fi = self._frame_index_from_sec(sec)
        return (fi / self.fps) if fi is not None else sec

    def _update_trim_thumb(self, which, frame_idx=None):
        """Display the frame-exact thumbnail for IN or OUT (async decode, PR1).
        Pass ``frame_idx`` when known (e.g. right after SET I/O) so the thumb
        matches the parked monitor frame exactly."""
        if which == "in":
            fi = (
                frame_idx
                if frame_idx is not None
                else source_frame_index_from_sec(
                    self.in_sec, self.fps, self._max_frame_idx
                )
            )
            lbl = self._trim_thumb_in
        else:
            fi = (
                frame_idx
                if frame_idx is not None
                else self._out_last_included_frame_index()
            )
            lbl = self._trim_thumb_out
        lbl.setVisible(True)
        self._thumb_loader.request(lbl, self.task.path, self.fps, fi, 106, 60)

    def _hide_trim_thumbs(self):
        for lbl in (self._trim_thumb_in, self._trim_thumb_out):
            lbl.clear()
            lbl.setVisible(False)

    def set_in(self):
        self.player.pause()
        self.btn_play.setText("▶ PLAY")
        fi = self._authoritative_paused_fi()
        if fi is None:
            fi = 0
        fi = max(0, min(int(fi), self._max_frame_idx))
        self.in_sec = self._sec_from_frame_index(fi)
        self.timeline.set_in(self._frame_index_to_timeline_ratio(fi))
        self._tc_edit_block = True
        self.edit_in.set_committed_text(format_frame_index_as_tc(fi, self.fps))
        self._tc_edit_block = False
        self._update_trim_thumb("in", frame_idx=fi)
        self._park_at_frame_index(fi)

    def set_out(self):
        self.player.pause()
        self.btn_play.setText("▶ PLAY")
        fi = max(0, min(int(self._authoritative_paused_fi() or 0), self._max_frame_idx))
        cap = self._default_out_sec if self.fps > 0 else self.duration_sec
        self._out_incl_fi = fi
        self.out_sec = exclusive_out_sec_from_included_frame(fi, self.fps, cap)
        in_fi = source_frame_index_from_sec(
            self.in_sec, self.fps, self._max_frame_idx, rounding="floor"
        )
        if source_frame_index_from_sec(self.out_sec, self.fps) <= in_fi:
            fi = min(in_fi, self._max_frame_idx)
            self._out_incl_fi = fi
            self.out_sec = exclusive_out_sec_from_included_frame(fi, self.fps, cap)
        self._sync_out_markers_ui()
        self._update_trim_thumb("out", frame_idx=fi)
        self._park_at_frame_index(fi, sync_tc_fields=True, preview_exact=True)

    def goto_first_frame(self):
        """Home — first source frame (frame 0)."""
        self._stop_loop_playback()
        self._park_at_frame_index(0)

    def goto_last_frame(self):
        """End — last source frame (frame N-1)."""
        self._stop_loop_playback()
        self._park_at_frame_index(self._max_frame_idx)

    def goto_in(self):
        """Jump the playhead to the IN point (NLE Shift+I)."""
        self._stop_loop_playback()
        in_fi = source_frame_index_from_sec(
            self.in_sec, self.fps, self._max_frame_idx, rounding="floor"
        )
        self._park_at_frame_index(in_fi)

    def goto_out(self):
        """Shift+O / GO TO OUT — last included frame (what export keeps)."""
        self._stop_loop_playback()
        self._park_at_frame_index(self._out_last_included_frame_index())

    def _goto_sec(self, sec):
        """Pause + frame-quantized seek (goto IN/OUT, [ ] cut jumps)."""
        self._park_at_sec(sec)

    def clear_trim(self):
        self.in_sec  = 0.0
        self.out_sec = self._default_out_sec if self.fps > 0 else self.duration_sec
        self._out_incl_fi = None
        self._restore_markers()
        self._sync_in_out_tc_fields()
        self._hide_trim_thumbs()

    @Slot(float, float)
    def _on_segment_selected(self, start_ratio, end_ratio):
        """Apply a Shift+Click segment selection to in_sec/out_sec. Both
        endpoints come from the segment-boundary cut PTSs (exclusive OUT, so
        the next scene's first frame is NOT included). We still frame-quantize
        for robustness against any sub-frame drift that snuck in via the cut
        timestamps coming from ffmpeg."""
        in_fi = self._frame_index_from_timeline_ratio(start_ratio, mode="floor")
        out_excl_fi = self._frame_index_from_timeline_ratio(
            end_ratio, mode="round"
        )
        out_excl_fi = max(in_fi + 1, min(out_excl_fi, self._total_source_frames))
        if out_excl_fi <= in_fi:
            return
        self.in_sec = self._sec_from_frame_index(in_fi)
        self.out_sec = self._sec_from_frame_index(out_excl_fi)
        self._out_incl_fi = max(in_fi, out_excl_fi - 1)
        # Update the timeline marker positions WITHOUT touching the segment
        # overlay state (manual=False), so the green selection stays painted
        # while the I/O markers move into place.
        self.timeline.set_in(
            self._frame_index_to_timeline_ratio(in_fi), manual=False
        )
        self._tc_edit_block = True
        self.edit_in.set_committed_text(format_frame_index_as_tc(in_fi, self.fps))
        self._tc_edit_block = False
        self._sync_out_markers_ui(manual=False)
        # Snap playhead to the IN of the selection so the user immediately
        # previews what they just picked.
        self._update_trim_thumb("in")
        self._update_trim_thumb("out")
        self._park_at_frame_index(in_fi)

    # ---- Scene detection ----

    def _snap_frame_index(self, fi):
        """Snap playhead frame index to nearest scene cut (frame-quantized)."""
        if not self.chk_snap.isChecked() or not self.cuts_fi or not self.fps:
            return fi
        nearest_fi = min(self.cuts_fi, key=lambda cf: abs(cf - fi))
        thr_frames = max(1, int(round(self.snap_threshold_sec * self.fps)))
        if abs(nearest_fi - fi) <= thr_frames:
            return nearest_fi
        return fi

    def _snap_sec(self, sec):
        """Snap to the nearest detected cut within `snap_threshold_sec`. If snap is
        disabled or no cut is close enough, return `sec` unchanged."""
        fi = source_frame_index_from_sec(sec, self.fps, self._max_frame_idx)
        return self._sec_from_frame_index(self._snap_frame_index(fi))

    def _jump_to_cut(self, direction):
        """Move the playhead to the previous (-1) or next (+1) scene cut."""
        if not self.cuts_fi:
            return
        cur_fi = self._authoritative_paused_fi() or 0
        if direction < 0:
            candidates = [f for f in self.cuts_fi if f < cur_fi]
            target_fi = candidates[-1] if candidates else self.cuts_fi[0]
        else:
            candidates = [f for f in self.cuts_fi if f > cur_fi]
            target_fi = candidates[0] if candidates else self.cuts_fi[-1]
        self._park_at_frame_index(target_fi)

    def _on_cuts_view_toggled(self, on):
        """Single-switch handler for the 👁 CUTS button. Shows/hides cut
        markers AND keeps the snap checkbox in lockstep so the timeline
        either fully respects the detected cuts or fully ignores them
        — never half-and-half (which was the source of "snap is acting
        weird" reports in the previous design with two independent
        toggles)."""
        on = bool(on)
        self.timeline.set_cuts_visible(on)
        # Align the snap checkbox: ON when cuts are visible, OFF when
        # hidden. We also disable the checkbox while cuts are hidden so
        # the user can't accidentally re-enable snap behavior while the
        # markers are invisible (would feel like a phantom snap).
        self.chk_snap.setChecked(on)
        self.chk_snap.setEnabled(on)
        # Update button label so the meaning of the toggle reads at a
        # glance (matching the "open eye / closed eye" idiom).
        self.btn_cuts_view.setText("👁 CUTS" if on else "🚫 CUTS")

    def _toggle_scene_detection(self):
        """Start scene detection, or cancel if already running."""
        if self.scene_worker is not None and self.scene_worker.isRunning():
            self.scene_worker.cancel()
            self.btn_detect.setEnabled(False)
            self.lbl_scene.setText("Cancelling…")
            return
        self.cuts_sec = []
        self.timeline.set_cuts([])
        self.btn_detect.setText("✖ CANCEL DETECTION")
        self.btn_detect.setEnabled(True)
        self.lbl_scene.setText("Analyzing… 0% (0 cuts)")
        # Reveal + zero the progress bar at scan start; _on_scene_finished
        # will hide it again when the run ends (success / fail / cancel).
        self.scene_progress.setValue(0)
        self.scene_progress.setVisible(True)
        scan_dur = self._media_duration_sec()
        worker = SceneDetectorWorker(
            self.task.path, scan_dur, threshold=0.30, fps=self.fps, parent=self
        )
        worker.progress.connect(self._on_scene_progress)
        worker.cuts_ready.connect(self._on_scene_done)
        worker.failed.connect(self._on_scene_failed)
        worker.finished.connect(self._on_scene_finished)
        self.scene_worker = worker
        worker.start()

    @Slot(int, int)
    def _on_scene_progress(self, pct, cuts_so_far):
        self.lbl_scene.setText(f"Analyzing… {pct}% ({cuts_so_far} cuts)")
        self.scene_progress.setValue(pct)

    @Slot(list)
    def _on_scene_done(self, cuts_fi):
        raw_n = len(cuts_fi)
        self._apply_scene_cut_frames(cuts_fi)
        if self.cuts_fi:
            self.lbl_scene.setText(f"{len(self.cuts_fi)} cut(s) detected — use [ / ] to jump")
        elif raw_n > 0:
            self.lbl_scene.setText(
                f"0 cut(s) after frame-align ({raw_n} raw) — check duration/fps in source specs"
            )
        else:
            self.lbl_scene.setText("No scene changes at threshold 0.30 — try another clip or re-DETECT")
        save_scene_cache(
            self._scene_content_key, self._scene_threshold, self.cuts_fi,
            src_path=self.task.path,
        )

    def _clear_scene_cache_clicked(self):
        """Drop RAM/disk scene cache for this source and clear timeline markers."""
        if self.scene_worker is not None and self.scene_worker.isRunning():
            self.scene_worker.cancel()
            self.scene_worker.wait(1500)
        if not self._scene_content_key:
            self.lbl_scene.setText("Cannot fingerprint this file — cache not keyed")
            return
        _ram, _disk = clear_scene_cache(self._scene_content_key)
        self.cuts_fi = []
        self.cuts_sec = []
        self.timeline.set_cuts([])
        self.lbl_scene.setText(
            f"Scene cache cleared ({_disk} file(s) removed) — click DETECT SCENES to rescan"
        )

    def _try_warm_start_scenes(self):
        """If the persistent cache has cuts for this source+threshold, load them
        immediately so the user sees the markers without clicking DETECT.
        Silently no-ops when the file can't be fingerprinted or cache is empty."""
        cached = load_scene_cache(self._scene_content_key, self._scene_threshold)
        if not cached:
            return
        dur = self._media_duration_sec()
        cuts_payload = cached.get("cuts_fi")
        if cached.get("ver", 1) >= 2 and cuts_payload:
            self._apply_scene_cut_frames(cuts_payload)
        else:
            max_fi = self._effective_max_frame_idx_for_cuts()
            legacy_fi = []
            for c in cached.get("cuts_sec") or []:
                if not (0.0 <= float(c) <= dur + 0.05):
                    continue
                fi = scene_cut_frame_index_from_detection(
                    float(c), self.fps, max_fi
                )
                if fi > 0:
                    legacy_fi.append(fi)
            self._apply_scene_cut_frames(legacy_fi)
        self.lbl_scene.setText(
            f"{len(self.cuts_sec)} cut(s) cached — use [ / ] to jump (re-DETECT to refresh)"
        )

    @Slot(str)
    def _on_scene_failed(self, msg):
        self.lbl_scene.setText(f"Detection failed: {msg}")

    @Slot()
    def _on_scene_finished(self):
        # Always re-enable + reset the button regardless of success/failure/cancel.
        self.btn_detect.setEnabled(True)
        self.btn_detect.setText("🎬 DETECT SCENES")
        # Hide the inline progress bar — keeping it visible at 100% after a
        # finished run reads as "still working" to the user.
        self.scene_progress.setVisible(False)
        if self.scene_worker is not None:
            try: self.scene_worker.deleteLater()
            except Exception: pass
            self.scene_worker = None

    def _stop_all_playback(self):
        """Stop player and kill any running scene detection."""
        self.player.stop()
        if self.scene_worker is not None and self.scene_worker.isRunning():
            self.scene_worker.cancel()
            self.scene_worker.wait(2000)

    def _finalize_trim_frame_alignment(self):
        """Snap IN/OUT to integer source-frame indices so OK matches ffmpeg."""
        if not self.fps or self.fps <= 0:
            return
        in_i = source_frame_index_from_sec(
            self.in_sec, self.fps, self._max_frame_idx
        )
        if self._out_incl_fi is not None:
            last_incl = max(0, min(int(self._out_incl_fi), self._max_frame_idx))
            out_excl_i = min(last_incl + 1, self._total_source_frames)
        else:
            out_excl_i = int(
                math.ceil(float(self.out_sec) * float(self.fps) - 1e-9)
            )
        out_excl_i = max(in_i + 1, min(out_excl_i, self._total_source_frames))
        self.in_sec = sec_from_source_frame_index(in_i, self.fps)
        self.out_sec = sec_from_source_frame_index(out_excl_i, self.fps)
        self._out_incl_fi = out_excl_i - 1

    def accept(self):
        self._finalize_trim_frame_alignment()
        self._trim_precise_shutdown()
        self._stop_all_playback()
        super().accept()

    def reject(self):
        self._trim_precise_shutdown()
        self._stop_all_playback()
        super().reject()

    def closeEvent(self, ev):
        self._trim_precise_shutdown()
        self._stop_all_playback()
        super().closeEvent(ev)

    def _trim_precise_shutdown(self):
        self._stop_loop_playback()
        self._precise_shutdown = True
        app = QApplication.instance()
        if app and self._tc_app_filter:
            app.removeEventFilter(self)
            self._tc_app_filter = False
        self._precise_seek_timer.stop()
        self._precise_resize_timer.stop()
        self._preview_gen += 10000
        with self._precise_lock:
            self._precise_coalesce = None



# --- Frame extraction utility ---

def _extract_frame_png_bytes(video_path, sec, fps, tw, th, frame_index=None):
    """Frame-exact grab as PNG bytes (no Qt).

    Uses a combined fast+precise seek path for 100% accurate frame retrieval.
    Pass ``frame_index`` when known (preferred).
    """
    try:
        tw = max(32, int(tw))
        th = max(32, int(th))
    except (TypeError, ValueError):
        tw, th = 320, 240
    fi = None
    if fps and float(fps) > 0:
        if frame_index is not None:
            fi = max(0, int(frame_index))
        else:
            fi = source_frame_index_from_sec(sec, fps)
        sec = sec_from_source_frame_index(fi, fps)
    else:
        sec = max(0.0, float(sec))
    fd, tmp_png = tempfile.mkstemp(suffix=".png", prefix="magifpf_")
    os.close(fd)
    try:
        vf_scale = f"scale={tw}:-2:flags=lanczos"
        flags = 0x08000000 if os.name == "nt" else 0
        # Frame index known: seek near target then select local n (fast + unique per fi).
        if fi is not None:
            lead = max(0, int(fi) - 3)
            local_n = int(fi) - lead
            lead_sec = sec_from_source_frame_index(lead, fps)
            cmd = [
                FFMPEG_PATH, "-y", "-nostdin",
                "-ss", f"{lead_sec:.6f}",
                "-i", video_path,
                "-vf", f"select=eq(n\\,{local_n}),{vf_scale}",
                "-frames:v", "1",
                "-vsync", "0",
                tmp_png,
            ]
            proc = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
                timeout=30,
            )
            if proc.returncode == 0 and os.path.exists(tmp_png):
                with open(tmp_png, "rb") as fh:
                    data = fh.read()
                if data:
                    return data
            # Accurate PTS seek (output-side -ss) — one distinct frame per index.
            cmd2 = [
                FFMPEG_PATH, "-y", "-nostdin",
                "-i", video_path,
                "-ss", f"{sec:.6f}",
                "-frames:v", "1",
                "-vf", vf_scale,
                "-vsync", "0",
                tmp_png,
            ]
            proc2 = subprocess.run(
                cmd2,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
                timeout=30,
            )
            if proc2.returncode == 0 and os.path.exists(tmp_png):
                with open(tmp_png, "rb") as fh:
                    data = fh.read()
                if data:
                    return data
        fast_seek = max(0.0, sec - 2.0)
        # Near t≈0, input-only seek is more reliable than combined seek on some MP4s.
        if fast_seek < 0.05:
            cmd = [
                FFMPEG_PATH, "-y", "-nostdin",
                "-i", video_path,
                "-ss", f"{max(0, sec):.6f}",
                "-frames:v", "1",
                "-vf", vf_scale,
                tmp_png,
            ]
        else:
            precise_seek = sec - fast_seek
            cmd = [
                FFMPEG_PATH, "-y", "-nostdin",
                "-ss", f"{fast_seek:.6f}",
                "-i", video_path,
                "-ss", f"{precise_seek:.6f}",
                "-frames:v", "1",
                "-vf", vf_scale,
                tmp_png,
            ]
        flags = 0x08000000 if os.name == "nt" else 0
        proc = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
            timeout=15,
        )
        if proc.returncode == 0 and os.path.exists(tmp_png):
            with open(tmp_png, "rb") as fh:
                data = fh.read()
            if data:
                return data
    except Exception:
        pass
    finally:
        try:
            os.remove(tmp_png)
        except OSError:
            pass
    # OpenCV frame index is unreliable at 23.976 — never use when fi is known.
    if HAS_CV2 and frame_index is None:
        cap = None
        try:
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                if fps and float(fps) > 0:
                    fi = source_frame_index_from_sec(sec, fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, fi))
                else:
                    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, sec) * 1000.0)
                ret, frame = cap.read()
                if ret and frame is not None:
                    h0, w0 = frame.shape[:2]
                    if w0 > 0 and h0 > 0:
                        scale = min(tw / float(w0), th / float(h0))
                        nw = max(1, int(round(w0 * scale)))
                        nh = max(1, int(round(h0 * scale)))
                        interp = (
                            cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
                        )
                        small = cv2.resize(frame, (nw, nh), interpolation=interp)
                        ok, buf = cv2.imencode(".png", small)
                        if ok:
                            return buf.tobytes()
        except Exception:
            pass
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
    return None


def extract_frame_at(video_path, sec, fps=None, tw=142, th=80, frame_index=None):
    """Frame-exact single-frame grab. Returns a scaled QPixmap or None."""
    data = _extract_frame_png_bytes(
        video_path, sec, fps, tw, th, frame_index=frame_index
    )
    if not data:
        return None
    try:
        img = QImage()
        if img.loadFromData(data):
            pix = QPixmap.fromImage(img)
            if not pix.isNull():
                return pix.scaled(
                    tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
    except Exception:
        pass
    return None


class _AsyncThumbLoader(QObject):
    """PR1: decode trim thumbnails OFF the UI thread.

    Same frame-exact decode path as ``extract_frame_at`` (so thumbs never
    drift from the export), but run in a daemon thread and delivered back to
    the owner thread via a Qt signal. Each target QLabel carries its own
    generation counter, so a rapid re-request — or a hide/clear via
    ``cancel`` — drops stale in-flight results without cross-cancelling the
    sibling IN/OUT label. QPixmap is built in the slot (UI thread); only the
    PNG bytes cross the thread boundary."""

    _done = Signal(object, int, object)  # (png_bytes|None, gen, QLabel)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._done.connect(self._apply)

    def request(self, label, video_path, fps, frame_index, tw, th, *, empty_text="—"):
        gen = getattr(label, "_thumb_gen", 0) + 1
        label._thumb_gen = gen
        label._thumb_size = (int(tw), int(th))
        label._thumb_empty_text = empty_text

        def _job():
            png = None
            try:
                png = _extract_frame_png_bytes(
                    video_path, 0.0, fps, tw, th, frame_index=frame_index
                )
            except Exception:
                png = None
            self._done.emit(png, gen, label)

        threading.Thread(target=_job, daemon=True).start()

    def cancel(self, label):
        """Invalidate any in-flight decode for this label (e.g. on hide)."""
        label._thumb_gen = getattr(label, "_thumb_gen", 0) + 1

    @Slot(object, int, object)
    def _apply(self, png, gen, label):
        if getattr(label, "_thumb_gen", 0) != gen:
            return
        tw, th = getattr(label, "_thumb_size", (142, 80))
        if png:
            img = QImage()
            if img.loadFromData(png):
                pix = QPixmap.fromImage(img)
                if not pix.isNull():
                    label.setPixmap(
                        pix.scaled(
                            tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                    )
                    return
        label.clear()
        label.setText(getattr(label, "_thumb_empty_text", "—"))


# --- UI Classes ---

class DropZoneWidget(QWidget):
    """Hero drop zone widget with two states: empty and loaded."""
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self):
        main_l = QVBoxLayout(self)
        main_l.setContentsMargins(0, 0, 0, 0)
        self._stack = QStackedWidget()
        main_l.addWidget(self._stack)

        # ── EMPTY STATE ──────────────────────────────────────────────
        self._w_empty = QFrame()
        self._w_empty.setObjectName("dz_empty")
        self._w_empty.setStyleSheet(
            f"QFrame#dz_empty {{ background: {COLOR_BG}; border: 2px dashed #2d2d2d; border-radius: 12px; }}"
        )
        ev = QVBoxLayout(self._w_empty)
        ev.setAlignment(Qt.AlignCenter)
        ev.setSpacing(14)

        self._lbl_icon = QLabel("🎬")
        self._lbl_icon.setAlignment(Qt.AlignCenter)
        self._lbl_icon.setStyleSheet("font-size: 58px; border: none; background: transparent;")

        self._lbl_drop_title = QLabel("Drop your video here")
        self._lbl_drop_title.setAlignment(Qt.AlignCenter)
        self._lbl_drop_title.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {COLOR_TEXT_BRIGHT}; border: none; background: transparent;"
        )

        lbl_formats = QLabel("MP4  ·  MOV  ·  MKV  ·  AVI  ·  WEBM")
        lbl_formats.setAlignment(Qt.AlignCenter)
        lbl_formats.setStyleSheet(
            "font-size: 11px; color: #444; border: none; background: transparent; letter-spacing: 2px;"
        )

        self.btn_browse = QPushButton("Browse File...")
        self.btn_browse.setToolTip("Open a file dialog to select a video to convert.")
        self.btn_browse.setFixedSize(150, 34)
        self.btn_browse.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1px solid #3a3a3a;
                color: #666; border-radius: 4px; font-size: 12px;
            }}
            QPushButton:hover {{ border-color: {COLOR_ACCENT}; color: {COLOR_ACCENT}; background: #0a1520; }}
        """)

        ev.addStretch(2)
        ev.addWidget(self._lbl_icon)
        ev.addWidget(self._lbl_drop_title)
        ev.addWidget(lbl_formats)
        ev.addSpacing(10)
        ev.addWidget(self.btn_browse, 0, Qt.AlignCenter)
        ev.addStretch(3)
        self._stack.addWidget(self._w_empty)

        # ── LOADED STATE ─────────────────────────────────────────────
        self._w_loaded = QFrame()
        self._w_loaded.setObjectName("dz_loaded")
        self._w_loaded.setStyleSheet(
            f"QFrame#dz_loaded {{ background: {COLOR_BG}; border: 1px solid {COLOR_BORDER}; border-radius: 12px; }}"
        )
        lv = QVBoxLayout(self._w_loaded)
        lv.setContentsMargins(28, 24, 28, 16)
        lv.setSpacing(0)

        top_row = QHBoxLayout()
        top_row.setSpacing(24)
        top_row.setAlignment(Qt.AlignTop)

        self._thumb = QLabel()
        self._thumb.setFixedSize(213, 120)
        self._thumb.setAlignment(Qt.AlignCenter)
        self._thumb.setStyleSheet(
            "background: #0e0e0e; border: 1px solid #1e1e1e; border-radius: 6px; font-size: 36px;"
        )
        self._thumb.setText("🎬")
        top_row.addWidget(self._thumb, 0, Qt.AlignTop)

        info_col = QVBoxLayout()
        info_col.setSpacing(8)
        info_col.setContentsMargins(0, 0, 0, 0)
        info_col.setAlignment(Qt.AlignTop)

        self._lbl_chip = QLabel("  READY  ")
        self._lbl_chip.setFixedHeight(20)
        self._lbl_chip.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._lbl_chip.setStyleSheet(
            f"background: {COLOR_ACCENT}; color: white; border-radius: 3px; "
            f"font-size: 10px; font-weight: bold; padding: 0 6px;"
        )

        self._lbl_filename = QLabel()
        self._lbl_filename.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {COLOR_TEXT_BRIGHT};"
        )
        self._lbl_filename.setWordWrap(True)

        self._lbl_meta = QLabel()
        self._lbl_meta.setStyleSheet(f"font-size: 12px; color: {COLOR_ACCENT};")

        self._lbl_filesize = QLabel()
        self._lbl_filesize.setStyleSheet("font-size: 11px; color: #555;")

        # Output plan summary — shows the user what the current settings
        # will produce (format, target, resolution, mode). Updated live by
        # MainWindow whenever any setting changes.
        self._lbl_output_plan = QLabel()
        self._lbl_output_plan.setWordWrap(True)
        self._lbl_output_plan.setStyleSheet(
            f"font-size: 11px; color: {COLOR_SUCCESS}; font-weight: bold; "
            f"padding: 4px 8px; background: #0a1a0a; border: 1px solid #1a3a1a; border-radius: 4px;"
        )
        self._lbl_output_plan.setVisible(False)

        info_col.addWidget(self._lbl_chip)
        info_col.addWidget(self._lbl_filename)
        info_col.addWidget(self._lbl_meta)
        info_col.addWidget(self._lbl_filesize)
        info_col.addWidget(self._lbl_output_plan)

        top_row.addLayout(info_col, 1)

        lv.addStretch(1)
        lv.addLayout(top_row)

        # ── Trim frame preview strip ────────────────────────────────
        # Shows the exact first and last frame of the trimmed region so
        # the user can spot flash-frames before encoding.
        self._trim_preview = QWidget()
        self._trim_preview.setVisible(False)
        tp_l = QHBoxLayout(self._trim_preview)
        tp_l.setContentsMargins(0, 8, 0, 0)
        tp_l.setSpacing(16)
        tp_l.addStretch(1)

        _thumb_style = (
            "background: #0e0e0e; border: 1px solid #1e1e1e; border-radius: 4px;"
        )
        _lbl_style = (
            f"font-size: 9px; font-weight: bold; color: #777; "
            "border: none; background: transparent;"
        )

        self._thumb_loader = _AsyncThumbLoader(self)  # PR1: async trim-strip thumbs
        in_col = QVBoxLayout(); in_col.setSpacing(2); in_col.setAlignment(Qt.AlignCenter)
        lbl_in_title = QLabel("▶  FIRST FRAME (IN)")
        lbl_in_title.setStyleSheet(_lbl_style)
        lbl_in_title.setAlignment(Qt.AlignCenter)
        self._thumb_in = QLabel()
        self._thumb_in.setFixedSize(142, 80)
        self._thumb_in.setAlignment(Qt.AlignCenter)
        self._thumb_in.setStyleSheet(_thumb_style)
        self._thumb_in.setText("—")
        in_col.addWidget(lbl_in_title)
        in_col.addWidget(self._thumb_in)

        out_col = QVBoxLayout(); out_col.setSpacing(2); out_col.setAlignment(Qt.AlignCenter)
        lbl_out_title = QLabel("LAST FRAME (OUT)  ◀")
        lbl_out_title.setStyleSheet(_lbl_style)
        lbl_out_title.setAlignment(Qt.AlignCenter)
        self._thumb_out = QLabel()
        self._thumb_out.setFixedSize(142, 80)
        self._thumb_out.setAlignment(Qt.AlignCenter)
        self._thumb_out.setStyleSheet(_thumb_style)
        self._thumb_out.setText("—")
        out_col.addWidget(lbl_out_title)
        out_col.addWidget(self._thumb_out)

        tp_l.addLayout(in_col)
        tp_l.addLayout(out_col)
        tp_l.addStretch(1)

        lv.addWidget(self._trim_preview)
        lv.addStretch(1)
        lv.addSpacing(16)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #1a1a1a;")
        lv.addWidget(divider)
        lv.addSpacing(10)

        bottom_row = QHBoxLayout()
        self.btn_change = QPushButton("↩  Change Video")
        self.btn_change.setToolTip("Replace the current video with a different one.")
        self.btn_change.setStyleSheet(
            f"QPushButton {{ background: #1a2a3a; border: 1px solid {COLOR_ACCENT}; "
            f"color: {COLOR_ACCENT}; border-radius: 3px; padding: 6px 18px; "
            f"font-weight: bold; font-size: 11px; }} "
            f"QPushButton:hover {{ background: {COLOR_ACCENT}; color: white; }}"
        )
        # Reset Status: only meaningful after a run completes (✅/❌). Mirrors
        # the right-click "Reset Status" entry in the batch table so the user
        # can re-run a finished single-mode task without reloading the source.
        self.btn_reset_status = QPushButton("🔄  Reset Status")
        self.btn_reset_status.setToolTip("Reset this task back to pending so you can re-encode it.")
        self.btn_reset_status.setStyleSheet(
            f"background: #1a1a1a; border: 1px solid #333; color: {COLOR_WARNING}; "
            f"border-radius: 3px; padding: 5px 14px; font-weight: bold;"
        )
        self.btn_reset_status.hide()
        self.btn_open_out = QPushButton("📂  Open Output Folder")
        self.btn_open_out.setToolTip("Open the folder containing the rendered output file.")
        self.btn_open_out.setStyleSheet(
            f"background: {COLOR_SUCCESS}; color: white; border-radius: 3px; "
            f"padding: 5px 14px; font-weight: bold;"
        )
        self.btn_open_out.hide()
        # Search again: force a fresh iterative search that ignores the saved
        # (cached) iterations for this run, without touching "Keep iterations".
        # Useful when a result was reused from a previous run but the user wants
        # the engine to actually encode and search again.
        self.btn_reiterate = QPushButton("🔁  Search Again")
        self.btn_reiterate.setToolTip(
            "Run the size search again from scratch, ignoring results saved from "
            "previous runs (does not change the 'Keep iterations' setting)."
        )
        self.btn_reiterate.setStyleSheet(
            f"QPushButton {{ background: #2a2030; border: 1px solid {COLOR_ACCENT}; "
            f"color: {COLOR_ACCENT}; border-radius: 3px; padding: 5px 14px; "
            f"font-weight: bold; }} "
            f"QPushButton:hover {{ background: {COLOR_ACCENT}; color: white; }}"
        )
        self.btn_reiterate.hide()
        bottom_row.addWidget(self.btn_change)
        bottom_row.addStretch()
        bottom_row.addWidget(self.btn_reiterate)
        bottom_row.addWidget(self.btn_reset_status)
        bottom_row.addWidget(self.btn_open_out)
        lv.addLayout(bottom_row)
        self._stack.addWidget(self._w_loaded)

    # ── Public API ──────────────────────────────────────────────────

    def show_analyzing(self, filename=""):
        """Switch to loaded state with an ANALYZING indicator while
        ffmpeg probes the source in the background."""
        self._lbl_filename.setText(filename or "Analyzing...")
        self._lbl_meta.setText("")
        self._lbl_filesize.setText("")
        self._thumb.clear()
        self._thumb.setText("🎬")
        self._lbl_chip.setText("  ⏳  ANALYZING...  ")
        self._lbl_chip.setStyleSheet(
            f"background: {COLOR_WARNING}; color: #000; border-radius: 3px; "
            f"font-size: 10px; font-weight: bold; padding: 0 6px;"
        )
        self.btn_reiterate.hide()
        self.btn_open_out.hide()
        self.btn_reset_status.hide()
        self._stack.setCurrentIndex(1)

    def load_video(self, task):
        """Switch to loaded state showing thumbnail + video metadata."""
        self._lbl_filename.setText(task.filename)
        s = task.specs
        dur = s.get('duration', 0)
        m, sec = divmod(int(dur), 60)
        h_v, m = divmod(m, 60)
        dur_str = f"{h_v:02d}:{m:02d}:{sec:02d}" if h_v > 0 else f"{m:02d}:{sec:02d}"
        fps_lbl = s.get("fps_display") or format_fps_for_display(s.get("fps"))
        self._lbl_meta.setText(
            f"{s.get('w', '?')} × {s.get('h', '?')}  ·  {fps_lbl} fps  ·  {dur_str}"
        )
        try:
            mb = os.path.getsize(task.path) / 1024 / 1024
            self._lbl_filesize.setText(f"Source: {mb:.1f} MB")
        except:
            self._lbl_filesize.setText("")

        self._thumb.clear()
        self._thumb.setText("🎬")
        pix = self._extract_thumbnail(task.path, dur)
        if pix is not None:
            self._thumb.setPixmap(pix)
        self.clear_trim_previews()

        self._lbl_chip.setText("  READY  ")
        self._lbl_chip.setStyleSheet(
            f"background: {COLOR_ACCENT}; color: white; border-radius: 3px; "
            f"font-size: 10px; font-weight: bold; padding: 0 6px;"
        )
        self.btn_reiterate.hide()
        self.btn_open_out.hide()
        self.btn_reset_status.hide()
        self._stack.setCurrentIndex(1)

    def mark_done(self, is_iterative=True):
        """Show the DONE chip and the post-run buttons. Verbose winner / cache
        details are surfaced by the result dialog (MainWindow), not inline, so
        nothing lingers on the panel after the next run. ``is_iterative`` gates
        the "Search Again" button (only meaningful for the AUTO engine)."""
        self._lbl_chip.setText("  ✅  DONE  ")
        self._lbl_chip.setStyleSheet(
            f"background: {COLOR_SUCCESS}; color: white; border-radius: 3px; "
            f"font-size: 10px; font-weight: bold; padding: 0 6px;"
        )
        self.btn_open_out.show()
        self.btn_reset_status.show()
        self.btn_reiterate.setVisible(bool(is_iterative))

    def mark_failed(self):
        """Show a failure chip and the reset button so the user can retry."""
        self._lbl_chip.setText("  ❌  FAILED  ")
        self._lbl_chip.setStyleSheet(
            f"background: {COLOR_DANGER}; color: white; border-radius: 3px; "
            f"font-size: 10px; font-weight: bold; padding: 0 6px;"
        )
        self.btn_reiterate.hide()
        self.btn_open_out.hide()
        self.btn_reset_status.show()

    def set_output_plan(self, text):
        """Show or hide the output-plan summary below the source metadata."""
        if text:
            self._lbl_output_plan.setText(text)
            self._lbl_output_plan.setVisible(True)
        else:
            self._lbl_output_plan.setVisible(False)

    def mark_ready(self):
        """Restore the READY state (used by Reset Status)."""
        self._lbl_chip.setText("  READY  ")
        self._lbl_chip.setStyleSheet(
            f"background: {COLOR_ACCENT}; color: white; border-radius: 3px; "
            f"font-size: 10px; font-weight: bold; padding: 0 6px;"
        )
        self.btn_reiterate.hide()
        self.btn_open_out.hide()
        self.btn_reset_status.hide()

    def reset(self):
        """Return to empty drop state."""
        self._thumb.clear()
        self._thumb.setText("🎬")
        self.clear_trim_previews()
        self._stack.setCurrentIndex(0)

    def _extract_thumbnail(self, video_path, duration_sec):
        """Try cv2 first; fall back to ffmpeg to grab a representative frame.
        Returns a scaled QPixmap (213x120) or None on failure."""
        target_w, target_h = 213, 120

        if HAS_CV2:
            try:
                cap = cv2.VideoCapture(video_path)
                if cap.isOpened():
                    if duration_sec and duration_sec > 0:
                        cap.set(cv2.CAP_PROP_POS_MSEC, min(1000.0, duration_sec * 1000.0 * 0.1))
                    ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = frame_rgb.shape
                        qi = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
                        return QPixmap.fromImage(qi).scaled(
                            target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
            except Exception:
                pass

        try:
            tmp_png = os.path.join(tempfile.gettempdir(), f"_dz_thumb_{os.getpid()}.png")
            seek = "00:00:01"
            if duration_sec and duration_sec > 2:
                ts = max(0.5, min(duration_sec * 0.1, 5.0))
                seek = f"{ts:.2f}"
            cmd = [
                FFMPEG_PATH, "-y", "-ss", seek, "-i", video_path,
                "-vframes", "1", "-vf", f"scale={target_w}:-1",
                tmp_png,
            ]
            flags = 0x08000000 if os.name == 'nt' else 0
            proc = subprocess.run(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=flags, timeout=8,
            )
            if proc.returncode == 0 and os.path.exists(tmp_png):
                pix = QPixmap(tmp_png)
                try:
                    os.remove(tmp_png)
                except OSError:
                    pass
                if not pix.isNull():
                    return pix.scaled(
                        target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
        except Exception:
            pass
        return None

    # ── Trim frame previews ────────────────────────────────────────

    def update_trim_previews(self, video_path, in_sec, out_sec, duration_sec, fps=None):
        """Display the first/last frames of the trimmed region (async, PR1).
        Hides the strip when the trim covers the full clip.  When *fps* is
        given, frame-index seeking is used for pixel-exact accuracy."""
        no_trim = (in_sec <= 0.01 and (out_sec is None or out_sec >= duration_sec - 0.01))
        if no_trim:
            self._thumb_loader.cancel(self._thumb_in)
            self._thumb_loader.cancel(self._thumb_out)
            self._trim_preview.setVisible(False)
            return
        if out_sec is None:
            out_sec = duration_sec
        in_fi = source_frame_index_from_sec(in_sec, fps) if fps else 0
        out_excl_fi = source_frame_index_from_sec(out_sec, fps) if fps else 0
        last_fi = max(0, out_excl_fi - 1)
        self._trim_preview.setVisible(True)
        self._thumb_loader.request(self._thumb_in, video_path, fps, in_fi, 142, 80)
        self._thumb_loader.request(self._thumb_out, video_path, fps, last_fi, 142, 80)

    def clear_trim_previews(self):
        """Hide trim previews (e.g. when source changes or trim is reset)."""
        self._thumb_loader.cancel(self._thumb_in)
        self._thumb_loader.cancel(self._thumb_out)
        self._trim_preview.setVisible(False)
        self._thumb_in.clear(); self._thumb_in.setText("—")
        self._thumb_out.clear(); self._thumb_out.setText("—")

    # ── Drag & Drop ─────────────────────────────────────────────────

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            self._set_drag_active(True)
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self._set_drag_active(False)

    def dropEvent(self, e):
        self._set_drag_active(False)
        urls = [u.toLocalFile() for u in e.mimeData().urls()]
        if urls:
            self.file_dropped.emit(urls[0])

    def _set_drag_active(self, active):
        if active:
            self._w_empty.setStyleSheet(
                f"QFrame#dz_empty {{ background: #060f1a; border: 2px dashed {COLOR_ACCENT}; border-radius: 12px; }}"
            )
            self._lbl_drop_title.setText("Release to load video")
            self._lbl_drop_title.setStyleSheet(
                f"font-size: 20px; font-weight: bold; color: {COLOR_ACCENT}; border: none; background: transparent;"
            )
        else:
            self._w_empty.setStyleSheet(
                f"QFrame#dz_empty {{ background: {COLOR_BG}; border: 2px dashed #2d2d2d; border-radius: 12px; }}"
            )
            self._lbl_drop_title.setText("Drop your video here")
            self._lbl_drop_title.setStyleSheet(
                f"font-size: 20px; font-weight: bold; color: {COLOR_TEXT_BRIGHT}; border: none; background: transparent;"
            )


class TaskAnalyzerWorker(QThread):
    """Runs get_video_specs (ffmpeg probe + VFR detection) off the main
    thread so the UI stays responsive during import."""
    finished = Signal(object)   # emits the completed Task
    failed = Signal(str, str)   # (path, error_message)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self._path = path

    def run(self):
        try:
            task = Task.__new__(Task)
            task.path = self._path
            task.filename = os.path.basename(self._path)
            task.status = "⌛"
            task.output_path = None
            task.vals = {"target": 16.0, "format": "GIF", "mode": "ITERATIVE",
                         "low": 1.5, "up": 0.5, "fps": 15, "qual": 90,
                         "dim_mode": "Original", "dim_perc": 100,
                         "dim_w": 640, "dim_h": 360, "alpha": False,
                         "prio": "Balanced", "trim_start": "00:00:00",
                         "trim_end": "", "keep_iterations": True,
                         "name_settings": True}
            task.specs = get_video_specs(self._path)
            if task.specs.get("err"):
                self.failed.emit(self._path, "Could not analyze the dropped video file.")
            else:
                self.finished.emit(task)
        except Exception as exc:
            self.failed.emit(self._path, str(exc))


class Task:
    def __init__(self, path):
        self.path = path; self.filename = os.path.basename(path); self.status = "⌛"
        self.specs = get_video_specs(path)
        # Result of last successful render; kept SEPARATE from `path` so re-runs
        # (Reset Status, Apply settings to selection) still encode the original source.
        self.output_path = None
        # Default Params
        self.vals = {"target": 16.0, "format": "GIF", "mode": "ITERATIVE", "low": 1.5, "up": 0.5, "fps": 15, "qual": 90, "dim_mode": "Original", "dim_perc": 100, "dim_w": 640, "dim_h": 360, "alpha": False, "prio": "Balanced", "trim_start": "00:00:00", "trim_end": "", "keep_iterations": True, "name_settings": True}

class MiniMath(QHBoxLayout):
    def __init__(self, label, span, step=0.1):
        super().__init__(); self.setSpacing(2); lbl = QLabel(label); lbl.setStyleSheet("color: #aaa; font-size: 10px;")
        lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        lbl.setMinimumWidth(20)
        span.setButtonSymbols(span.ButtonSymbols.NoButtons)
        span.setFixedWidth(58)
        bm = QPushButton("−"); bp = QPushButton("+")
        for b in [bm, bp]: 
            b.setFixedSize(20, 20)
            b.setStyleSheet("background: #333; border: 1px solid #666; border-radius: 3px; color: white; font-weight: bold; font-size: 12px; padding: 0px;")
        self.addWidget(lbl, 1); self.addWidget(bm); self.addWidget(span); self.addWidget(bp)
        bm.clicked.connect(lambda: span.setValue(span.value() - step)); bp.clicked.connect(lambda: span.setValue(span.value() + step))

class LabeledSnapSlider(QSlider):
    """A QSlider with four behaviour upgrades on top of stock Qt:

    1. **Click-to-jump (precise).** Clicking anywhere on the track moves
       the handle to that exact position, instead of Qt's default
       page-step behaviour. Single clicks DO NOT snap — if the user
       clicked at 27 % they get 27 %, not a magnetic pull to 25.
    2. **Drag-snap (magnetic).** While dragging, the value is pulled to
       the nearest registered snap target if it falls within ±tolerance.
       Tolerance is expressed as a fraction of the bar width (default
       3.5 %) so the magnetic feel is uniform regardless of value range
       or whether bilinear mapping is active. Programmatic ``setValue()``
       calls (spinbox typing, wheel, set_dict) bypass snap entirely.
    3. **In-track decorations.** Custom-painted text labels under chosen
       positions ("25", "50", …) live ON the bar instead of as a separate
       chip strip. An optional "upscale zone" tints the portion of the
       track above a threshold value in red so the user sees at a glance
       that anything past that mark is a quality regression.
    4. **Bi-linear visual mapping.** When the value range is lopsided
       (e.g. 1-400 with most useful work happening in 1-100), setting a
       pivot tells the slider to give half the bar width to the
       [min..pivot] range and the other half to [pivot..max]. The handle
       still reports the underlying user value via ``.value()``; the trick
       is purely in the ``opt.sliderPosition`` we feed Qt's painter, so
       no other code in the app needs to learn about the mapping.
    """

    # Emitted when a snap activates (True) or releases (False). Parent
    # widgets can connect to this to flash a highlight, change a label, etc.
    snapped = Signal(bool)

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self._labeled_values = []
        self._snap_targets = []
        self._snap_tolerance_ratio = 0.035
        self._upscale_threshold = None
        self._upscale_color = QColor(255, 80, 80, 120)
        self._label_color = QColor("#999")
        self._label_color_warn = QColor("#ff6b6b")
        self._pivot_value = None
        self._pivot_visual_ratio = 0.5
        self._is_snapped = False
        # Reserve room below the groove for the custom-drawn labels.
        self.setMinimumHeight(36)
        self.setTickPosition(QSlider.NoTicks)

    # ---- Public configuration -------------------------------------------------

    def setLabeledValues(self, values):
        self._labeled_values = sorted(int(v) for v in values)
        self.update()

    def setSnapTargets(self, targets, tolerance=None):
        """Targets are user values; tolerance is a *ratio of bar width*
        (e.g. 0.04 == snap if the dragged value's visual position is
        within 4 % of the bar width of any target)."""
        self._snap_targets = sorted(int(t) for t in targets)
        if tolerance is not None:
            self._snap_tolerance_ratio = float(tolerance)

    def setUpscaleThreshold(self, value):
        """Pass an int to paint the track from `value`→max() in the warn
        colour. Pass None to clear the overlay."""
        self._upscale_threshold = value
        self.update()

    def setBilinearPivot(self, pivot_value, left_visual_ratio=0.5):
        """Activate bi-linear visual mapping where [min..pivot] occupies
        `left_visual_ratio` of the bar width (default 50 %) and
        [pivot..max] occupies the rest. Useful when one side of the
        range is much larger numerically than the other (e.g. a 1-400
        slider where the meaningful downscale region 1-100 would
        otherwise be crushed against the left edge). Pass None as
        pivot_value to revert to a plain linear scale."""
        self._pivot_value = pivot_value
        self._pivot_visual_ratio = max(0.05, min(0.95, left_visual_ratio))
        self.update()

    # ---- Value <-> visual ratio mapping --------------------------------------

    def _value_to_ratio(self, value):
        """Map a user value to a [0, 1] horizontal ratio across the groove."""
        vmin, vmax = self.minimum(), self.maximum()
        if vmax <= vmin:
            return 0.0
        pv = self._pivot_value
        if pv is None or pv <= vmin or pv >= vmax:
            return (value - vmin) / (vmax - vmin)
        r = self._pivot_visual_ratio
        if value <= pv:
            return ((value - vmin) / (pv - vmin)) * r
        return r + ((value - pv) / (vmax - pv)) * (1.0 - r)

    def _ratio_to_value(self, ratio):
        """Inverse of _value_to_ratio."""
        vmin, vmax = self.minimum(), self.maximum()
        ratio = max(0.0, min(1.0, ratio))
        pv = self._pivot_value
        if pv is None or pv <= vmin or pv >= vmax:
            return int(round(vmin + ratio * (vmax - vmin)))
        r = self._pivot_visual_ratio
        if ratio <= r:
            return int(round(vmin + (ratio / r) * (pv - vmin))) if r > 0 else int(pv)
        return int(round(pv + ((ratio - r) / (1.0 - r)) * (vmax - pv)))

    def _apply_snap(self, v):
        """Snap to the nearest target if its VISUAL distance (in
        bar-width fractions) is within the tolerance ratio. Doing snap
        in visual space — instead of value space — keeps the magnetic
        feel consistent across linear and bilinear modes.
        Also emits `snapped(True/False)` whenever the snapped state changes
        so the parent can show visual feedback (e.g. glow on the groove)."""
        v_ratio = self._value_to_ratio(v)
        best = None
        best_dist = self._snap_tolerance_ratio
        for t in self._snap_targets:
            d = abs(self._value_to_ratio(t) - v_ratio)
            if d <= best_dist:
                best_dist = d
                best = t
        did_snap = best is not None
        if did_snap != self._is_snapped:
            self._is_snapped = did_snap
            self.snapped.emit(did_snap)
        return best if best is not None else v

    def _value_from_position(self, pt):
        """Map a widget-local mouse point to a user value, using the
        actual groove geometry from the active QStyle (so this works
        identically on Fusion, Windows, macOS, etc.)."""
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self)
        handle = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self)
        if self.orientation() != Qt.Horizontal:
            return self.value()
        slider_min = groove.x()
        slider_max = groove.right() - handle.width() + 1
        slider_length = slider_max - slider_min
        if slider_length <= 0:
            return self.value()
        # Subtract half the handle width so clicking visually under the
        # cursor lines up with the handle's centre, not its left edge.
        x = pt.x() - handle.width() // 2
        ratio = max(0.0, min(1.0, (x - slider_min) / slider_length))
        return self._ratio_to_value(ratio)

    # ---- Mouse handling -------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Both click AND drag snap magnetically to the nearest labelled
            # preset. The spinbox remains snap-free for fine control.
            v = self._apply_snap(self._value_from_position(event.position().toPoint()))
            self.setValue(v)
            self.sliderMoved.emit(v)
            self.setSliderDown(True)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isSliderDown() and (event.buttons() & Qt.LeftButton):
            # Drag DOES snap — the magnetic feel is useful for quickly
            # landing on the labelled presets without aiming pixel-perfect.
            v = self._apply_snap(self._value_from_position(event.position().toPoint()))
            self.setValue(v)
            self.sliderMoved.emit(v)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.isSliderDown() and event.button() == Qt.LeftButton:
            self.setSliderDown(False)
            self.sliderReleased.emit()
            # Clear the snapped highlight once the user releases the handle.
            if self._is_snapped:
                self._is_snapped = False
                self.snapped.emit(False)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ---- Painting -------------------------------------------------------------

    def paintEvent(self, event):
        # Delegate the ENTIRE base rendering (groove, blue sub-page fill,
        # handle) to Qt via super().paintEvent(). This preserves the
        # Fusion style's filled-groove look that got lost when we were
        # manually calling drawComplexControl with our own QPainter.
        #
        # For the bi-linear case we temporarily shift `sliderPosition` to
        # the visual-mapped value (with signals blocked so nothing
        # propagates) — Qt sees the virtual position, paints the handle
        # and blue fill there, and we immediately restore the real value.
        if self._pivot_value is not None:
            ratio = self._value_to_ratio(self.value())
            vmin, vmax = self.minimum(), self.maximum()
            virtual_pos = int(round(vmin + ratio * (vmax - vmin)))
            real_pos = self.sliderPosition()
            self.blockSignals(True)
            self.setSliderPosition(virtual_pos)
            super().paintEvent(event)
            self.setSliderPosition(real_pos)
            self.blockSignals(False)
        else:
            super().paintEvent(event)
        if not self._labeled_values and self._upscale_threshold is None:
            return
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        groove = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self)
        handle = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self)
        # Helper: pixel x where the handle CENTRE parks for a given value.
        # We account for the handle's half-width offset on each end so
        # labels align with where the handle actually lands, not with
        # where the bare ratio would put a 0-width point.
        travel = max(1, groove.width() - handle.width())
        half_w = handle.width() // 2
        def x_for(v):
            return groove.x() + half_w + int(round(self._value_to_ratio(v) * travel))
        # ---- Upscale zone overlay (red tint over the >threshold portion)
        if self._upscale_threshold is not None and self.maximum() > self._upscale_threshold:
            t_x = x_for(self._upscale_threshold)
            zone = QRect(t_x, groove.y(), groove.right() - t_x + 1, groove.height())
            p.fillRect(zone, self._upscale_color)
        # ---- Tick marks + value labels under the groove.
        # Ticks always render (1-px lines, no overlap risk). Text labels
        # skip themselves if they would crowd the previous one — only
        # really matters as a safety net; the bilinear scale already
        # eliminates the crowding that was happening on the linear 1-400.
        if self._labeled_values:
            f = p.font()
            f.setPointSize(7)
            f.setBold(True)
            p.setFont(f)
            fm = p.fontMetrics()
            label_y = self.height() - 2  # baseline near the bottom edge
            tick_y_top = groove.bottom() + 2
            tick_y_bottom = tick_y_top + 3
            min_label_gap = 2
            last_label_right = -10000
            for v in self._labeled_values:
                if v < self.minimum() or v > self.maximum():
                    continue
                x = x_for(v)
                in_red_zone = (
                    self._upscale_threshold is not None
                    and v > self._upscale_threshold
                )
                color = self._label_color_warn if in_red_zone else self._label_color
                p.setPen(color)
                p.drawLine(x, tick_y_top, x, tick_y_bottom)
                text = f"{v}%"
                text_w = fm.horizontalAdvance(text)
                text_x = max(0, min(self.width() - text_w, x - text_w // 2))
                if text_x < last_label_right + min_label_gap:
                    continue
                p.drawText(text_x, label_y, text)
                last_label_right = text_x + text_w
        p.end()


class ResizeBox(QGroupBox):
    def __init__(self, title="📏 OUTPUT DIMENSIONS"):
        super().__init__(title)
        l = QVBoxLayout(self); l.setContentsMargins(10, 15, 10, 10); l.setSpacing(4)
        self.opt = QComboBox(); self.opt.addItems(["Original", "Percentage (%)", "Lock Width", "Lock Height", "Manual WxH"])
        self.opt.setToolTip("Choose how the output resolution is calculated.\nOriginal = same as source. Percentage = scale by %. Lock Width/Height = fix one dimension, auto-calculate the other.")
        l.addWidget(self.opt)
        
        # Percentage scaling — slider + spinbox + upscale opt-in, all stacked
        # inside p_ctr so the whole subsection hides/shows together when the
        # user switches dimension mode.
        # The slider itself is a LabeledSnapSlider, which paints "25/50/75/
        # 100" labels under tick marks ON the bar (no separate chip strip
        # needed) and snaps to those values during drag/click. The spinbox
        # bypasses snap so manual entry of off-grid values like 37 % stays
        # exact.
        self.p_ctr = QWidget()
        p_v = QVBoxLayout(self.p_ctr)
        p_v.setContentsMargins(0, 0, 0, 0)
        p_v.setSpacing(3)
        self.PERC_MAX_NORMAL = 100
        self.PERC_MAX_UPSCALE = 400
        # Snap/label targets per mode. In upscale we pair the extended set
        # with a bi-linear visual mapping (pivot at 100 %, 50/50 split) so
        # the downscale half (1-100) gets the left half of the bar and
        # the upscale half (100-400) gets the right half. With that
        # mapping, ALL these values land at evenly-spaced visual positions
        # — no more cramming the first four marks into the leftmost
        # quarter of a linear 1-400 bar. 150 is intentionally dropped:
        # under bilinear it would sit too close to 100 and 200 to be
        # readable, and 1.5× scaling is rarely a discrete preset target.
        self._snap_targets_normal = [25, 50, 75, 100]
        self._snap_targets_upscale = [25, 50, 75, 100, 200, 300, 400]
        # Row 1: slider + spinbox.
        row1 = QHBoxLayout(); row1.setContentsMargins(0, 0, 0, 0); row1.setSpacing(6)
        self.slider_perc = LabeledSnapSlider(Qt.Horizontal)
        self.slider_perc.setRange(1, self.PERC_MAX_NORMAL)
        self.slider_perc.setToolTip(
            "Scale the output resolution as a percentage of the original.\n"
            "• Click on the bar  → jump to that exact spot (no snap).\n"
            "• Drag the handle   → snaps magnetically to the marked presets within ±2 %.\n"
            "• Mouse wheel       → fine 1 % increments.\n"
            "• Spinbox on right  → exact off-grid values (e.g. 37 %)."
        )
        self.slider_perc.setLabeledValues(self._snap_targets_normal)
        # Snap tolerance is a fraction of bar width (3.5 % ≈ ~9 px on a
        # 250 px bar). Bumped from the original ±2 raw units so the magnet
        # feels stronger during drag, while clicks stay precise (no snap).
        self.slider_perc.setSnapTargets(self._snap_targets_normal, tolerance=0.035)
        self.s_perc = QSpinBox(); self.s_perc.setRange(1, self.PERC_MAX_NORMAL); self.s_perc.setSuffix("%"); self.s_perc.setFixedWidth(60)
        self.s_perc.setToolTip("Scale percentage. Manual entry bypasses snapping for fine control (e.g. 37%).")
        row1.addWidget(self.slider_perc); row1.addWidget(self.s_perc)
        p_v.addLayout(row1)
        self.s_perc.valueChanged.connect(self.slider_perc.setValue); self.slider_perc.valueChanged.connect(self.s_perc.setValue)
        self.s_perc.setValue(100)

        # Upscale override — off by default. UPSCALING blows up the source
        # pixels (no new information added) so it's a quality regression
        # that the user has to opt into explicitly. When enabled, the
        # slider extends to 400 %, the >100 % portion is tinted red on the
        # track itself, and 150/200 % labels appear in red. Auto-enabled
        # by set_dict() if a preset arrives carrying dim_perc > 100
        # (otherwise the value would be silently clamped).
        upscale_row = QHBoxLayout(); upscale_row.setContentsMargins(0, 2, 0, 0); upscale_row.setSpacing(6)
        self.chk_upscale = QCheckBox("Allow upscaling (>100%)")
        self.chk_upscale.setToolTip(
            "Off by default. When enabled, the slider extends up to 400% so you can\n"
            "scale the output ABOVE the source resolution. The >100% portion of the\n"
            "bar turns red as a reminder: no new pixel information is added — the\n"
            "encoder just stretches what's there. Useful for matching a target\n"
            "canvas size, not for improving fidelity."
        )
        self.chk_upscale.setStyleSheet(
            "QCheckBox { color: #ffab00; font-weight: bold; spacing: 6px; font-size: 10px; padding: 2px 0; }"
            "QCheckBox::indicator { width: 14px; height: 14px; border-radius: 2px; }"
            "QCheckBox::indicator:unchecked { background-color: #2a2a2a; border: 1px solid #555; }"
            "QCheckBox::indicator:checked { background-color: #ffab00; border: 1px solid #fff; }"
        )
        self.chk_upscale.toggled.connect(self._toggle_upscale)
        upscale_row.addWidget(self.chk_upscale)
        upscale_row.addStretch()
        p_v.addLayout(upscale_row)

        # Warning label — visible only when upscale is enabled.
        self.lbl_upscale_warn = QLabel("⚠ Upscaling will stretch pixels — output quality may be degraded.")
        self.lbl_upscale_warn.setStyleSheet(
            f"color: {COLOR_DANGER}; font-size: 9px; font-weight: bold; padding: 1px 0;"
        )
        self.lbl_upscale_warn.setWordWrap(True)
        self.lbl_upscale_warn.setVisible(False)
        p_v.addWidget(self.lbl_upscale_warn)

        # Snap feedback: when the slider snaps to a preset, the groove
        # brightens to a lighter accent colour so the user sees "I locked
        # onto a detent". On release it returns to normal.
        self._slider_base_style = (
            f"QSlider::groove:horizontal {{ background: #2a2a2a; height: 6px; border-radius: 3px; }}"
            f"QSlider::handle:horizontal {{ background: {COLOR_ACCENT}; width: 14px; margin: -4px 0; border-radius: 7px; }}"
            f"QSlider::sub-page:horizontal {{ background: {COLOR_ACCENT}; border-radius: 3px; }}"
        )
        self._slider_snap_style = (
            f"QSlider::groove:horizontal {{ background: #2a2a2a; height: 6px; border-radius: 3px; }}"
            f"QSlider::handle:horizontal {{ background: #66ccff; width: 14px; margin: -4px 0; border-radius: 7px; border: 2px solid white; }}"
            f"QSlider::sub-page:horizontal {{ background: #66ccff; border-radius: 3px; }}"
        )
        self.slider_perc.setStyleSheet(self._slider_base_style)
        self.slider_perc.snapped.connect(self._on_snap_feedback)
        
        self.s_w = QSpinBox(); self.s_w.setRange(1, 7680)
        self.s_w.setToolTip("Output width in pixels.")
        self.s_h = QSpinBox(); self.s_h.setRange(1, 4320)
        self.s_h.setToolTip("Output height in pixels.")
        
        for w in [self.p_ctr, self.s_w, self.s_h]: l.addWidget(w)

        # Spring between the mode-specific widgets above and the
        # always-visible target readout below. When we hide widgets in
        # ``refresh()``, this stretch absorbs the freed vertical space
        # so the groupbox's TOTAL height stays constant — and so does
        # the position of every section beneath it (TRIM, MAKE IT,
        # FRAME CACHE, etc). Without this, switching mode reflows the
        # entire right column.
        l.addStretch(1)

        self.lbl_live = QLabel("-- x --"); self.lbl_live.setAlignment(Qt.AlignCenter)
        self.lbl_live.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 11px; font-weight: bold; padding: 4px; background: #0a1014; border-radius: 3px;")
        l.addWidget(self.lbl_live)
        
        self.opt.currentIndexChanged.connect(self.refresh)

        # Lock the box to its tallest natural layout (every widget
        # visible at once = "Manual WxH" mode + slider row + upscale
        # warning). Temporarily show the warning label so it factors
        # into the size calculation, then hide it again.
        self.lbl_upscale_warn.setVisible(True)
        l.activate()
        max_h = self.sizeHint().height()
        self.setFixedHeight(max_h + 6)
        self.lbl_upscale_warn.setVisible(False)

        self.refresh()
        
    def refresh(self):
        m = self.opt.currentIndex()
        self.p_ctr.setVisible(m == 1); self.s_w.setVisible(m in [2, 4]); self.s_h.setVisible(m in [3, 4])

    def _toggle_upscale(self, on):
        """Extend or restrict the percentage range. When enabled, the slider
        and spinbox accept up to PERC_MAX_UPSCALE (400 %), the bar switches
        to a bi-linear visual scale (pivot at 100 % so downscale and
        upscale each get half the bar), the >100 % portion of the track
        is tinted red, and the upscale-side labels render in red too.
        When disabled, the slider reverts to a plain linear 1-100 scale
        and any value > 100 is clamped back so the next encode doesn't
        accidentally upscale."""
        new_max = self.PERC_MAX_UPSCALE if on else self.PERC_MAX_NORMAL
        targets = self._snap_targets_upscale if on else self._snap_targets_normal
        # Spinbox range FIRST so the chained valueChanged → slider.setValue
        # doesn't get clamped on the round-trip when we restore the value.
        self.s_perc.setMaximum(new_max)
        self.slider_perc.setMaximum(new_max)
        self.slider_perc.setLabeledValues(targets)
        self.slider_perc.setSnapTargets(targets, tolerance=0.035)
        self.slider_perc.setUpscaleThreshold(100 if on else None)
        # Bi-linear ON in upscale mode so the 1-100 region keeps half the
        # bar (otherwise it'd shrink to ~25 % of width and the marks would
        # overlap). OFF in normal mode so the simple 1-100 scale is plain
        # linear like before.
        self.slider_perc.setBilinearPivot(100 if on else None, left_visual_ratio=0.5)
        self.lbl_upscale_warn.setVisible(on)
        if not on and self.s_perc.value() > 100:
            self.s_perc.setValue(100)

    def _on_snap_feedback(self, is_snapped):
        """Toggle the slider's groove/handle style between the normal accent
        colour and a brighter 'locked onto preset' variant so the user gets
        immediate visual confirmation that they landed on a detent."""
        self.slider_perc.setStyleSheet(
            self._slider_snap_style if is_snapped else self._slider_base_style
        )

    def get_dict(self):
        return {"dim_mode": self.opt.currentText(), "dim_perc": self.s_perc.value(), "dim_w": self.s_w.value(), "dim_h": self.s_h.value()}

    def set_dict(self, d):
        idx = self.opt.findText(d.get("dim_mode", "Original")); self.opt.setCurrentIndex(idx if idx>=0 else 0)
        # Auto-enable upscale BEFORE setting the value so a preset carrying
        # dim_perc > 100 doesn't get silently clamped to 100 by the still-
        # narrow spinbox range. Toggling chk_upscale runs _toggle_upscale,
        # which widens both the spinbox and slider maximums.
        perc = int(d.get("dim_perc", 100))
        if perc > 100 and not self.chk_upscale.isChecked():
            self.chk_upscale.setChecked(True)
        elif perc <= 100 and self.chk_upscale.isChecked():
            self.chk_upscale.setChecked(False)
        self.s_perc.setValue(perc); self.s_w.setValue(d.get("dim_w", 640)); self.s_h.setValue(d.get("dim_h", 360))

class SettingsPanel(QFrame):
    def __init__(self):
        super().__init__()
        # Wider than v3.0: the settings groups now sit in a 2-column grid
        # so the panel needs roughly twice the horizontal real estate. The
        # tradeoff is a much shorter overall height (we save ~270 px on
        # 1080-class screens) and the right column no longer requires a
        # scrollbar at launch on any reasonable display.
        # The min reserves enough room for the ENCODING MODE column to fit
        # the "Balanced / FPS / Quality" radio row + spinbox controls
        # without clipping; max caps the panel so it doesn't eat the whole
        # window when the user has stretched it past 2K.
        # Min lowered after FRAME CACHE was reflowed onto two rows
        # (PURGE moved to its own right-aligned line) — the navigation
        # row (Path + SET/OPEN/RESET) now needs ~480 px instead of the
        # ~720 the 4-button cluster wanted. 760 leaves enough headroom
        # for ENCODING MODE's "Balanced / FPS / Quality" radios on the
        # right column at the smallest supported window width (1280
        # logical, e.g. 1080p @ 150 % DPI). Max is 940 so the panel
        # doesn't eat the whole window on 2K+ displays.
        self.setFixedWidth(540)
        self.setObjectName("settings_panel")
        self.setStyleSheet(f"#settings_panel {{ background: {COLOR_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; }}")
        # Load persisted app-level prefs FIRST so any widget created below
        # can read its initial state from disk (chart visibility, cache
        # dir, etc.) without hitting an AttributeError.
        self._app_settings = load_app_settings() or {}
        # Root layout for Panel
        root_l = QVBoxLayout(self)
        root_l.setContentsMargins(0,0,0,0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; } QScrollBar:vertical { width: 8px; } QScrollBar:horizontal { height: 0px; }")
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        l = QVBoxLayout(self.content_widget)
        l.setContentsMargins(4, 8, 2, 8)
        l.setSpacing(8)
        
        self.scroll.setWidget(self.content_widget)
        root_l.addWidget(self.scroll)
        
        # --- 0. PRESETS ---
        gb_pre = QFrame(); gb_pre.setStyleSheet(f"background: #1a1a1a; border-radius: 4px; border: 1px solid #333;"); l_pre = QHBoxLayout(gb_pre); l_pre.setContentsMargins(4, 4, 4, 4); l_pre.setSpacing(4)
        l_pre.addWidget(QLabel("📂 PRESET:"))
        self.preset = QComboBox(); self.preset.setStyleSheet("font-weight: bold; font-size: 11px; padding: 4px;")
        self.preset.setToolTip("Select a saved preset to load its format, encoding, and dimension settings.")
        l_pre.addWidget(self.preset, 1)
        
        self.btn_save_pre = QPushButton("➕"); self.btn_save_pre.setToolTip("Save as NEW Preset")
        self.btn_upd_pre = QPushButton("💾"); self.btn_upd_pre.setToolTip("Update CURRENT Preset (Overwrite)")
        self.btn_del_pre = QPushButton("🗑️"); self.btn_del_pre.setToolTip("Delete Selected Preset")
        self.btn_open_pre = QPushButton("📂"); self.btn_open_pre.setToolTip("Open Presets Folder")
        for b in [self.btn_save_pre, self.btn_upd_pre, self.btn_del_pre, self.btn_open_pre]:
            b.setFixedSize(26, 26); b.setStyleSheet("border: none; background: #333; border-radius: 3px; padding: 2px;"); l_pre.addWidget(b)
            
        l.addWidget(gb_pre)

        # Below PRESETS we lay out the configurable groups in 2 vertical
        # COLUMNS (not rows): left column flows FORMAT → DIMENSIONS, right
        # column hosts the much taller ENCODING MODE. This avoids the
        # awkward "DIMENSIONS floats far below FORMAT" gap that the row-
        # based grid produced (FORMAT was ~150 px while ENCODING was
        # ~270 px, leaving DIMENSIONS levitating ~120 px below FORMAT).
        # TRIM is hoisted out into its own centered row at the very
        # bottom of the panel so its optional-step nature reads clearly.
        cols_row = QHBoxLayout(); cols_row.setSpacing(6); cols_row.setContentsMargins(0, 0, 0, 0)
        col_l = QVBoxLayout(); col_l.setSpacing(8); col_l.setContentsMargins(0, 0, 0, 0)
        col_r = QVBoxLayout(); col_r.setSpacing(8); col_r.setContentsMargins(0, 0, 0, 0)
        cols_row.addLayout(col_l, 2)
        cols_row.addLayout(col_r, 3)
        l.addLayout(cols_row)

        self.btn_del_pre.clicked.connect(self.delete_preset)
        self.btn_upd_pre.clicked.connect(self.update_preset)
        
        # --- 1. FORMAT & SETTINGS ---
        self.gb_fmt = QGroupBox("1. FORMAT SETTINGS (WebP)")
        gb_style = f"""
            QGroupBox {{ color: {COLOR_TEXT_BRIGHT}; border: 1px solid #2d4050; background: #0e161b; font-size: 11px; font-weight: bold; margin-top: 15px; border-radius: 4px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; color: {COLOR_ACCENT}; }}
            QComboBox, QSpinBox, QDoubleSpinBox {{ background: #1a2630; border: 1px solid #2d4050; color: white; }}
        """
        self.gb_fmt.setStyleSheet(gb_style)
        v_fmt = QVBoxLayout(self.gb_fmt); v_fmt.setSpacing(6)
        
        # Format Buttons
        r_fmt = QHBoxLayout(); self.fmt_g = QButtonGroup(self); self.b_gif = QPushButton("GIF"); self.b_webp = QPushButton("WebP")
        self.b_gif.setToolTip("Export as animated GIF"); self.b_webp.setToolTip("Export as animated WebP")
        for b in [self.b_gif, self.b_webp]: 
            b.setCheckable(True); self.fmt_g.addButton(b); b.setObjectName("fmt_btn"); b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            r_fmt.addWidget(b)
        self.b_gif.setChecked(True)
        v_fmt.addLayout(r_fmt)
        
        # Toggles Row 1: Loop & Transparency
        r_t1 = QHBoxLayout()
        self.chk_loop = QCheckBox("Loop Forever"); self.chk_loop.setToolTip("Make the GIF loop infinitely.")
        self.chk_alpha = QCheckBox("Transparency"); self.chk_alpha.setToolTip("Try to preserve alpha/transparency from the source video.")
        r_t1.addWidget(self.chk_loop); r_t1.addWidget(self.chk_alpha)
        v_fmt.addLayout(r_t1)
        
        # Toggles Row 2: Optimization
        r_t2 = QHBoxLayout()
        self.chk_fast = QCheckBox("Fast Mode"); self.chk_fast.setToolTip("Prioritize encoding speed over file size compression.")
        self.chk_loss = QCheckBox("Lossless (WebP)"); self.chk_loss.setToolTip("Enable true lossless encoding (larger files but 100% quality).")
        r_t2.addWidget(self.chk_fast); r_t2.addWidget(self.chk_loss)
        v_fmt.addLayout(r_t2)
        
        # Explicit hardcore styles for checkboxes to bypass cascading bugs
        chk_style = """
            QCheckBox { color: white; font-weight: bold; spacing: 8px; font-size: 12px; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 3px; }
            QCheckBox::indicator:unchecked { background-color: #333; border: 2px solid #ddd; }
            QCheckBox::indicator:checked { background-color: #25a0ff; border: 2px solid #fff; }
        """
        for cb in [self.chk_loop, self.chk_alpha, self.chk_fast, self.chk_loss]:
            cb.setStyleSheet(chk_style)
        
        # Alpha Tester Button (Conditional)
        self.b_at = QPushButton("🔍 OPEN ALPHA TESTER"); self.b_at.setFixedHeight(24)
        self.b_at.setToolTip("Open the transparency inspector to preview alpha channel rendering.")
        self.b_at.setStyleSheet(f"background: #1a1a1a; color: {COLOR_ACCENT}; border: 1px solid {COLOR_ACCENT}; font-size: 10px; font-weight: bold;")
        v_fmt.addWidget(self.b_at)
        
        # FORMAT and DIMENSIONS share the LEFT column, stacked top-to-bottom.
        # Both groupboxes now sit at fixed natural heights — DIMS in
        # particular has its own setFixedHeight() locked to its tallest
        # variant, so swapping between Original / Percentage / Manual
        # WxH no longer changes the column height. A trailing stretch
        # absorbs whatever slack remains so the column borders still
        # reach down toward the right column's bottom without the box
        # itself resizing.
        col_l.addWidget(self.gb_fmt)

        # --- 2. DIMENSIONS & TRIM ---
        self.res_box = ResizeBox("2. OUTPUT DIMENSIONS 📏")
        self.res_box.setStyleSheet(gb_style)
        col_l.addWidget(self.res_box, 0)
        col_l.addStretch(1)
        
        # Trim Box — sits centered below FORMAT/DIMS/ENCODING because it
        # is a strictly optional step (you can MAKE without trimming). The
        # centered, narrower placement is what signals "optional" — no
        # text suffix needed.
        self.gb_trim = QGroupBox("✂️ TRIM VIDEO")
        self.gb_trim.setStyleSheet(gb_style)
        v_trim = QVBoxLayout(self.gb_trim)
        
        self.btn_open_trimmer = QPushButton("✂️ OPEN TRIMMER")
        self.btn_open_trimmer.setEnabled(False)
        self.btn_open_trimmer.setStyleSheet(f"""
            QPushButton {{ background-color: {COLOR_STATE_INFO}; color: white; font-weight: bold; padding: 6px; border-radius: 3px; }}
            QPushButton:disabled {{ background-color: {COLOR_BG}; color: #555; border: 1px solid #333; }}
        """)
        self.btn_open_trimmer.setToolTip("Open video to precisely set In and Out points")
        
        h_trim_vals = QHBoxLayout()
        # Frame-aware tracking of the active task's fps and duration. Used to
        # render trim values in NLE timecode (HH:MM:SS:FF) for the In/Out
        # fields, AND to compute the live "Length" readout between them.
        # Defaults to 25 fps / 0 sec until a task is loaded;
        # `set_current_fps()` updates both.
        self._current_fps = 25.0
        self._current_duration_sec = 0.0
        # Start fields EMPTY at boot — populated only once a video is
        # loaded. Showing "00:00:00:00" with no source attached looks
        # confusing (it suggests a trim is in effect when nothing is).
        self.t_start = QLineEdit(""); self.t_start.setPlaceholderText("Start")
        self.t_start.setToolTip("HH:MM:SS:FF, HH:MM:SS, or seconds (e.g. 5.234). Auto-formats to frames on blur.")
        self.t_start.setMaximumWidth(95)
        self.t_start.setEnabled(False)
        # OUT placeholder reads "End" when no source is loaded; once a
        # task is active set_current_fps swaps it for the source's actual
        # end TC (so the user sees the real clamp value, not "End").
        self.t_end = QLineEdit(); self.t_end.setPlaceholderText("End")
        self.t_end.setEnabled(False)
        self.t_end.setToolTip(
            "Last frame INCLUDED in the export (HH:MM:SS:FF, HH:MM:SS, or seconds).\n"
            "Empty = end of clip. Internally stored as exclusive OUT for ffmpeg."
        )
        self.t_end.setMaximumWidth(95)
        # Auto-normalize manual input to HH:MM:SS.ms when the user leaves the field;
        # this keeps storage consistent regardless of how the user typed it.
        self.t_start.editingFinished.connect(lambda: self._normalize_trim_field(self.t_start, "00:00:00"))
        self.t_end.editingFinished.connect(lambda: self._normalize_trim_field(self.t_end, ""))
        # Live "Length" readout — recomputes whenever either side changes.
        # textChanged fires on every keystroke so the value tracks typing,
        # not just on blur (matches the trim dialog's IN/OUT/Length feel).
        self.t_start.textChanged.connect(self._refresh_trim_length)
        self.t_end.textChanged.connect(self._refresh_trim_length)

        # Length readout, mirroring the trim dialog's HH:MM:SS:FF format.
        # Sits BETWEEN In/Out so it reads as "In ─ Length ─ Out" — same
        # visual cadence as a typical NLE trim panel. Hidden until a real
        # trim exists (IN > 0 or OUT < end of clip); when the range covers
        # the entire clip it just duplicates the source duration, which
        # is noise.
        self.lbl_trim_length = QLabel("Length: 00:00:00:00")
        self.lbl_trim_length.setStyleSheet(
            f"color: {COLOR_ACCENT}; font-weight: bold; font-size: 11px; "
            "padding: 2px 4px;"
        )
        self.lbl_trim_length.setToolTip("Effective trim duration (Out − In) in HH:MM:SS:FF.")
        self.lbl_trim_length.setVisible(False)

        h_trim_vals.addWidget(QLabel("In:")); h_trim_vals.addWidget(self.t_start)
        h_trim_vals.addStretch()
        h_trim_vals.addWidget(self.lbl_trim_length)
        h_trim_vals.addStretch()
        h_trim_vals.addWidget(QLabel("Out:")); h_trim_vals.addWidget(self.t_end)
        
        v_trim.addWidget(self.btn_open_trimmer)
        v_trim.addLayout(h_trim_vals)
        
        # --- 3. ENCODING MODE ---
        self.gb_mode = QGroupBox("3. ENCODING")
        self.gb_mode.setStyleSheet(gb_style)
        v_mode = QVBoxLayout(self.gb_mode); v_mode.setContentsMargins(4, 10, 2, 5)
        self.tabs = QTabWidget(); self.tabs.setObjectName("mode_tabs")
        self.tabs.setToolTip("AUTO OPTIMIZE: iteratively adjusts quality to hit a target file size.\nMANUAL: encode with fixed FPS and quality values.")
        # Tab styling matched to the GIF/WebP toggle pair in FORMAT (see
        # `QPushButton#fmt_btn` in the global QSS): same 30 px height, same
        # 12 px bold font, same accent fill + white border on selection.
        # `setExpanding(True)` makes the two tabs share the full width like
        # the FORMAT button row, instead of left-clumping at native size.
        # Tabs are FULLY rounded (border-radius on all 4 corners) to read as
        # standalone buttons rather than the legacy "tab merging into pane"
        # convention — matches the pill-button feel of GIF/WebP. The pane
        # below them keeps a small `margin-top` so the rounded bottoms
        # have breathing room and aren't visually clipped by the pane border.
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLOR_BORDER}; background: transparent; margin-top: 4px; }}
            QTabBar {{ qproperty-drawBase: 0; }}
            QTabBar::tab {{
                background: #1a1a1a; color: #888;
                padding: 0px 16px; min-height: 30px;
                border: 1px solid #444; margin-right: 4px;
                border-radius: 4px;
                font-weight: bold; font-size: 12px;
            }}
            QTabBar::tab:selected {{
                background: {COLOR_ACCENT}; color: white;
                border: 2px solid white;
                font-weight: 900;
            }}
            QTabBar::tab:!selected:hover {{ background: #2a2a2a; color: white; }}
        """)
        self.tabs.tabBar().setExpanding(True)
        self.tabs.tabBar().setDocumentMode(True)
        
        # ITERATIVE TAB
        it = QWidget(); iv = QVBoxLayout(it); iv.setContentsMargins(4, 5, 2, 5)
        self.mb_sp = QDoubleSpinBox(); self.mb_sp.setRange(0.01, 2000.0); self.mb_sp.setDecimals(2); self.mb_sp.setValue(16.0); self.mb_sp.setToolTip("Target file size to maintain across the batch (in Megabytes).")
        self.low_sp = QDoubleSpinBox(); self.up_sp = QDoubleSpinBox(); [s.setRange(0.0, 1000.0) for s in [self.low_sp, self.up_sp]]; [s.setDecimals(2) for s in [self.low_sp, self.up_sp]]
        self.low_sp.setToolTip("Minimum buffer size (lower values give tighter size control but worse quality fluctuations).")
        self.up_sp.setToolTip("Maximum buffer size (higher values give more quality leeway).")
        
        iv.addLayout(MiniMath("TARGET SIZE (MB):", self.mb_sp, 0.5))
        
        # Optimize Priority — checkable QPushButtons styled like the GIF/WebP
        # toggles in the FORMAT panel above. Same "pick 1 of N" semantics as
        # the old radio row (QButtonGroup gives us the exclusivity for free,
        # and .checkedId() / .isChecked() / .setChecked() match the old API
        # so every read site downstream keeps working unchanged), but the
        # visual language is now consistent across the two panels.
        pb = QFrame(); pl = QVBoxLayout(pb); pl.setContentsMargins(0, 4, 0, 0); pl.setSpacing(4)
        lbl_opt = QLabel("OPTIMIZE FOR")
        lbl_opt.setStyleSheet("font-size: 9px; color: #888; font-weight: bold; letter-spacing: 0.5px;")
        pl.addWidget(lbl_opt)
        prio_row = QHBoxLayout(); prio_row.setSpacing(4)
        self.bg_prio = QButtonGroup(self)
        self.p_bal = QPushButton("Balanced"); self.p_bal.setToolTip("Balance both visual quality and smooth framerate.")
        self.p_fps = QPushButton("FPS"); self.p_fps.setToolTip("Prioritize maintaining a high framerate during heavy compression.")
        self.p_ql = QPushButton("Quality"); self.p_ql.setToolTip("Prioritize visual fidelity, sacrificing frame rate if needed.")
        # IDs MUST stay 0/1/2 — `prio_map = {0:"Balanced", 1:"FPS", 2:"Quality"}`
        # in get_dict_for_prio() reads bg_prio.checkedId() against that mapping.
        for i, b in enumerate([self.p_bal, self.p_fps, self.p_ql]):
            b.setCheckable(True)
            b.setObjectName("fmt_btn")  # picks up the global GIF/WebP toggle QSS
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.bg_prio.addButton(b, i)
            prio_row.addWidget(b)
        self.p_bal.setChecked(True)
        pl.addLayout(prio_row)
        iv.addWidget(pb)
        
        # Advanced buffers (collapsible-ish via layout)
        adv_f = QFrame(); adv_l = QVBoxLayout(adv_f); adv_l.setContentsMargins(0, 0, 0, 0)
        adv_l.addLayout(MiniMath("LOWER BUFFER (MB):", self.low_sp, 0.1))
        adv_l.addLayout(MiniMath("UPPER BUFFER (MB):", self.up_sp, 0.1))
        iv.addWidget(adv_f)

        # Knowledge cache toggle: when on, the search engine keeps every iteration
        # on disk inside <source>_ITERATIONS/ and uses them on subsequent runs to
        # warm-start the binary search (or skip it entirely on Tier-1 matches).
        self.chk_keep_iter = QCheckBox("Keep iterations (warm-start hint)")
        # Default ON so the iterative engine has a populated knowledge
        # cache from the very first encode — Tier-1 hits, secant seeds,
        # and `_seed_q_from_cache` interpolation only matter when the
        # ``_ITERATIONS`` folder next to the source is allowed to grow.
        # Filenames now carry an attempt signature (sigXXXXXXXX) so
        # samples from different trims / alpha / lossless configs stay
        # cleanly separated; turning this on by default is safe.
        self.chk_keep_iter.setChecked(True)
        self.chk_keep_iter.setToolTip(
            "Save every attempted iteration in <source>_ITERATIONS/ and use them as\n"
            "a starting hint on the NEXT run for the same source. If a previous file\n"
            "already matches the requested size and FPS, the search is skipped."
        )
        # Mirror the FORMAT panel's checkbox style (chk_style, ~L5256) so the
        # two panels share visual weight: same 18×18 indicator, same blue
        # fill on check, same bold 12 px label.
        adv_chk_style = """
            QCheckBox { color: white; font-weight: bold; spacing: 8px; font-size: 12px; padding: 2px 0; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 3px; }
            QCheckBox::indicator:unchecked { background-color: #333; border: 2px solid #ddd; }
            QCheckBox::indicator:checked { background-color: #25a0ff; border: 2px solid #fff; }
        """
        self.chk_keep_iter.setStyleSheet(adv_chk_style)
        iv.addWidget(self.chk_keep_iter)

        # v2.7 parity: tag the output filename with the actual settings used
        # to produce it (Q, FPS, dimensions). Easier to organize batches when
        # you can read the params straight off the file. Default ON.
        self.chk_name_settings = QCheckBox("Tag filename with settings (Q/FPS/size)")
        self.chk_name_settings.setChecked(True)
        self.chk_name_settings.setToolTip(
            "When ON, the output filename gets a suffix encoding the actual\n"
            "encoded params, e.g.  myclip_Q72_F18_640x360.webp\n"
            "For the iterative engine the suffix uses the WINNER's settings,\n"
            "so it accurately reflects what's inside the file. Useful for\n"
            "comparing batches of different runs at a glance."
        )
        self.chk_name_settings.setStyleSheet(adv_chk_style)
        iv.addWidget(self.chk_name_settings)

        self.tabs.addTab(it, "AUTO OPTIMIZE")
        
        # MANUAL TAB
        mt = QWidget(); mv = QVBoxLayout(mt); mv.setContentsMargins(5, 5, 5, 5)
        self.fps_sp = QSpinBox(); self.qual_sp = QSpinBox(); self.fps_sp.setRange(1, 60); self.qual_sp.setRange(1, 100); self.fps_sp.setValue(15); self.qual_sp.setValue(90)
        self.fps_sp.setToolTip("Force a specific frames per second regardless of file size.")
        self.qual_sp.setToolTip("Force a static quality parameter (1 is worst, 100 is lossless).")
        mv.addLayout(MiniMath("TARGET FPS:", self.fps_sp, 1)); mv.addLayout(MiniMath("QUALITY (1-100):", self.qual_sp, 5)); mv.addStretch()
        self.tabs.addTab(mt, "MANUAL (Fixed)")
        
        v_mode.addWidget(self.tabs)
        # ENCODING MODE owns the entire right column. It's the tallest of
        # the four groups so giving it its own column lets FORMAT and DIMS
        # stay naturally close in the left column. ENCODING also gets a
        # vertical stretch so if the user's setup happens to make it the
        # SHORTER column (e.g. some font/DPI combo), it'll grow to match
        # DIMS's bottom — keeping the two columns' baselines aligned in
        # both directions.
        col_r.addWidget(self.gb_mode, 1)

        # TRIM as an optional, centered "step" below the two columns.
        # Capped at ~70% of panel width and bracketed by stretches so it
        # reads as a tertiary action — not a peer of FORMAT/DIMS/ENCODING.
        trim_row = QHBoxLayout(); trim_row.setContentsMargins(0, 0, 0, 0)
        trim_row.addStretch(1)
        self.gb_trim.setMaximumWidth(530)
        self.gb_trim.setMinimumWidth(380)
        trim_row.addWidget(self.gb_trim, 0, Qt.AlignHCenter)
        trim_row.addStretch(1)
        l.addLayout(trim_row)
        
        # --- SYSTEM TAB (Hidden in tabs normally, moved to bottom tools) ---
        # (Simplified system tools into a popup or bottom link if needed, but for now kept minimal)
        
        l.addStretch()
        
        # --- ACTIONS ---
        # Batch Mode Toggle
        self.batch_en = QCheckBox("  BATCH QUEUE MODE"); self.batch_en.setToolTip("Apply the selected format and encoding profile above to ALL videos checked in the queue.")
        self.batch_en.setStyleSheet(f"""
            QCheckBox {{ color: {COLOR_WARNING}; font-weight: bold; font-size: 12px; padding: 6px; background: #1a1a00; border: 1px solid #333; border-radius: 4px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 3px; }}
            QCheckBox::indicator:unchecked {{ background-color: #333; border: 2px solid #ddd; }}
            QCheckBox::indicator:checked {{ background-color: {COLOR_SUCCESS}; border: 2px solid #fff; }}
        """)
        root_l.addWidget(self.batch_en)
        
        # MAIN STATUS & PROGRESS BAR
        status_l = QVBoxLayout()
        self.lbl_status = QLabel("READY"); self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet(f"color: {COLOR_ACCENT}; font-weight: bold; font-size: 11px;")
        self.pbar = QProgressBar(); self.pbar.setFixedHeight(6); self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet(f"QProgressBar {{ background-color: #2a2a2a; border-radius: 3px; }} QProgressBar::chunk {{ background-color: {COLOR_ACCENT}; border-radius: 3px; }}")
        status_l.addWidget(self.pbar)
        status_l.addWidget(self.lbl_status)
        root_l.addLayout(status_l)

        # NOTE: the iterative search chart used to live here, in the right
        # column. It moved to a full-width drawer at the bottom of the main
        # window so (a) the right column stays compact enough to fit a
        # 1920x1080 screen with no resize, and (b) the chart gets the full
        # window width when expanded. Wiring lives in MainWindow now.
        
        # MAKE IT
        self.go_btn = QPushButton("MAKE IT!"); self.go_btn.setFixedHeight(42)
        self.go_btn.setToolTip("Start encoding with the current settings. In batch mode, processes all queued tasks.")
        self.go_btn.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white; font-size: 16px; font-weight: bold; border-radius: 4px;")
        go_row = QHBoxLayout()
        go_row.setContentsMargins(30, 0, 30, 0)
        go_row.addWidget(self.go_btn)
        root_l.addLayout(go_row)
        
        # --- Advanced: Frame Cache location ---
        # Persistent override for the PNG frame cache root. Default is the OS
        # temp directory; users can point it at a fast SSD or a project folder
        # to keep extracted frames close to the source. Stored in app_settings.json.
        cfg_cache = self._app_settings.get("cache_dir")
        self.cache_dir = cfg_cache if (cfg_cache and isinstance(cfg_cache, str)) else DEFAULT_CACHE_DIR

        gb_cache = QFrame()
        gb_cache.setObjectName("cache_box")
        gb_cache.setStyleSheet(
            f"QFrame#cache_box {{ background: #0e161b; border: 1px solid #2d4050; border-radius: 4px; }}"
        )
        cache_v = QVBoxLayout(gb_cache)
        cache_v.setContentsMargins(8, 6, 8, 6)
        cache_v.setSpacing(3)

        # Title + path on the same row
        h_cache = QHBoxLayout(); h_cache.setSpacing(6)
        lbl_cache_title = QLabel("🟠 FRAME CACHE")
        lbl_cache_title.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 10px; font-weight: bold;")
        h_cache.addWidget(lbl_cache_title)
        lbl_path_caption = QLabel("Path:")
        lbl_path_caption.setStyleSheet("color: #666; font-size: 9px; font-weight: normal;")
        h_cache.addWidget(lbl_path_caption)
        self.lbl_cache_path = QLabel(self._cache_label_text())
        self.lbl_cache_path.setStyleSheet("font-size: 9px; color: #999; font-style: italic; font-weight: normal;")
        self.lbl_cache_path.setToolTip(self.cache_dir)
        self.lbl_cache_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_cache_path.setMinimumWidth(40)
        self.lbl_cache_path.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        h_cache.addWidget(self.lbl_cache_path, 1)
        cache_v.addLayout(h_cache)

        cache_btn_style = (
            "font-size: 9px; color: #ddd; background: #2a2a2a; "
            "border: 1px solid #3a3a3a; border-radius: 3px; "
            "padding: 2px 6px; font-weight: bold;"
        )
        h_btns = QHBoxLayout(); h_btns.setSpacing(4)
        self.btn_cache_set = QPushButton("SET")
        self.btn_cache_open = QPushButton("OPEN")
        self.btn_cache_reset = QPushButton("RESET")
        for b in [self.btn_cache_set, self.btn_cache_open, self.btn_cache_reset]:
            b.setFixedHeight(20)
            b.setStyleSheet(cache_btn_style)
            b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            h_btns.addWidget(b)
        self.btn_purge_cache = QPushButton("PURGE")
        self.btn_purge_cache.setFixedHeight(20)
        self.btn_purge_cache.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_purge_cache.setStyleSheet(
            f"font-size: 9px; color: white; background: {COLOR_DANGER}; "
            f"border: 1px solid #5a1a1a; border-radius: 3px; "
            f"padding: 2px 10px; font-weight: bold;"
        )
        h_btns.addWidget(self.btn_purge_cache)
        h_btns.addStretch()
        cache_v.addLayout(h_btns)

        self.btn_cache_set.setToolTip("Choose a custom folder for the PNG frame cache.")
        self.btn_cache_open.setToolTip("Open the cache folder in the file explorer.")
        self.btn_cache_reset.setToolTip(f"Reset back to the default ({DEFAULT_CACHE_DIR}).")
        self.btn_purge_cache.setToolTip("Delete every cached PNG frame folder. A confirmation will be shown first.")
        root_l.addWidget(gb_cache)

        # Diagnostic strip — independent from the cache section. System
        # Console and About are auxiliary actions, not cache controls,
        # so they live on their own row at the bottom of the panel.
        # They used to be grey 9-px text links and were hard to spot;
        # now they're proper bordered buttons with subtle accent colors
        # so the user can find them at a glance without competing with
        # the main MAKE / queue actions visually.
        h_tools = QHBoxLayout()
        h_tools.setContentsMargins(0, 2, 0, 0)
        h_tools.setSpacing(6)
        self.c_btn = QPushButton("⚙ Console")
        self.c_btn.setCursor(Qt.PointingHandCursor)
        self.c_btn.setToolTip("Toggle the diagnostic log panel (FFmpeg / engine output).")
        self.c_btn.setStyleSheet(
            "QPushButton {"
            "  font-size: 10px; font-weight: bold;"
            "  color: #cfd6dc; background: #1a2230;"
            "  border: 1px solid #2a3a52; border-radius: 3px;"
            "  padding: 3px 8px;"
            "}"
            "QPushButton:hover { background: #25324a; border-color: #3a4a66; color: white; }"
            "QPushButton:pressed { background: #15202c; }"
        )
        self.about_btn = QPushButton("ⓘ About")
        self.about_btn.setCursor(Qt.PointingHandCursor)
        self.about_btn.setToolTip(
            "App info, version, author and credits to the open-source projects this tool is built on."
        )
        self.about_btn.setStyleSheet(
            "QPushButton {"
            f"  font-size: 10px; font-weight: bold;"
            f"  color: white; background: {COLOR_ACCENT};"
            "  border: none; border-radius: 3px;"
            "  padding: 3px 10px;"
            "}"
            f"QPushButton:hover {{ background: {COLOR_ACCENT_HOVER}; }}"
            "QPushButton:pressed { background: #1a78c2; }"
        )
        self.chk_tooltips = QCheckBox("Tooltips")
        self.chk_tooltips.setChecked(True)
        self.chk_tooltips.setToolTip("Show or hide hover tooltips on all controls.")
        self.chk_tooltips.setStyleSheet(
            f"QCheckBox {{ color: {COLOR_TEXT}; font-size: 10px; padding: 4px 0; }}"
            f"QCheckBox::indicator {{ width: 13px; height: 13px; border-radius: 3px; }}"
            f"QCheckBox::indicator:unchecked {{ background-color: #2a2a2a; border: 1px solid #555; }}"
            f"QCheckBox::indicator:checked {{ background-color: {COLOR_ACCENT}; border: 1px solid #fff; }}"
        )
        self.chk_tooltips.toggled.connect(self._toggle_tooltips)

        h_tools.addWidget(self.about_btn)
        h_tools.addWidget(self.c_btn)
        h_tools.addWidget(self.chk_tooltips)
        h_tools.addStretch()
        root_l.addLayout(h_tools)
        
        # Connections
        self.fmt_g.buttonClicked.connect(self.update_ui); 
        self.chk_alpha.toggled.connect(self.update_ui); 
        self.chk_loop.toggled.connect(self.update_ui); 
        self.chk_fast.toggled.connect(self.update_ui); 
        self.chk_loss.toggled.connect(self.update_ui);
        
        self.mb_sp.valueChanged.connect(self.update_ui)
        self.fps_sp.valueChanged.connect(self.update_ui)
        self.qual_sp.valueChanged.connect(self.update_ui)
        # bg_prio used to be silent — switching Balanced/FPS/Quality didn't
        # refresh the dynamic groupbox title ("ENCODING (Auto: 16.0MB | Bal)").
        # Wiring it through update_ui matches every other interactive widget
        # in the panel and costs nothing.
        self.bg_prio.buttonClicked.connect(self.update_ui)
        self.tabs.currentChanged.connect(self.update_ui)
        self.res_box.opt.currentIndexChanged.connect(self.update_ui)
        self.res_box.s_perc.valueChanged.connect(self.update_ui)
        self.res_box.s_w.valueChanged.connect(self.update_ui)
        self.res_box.s_h.valueChanged.connect(self.update_ui)
        
        self.btn_purge_cache.clicked.connect(self.purge_cache)
        self.btn_cache_set.clicked.connect(self.set_cache_dir)
        self.btn_cache_open.clicked.connect(self.open_cache_dir)
        self.btn_cache_reset.clicked.connect(self.reset_cache_dir)
        self.batch_en.toggled.connect(self.update_ui)
        
        # Presets live next to the executable (Windows/dev) or in the standard
        # per-user folder on macOS .app builds — see _user_presets_dir().
        self.presets_dir = _user_presets_dir()
        os.makedirs(self.presets_dir, exist_ok=True)
        self.btn_save_pre.clicked.connect(self.save_preset)
        self.btn_open_pre.clicked.connect(self.open_presets_folder)
        self.preset.currentIndexChanged.connect(self.load_preset)
        self.refresh_presets()
        
        QTimer.singleShot(100, self.load_initial_state)

    def load_initial_state(self):
        """Refresh presets, then restore the last-used single-mode settings from
        app_settings.json (v3.1.9).

        Trim is NOT a concern here: set_vals only applies a trim when a source is
        loaded (duration > 0), so at boot the panel restores every encoding
        parameter the user last used while the trim fields stay clean."""
        self.refresh_presets()
        try:
            last = (load_app_settings() or {}).get("last_single_vals")
            if isinstance(last, dict) and last:
                self.set_vals(last)
        except Exception:
            pass

    def delete_preset(self):
        name = self.preset.currentText()
        if not name or name == "Select Preset..." or name == "Standard Default": return
        path = os.path.join(self.presets_dir, name + ".json")
        if os.path.exists(path):
            try: 
                os.remove(path)
                self.refresh_presets()
            except: pass

    _TT_HIDE = "QToolTip { max-width: 0; max-height: 0; padding: 0; margin: 0; background: transparent; border: none; }"

    def _toggle_tooltips(self, enabled):
        """Globally show or hide tooltips."""
        app = QApplication.instance()
        current = app.styleSheet() or ""
        cleaned = current.replace(self._TT_HIDE, "").strip()
        if enabled:
            app.setStyleSheet(cleaned)
        else:
            app.setStyleSheet(cleaned + " " + self._TT_HIDE)

    def update_ui(self):
        is_gif = self.b_gif.isChecked()
        self.chk_loss.setVisible(not is_gif)
        self.chk_loop.setVisible(is_gif)
        self.b_at.setVisible(self.chk_alpha.isChecked())
        
        
        # Force format button visual state (Qt :checked pseudo-selector unreliable with QButtonGroup)
        style_active = f"background-color: {COLOR_ACCENT}; color: white; border: 2px solid white; font-weight: 900; font-size: 12px;"
        style_inactive = f"background-color: {COLOR_PANEL}; color: {COLOR_TEXT}; border: 1px solid #444; font-size: 12px;"
        self.b_gif.setStyleSheet(style_active if is_gif else style_inactive)
        self.b_webp.setStyleSheet(style_inactive if is_gif else style_active)
        
        # --- DYNAMIC TITLES ---
        # 1. Format
        fmt = "GIF" if is_gif else "WebP"
        opts = []
        if self.chk_alpha.isChecked(): opts.append("Trsp")
        if is_gif and self.chk_loop.isChecked(): opts.append("Loop")
        if not is_gif and self.chk_loss.isChecked(): opts.append("Lossless")
        if self.chk_fast.isChecked(): opts.append("Fast")
        
        title_fmt = f"1. FORMAT SETTINGS ({fmt}"
        if opts: title_fmt += " | " + " ".join(opts)
        title_fmt += ")"
        self.gb_fmt.setTitle(title_fmt)
        
        # 2. Dimensions
        try:
            d_mode = self.res_box.opt.currentText()
            d_val = ""
            if d_mode == "Percentage (%)": d_val = f"{self.res_box.s_perc.value()}%"
            elif d_mode == "Lock Width": d_val = f"W:{self.res_box.s_w.value()}"
            elif d_mode == "Lock Height": d_val = f"H:{self.res_box.s_h.value()}"
            elif d_mode == "Manual WxH": d_val = f"{self.res_box.s_w.value()}x{self.res_box.s_h.value()}"
            else: d_val = "Orig"
            self.res_box.setTitle(f"2. OUTPUT DIMENSIONS ({d_val}) 📏")
        except: pass

        # 3. Encoding Mode
        try:
            if self.tabs.currentIndex() == 0: # Iterative
                 prio = "Mixed"
                 if self.p_bal.isChecked(): prio = "Bal"
                 elif self.p_fps.isChecked(): prio = "FPS"
                 elif self.p_ql.isChecked(): prio = "Qual"
                 self.gb_mode.setTitle(f"3. ENCODING (Auto: {self.mb_sp.value():.1f}MB | {prio})")
            else: # Manual
                 self.gb_mode.setTitle(f"3. ENCODING (Fix: {self.fps_sp.value()}fps | Q:{self.qual_sp.value()})")
        except: pass

    def open_presets_folder(self):
        open_path_in_os(self.presets_dir)

    def refresh_presets(self):
        self.preset.blockSignals(True)
        self.preset.clear()
        self.preset.addItem("Select Preset...")
        self.preset.addItem("Standard Default")
        try:
            for f in sorted(os.listdir(self.presets_dir)):
                if f.endswith(".json") and not f.startswith("_"): self.preset.addItem(os.path.splitext(f)[0])
        except: pass
        self.preset.blockSignals(False)

    def load_preset(self):
        idx = self.preset.currentIndex()
        if idx <= 0: return
        name = self.preset.currentText()
        
        if name == "Standard Default":
            self.set_vals({"target": 16.0, "format": "GIF", "mode": "ITERATIVE", "low": 1.5, "up": 0.5, "fps": 15, "qual": 90, "dim_mode": "Original", "dim_perc": 100, "dim_w": 640, "dim_h": 360, "alpha": False, "prio": "Balanced"})
            return

        path = os.path.join(self.presets_dir, name + ".json")
        try:
            with open(path, 'r') as f: data = json.load(f)
            self.set_vals(data)
        except Exception as e: print(f"Error loading preset: {e}")

    def _cache_label_text(self):
        """Pretty-print the active cache path. We collapse the OS temp dir to
        '(default temp)' so the row stays readable; the full path is always
        available in the tooltip."""
        path = self.cache_dir or DEFAULT_CACHE_DIR
        if os.path.normpath(path) == os.path.normpath(DEFAULT_CACHE_DIR):
            return "(default temp)"
        # Truncate long paths from the LEFT so the trailing folder name (the
        # most identifying part) stays visible.
        if len(path) > 60:
            return "…" + path[-58:]
        return path

    def _refresh_cache_label(self):
        if hasattr(self, "lbl_cache_path"):
            self.lbl_cache_path.setText(self._cache_label_text())
            self.lbl_cache_path.setToolTip(self.cache_dir or DEFAULT_CACHE_DIR)

    def _persist_cache_dir(self):
        """Write the current cache path to app_settings.json. We only persist
        non-default values to keep the settings file empty when the user hasn't
        customized anything (cleaner sync across machines).

        Reload-before-write protects against clobbering other keys (e.g.
        show_iter_chart, owned by MainWindow) that may have been written
        more recently than the in-memory snapshot we hold."""
        s = dict(load_app_settings() or {})
        if not self.cache_dir or os.path.normpath(self.cache_dir) == os.path.normpath(DEFAULT_CACHE_DIR):
            s.pop("cache_dir", None)
        else:
            s["cache_dir"] = self.cache_dir
        self._app_settings = s
        save_app_settings(s)

    def set_cache_dir(self):
        chosen = QFileDialog.getExistingDirectory(self, "Choose Frame Cache Folder", self.cache_dir or DEFAULT_CACHE_DIR)
        if not chosen:
            return
        # Sanity check: we must be able to write here, otherwise reject so the
        # user gets immediate feedback instead of a mid-job ffmpeg failure.
        try:
            os.makedirs(chosen, exist_ok=True)
            probe = os.path.join(chosen, ".gif_tool_probe")
            with open(probe, "w") as f: f.write("ok")
            os.remove(probe)
        except Exception as e:
            QMessageBox.warning(self, "Cache Folder", f"Cannot write to that folder:\n{e}")
            return
        self.cache_dir = chosen
        self._persist_cache_dir()
        self._refresh_cache_label()

    def open_cache_dir(self):
        target = self.cache_dir or DEFAULT_CACHE_DIR
        try:
            if not os.path.exists(target): os.makedirs(target, exist_ok=True)
        except Exception as e:
            QMessageBox.warning(self, "Open Cache Folder", str(e))
            return
        if not open_path_in_os(target):
            QMessageBox.warning(self, "Open Cache Folder",
                                f"Could not open: {target}")

    def reset_cache_dir(self):
        if os.path.normpath(self.cache_dir or "") == os.path.normpath(DEFAULT_CACHE_DIR):
            return
        self.cache_dir = DEFAULT_CACHE_DIR
        self._persist_cache_dir()
        self._refresh_cache_label()

    def purge_cache(self):
        # Always purge the ACTIVE cache dir, not the hardcoded default — otherwise
        # users with a custom path would think the button doesn't work.
        target = self.cache_dir or DEFAULT_CACHE_DIR
        # Compute current footprint so the user can decide informedly. Skipped
        # silently if the folder doesn't exist or scanning fails (don't block
        # purge on a flaky disk).
        size_str = ""
        try:
            if os.path.exists(target):
                total = 0
                for root, _, files in os.walk(target):
                    for fn in files:
                        try: total += os.path.getsize(os.path.join(root, fn))
                        except OSError: pass
                size_str = f"\n\nCurrent size: {total / (1024 * 1024):.1f} MB"
        except Exception:
            pass
        confirm = QMessageBox.question(
            self,
            "Purge Cache?",
            f"This will delete every cached PNG frame in:\n{target}{size_str}\n\n"
            "Next runs will re-extract frames from source (slower the first time).\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            if os.path.exists(target):
                shutil.rmtree(target)
            os.makedirs(target, exist_ok=True)
            QMessageBox.information(self, "Cache Purged", f"Cleared:\n{target}")
        except Exception as e:
            QMessageBox.warning(self, "Cache Purge Failed", str(e))

    def _suggested_preset_name(self, vals):
        """Build a v2.7-style descriptive default name from the live UI
        values, e.g. ``WebP_16MB_Balanced_OriginalSize``,
        ``GIF_Manual_F15_Q90_Width600px``, ``WebP_8MB_FPS_640x360px_Alpha``.

        We mirror v2.7's encoding so users coming back to the tool see
        familiar suggestions, then they can keep, tweak, or fully
        rewrite the name in the dialog. Logic:

        - ``fmt``: ``GIF`` or ``WebP``.
        - Mode block:
            * Iterative → ``{mb}MB_{Prio}`` where mb prints integers
              without the trailing ``.0`` (16, not 16.0).
            * Manual    → ``Manual_F{fps}_Q{qual}``.
        - Dim block: ``OriginalSize`` / ``Scale{n}pct`` /
          ``Width{n}px`` / ``Height{n}px`` / ``{w}x{h}px``.
        - ``_Alpha`` suffix when transparency is on.
        """
        fmt = vals.get("format", "GIF")
        if vals.get("mode", "ITERATIVE") == "ITERATIVE":
            try:
                mb_f = float(vals.get("target", 16.0))
                mb_str = str(int(mb_f)) if mb_f.is_integer() else f"{mb_f:g}"
            except Exception:
                mb_str = "Target"
            mode_str = f"{mb_str}MB_{vals.get('prio', 'Balanced')}"
        else:
            mode_str = f"Manual_F{vals.get('fps', 15)}_Q{vals.get('qual', 90)}"

        dm = vals.get("dim_mode", "Original")
        if dm == "Original":          dim = "OriginalSize"
        elif dm == "Percentage (%)":  dim = f"Scale{vals.get('dim_perc', 100)}pct"
        elif dm == "Lock Width":      dim = f"Width{vals.get('dim_w', 640)}px"
        elif dm == "Lock Height":     dim = f"Height{vals.get('dim_h', 360)}px"
        else:                         dim = f"{vals.get('dim_w', 640)}x{vals.get('dim_h', 360)}px"

        name = f"{fmt}_{mode_str}_{dim}"
        if vals.get("alpha"):
            name += "_Alpha"
        return name

    def save_preset(self):
        import PySide6.QtWidgets as qw
        # Pre-fill with a v2.7-style descriptive name derived from the
        # current UI state. The user can keep it, tweak it, or replace
        # it entirely — the dialog selects all by default so retyping
        # over the suggestion is one keystroke.
        vals = self.get_vals()
        suggested = self._suggested_preset_name(vals)
        name, ok = qw.QInputDialog.getText(
            self, "Save New Preset", "Enter preset name:",
            qw.QLineEdit.Normal, suggested
        )
        if ok and name.strip():
            clean_name = "".join([c for c in name if c.isalnum() or c in " -_"]).strip()
            path = os.path.join(self.presets_dir, clean_name + ".json")
            # Block accidental overwrites — if a preset with this name
            # already exists, ask before replacing it. Without this the
            # save was silently destructive, which is bad UX once we
            # start suggesting names that may collide with prior saves.
            if os.path.exists(path):
                resp = QMessageBox.question(
                    self, "Overwrite Preset?",
                    f"A preset named '{clean_name}' already exists.\nOverwrite it?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if resp != QMessageBox.Yes:
                    return
            try:
                with open(path, 'w') as f: json.dump(vals, f, indent=4)
                self.refresh_presets()
                self.preset.setCurrentText(clean_name)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save preset:\n{e}")

    def update_preset(self):
        name = self.preset.currentText()
        if not name or name == "Select Preset..." or name == "Standard Default": return
        path = os.path.join(self.presets_dir, name + ".json")
        try:
            with open(path, 'w') as f: json.dump(self.get_vals(), f, indent=4)
            QMessageBox.information(self, "Preset Updated", f"Preset '{name}' updated successfully.")
        except Exception as e: QMessageBox.critical(self, "Error", f"Failed to update preset:\n{e}")

    def persist_last_vals(self):
        """Remember the current single-mode parameters in app_settings.json so the
        NEXT launch restores them instead of snapping back to the hard-coded
        defaults (v3.1.9). Trim is saved too but is only re-applied when a source
        is actually loaded (see set_vals), so it never resurrects a stale TC range
        on a fresh boot."""
        try:
            s = dict(load_app_settings() or {})
            s["last_single_vals"] = self.get_vals()
            self._app_settings = s
            save_app_settings(s)
        except Exception:
            pass

    def save_session(self):
        """Persist the last-used single-mode settings on close (v3.1.9).

        Previously a no-op (session restore was disabled). We now store just the
        parameter set — not the loaded clip or trim range — so reopening the app
        restores where the user left off without resurrecting a stale trim."""
        self.persist_last_vals()

    def set_current_fps(self, fps, duration_sec=None):
        """Update the fps and (optionally) total duration used to render trim
        values as HH:MM:SS:FF in the manual In/Out fields and the Length
        readout. Should be called BEFORE set_vals whenever the active task
        changes (load_single, on_table_sel single-row case).

        We do NOT re-format the existing field text here — set_vals is
        always called immediately after, which writes the proper
        frame-formatted value. We DO refresh the OUT placeholder and the
        Length label so they reflect the new source's TC range.

        Pass ``duration_sec=0`` (or None) to indicate "no source loaded";
        the OUT placeholder reverts to "End" and Length hides itself."""
        try: fps = float(fps)
        except (ValueError, TypeError): fps = 0.0
        if fps > 0:
            self._current_fps = fps
        if duration_sec is not None:
            try: dur = float(duration_sec)
            except (ValueError, TypeError): dur = 0.0
            self._current_duration_sec = max(0.0, dur)
            # OUT placeholder reflects loaded source state:
            #   - duration > 0 → real end TC (HH:MM:SS:FF), tells the user
            #     exactly what "leave it empty" will clamp to.
            #   - duration == 0 (no source) → literal "End", same as v3.0.
            if self._current_duration_sec > 0 and self._current_fps > 0:
                incl_end = inclusive_display_sec_from_exclusive_out(
                    self._current_duration_sec, self._current_fps
                )
                tc_end = format_seconds_as_tc_frames(incl_end, self._current_fps)
            else:
                tc_end = "End"
            self.t_end.setPlaceholderText(tc_end)
        # Recompute the Length readout — both the new fps and the new
        # duration affect it (an empty OUT field resolves to duration_sec).
        self._refresh_trim_length()

    def clear_trim_fields(self):
        """Wipe the manual In/Out fields and reset the OUT placeholder to
        "End". Called when no video is loaded (e.g. app boot before the
        user drops anything, or after closing single mode without a task)
        so the panel doesn't display a stale TC range from a previous
        session as if a real trim were active."""
        for f in (self.t_start, self.t_end):
            f.blockSignals(True)
            f.setText("")
            f.blockSignals(False)
        self.t_end.setPlaceholderText("End")
        self._refresh_trim_length()

    def _refresh_trim_length(self):
        """Recompute and (un)hide the Length readout based on the current
        IN/OUT fields plus the active source's fps/duration.

        Visibility rules — Length is shown ONLY when there's an actual
        trim to report:
          1. A source is loaded (``_current_duration_sec > 0``).
          2. AND either IN > 0 or OUT < clip end (i.e. the range is a
             strict subset of the full clip).

        Without rule 2, "Length" would just duplicate the source duration
        and add visual noise. Without rule 1, we'd be showing a TC built
        from stale session data with no source attached."""
        if not hasattr(self, "lbl_trim_length"):
            return
        fps = self._current_fps if self._current_fps > 0 else 25.0
        dur = self._current_duration_sec

        # No source → hide entirely. Trim fields should be empty in this
        # state too (set_vals + clear_trim_fields enforce that).
        if dur <= 0:
            self.lbl_trim_length.setVisible(False)
            return

        in_raw = self.t_start.text().strip()
        out_raw = self.t_end.text().strip()
        in_sec = parse_trim_to_seconds(in_raw, default=0.0, fps=fps)
        if in_sec is None: in_sec = 0.0
        if out_raw:
            out_display = parse_trim_to_seconds(out_raw, default=dur, fps=fps)
            if out_display is None:
                out_display = dur
            out_sec = parse_trim_end_display_to_exclusive(out_display, fps, dur)
            if out_sec is None:
                out_sec = dur
        else:
            out_sec = dur

        # Half a millisecond of slack so float round-trips through TC
        # don't trip the "is this a real trim?" check on the boundary.
        EPS = 0.0005
        in_set = in_sec > EPS
        out_set = out_sec < (dur - EPS)
        if not (in_set or out_set):
            # Range == full clip → no real trim, hide the readout.
            self.lbl_trim_length.setVisible(False)
            return

        self.lbl_trim_length.setVisible(True)
        length = max(0.0, float(out_sec) - float(in_sec))
        tc = format_seconds_as_tc_frames(length, fps) or "00:00:00:00"
        self.lbl_trim_length.setText(f"Length: {tc}")

    def _normalize_trim_field(self, line_edit, default_text):
        """Re-format a trim QLineEdit to HH:MM:SS:FF after the user finishes editing.
        - Accepts seconds ('5.234'), HH:MM:SS[.ms] AND HH:MM:SS:FF.
        - Empty input → `default_text` (used to clear out_end while keeping t_start='00:00:00').
        - Unparseable input → revert to `default_text` so we never persist garbage."""
        raw = line_edit.text().strip()
        if not raw:
            line_edit.setText(default_text)
            return
        sec = parse_trim_to_seconds(raw, default=None, fps=self._current_fps)
        if sec is None:
            line_edit.setText(default_text)
            return
        formatted = format_seconds_as_tc_frames(sec, self._current_fps) or default_text
        if formatted != raw:
            # Block to avoid editingFinished re-firing recursively under some platforms.
            line_edit.blockSignals(True)
            line_edit.setText(formatted)
            line_edit.blockSignals(False)

    def get_vals(self): # Return ALL values
        prio_map = {0:"Balanced", 1:"FPS", 2:"Quality"}
        # Trim is rendered as HH:MM:SS:FF in the UI (frame-aware) but stored as
        # HH:MM:SS.ms so it's directly usable by ffmpeg's -ss/-to. We parse
        # whatever the user typed (any format) and re-emit ms for storage.
        raw_start = self.t_start.text().strip()
        raw_end   = self.t_end.text().strip()
        sec_start = parse_trim_to_seconds(raw_start, default=0.0, fps=self._current_fps)
        if raw_end:
            sec_end_display = parse_trim_to_seconds(
                raw_end, default=None, fps=self._current_fps
            )
            sec_end_excl = parse_trim_end_display_to_exclusive(
                sec_end_display, self._current_fps,
                self._current_duration_sec if self._current_duration_sec > 0 else None,
            )
            trim_end_ms = (
                format_seconds_as_tc(sec_end_excl) if sec_end_excl is not None else ""
            )
        else:
            trim_end_ms = ""
        trim_start_ms = format_seconds_as_tc(sec_start) if sec_start > 0.001 else "00:00:00"
        return {
            "target": self.mb_sp.value(), "format": "GIF" if self.b_gif.isChecked() else "WebP",
            "low": self.low_sp.value(), "up": self.up_sp.value(), "prio": prio_map.get(self.bg_prio.checkedId(), "Balanced"),
            "mode": "ITERATIVE" if self.tabs.currentIndex() == 0 else "MANUAL",
            "fps": self.fps_sp.value(), "qual": self.qual_sp.value(),
            "play_once": not self.chk_loop.isChecked(), "fast": self.chk_fast.isChecked(), "alpha": self.chk_alpha.isChecked(), "lossless": self.chk_loss.isChecked(),
            "trim_start": trim_start_ms, "trim_end": trim_end_ms,
            "keep_iterations": self.chk_keep_iter.isChecked(),
            "name_settings": self.chk_name_settings.isChecked(),
            **self.res_box.get_dict()
        }
    
    def set_vals(self, v):
        """Load values from a preset dict. Supports both v2.7 and v3.0 formats."""
        print(f"DEBUG set_vals called with: {list(v.keys())[:5]}...")  # Debug
        
        # Helper to get value from either format
        def get_val(v3_key, v27_key, default, is_float=False):
            val = v.get(v3_key)  # Try v3 key first
            if val is None:
                val = v.get(v27_key, default)  # Fallback to v2.7 key
            if val is None:
                val = default
            # Handle string numbers from v2.7 format
            if is_float and isinstance(val, str):
                try: val = float(val)
                except: val = default
            return val
        
        try:
            # Numeric values
            self.mb_sp.setValue(float(get_val("target", "-TARGET_MB-", 16.0, True)))
            self.low_sp.setValue(float(get_val("low", "-LOWER_MARGIN-", 1.5, True)))
            self.up_sp.setValue(float(get_val("up", "-UPPER_MARGIN-", 0.5, True)))
            self.fps_sp.setValue(int(get_val("fps", "-MANUAL_FPS-", 15, True)))
            self.qual_sp.setValue(int(get_val("qual", "-MANUAL_QUALITY-", 90, True)))
            
            # Format (v3: "format"="GIF", v2.7: "-FORMAT_GIF-"=True)
            if "format" in v:
                is_gif = v["format"] == "GIF"
            else:
                is_gif = v.get("-FORMAT_GIF-", True)
            self.b_gif.setChecked(is_gif)
            self.b_webp.setChecked(not is_gif)
            
            # Mode (v3: "mode"="ITERATIVE", v2.7: "-ENABLE_ITERATIVE-"=True)
            if "mode" in v:
                is_iter = v["mode"] == "ITERATIVE"
            else:
                is_iter = v.get("-ENABLE_ITERATIVE-", True)
            self.tabs.setCurrentIndex(0 if is_iter else 1)
            
            # Checkboxes
            self.chk_loop.setChecked(not get_val("play_once", "-PLAY_ONCE-", False))
            self.chk_fast.setChecked(get_val("fast", "-FASTER_ENCODE-", False))
            self.chk_alpha.setChecked(get_val("alpha", "-HAS_ALPHA-", False))
            self.chk_loss.setChecked(get_val("lossless", "-WEBP_LOSSLESS-", False))
            # Default to True so legacy presets that pre-date this flag opt
            # in to the warm-start cache automatically — matches the
            # checkbox's fresh-start default in __init__.
            self.chk_keep_iter.setChecked(bool(get_val("keep_iterations", "-KEEP_ALL_ITER-", True)))
            # New in v3.1: tag-filename-with-settings. Default to True for new
            # presets, but honor explicit False from saved presets.
            self.chk_name_settings.setChecked(bool(get_val("name_settings", "-NAME_SETTINGS-", True)))
            
            # Priority (v3: "prio"="FPS", v2.7: "-PRIO_FPS-"=True)
            if "prio" in v:
                pm = v["prio"]
            elif v.get("-PRIO_FPS-"): pm = "FPS"
            elif v.get("-PRIO_QUAL-"): pm = "Quality"
            else: pm = "Balanced"
            
            if pm == "Balanced": self.p_bal.setChecked(True)
            elif pm == "FPS": self.p_fps.setChecked(True)
            elif pm == "Quality": self.p_ql.setChecked(True)
            
            # Dimensions (simplified, just use v3 format for now)
            self.res_box.set_dict(v)
            
            # Trim — stored as HH:MM:SS.ms (or legacy seconds string), but
            # displayed in the manual In/Out fields as HH:MM:SS:FF using the
            # active fps. We ONLY apply trim if a source is currently loaded
            # (duration > 0). Restoring a saved-session trim into an empty
            # panel makes it look like a trim is active when there's no
            # video to trim — confusing on app boot and after Reset Single.
            if self._current_duration_sec > 0:
                raw_start = get_val("trim_start", "-TRIM_START-", "00:00:00")
                raw_end = get_val("trim_end", "-TRIM_END-", "")
                sec_start = parse_trim_to_seconds(raw_start, default=0.0, fps=self._current_fps)
                self.t_start.setText(format_seconds_as_tc_frames(sec_start, self._current_fps) or "00:00:00:00")
                if raw_end:
                    sec_end_excl = parse_trim_to_seconds(
                        raw_end, default=None, fps=self._current_fps
                    )
                    if sec_end_excl is not None:
                        incl_sec = inclusive_display_sec_from_exclusive_out(
                            sec_end_excl, self._current_fps
                        )
                        self.t_end.setText(
                            format_seconds_as_tc_frames(incl_sec, self._current_fps)
                        )
                    else:
                        self.t_end.setText("")
                else:
                    self.t_end.setText("")
            else:
                # No source loaded → ensure trim UI is empty + Length hides
                # itself. clear_trim_fields handles both fields and the
                # OUT placeholder ("End").
                self.clear_trim_fields()
            
            print(f"DEBUG set_vals SUCCESS: GIF={is_gif}, Iter={is_iter}, Prio={pm}")
            
        except Exception as e:
            print(f"Error setting values: {e}")
        finally:
            self.update_ui()

# --- Main Window ---
class ReorderableTable(QTableWidget):
    """QTableWidget that supports drag-and-drop row reordering from any cell.
    Emits rows_reordered(source_row_indices: list[int], drop_row: int) on drop;
    the receiver mutates the data model and refreshes the table.

    Critical: `event.setDropAction(Qt.IgnoreAction)` BEFORE accept() prevents Qt's
    default cell-level move (which would remove the source items and break the rows)."""
    rows_reordered = Signal(list, int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.IgnoreAction)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event):
        if event.source() is self:
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.source() is self:
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.source() is not self:
            event.ignore()
            return
        source_rows = sorted(set(i.row() for i in self.selectedItems()))
        if not source_rows:
            event.ignore()
            return
        drop_row = self.rowAt(event.pos().y())
        if drop_row == -1:
            drop_row = self.rowCount()
        else:
            indicator = self.dropIndicatorPosition()
            if indicator == QAbstractItemView.BelowItem:
                drop_row += 1
        self.rows_reordered.emit(source_rows, drop_row)
        event.setDropAction(Qt.IgnoreAction)
        event.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        # Window icon: try the bundled .ico first (PyInstaller exe carries
        # it next to the binary via the spec file), then fall back to the
        # source-tree path when running directly from the .py.
        self._apply_window_icon()
        # Adaptive sizing: pick a launch size that ALWAYS fits on the
        # user's screen without forcing scrollbars or clipping the UI.
        # We compute three values from the available work area:
        #   - ``min_w`` / ``min_h``: hard floor — the layout simply
        #     can't render below this without overlap. Picked just
        #     below the natural single-mode size so the user can shrink
        #     a bit if they want.
        #   - ``init_w`` / ``init_h``: the initial size we resize to.
        #     Caps at 1500 × 900 (our "ideal" layout dimensions) but
        #     never exceeds the screen's available work area minus
        #     ~40 px of headroom (so the title bar and taskbar always
        #     stay reachable).
        # This matters most for high-DPI 1080 displays at 125-150%
        # scaling, where logical width drops to 1280-1536 and a hard
        # 1500 minimum would clip the FRAME CACHE row off the right.
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        avail_w = (avail.width() - 40) if avail else 1500
        avail_h = (avail.height() - 40) if avail else 900
        ideal_w, ideal_h = 1500, 680
        floor_w, floor_h = 1280, 560
        init_w = max(floor_w, min(ideal_w, avail_w))
        init_h = max(floor_h, min(ideal_h, avail_h))
        # Minimum allows the user to shrink a bit but never below the
        # floor we know the layout supports. We also clamp the minimum
        # to the screen so on tiny displays Qt doesn't refuse to show
        # the window at all.
        min_w = min(floor_w, avail_w)
        min_h = min(floor_h, avail_h)
        self.setMinimumSize(min_w, min_h)
        self.resize(init_w, init_h)
        self.setStyleSheet(GLOBAL_STYLE)
        cw = QWidget(); self.setCentralWidget(cw); 
        
        # Main Vertical Layout
        main_v = QVBoxLayout(cw); main_v.setContentsMargins(10, 10, 10, 10); main_v.setSpacing(10)
        
        # Content Area (Stack + Settings)
        self._content_h = QHBoxLayout(); self._content_h.setSpacing(10)
        content_h = self._content_h
        self.stack = QStackedWidget(); content_h.addWidget(self.stack, 1)
        
        # Drop Zone — hero DnD widget (single file mode)
        self.drop_zone = DropZoneWidget()
        self.stack.addWidget(self.drop_zone)
        
        # Batch Panel (Cleaned up, no output controls)
        self.batch = QFrame()
        self.batch.setObjectName("batch_frame")
        self.batch.setStyleSheet(f"QFrame#batch_frame {{ background: {COLOR_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 8px; }}")
        bl = QVBoxLayout(self.batch)
        bl.setContentsMargins(8, 8, 8, 8); bl.setSpacing(6)
        
        # Batch Info Label (shows selected task info)
        self.lbl_batch_info = QLabel("Drop video files or click 'Add Files' to start")
        self.lbl_batch_info.setStyleSheet(f"color: #666; font-style: italic; font-size: 10px; padding: 2px 4px; background: {COLOR_BG}; border-radius: 3px;")
        self.lbl_batch_info.setWordWrap(True)
        bl.addWidget(self.lbl_batch_info)

        # Batch trim preview strip (mirrors DropZone's, shown for selected row).
        # Fixed height so the table below never shifts when thumbnails appear.
        self._batch_trim_preview = QWidget()
        self._batch_trim_preview.setFixedHeight(88)
        _btp_l = QHBoxLayout(self._batch_trim_preview)
        _btp_l.setContentsMargins(0, 2, 0, 2)
        _btp_l.setSpacing(12)
        _btp_thumb_style = "background: #0e0e0e; border: 1px solid #1e1e1e; border-radius: 3px;"
        _btp_lbl_style = "font-size: 9px; font-weight: bold; color: #777; border: none; background: transparent;"

        _btp_in_col = QVBoxLayout(); _btp_in_col.setSpacing(1)
        self._btp_in_lbl = QLabel("▶ FIRST FRAME (IN)")
        self._btp_in_lbl.setStyleSheet(_btp_lbl_style); self._btp_in_lbl.setAlignment(Qt.AlignCenter)
        self._btp_in_lbl.setVisible(False)
        self._batch_thumb_in = QLabel(); self._batch_thumb_in.setFixedSize(120, 68)
        self._batch_thumb_in.setAlignment(Qt.AlignCenter); self._batch_thumb_in.setStyleSheet(_btp_thumb_style)
        _btp_in_col.addWidget(self._btp_in_lbl); _btp_in_col.addWidget(self._batch_thumb_in)

        _btp_out_col = QVBoxLayout(); _btp_out_col.setSpacing(1)
        self._btp_out_lbl = QLabel("LAST FRAME (OUT) ◀")
        self._btp_out_lbl.setStyleSheet(_btp_lbl_style); self._btp_out_lbl.setAlignment(Qt.AlignCenter)
        self._btp_out_lbl.setVisible(False)
        self._batch_thumb_out = QLabel(); self._batch_thumb_out.setFixedSize(120, 68)
        self._batch_thumb_out.setAlignment(Qt.AlignCenter); self._batch_thumb_out.setStyleSheet(_btp_thumb_style)
        _btp_out_col.addWidget(self._btp_out_lbl); _btp_out_col.addWidget(self._batch_thumb_out)

        _btp_l.addStretch(1)
        _btp_l.addLayout(_btp_in_col)
        _btp_l.addLayout(_btp_out_col)
        _btp_l.addStretch(1)
        bl.addWidget(self._batch_trim_preview)
        
        # Table - 11 columns to match v2.7 + Trim. ReorderableTable enables full-row DnD.
        self.table = ReorderableTable(0, 11)
        self.table.setHorizontalHeaderLabels(["#", "Status", "Source File", "Format", "Target MB", "Orig Res", "Tgt Res", "Orig FPS", "Tgt FPS", "Mode", "Trim"])
        self.table.setColumnWidth(0, 28)   # #
        self.table.setColumnWidth(1, 45)   # Status
        self.table.setColumnWidth(2, 200)  # Filename (stretch below absorbs extra)
        self.table.setColumnWidth(3, 55)   # Format
        self.table.setColumnWidth(4, 75)   # Target MB
        self.table.setColumnWidth(5, 85)   # Orig Res
        self.table.setColumnWidth(6, 85)   # Tgt Res
        self.table.setColumnWidth(7, 60)   # Orig FPS
        self.table.setColumnWidth(8, 60)   # Tgt FPS
        self.table.setColumnWidth(9, 55)   # Mode
        self.table.setColumnWidth(10, 80)  # Trim
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # READ ONLY
        # "Source File" (col 2) stretches to absorb any extra horizontal
        # space — the rest of the columns are data-tight and don't benefit
        # from extra width, but filenames are typically truncated so giving
        # them the slack lets the user read longer paths at a glance.
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        # Double-click on a finished (✅) row opens the resulting GIF/WebP with
        # the OS default app. Rows in any other status are ignored.
        self.table.cellDoubleClicked.connect(self._on_table_double_click)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            f"QTableWidget {{ alternate-background-color: #0e0e0e; gridline-color: #1a1a1a; "
            f"selection-background-color: {COLOR_SELECT}; selection-color: {COLOR_TEXT_BRIGHT}; }}"
            f"QTableWidget::item:selected {{ background-color: {COLOR_SELECT}; color: {COLOR_TEXT_BRIGHT}; }}"
            f"QTableWidget::item:selected:!active {{ background-color: {COLOR_SELECT}; color: {COLOR_TEXT_BRIGHT}; }}"
            f"QTableWidget::item:selected:!focus {{ background-color: {COLOR_SELECT}; color: {COLOR_TEXT_BRIGHT}; }}"
        )
        
        self.table.setColumnHidden(0, True) # Hide redundant # internal column

        bl.addWidget(self.table, 1)  # Stretch to fill
        
        # --- Batch Toolbar ---
        toolbar_style = "font-size: 11px; padding: 4px 10px;"
        
        b_row1 = QHBoxLayout(); b_row1.setSpacing(5)
        # Add Files (prominent)
        self.btn_b_add = QPushButton("➕ Add Files"); self.btn_b_add.setToolTip("Add video files to queue")
        self.btn_b_add.setStyleSheet(f"background: {COLOR_ACCENT}; color: white; font-weight: bold; {toolbar_style}")
        b_row1.addWidget(self.btn_b_add)
        
        # Save Settings to Selected Tasks
        self.up_btn = QPushButton("💾 Apply to selection")
        self.up_btn.setToolTip("Apply current right-panel settings to selected rows")
        self.up_btn.setStyleSheet(f"background: {COLOR_SUCCESS}; color: white; font-weight: bold; {toolbar_style}")
        b_row1.addWidget(self.up_btn)

        # Recover Settings from Selected Task
        self.btn_b_recover = QPushButton("📥 Recover settings")
        self.btn_b_recover.setToolTip("Load the selected task's settings into the right panel")
        self.btn_b_recover.setStyleSheet(f"background: #3a3a1a; color: {COLOR_WARNING}; font-weight: bold; {toolbar_style}")
        b_row1.addWidget(self.btn_b_recover)
        
        # Duplicate Selected — clones each selected task with its current
        # vals (format/mode/trim/etc) so the user can render the same
        # source with multiple settings (e.g. one GIF and one WebP, or
        # several quality targets) without re-adding the file.
        self.btn_b_dup = QPushButton("📑 Duplicate")
        self.btn_b_dup.setToolTip("Duplicate selected tasks with their current settings (Ctrl+D)")
        self.btn_b_dup.setShortcut("Ctrl+D")
        self.btn_b_dup.setStyleSheet(f"background: #2a4a6a; color: white; {toolbar_style}")
        b_row1.addWidget(self.btn_b_dup)

        # Remove Selected
        self.btn_b_rem = QPushButton("❌ Remove"); self.btn_b_rem.setToolTip("Remove selected tasks from queue")
        self.btn_b_rem.setStyleSheet(f"background: {COLOR_DANGER}; color: white; {toolbar_style}")
        b_row1.addWidget(self.btn_b_rem)
        b_row1.addStretch()

        # Reset Status / Clear
        self.btn_b_rst = QPushButton("Reset Status"); self.btn_b_rst.setToolTip("Reset status of selected tasks to Waiting")
        self.btn_b_rst.setStyleSheet(f"background: #2a2a2a; color: #aaa; {toolbar_style}")
        self.btn_b_clr = QPushButton("🧹 Clear Queue"); self.btn_b_clr.setToolTip("Remove ALL tasks from queue")
        self.btn_b_clr.setStyleSheet(f"background: #2a2a2a; color: #666; {toolbar_style}")
        b_row1.addWidget(self.btn_b_rst); b_row1.addWidget(self.btn_b_clr)
        bl.addLayout(b_row1)
        
        b_row2 = QHBoxLayout(); b_row2.setSpacing(5)
        # Selection buttons
        self.btn_b_sel_all = QPushButton("Select All"); self.btn_b_sel_all.setToolTip("Select all tasks (Ctrl+A)")
        self.btn_b_sel_inv = QPushButton("Invert Sel"); self.btn_b_sel_inv.setToolTip("Invert current selection")
        for btn in [self.btn_b_sel_all, self.btn_b_sel_inv]:
            btn.setStyleSheet(f"background: #2a2a2a; color: {COLOR_WARNING}; {toolbar_style}")
        b_row2.addWidget(self.btn_b_sel_all); b_row2.addWidget(self.btn_b_sel_inv)
        
        # Separator
        sep1 = QFrame(); sep1.setFrameShape(QFrame.VLine); sep1.setStyleSheet("color: #333;")
        b_row2.addWidget(sep1)
        
        # Movement buttons
        self.btn_b_up = QPushButton("▲ Up"); self.btn_b_up.setToolTip("Move selected tasks up")
        self.btn_b_dn = QPushButton("▼ Down"); self.btn_b_dn.setToolTip("Move selected tasks down")
        for btn in [self.btn_b_up, self.btn_b_dn]:
            btn.setStyleSheet(f"background: #2a2a2a; color: #ccc; {toolbar_style}")
        b_row2.addWidget(self.btn_b_up); b_row2.addWidget(self.btn_b_dn)
        b_row2.addStretch()
        bl.addLayout(b_row2)
        self.stack.addWidget(self.batch)
        
        # --- Footer: Output Destination (Global) ---
        footer = QFrame()
        footer.setObjectName("footer_out")
        footer.setStyleSheet(
            f"QFrame#footer_out {{ background: #111a11; "
            f"border-top: 2px solid {COLOR_SUCCESS}; }}"
        )
        fl = QVBoxLayout(footer)
        fl.setContentsMargins(10, 4, 10, 4)
        fl.setSpacing(1)

        top_footer = QHBoxLayout()
        top_footer.setSpacing(8)
        self.lbl_bout = QLabel("OUTPUT DESTINATION:")
        self.lbl_bout.setStyleSheet(
            f"color: {COLOR_SUCCESS}; font-weight: bold; font-size: 10px;"
        )
        self.chk_bout = QCheckBox("Use Source Folder")
        self.chk_bout.setChecked(True)
        self.chk_bout.setToolTip("When checked, output files are saved next to the source video.\nUncheck to choose a custom output folder or filename.")
        self.chk_bout.setStyleSheet(
            f"QCheckBox {{ color: {COLOR_ACCENT}; font-weight: bold; font-size: 10px; }}"
            f"QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 2px; border: 1px solid #aaa; }}"
            f"QCheckBox::indicator:checked {{ background-color: {COLOR_ACCENT}; border: 1px solid {COLOR_ACCENT}; }}"
            f"QCheckBox::indicator:unchecked {{ background-color: #333; }}"
        )
        self.txt_bout = QLineEdit()
        self.txt_bout.setPlaceholderText("Select output folder (batch) or file (single)...")
        self.txt_bout.setEnabled(False)
        self.txt_bout.setStyleSheet("padding: 3px; font-size: 10px;")
        self.txt_bout.setToolTip(
            "Single mode: pick an exact output file (you can rename it).\n"
            "Batch mode: pick a folder; each task auto-derives its filename from its source."
        )
        self.btn_bout = QPushButton("📂 Change...")
        self.btn_bout.setToolTip("Browse for a custom output folder (batch) or file (single).")
        self.btn_bout.setStyleSheet("padding: 3px 8px; font-size: 10px;")
        self.btn_bout.setEnabled(False)
        top_footer.addWidget(self.lbl_bout)
        top_footer.addWidget(self.chk_bout)
        top_footer.addWidget(self.txt_bout, 1)
        top_footer.addWidget(self.btn_bout)
        fl.addLayout(top_footer)

        self._lbl_resolved_path = QLabel("")
        self._lbl_resolved_path.setStyleSheet(
            "color: #556655; font-size: 10px; font-style: italic; padding: 0 0 0 2px;"
        )
        fl.addWidget(self._lbl_resolved_path)
        
        # --- Add layouts to Main Vertical ---
        
        # Content Row (Stack + Settings + Log).
        # Settings panel has a FIXED width (no stretch) so it never grows
        # when the window widens for batch mode — all extra width goes to
        # the stack (drop zone / batch table) via its stretch=1 factor.
        # This keeps the settings panel identical in both modes while the
        # batch table gets maximum room for its 11 columns.
        self.settings = SettingsPanel()
        content_h.addWidget(self.settings, 0)
        
        # Log — independent floating window
        self._console_win = QDialog(self)
        self._console_win.setWindowTitle("System Console — MakeAGIF/WEBP")
        self._console_win.resize(520, 400)
        self._console_win.setStyleSheet(f"background: {COLOR_BG};")
        cwl = QVBoxLayout(self._console_win)
        cwl.setContentsMargins(6, 6, 6, 6)
        cwl.setSpacing(4)

        log_tools = QHBoxLayout()
        self.btn_clr_log = QPushButton("Clear"); self.btn_clr_log.setToolTip("Clear all console output.")
        self.btn_cpy_log = QPushButton("Copy All"); self.btn_cpy_log.setToolTip("Copy the full console log to clipboard.")
        for b in [self.btn_clr_log, self.btn_cpy_log]:
            b.setStyleSheet(
                f"padding: 4px 10px; font-size: 10px; font-weight: bold; "
                f"background: #1a1a1a; color: #aaa; border: 1px solid #333; border-radius: 3px;"
            )
        log_tools.addWidget(self.btn_clr_log, 1)
        log_tools.addWidget(self.btn_cpy_log)
        cwl.addLayout(log_tools)

        self.view = QTextEdit(); self.view.setReadOnly(True)
        self.view.setStyleSheet(
            f"background: #0a0a0a; color: {COLOR_SUCCESS}; font-family: Consolas, 'Menlo', monospace; "
            f"font-size: 10px; border: 1px solid {COLOR_BORDER}; border-radius: 3px;"
        )
        cwl.addWidget(self.view)
        
        main_v.addLayout(content_h, 1) # Content takes available space

        # ── Iter Chart Window (floating, opens on demand) ──────────────────
        self._app_settings = load_app_settings()
        self._iter_chart_win = QDialog(self)
        self._iter_chart_win.setWindowTitle("📊 Iteration Chart — MakeAGIF/WEBP")
        self._iter_chart_win.resize(680, 320)
        self._iter_chart_win.setStyleSheet(f"background: {COLOR_BG};")
        icw_l = QVBoxLayout(self._iter_chart_win)
        icw_l.setContentsMargins(8, 8, 8, 8)
        self.iter_chart = IterChartWidget()
        icw_l.addWidget(self.iter_chart)

        # Toggle button stays in the main layout as a thin bar
        self.iter_drawer = QFrame()
        self.iter_drawer.setObjectName("iter_drawer")
        self.iter_drawer.setStyleSheet(
            f"QFrame#iter_drawer {{ background: {COLOR_PANEL}; "
            f"border: 1px solid {COLOR_BORDER}; border-radius: 4px; }}"
        )
        drawer_l = QHBoxLayout(self.iter_drawer)
        drawer_l.setContentsMargins(8, 3, 8, 3)
        self.btn_chart_toggle = QPushButton("📊 Iteration Chart  ▶")
        self.btn_chart_toggle.setStyleSheet(
            "QPushButton { background: transparent; color: #888; font-size: 10px; "
            "font-weight: bold; padding: 2px 6px; border: 0; text-align: left; } "
            "QPushButton:hover { color: #ddd; }"
        )
        self.btn_chart_toggle.setFocusPolicy(Qt.NoFocus)
        self.btn_chart_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_chart_toggle.setToolTip(
            "Open the iterative search trajectory chart in a separate window."
        )
        self.btn_chart_toggle.clicked.connect(self._toggle_iter_chart)
        drawer_l.addWidget(self.btn_chart_toggle)
        drawer_l.addStretch(1)
        main_v.addWidget(self.iter_drawer)
        self._iter_chart_visible = False

        main_v.addWidget(footer) # Footer fixed at bottom
        
        self.setAcceptDrops(True)
        self.worker = None
        self._import_worker = None
        self.queue_data = [] # List of Tasks
        self._batch_thumb_loader = _AsyncThumbLoader(self)  # PR1: async batch thumbs
        self.current_single_task = None
        
        # Connections
        self.settings.batch_en.toggled.connect(self.toggle_mode)
        self.settings.btn_open_trimmer.clicked.connect(self.open_trimmer)
        # Alpha-tester button (FORMAT group, only visible when "Transparency"
        # is checked). Opens the v2.7-era HTML transparency inspector,
        # auto-loaded with the most recently rendered output if available.
        self.settings.b_at.clicked.connect(self.open_alpha_tester)
        self.settings.c_btn.clicked.connect(self.toggle_log)
        self.settings.about_btn.clicked.connect(self.show_about)
        self.table.itemSelectionChanged.connect(self.on_table_sel)
        self.up_btn.clicked.connect(self.apply_settings_to_sel)
        self.settings.go_btn.clicked.connect(self.start_processing)
        
        # Live Dimension Updates
        self.settings.res_box.opt.currentIndexChanged.connect(self.update_live_dims)
        self.settings.res_box.s_perc.valueChanged.connect(self.update_live_dims)
        self.settings.res_box.s_w.valueChanged.connect(self.update_live_dims)
        self.settings.res_box.s_h.valueChanged.connect(self.update_live_dims)
        # Live output-plan summary in the drop zone (format, mode, target).
        # Dimension signals already flow through update_live_dims which calls
        # _refresh_output_plan at the end; these cover the non-dimension
        # settings that also affect the plan text.
        self.settings.fmt_g.buttonClicked.connect(lambda: self._refresh_output_plan())
        self.settings.tabs.currentChanged.connect(lambda: self._refresh_output_plan())
        self.settings.bg_prio.buttonClicked.connect(lambda: self._refresh_output_plan())
        self.settings.mb_sp.valueChanged.connect(lambda: self._refresh_output_plan())
        self.settings.low_sp.valueChanged.connect(lambda: self._refresh_output_plan())
        self.settings.up_sp.valueChanged.connect(lambda: self._refresh_output_plan())
        self.settings.fps_sp.valueChanged.connect(lambda: self._refresh_output_plan())
        self.settings.qual_sp.valueChanged.connect(lambda: self._refresh_output_plan())
        self.settings.chk_alpha.toggled.connect(lambda: self._refresh_output_plan())
        self.settings.chk_fast.toggled.connect(lambda: self._refresh_output_plan())
        self.settings.chk_loss.toggled.connect(lambda: self._refresh_output_plan())
        # Trim-frame previews — refresh when the user manually edits In/Out.
        self.settings.t_start.editingFinished.connect(self._refresh_trim_previews)
        self.settings.t_end.editingFinished.connect(self._refresh_trim_previews)
        
        self.drop_zone.btn_browse.clicked.connect(self.browse_single)
        self.drop_zone.btn_change.clicked.connect(self.browse_single)
        self.drop_zone.btn_open_out.clicked.connect(self._open_single_output_folder)
        self.drop_zone.btn_reset_status.clicked.connect(self._reset_single_status)
        self.drop_zone.btn_reiterate.clicked.connect(self._reiterate_single)
        self.drop_zone.file_dropped.connect(self._start_single_import)
        self.btn_clr_log.clicked.connect(self.view.clear)
        self.btn_cpy_log.clicked.connect(self.view.selectAll) # Hacky copy
        self.btn_cpy_log.clicked.connect(self.view.copy)
        
        # Batch panel connections
        self._connect_batch_buttons()

        # Auto-fit window height to the natural settings panel content
        # AFTER Qt has had a chance to lay everything out. Done with a
        # zero-delay singleshot so it runs once on the next event-loop
        # iteration, when sizeHint() reports real values instead of the
        # collapsed pre-show defaults.
        QTimer.singleShot(0, self._fit_to_settings)

    def _fit_to_settings(self):
        """Resize the window so the entire settings panel is visible without
        a vertical scrollbar.

        The right column is half scroll-area (the configurable groups) and
        half always-visible strip (BATCH MODE checkbox, status, MAKE IT,
        cache controls, console/purge). The scroll area's own sizeHint
        collapses to its minimum, so we ask the inner ``content_widget``
        directly and then add the bottom strip + window-level overhead.

        Clamped to the screen's available geometry minus ~40 px so the
        title bar never gets pushed off-screen on a 768/900-class panel."""
        s = self.settings
        # Inside the scroll: PRESET row + FORMAT + DIMENSIONS + ENCODING +
        # TRIM groups, plus inter-item spacings. Use the viewport's idea
        # of how tall its child wants to be — that's the unscrolled total.
        inner = max(
            s.content_widget.sizeHint().height(),
            s.content_widget.minimumSizeHint().height(),
        )
        # Below the scroll, in root_l, sit several widgets with ~6 px
        # spacing: the BATCH toggle, progress bar, status label, MAKE IT
        # button, the FRAME CACHE groupbox (1 row of buttons inside) and
        # the diagnostic strip (System Console link). We sum sizeHint
        # heights so any future widget added here gets accounted for
        # automatically. The groupbox adds ~24 px of title + padding on
        # top of its single inner row.
        bottom_strip = (
            s.batch_en.sizeHint().height()
            + s.pbar.sizeHint().height()
            + s.lbl_status.sizeHint().height()
            + s.go_btn.sizeHint().height()
            + s.btn_cache_set.sizeHint().height()  # cache row 1 (SET/OPEN/RESET)
            + s.btn_purge_cache.sizeHint().height()  # cache row 2 (PURGE)
            + 24  # FRAME CACHE groupbox title + vertical margins
            + s.c_btn.sizeHint().height()
            + 6 * 7  # rough inter-row spacing (one extra row vs. before)
        )
        settings_natural = inner + bottom_strip + 16  # panel padding fudge

        # Window-level overhead: main_v outer margins + spacing between the
        # top-level rows + footer + iter chart toggle bar + title bar.
        chrome = (
            20   # main_v contentsMargins (10 top + 10 bottom)
            + 10 # main_v.spacing across content rows
            + 38 # footer "OUTPUT DESTINATION" bar
            + 28 # iter drawer toggle bar
        )

        needed = settings_natural + chrome

        # Clamp to the screen so we never push chrome off the top.
        screen = self.screen() or QApplication.primaryScreen()
        avail_h = screen.availableGeometry().height() if screen else 1000
        target_h = max(self.minimumHeight(), min(needed, avail_h - 40))

        self.resize(self.width(), int(target_h))
        self._center_on_screen()

    def _apply_window_icon(self):
        """Resolve and apply the window/taskbar icon.

        We probe a small list of likely paths so the same code works
        in three contexts:
          1. Running from source     -> ``MakeAGIF.ico`` next to the .py
          2. PyInstaller bundle      -> ``sys._MEIPASS`` extraction dir
          3. PyInstaller exe icon    -> next to the .exe in ``dist/``
        The ICO is multi-resolution (16/32/48/64/128/256), so Qt picks
        the right size automatically for the title bar, taskbar, and
        Alt+Tab switcher."""
        candidates = []
        # Path 1: alongside this script (dev mode).
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            candidates.append(os.path.join(here, "MakeAGIF.ico"))
        except Exception:
            pass
        # Path 2: PyInstaller's temp extraction dir (one-file builds).
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, "MakeAGIF.ico"))
        # Path 3: alongside the running executable (one-folder / dist).
        try:
            exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            candidates.append(os.path.join(exe_dir, "MakeAGIF.ico"))
        except Exception:
            pass
        for p in candidates:
            if p and os.path.isfile(p):
                ic = QIcon(p)
                if not ic.isNull():
                    self.setWindowIcon(ic)
                    # Also set application-level icon so the taskbar
                    # and Alt+Tab pick it up reliably on Windows.
                    QApplication.instance().setWindowIcon(ic)
                    return

    def _center_on_screen(self):
        """Center the main window on the user's current screen.
        
        We use ``availableGeometry`` (excludes taskbars/docks) and
        ``frameGeometry`` (includes window chrome) so the *visual* center
        of the window matches the visual center of the work area on any
        resolution. We resolve the screen with ``self.screen()`` first
        (the screen the window currently lives on) and fall back to the
        primary screen if Qt hasn't bound it yet — that fallback matters
        on the very first call right after construction."""
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return
        avail = screen.availableGeometry()
        fr = self.frameGeometry()
        fr.moveCenter(avail.center())
        # Clamp to the work area so we never spawn partially off-screen
        # (e.g. when the window is wider than the active monitor for
        # whatever reason).
        x = max(avail.left(), fr.left())
        y = max(avail.top(), fr.top())
        self.move(x, y)

    def show_about(self):
        """Open the About / Credits dialog.

        We use a custom QDialog (instead of QMessageBox.about) because
        we want clickable hyperlinks, an icon header, and a scrollable
        license list. Everything sits in a dark-themed QTextBrowser
        with ``openExternalLinks=True`` so clicking a project name in
        the credits launches the user's browser to the upstream site.
        """
        from PySide6.QtWidgets import QDialog, QTextBrowser, QPushButton
        dlg = QDialog(self)
        dlg.setWindowTitle(f"About — {APP_TITLE}")
        dlg.setMinimumSize(560, 540)
        dlg.setStyleSheet(f"""
            QDialog {{ background: {COLOR_BG}; }}
            QLabel  {{ color: {COLOR_TEXT}; }}
            QPushButton {{
                background: {COLOR_ACCENT}; color: white; border: none;
                border-radius: 4px; padding: 6px 18px; font-weight: bold;
            }}
            QPushButton:hover {{ background: #1f8ee0; }}
            QTextBrowser {{
                background: #0a1014; color: #d0d4d8;
                border: 1px solid #1a2230; border-radius: 4px;
                padding: 10px; font-size: 12px;
            }}
            QTextBrowser a {{ color: {COLOR_ACCENT}; text-decoration: none; }}
        """)
        v = QVBoxLayout(dlg); v.setContentsMargins(16, 16, 16, 12); v.setSpacing(10)

        # Header with app icon (if available) + title block.
        head = QHBoxLayout(); head.setSpacing(12)
        try:
            ic = self.windowIcon()
            if ic and not ic.isNull():
                lbl_ic = QLabel()
                pm = ic.pixmap(64, 64)
                lbl_ic.setPixmap(pm)
                head.addWidget(lbl_ic)
        except Exception:
            pass
        title_box = QVBoxLayout(); title_box.setSpacing(2)
        # Title is the bare app name — version + author live on their
        # own lines so the header reads cleanly at a glance.
        lbl_t = QLabel("MakeAGIF / WEBP")
        lbl_t.setStyleSheet(f"color: white; font-size: 18px; font-weight: bold;")
        # OS label is derived at runtime so each build self-identifies (the macOS
        # .app no longer says "Windows build").
        _os_label = "macOS" if sys.platform == "darwin" else ("Windows" if os.name == "nt" else "Linux")
        lbl_v = QLabel(f"{SCRIPT_VERSION}  ·  {_os_label} build")
        lbl_v.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 11px; font-weight: bold;")
        lbl_a = QLabel(f"Created by {APP_AUTHOR}")
        lbl_a.setStyleSheet(f"color: {COLOR_TEXT_BRIGHT}; font-size: 12px;")
        lbl_d = QLabel("Video → animated GIF / WebP converter with iterative size optimization.")
        lbl_d.setStyleSheet(f"color: {COLOR_TEXT}; font-size: 11px;")
        lbl_d.setWordWrap(True)
        title_box.addWidget(lbl_t)
        title_box.addWidget(lbl_a)
        title_box.addWidget(lbl_v)
        title_box.addWidget(lbl_d)
        head.addLayout(title_box, 1)
        v.addLayout(head)

        # Credits / licenses block. We acknowledge:
        #   - FFmpeg (LGPL/GPL): video probing, scene detection, encoding pipeline
        #   - gifski (AGPL):     high-quality GIF encoder (all GIFs)
        #   - ImageMagick (Apache 2): WebP for alpha on Windows
        #   - libwebp / img2webp (BSD): self-contained WebP encoder on macOS
        #   - Qt / PySide6 (LGPL): the entire UI / multimedia layer
        #   - Python (PSF):      runtime
        #   - PyInstaller (GPL+exception): packaging
        # The links below open the upstream project home pages on click.
        body = QTextBrowser()
        body.setOpenExternalLinks(True)
        body.setHtml(f"""
        <h3 style="color:#fff; margin: 0 0 8px 0;">Credits & open-source acknowledgements</h3>
        <p>This tool is built on, and ships with, several outstanding open-source
        projects. Huge thanks to all the maintainers and contributors.</p>

        <h4 style="color:#fff; margin: 12px 0 4px 0;">Bundled binaries</h4>
        <ul style="margin: 0; padding-left: 18px;">
          <li><b><a href="https://ffmpeg.org">FFmpeg</a></b> &amp;
              <b><a href="https://ffmpeg.org">FFprobe</a></b> — the video
              probing, scene-cut detection and encoding backbone.
              Licensed under LGPLv2.1+ / GPLv2+.<br>
              Windows builds courtesy of
              <a href="https://www.gyan.dev/ffmpeg/builds/">gyan.dev</a>;
              macOS (arm64) via <a href="https://brew.sh">Homebrew</a>.</li>
          <li><b><a href="https://gif.ski">gifski</a></b> by Kornel Lesiński —
              the high-quality GIF encoder used in the GIF pipeline.
              Licensed under AGPLv3.</li>
          <li><b><a href="https://imagemagick.org">ImageMagick</a></b> —
              WebP assembler for transparency on Windows.
              Licensed under the Apache 2.0 / ImageMagick license.</li>
          <li><b><a href="https://developers.google.com/speed/webp">libwebp</a></b>
              (img2webp) by Google — the self-contained WebP encoder used on
              macOS. BSD-3-Clause license.</li>
        </ul>

        <h4 style="color:#fff; margin: 12px 0 4px 0;">Runtime / framework</h4>
        <ul style="margin: 0; padding-left: 18px;">
          <li><b><a href="https://www.qt.io">Qt</a></b> via
              <b><a href="https://wiki.qt.io/Qt_for_Python">PySide6</a></b> —
              entire UI, multimedia preview, drag &amp; drop. LGPLv3.</li>
          <li><b><a href="https://www.python.org">Python</a></b> — runtime.
              PSF License.</li>
          <li><b><a href="https://www.pyinstaller.org">PyInstaller</a></b> —
              produces the standalone app (Windows .exe / macOS .app).
              GPL with bootloader exception.</li>
          <li><b><a href="https://upx.github.io">UPX</a></b> — final-stage
              executable compression (Windows). GPLv2+ with linking exception.</li>
        </ul>

        <h4 style="color:#fff; margin: 12px 0 4px 0;">Algorithms</h4>
        <ul style="margin: 0; padding-left: 18px;">
          <li>Iterative size search: in-house bisection with live-secant
              interpolation, persistent knowledge cache and warm-start hints.</li>
          <li>Scene-cut detection: FFmpeg <code>select=gt(scene,T)</code>
              filter, results cached on disk by content hash.</li>
          <li>Frame-perfect trimming: NLE-style timecode round-trip with
              symmetric parsing/formatting and frame quantization.</li>
        </ul>

        <p style="margin-top: 12px; color: #888; font-size: 10px;">
        This tool is provided as-is, with no warranty. The bundled binaries
        retain their original licenses; see each project's site for full terms.<br>
        Application code, UI design and iterative-search engine
        © <b>{APP_AUTHOR}</b>.
        </p>
        """)
        v.addWidget(body, 1)

        # Close button.
        h_btn = QHBoxLayout(); h_btn.addStretch()
        b_close = QPushButton("Close")
        b_close.clicked.connect(dlg.accept)
        h_btn.addWidget(b_close)
        v.addLayout(h_btn)

        dlg.exec()

    def open_alpha_tester(self):
        """Launch the v2.7-style transparency inspector in the default
        browser. Tries to pre-load the most recently rendered output so
        the user doesn't have to hunt for it manually:

          1. Single mode: use ``current_single_task.output_path`` if the
             task succeeded.
          2. Batch mode: use the SELECTED task's ``output_path`` if it
             succeeded; if multiple are selected, the first completed one.
          3. Otherwise: open in manual mode (browser shows upload box).

        Best-effort: a missing/invalid file just opens the tester empty
        so the user can drag in a file from disk."""
        candidate = None
        try:
            if self.settings.batch_en.isChecked():
                # Batch: try the current selection, fall back to the most
                # recent successful task in the queue.
                sel_rows = sorted(set(i.row() for i in self.table.selectedItems()))
                pool = [self.queue_data[r] for r in sel_rows if 0 <= r < len(self.queue_data)]
                if not pool:
                    pool = list(self.queue_data)
                for t in pool:
                    op = getattr(t, "output_path", None)
                    if t.status == "✅" and op and os.path.exists(op):
                        candidate = op
                        break
            else:
                t = self.current_single_task
                op = getattr(t, "output_path", None) if t else None
                if op and os.path.exists(op):
                    candidate = op
        except Exception:
            candidate = None

        ok = open_alpha_tester(candidate)
        if not ok:
            QMessageBox.warning(
                self, "Alpha Tester",
                "Could not open the transparency tester. Check that your "
                "default browser is set up correctly."
            )

    def open_trimmer(self):
        task = self.current_single_task if not self.settings.batch_en.isChecked() else None
        sel_row = None
        if not task and self.settings.batch_en.isChecked():
            sel_rows = sorted(set(i.row() for i in self.table.selectedItems()))
            if len(sel_rows) == 1:
                task = self.queue_data[sel_rows[0]]
                sel_row = sel_rows[0]
                
        if not task:
            QMessageBox.warning(self, "No Task", "Please select exactly one task to Trim.")
            return

        task_fps = float(task.specs.get("fps", 25) or 25)
        # Recover existing trim points to restore them in the dialog. Accepts both
        # raw seconds ('5.234') and HH:MM:SS strings, since the user can type either
        # format in the manual field.  Pass fps so HH:MM:SS:FF round-trips exactly.
        existing_in = parse_trim_to_seconds(task.vals.get("trim_start"), default=0.0, fps=task_fps)
        raw_end = task.vals.get("trim_end")
        existing_out = parse_trim_to_seconds(raw_end, default=None, fps=task_fps) if raw_end else None
            
        dlg = TrimDialog(task, self, initial_in_sec=existing_in, initial_out_sec=existing_out)
        if dlg.exec() == QDialog.Accepted:
            # Integer frame indices → storage TC (avoids 23.976 float round-trip drift).
            in_fi = source_frame_index_from_sec(
                dlg.in_sec, task_fps, dlg._max_frame_idx
            )
            out_incl_fi = dlg._out_last_included_frame_index()
            in_sec = sec_from_source_frame_index(in_fi, task_fps)
            out_sec = sec_from_source_frame_index(out_incl_fi + 1, task_fps)
            clip_end = getattr(dlg, "_default_out_sec", dlg.duration_sec)
            if in_sec <= 0.001 and out_sec >= clip_end - (1.5 / max(task_fps, 1e-9)):
                start_storage, end_storage = "00:00:00", ""
                start_display, end_display = "00:00:00:00", ""
            else:
                start_storage = format_seconds_as_tc(in_sec) or "00:00:00"
                end_storage = format_seconds_as_tc(out_sec) if out_sec < dlg.duration_sec else ""
                start_display = format_frame_index_as_tc(in_fi, task_fps)
                if out_sec < dlg.duration_sec:
                    end_display = format_frame_index_as_tc(out_incl_fi, task_fps)
                else:
                    end_display = ""
            self.settings.t_start.setText(start_display)
            self.settings.t_end.setText(end_display)
            if task and hasattr(task, 'vals'):
                task.vals["trim_start"] = start_storage
                task.vals["trim_end"]   = end_storage

            if sel_row is not None:
                self.update_row(sel_row)

            self._refresh_trim_previews()

    def browse_single(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video Files (*.mp4 *.mov *.avi *.mkv *.webm)")
        if f:
            self._start_single_import(f)
        
    def _connect_batch_buttons(self):
        """Called from __init__ to connect batch-related signals."""
        self.chk_bout.toggled.connect(lambda c: (self.txt_bout.setEnabled(not c), self.btn_bout.setEnabled(not c), self._update_resolved_path()))
        self.txt_bout.textChanged.connect(lambda: self._update_resolved_path())
        self.btn_bout.clicked.connect(self.browse_batch_out)
        self.btn_b_add.clicked.connect(self.batch_add_files)
        self.btn_b_recover.clicked.connect(self.batch_recover_settings)
        self.btn_b_dup.clicked.connect(self.batch_duplicate_sel)
        self.btn_b_rem.clicked.connect(self.batch_remove_sel)
        self.btn_b_rst.clicked.connect(self.batch_reset_sel)
        self.btn_b_clr.clicked.connect(self.batch_clear)
        self.btn_b_sel_all.clicked.connect(self.table.selectAll)
        self.btn_b_sel_inv.clicked.connect(self.invert_selection)
        self.btn_b_up.clicked.connect(lambda: self.move_rows(-1))
        self.btn_b_dn.clicked.connect(lambda: self.move_rows(1))
        self.table.rows_reordered.connect(self.on_rows_dropped)

    def _update_resolved_path(self):
        """Show the resolved output path in the footer so the user always
        knows where files will land."""
        if self.chk_bout.isChecked():
            task = self.current_single_task
            if task:
                folder = os.path.dirname(task.path)
                self._lbl_resolved_path.setText(f"→  {folder}")
            else:
                self._lbl_resolved_path.setText("→  Same folder as the source video")
        else:
            custom = self.txt_bout.text().strip()
            if custom:
                self._lbl_resolved_path.setText(f"→  {custom}")
            else:
                self._lbl_resolved_path.setText("")

    def closeEvent(self, event):
        self.settings.save_session()
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        event.accept()

    def _select_rows(self, rows, focus_row=None):
        """Re-select the given row indices using the selection model directly.
        IMPORTANT: we cannot call `setCurrentCell` while the table is in
        ExtendedSelection mode after a multi-row programmatic select — Qt
        treats `setCurrentCell` as a `ClearAndSelect` command in that mode and
        wipes the multi-selection down to the current row. Instead we drive
        selection via QItemSelectionModel and use NoUpdate when moving the
        current index so the multi-row highlight survives."""
        sel_model = self.table.selectionModel()
        model = self.table.model()
        if not rows or model is None:
            self.table.clearSelection()
            return

        cols = self.table.columnCount()
        valid_rows = []
        selection = QItemSelection()
        for r in rows:
            if 0 <= r < self.table.rowCount():
                top = model.index(r, 0)
                bot = model.index(r, max(0, cols - 1))
                selection.select(top, bot)
                valid_rows.append(r)

        if not valid_rows:
            self.table.clearSelection()
            return

        sel_model.select(
            selection,
            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
        )

        target = focus_row if focus_row is not None and 0 <= focus_row < self.table.rowCount() else valid_rows[0]
        sel_model.setCurrentIndex(model.index(target, 1), QItemSelectionModel.NoUpdate)
        anchor = self.table.item(target, 1) or self.table.item(target, 2)
        if anchor: self.table.scrollToItem(anchor)
        self.table.viewport().update()

    def invert_selection(self):
        """Invert selection using the unified row-selection helper."""
        total_rows = self.table.rowCount()
        if total_rows == 0: return
        current_sel = set(i.row() for i in self.table.selectedItems())
        inverted = [r for r in range(total_rows) if r not in current_sel]
        self._select_rows(inverted)
    
    def on_rows_dropped(self, source_rows, drop_row):
        """Handle drag-and-drop row reordering from anywhere in the table.
        Reorders queue_data, refreshes the table, and re-selects the moved rows."""
        if not source_rows: return
        items = [self.queue_data[r] for r in source_rows]
        adjusted_drop = drop_row - sum(1 for r in source_rows if r < drop_row)
        adjusted_drop = max(0, min(adjusted_drop, len(self.queue_data) - len(source_rows)))

        self.table.blockSignals(True)
        for r in reversed(source_rows):
            del self.queue_data[r]
        for i, t in enumerate(items):
            self.queue_data.insert(adjusted_drop + i, t)
        for i in range(len(self.queue_data)):
            self.update_row(i)
        self.table.blockSignals(False)

        new_sel = list(range(adjusted_drop, adjusted_drop + len(items)))
        self._select_rows(new_sel, focus_row=adjusted_drop)

    def batch_recover_settings(self):
        """Load the first selected task's settings into the right panel."""
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows:
            return
        task = self.queue_data[rows[0]]
        if hasattr(task, 'vals') and task.vals:
            self.settings.set_vals(task.vals)
            self.lbl_batch_info.setText(
                f"Recovered settings from: {task.filename}"
            )
            self.lbl_batch_info.setStyleSheet(
                f"color: {COLOR_WARNING}; font-style: italic; font-size: 10px; "
                f"padding: 2px 4px; background: #1a1a00; border-radius: 3px;"
            )

    # --- Batch Logic ---
    def browse_batch_out(self):
        # In SINGLE mode, offer a Save-As dialog seeded with <source>_Optimized.<ext>
        # so the user can both pick the destination folder AND tweak the filename
        # in one shot. In BATCH mode this can't be a per-file picker — we keep the
        # folder-only dialog because the queue auto-derives names from each source.
        is_batch = self.settings.batch_en.isChecked()
        if not is_batch and self.current_single_task:
            base = os.path.splitext(os.path.basename(self.current_single_task.path))[0]
            # Read the LIVE radio state, not task.vals — the task vals only get
            # synced on MAKE press, so toggling GIF↔WebP wouldn't reflect here
            # otherwise (the picker would show the stale extension).
            fmt = "WEBP" if self.settings.b_webp.isChecked() else "GIF"
            ext = ".gif" if fmt == "GIF" else ".webp"
            ext_filter = "GIF (*.gif)" if fmt == "GIF" else "WebP (*.webp)"
            # Seed with the existing txt_bout dir if any, else the source's folder.
            cur = self.txt_bout.text().strip()
            seed_dir = cur if (cur and os.path.isdir(cur)) else \
                       (os.path.dirname(cur) if (cur and os.path.isdir(os.path.dirname(cur))) else
                        os.path.dirname(self.current_single_task.path))
            seed_name = f"{base}_Optimized{ext}"
            seed_path = os.path.join(seed_dir, seed_name)
            picked, _ = QFileDialog.getSaveFileName(self, "Save Output As", seed_path, ext_filter)
            if picked:
                # Force the right extension if Qt didn't append it (some platforms).
                pick_base, pick_ext = os.path.splitext(picked)
                if pick_ext.lower() != ext:
                    picked = pick_base + ext
                self.txt_bout.setText(picked)
            return
        # BATCH (or single without a loaded task) → folder picker.
        d = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if d: self.txt_bout.setText(d)
        
    def batch_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Videos", "", "Video Files (*.mp4 *.mov *.mkv *.avi *.webm)")
        if files:
            for f in files:
                self._start_batch_import(f)

    def batch_duplicate_sel(self):
        """Clone selected queue rows in place.

        Each duplicate inherits the source's ``vals`` (format, mode,
        target, prio, fps, qual, dim_*, alpha, trim, etc.) so the user
        can run the same file through several settings without
        re-importing it. We:

        - Insert each clone immediately AFTER its source row, keeping
          source/copy visually adjacent.
        - Reset ``status`` to ⌛ and ``output_path`` to None — even if
          the source already finished, the clone is a fresh task.
        - Skip the expensive ``get_video_specs(path)`` call by reusing
          the source's ``specs`` dict (it's read-only by convention,
          so sharing the reference is safe and dramatically faster
          when duplicating many rows).
        - Deep-copy ``vals`` so editing the clone doesn't bleed back
          into the source's settings.
        - Select the freshly inserted clones so the user can chain
          this with "Apply settings to selection" or open the trimmer.
        """
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows:
            self.lbl_batch_info.setText("ℹ Select at least one task to duplicate.")
            self.lbl_batch_info.setStyleSheet(
                f"color: {COLOR_TEXT}; font-style: italic; font-size: 10px; padding: 2px 4px;"
            )
            return

        # Walk in reverse so each insert at (src_row + 1) doesn't shift
        # the indices we still have to process.
        new_indices = []
        for r in sorted(rows, reverse=True):
            src = self.queue_data[r]
            clone = Task.__new__(Task)
            clone.path = src.path
            clone.filename = src.filename
            clone.specs = src.specs
            clone.status = "⌛"
            clone.output_path = None
            clone.vals = copy.deepcopy(src.vals)

            insert_at = r + 1
            self.queue_data.insert(insert_at, clone)
            self.table.insertRow(insert_at)
            new_indices.append(insert_at)

        # Indices captured during reverse insertion are valid *as inserted*
        # but later inserts shift earlier ones down by 1 each. Easier to
        # just rebuild every row's display from scratch.
        for i in range(len(self.queue_data)):
            self.update_row(i)

        # Recompute the post-shift indices of the new clones: every clone
        # we inserted shifted by the number of clones that landed before
        # it. Since we inserted in reverse, ``new_indices`` is already in
        # descending order; selection via the original positions is now
        # off by the number of later inserts that happened *before* in
        # the reversed loop. Cleanest path is just to map source rows to
        # their final clone positions in forward order.
        final_clone_rows = []
        offset = 0
        for src_row in rows:  # ascending
            offset += 1
            final_clone_rows.append(src_row + offset)
        self._select_rows(final_clone_rows, focus_row=final_clone_rows[0])

        self.update_make_button()
        n = len(rows)
        self.lbl_batch_info.setText(f"📑 Duplicated {n} task(s) — adjust settings on the new rows and run.")
        self.lbl_batch_info.setStyleSheet(
            f"color: {COLOR_SUCCESS}; font-style: italic; font-size: 10px; "
            f"padding: 2px 4px; background: #001a00; border-radius: 3px;"
        )

    def batch_remove_sel(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()), reverse=True)
        if not rows:
            return
        n = len(rows)
        if QMessageBox.question(
            self, "Remove Tasks",
            f"Remove {n} selected task(s) from the queue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        for r in rows:
            self.table.removeRow(r)
            del self.queue_data[r]
        for i in range(len(self.queue_data)): self.update_row(i)
        self.update_make_button()
        self.lbl_batch_info.setText(f"{len(self.queue_data)} task(s) remaining")
            
    def batch_reset_sel(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows:
            return
        n = len(rows)
        if QMessageBox.question(
            self, "Reset Status",
            f"Reset status of {n} selected task(s) back to pending?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        for r in rows:
            self.queue_data[r].status = "⌛"
            self.update_row(r)
        self.update_make_button()
            
    def batch_clear(self):
        if not self.queue_data:
            return
        if QMessageBox.question(
            self, "Clear Queue",
            f"Remove all {len(self.queue_data)} task(s) from the queue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        self.queue_data.clear()
        self.table.setRowCount(0)
        self.update_make_button()
        self.lbl_batch_info.setText("Queue cleared")
        self.lbl_batch_info.setStyleSheet(f"color: #666; font-style: italic; font-size: 10px; padding: 2px 4px; background: {COLOR_BG}; border-radius: 3px;")
        
    def move_rows(self, direction):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows: return
        if direction == -1 and rows[0] == 0: return
        if direction == 1 and rows[-1] == len(self.queue_data) - 1: return

        self.table.blockSignals(True)
        iter_rows = rows if direction == -1 else list(reversed(rows))
        new_sel = []
        for r in iter_rows:
            swap_r = r + direction
            self.queue_data[r], self.queue_data[swap_r] = self.queue_data[swap_r], self.queue_data[r]
            new_sel.append(swap_r)
        for i in range(len(self.queue_data)): self.update_row(i)
        self.table.blockSignals(False)

        self._select_rows(sorted(new_sel), focus_row=new_sel[0])

    def move_rows_extreme(self, direction):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows: return

        self.table.blockSignals(True)
        others = [x for x in range(len(self.queue_data)) if x not in rows]
        new_order = rows + others if direction == -1 else others + rows
        self.queue_data = [self.queue_data[i] for i in new_order]
        for i in range(len(self.queue_data)): self.update_row(i)
        self.table.blockSignals(False)

        start_idx = 0 if direction == -1 else len(others)
        new_sel = list(range(start_idx, start_idx + len(rows)))
        self._select_rows(new_sel, focus_row=new_sel[0])

    def show_context_menu(self, pos):
        menu = QMenu(self)
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows: return
        
        t = self.queue_data[rows[0]]
        
        menu.addAction("📂 Open Source Folder", lambda: open_path_in_os(os.path.dirname(t.path)))
        menu.addAction("📋 Copy Source Path", lambda: QApplication.clipboard().setText(t.path))
        menu.addSeparator()
        
        # Output actions appear only for tasks that finished successfully
        if t.status == "✅" and getattr(t, "output_path", None) and os.path.exists(t.output_path):
            out_path = t.output_path
            menu.addAction("▶ Open Output File", lambda: self._open_output_path(out_path))
            menu.addAction("📂 Open Output Folder", lambda: open_path_in_os(os.path.dirname(out_path)))
            menu.addAction("📋 Copy Output Path", lambda: QApplication.clipboard().setText(out_path))
            menu.addSeparator()
             
        menu.addAction("📥 Recover Settings to Panel", self.batch_recover_settings)
        menu.addSeparator()
        menu.addAction("🔄 Reset Status", self.batch_reset_sel)
        # Duplicate keeps the user in the right-click flow when they
        # want a parallel run of the same source with tweaked settings
        # (e.g. GIF + WebP variants, or several quality targets).
        menu.addAction("📑 Duplicate Selected", self.batch_duplicate_sel)
        menu.addAction("❌ Remove Selected", self.batch_remove_sel)
        
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _open_output_path(self, path):
        """Open a finished output (gif/webp) with the OS default application."""
        if not path or not os.path.exists(path):
            self.lbl_batch_info.setText(f"⚠ Output file no longer exists: {path}")
            self.lbl_batch_info.setStyleSheet(
                f"color: {COLOR_WARNING}; font-weight: bold; font-size: 10px; "
                f"padding: 2px 4px; background: #1a1500; border-radius: 3px;"
            )
            return
        # Routed through the cross-platform helper so Windows / macOS /
        # Linux all share one code path. Failures are logged but don't
        # raise — opening files is best-effort and shouldn't crash the UI.
        if not open_path_in_os(path):
            self.log(f"[ERROR] Could not open '{path}'")

    def _on_table_double_click(self, row, col):
        """Double-click a finished (✅) row to open its output file."""
        if row < 0 or row >= len(self.queue_data): return
        t = self.queue_data[row]
        out_path = getattr(t, "output_path", None)
        if t.status == "✅" and out_path and os.path.exists(out_path):
            self._open_output_path(out_path)
        else:
            # Quietly hint — most users will assume nothing happened otherwise.
            self.lbl_batch_info.setText(
                "ℹ Double-click only opens completed (✅) rows. Run the queue first."
            )
            self.lbl_batch_info.setStyleSheet(
                f"color: {COLOR_TEXT}; font-size: 10px; padding: 2px 4px;"
            )

    def update_live_dims(self):
        task = None
        multi = False
        if self.settings.batch_en.isChecked():
            sel_rows = sorted(set(i.row() for i in self.table.selectedItems()))
            if len(sel_rows) == 1 and 0 <= sel_rows[0] < len(self.queue_data):
                task = self.queue_data[sel_rows[0]]
            elif len(sel_rows) > 1:
                multi = True
        else:
            task = self.current_single_task
            
        if multi:
            vals = self.settings.get_vals()
            d_mode = vals.get("dim_mode", "Original")
            if d_mode == "Percentage (%)":
                 self.settings.res_box.lbl_live.setText(f"Target: {vals.get('dim_perc', 100)}% (Multi)")
            elif d_mode in ["Lock Width", "Lock Height", "Manual WxH"]:
                 self.settings.res_box.lbl_live.setText("Target: Fixed Res (Multi)")
            else:
                 self.settings.res_box.lbl_live.setText("Target: Original (Multi)")
            self.settings.res_box.lbl_live.setStyleSheet(f"color: {COLOR_WARNING}; font-size: 11px; font-weight: bold; padding: 4px; background: #1a1500; border-radius: 3px;")
            return
            
        if not task or not getattr(task, 'specs', None):
            self.settings.res_box.lbl_live.setText("~ x ~")
            self.settings.res_box.lbl_live.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 11px; font-weight: bold; padding: 4px; background: #0a1014; border-radius: 3px;")
            return
            
        vals = self.settings.get_vals()
        tw, th = calculate_target_dims(task.specs, vals)
        if tw > 0 and th > 0:
            # Aspect-ratio sanity check for "Manual WxH". The other
            # modes are AR-preserving by construction (Original /
            # Percentage scale uniformly; Lock W/H derive the missing
            # axis from the source). Manual lets the user pick both
            # axes independently, so we explicitly warn when the
            # resulting AR drifts >1% from the source — that 1%
            # absorbs even-rounding error on odd source dimensions
            # while still catching genuine stretch (e.g. forcing a
            # 16:9 source into 1:1 or 4:3).
            src_w = task.specs.get('w', 0)
            src_h = task.specs.get('h', 0)
            ar_src = (src_w / src_h) if (src_w > 0 and src_h > 0) else 0.0
            ar_tgt = tw / th
            ar_break = (
                vals.get("dim_mode") == "Manual WxH"
                and ar_src > 0
                and abs(ar_tgt - ar_src) / ar_src > 0.01
            )
            if ar_break:
                # Single-line red banner — the box has a locked height,
                # so wrapping or growing the label would clip. Full
                # diagnostic numbers live in the tooltip on hover.
                self.settings.res_box.lbl_live.setText(
                    f"⚠ {tw} x {th}  ·  AR break"
                )
                self.settings.res_box.lbl_live.setStyleSheet(
                    "color: white; background: " + COLOR_DANGER + "; "
                    "font-size: 12px; font-weight: bold; padding: 4px; "
                    "border-radius: 3px;"
                )
                self.settings.res_box.lbl_live.setToolTip(
                    "Manual WxH: aspect ratio doesn't match the source.\n"
                    f"Source: {src_w}×{src_h}  (AR {ar_src:.3f})\n"
                    f"Target: {tw}×{th}  (AR {ar_tgt:.3f})\n\n"
                    "The output will look stretched / squashed.\n"
                    "Use 'Lock Width' or 'Lock Height' to keep AR."
                )
            else:
                self.settings.res_box.lbl_live.setText(f"Target: {tw} x {th}")
                self.settings.res_box.lbl_live.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 13px; font-weight: bold; padding: 4px; background: #0a1014; border-radius: 3px;")
                self.settings.res_box.lbl_live.setToolTip("")
        else:
             self.settings.res_box.lbl_live.setText("Invalid Dims")
        self._refresh_output_plan()

    def _refresh_output_plan(self):
        """Build a compact summary of the current encoding settings and
        push it to the drop zone. Only visible in single mode when a
        source is loaded — in batch mode the per-row columns already
        show this information."""
        if self.settings.batch_en.isChecked():
            self.drop_zone.set_output_plan("")
            return
        task = self.current_single_task
        if not task or not getattr(task, 'specs', None):
            self.drop_zone.set_output_plan("")
            return
        vals = self.settings.get_vals()
        fmt = vals.get("format", "GIF")
        tw, th = calculate_target_dims(task.specs, vals)
        dim_str = f"{tw}×{th}" if tw > 0 and th > 0 else "?"
        parts = [f"📦 {fmt}"]
        if vals.get("mode") == "ITERATIVE":
            prio_map = {"Balanced": "Balanced", "FPS": "FPS prio", "Quality": "Quality prio"}
            prio = prio_map.get(vals.get("prio", "Balanced"), "Balanced")
            target = vals.get("target", 16)
            low = vals.get("low", 0)
            up = vals.get("up", 0)
            range_str = f"{target:.1f} MB"
            if low > 0 or up > 0:
                range_str += f" (−{low:.2f}/+{up:.2f})"
            parts.append(f"Auto {range_str}  ·  {prio}")
        else:
            parts.append(f"Manual  ·  Q{vals.get('qual', 90)}  ·  {vals.get('fps', 15)} fps")
        parts.append(f"→ {dim_str}")
        flags = []
        if vals.get("alpha"): flags.append("Alpha")
        if fmt == "GIF" and not vals.get("play_once", False): flags.append("Loop")
        if fmt == "WebP" and vals.get("lossless"): flags.append("Lossless")
        if vals.get("fast"): flags.append("Fast")
        if flags:
            parts.append(" · ".join(flags))
        self.drop_zone.set_output_plan("   ".join(parts))

    def _refresh_trim_previews(self):
        """Extract first/last frame thumbnails based on the current trim
        points and push them to the appropriate preview strip.  Works in
        both single mode (DropZone strip) and batch mode (batch panel strip)."""
        if self.settings.batch_en.isChecked():
            # Batch mode: resolve the selected task from the queue
            sel_rows = sorted(set(i.row() for i in self.table.selectedItems()))
            if len(sel_rows) == 1 and 0 <= sel_rows[0] < len(self.queue_data):
                task = self.queue_data[sel_rows[0]]
            else:
                task = None
            target_widget = self._batch_trim_preview
        else:
            task = self.current_single_task
            target_widget = self.drop_zone

        if not task or not getattr(task, 'specs', None):
            if target_widget is self.drop_zone:
                self.drop_zone.clear_trim_previews()
            else:
                self._hide_batch_trim_previews()
            return

        fps = self.settings._current_fps
        dur = self.settings._current_duration_sec
        in_raw = self.settings.t_start.text().strip()
        out_raw = self.settings.t_end.text().strip()
        in_sec = parse_trim_to_seconds(in_raw, default=0.0, fps=fps) or 0.0
        if out_raw:
            out_display = parse_trim_to_seconds(out_raw, default=None, fps=fps)
            out_sec = parse_trim_end_display_to_exclusive(out_display, fps, dur)
        else:
            out_sec = None

        if target_widget is self.drop_zone:
            self.drop_zone.update_trim_previews(task.path, in_sec, out_sec, dur, fps=fps)
        else:
            self._update_batch_trim_previews(task.path, in_sec, out_sec, dur, fps)

    def _update_batch_trim_previews(self, video_path, in_sec, out_sec, dur, fps):
        no_trim = (in_sec <= 0.01 and (out_sec is None or out_sec >= dur - 0.01))
        if no_trim:
            self._hide_batch_trim_previews()
            return
        if out_sec is None:
            out_sec = dur
        in_fi = source_frame_index_from_sec(in_sec, fps) if fps else 0
        out_excl_fi = source_frame_index_from_sec(out_sec, fps) if fps else 0
        last_fi = max(0, out_excl_fi - 1)
        self._btp_in_lbl.setVisible(True)
        self._btp_out_lbl.setVisible(True)
        self._batch_thumb_in.setVisible(True)
        self._batch_thumb_out.setVisible(True)
        self._batch_thumb_loader.request(
            self._batch_thumb_in, video_path, fps, in_fi, 120, 68
        )
        self._batch_thumb_loader.request(
            self._batch_thumb_out, video_path, fps, last_fi, 120, 68
        )

    def _hide_batch_trim_previews(self):
        self._batch_thumb_loader.cancel(self._batch_thumb_in)
        self._batch_thumb_loader.cancel(self._batch_thumb_out)
        self._batch_thumb_in.clear(); self._batch_thumb_in.setVisible(False)
        self._batch_thumb_out.clear(); self._batch_thumb_out.setVisible(False)
        self._btp_in_lbl.setVisible(False)
        self._btp_out_lbl.setVisible(False)

    def toggle_mode(self, checked):
        mode = self.settings.batch_en.isChecked()
        self.stack.setCurrentIndex(1 if mode else 0)

        # When the window is maximized it already fills the screen —
        # resizing it would break the maximized state and snap it to a
        # smaller windowed size. Skip the width swap + re-center entirely
        # and let the stretch-based layout (configured by changeEvent)
        # distribute the available space automatically.
        if not (self.windowState() & Qt.WindowMaximized):
            cur_h = self.height()
            screen = self.screen() or QApplication.primaryScreen()
            avail_w = (screen.availableGeometry().width() - 40) if screen else 1820
            ideal_w = 1820 if mode else 1500
            floor_w = 1480 if mode else 1280
            target_w = max(floor_w, min(ideal_w, avail_w))
            self.resize(target_w, cur_h)
            QTimer.singleShot(0, self._center_on_screen)
        
        if mode:
            # Batch Mode logic
            self.update_make_button()
            self.on_table_sel()
        else:
            # Single Mode logic — trimmer only available when a file is loaded
            has_task = self.current_single_task is not None
            self.settings.btn_open_trimmer.setEnabled(has_task)
            self.settings.t_start.setEnabled(has_task)
            self.settings.t_end.setEnabled(has_task)
            self.update_live_dims()

    def changeEvent(self, event):
        """When the window is maximized, unlock the settings panel width so
        both the content area AND the settings panel stretch to use all
        available screen space. When restored to normal, snap the settings
        panel back to its fixed 540 px width so it doesn't eat into the
        stack (batch table / drop zone)."""
        super().changeEvent(event)
        if event.type() != event.Type.WindowStateChange:
            return
        maximized = bool(self.windowState() & Qt.WindowMaximized)
        if maximized:
            self.settings.setFixedWidth(16777215)  # QWIDGETSIZE_MAX — removes constraint
            self.settings.setMinimumWidth(480)
            self.settings.setMaximumWidth(800)
            # Give the settings panel some stretch so it grows proportionally
            # alongside the stack. 1:3 ratio keeps ~75 % of extra width on
            # the stack (which benefits more) and ~25 % on the settings.
            idx = self._content_h.indexOf(self.settings)
            if idx >= 0:
                self._content_h.setStretch(idx, 1)
                self._content_h.setStretch(self._content_h.indexOf(self.stack), 3)
        else:
            self.settings.setMinimumWidth(540)
            self.settings.setMaximumWidth(540)
            idx = self._content_h.indexOf(self.settings)
            if idx >= 0:
                self._content_h.setStretch(idx, 0)
                self._content_h.setStretch(self._content_h.indexOf(self.stack), 1)

    def update_make_button(self):
        """Update the MAKE IT button text/state based on mode and queue (v2.7 behavior)."""
        if self.settings.batch_en.isChecked():
            pending = [t for t in self.queue_data if t.status in ["⌛", "✋"]]
            num_pending = len(pending)
            has_items = len(self.queue_data) > 0
            
            if num_pending > 0:
                self.settings.go_btn.setText(f"RUN QUEUE ({num_pending})")
                self.settings.go_btn.setStyleSheet(f"background: {COLOR_SUCCESS}; color: white; font-weight: bold; font-size: 18px; border-radius: 4px;")
                self.settings.go_btn.setEnabled(True)
            elif has_items:
                self.settings.go_btn.setText("ALL TASKS DONE")
                self.settings.go_btn.setStyleSheet(f"background: #333; color: #666; font-weight: bold; font-size: 18px; border-radius: 4px;")
                self.settings.go_btn.setEnabled(False)
            else:
                self.settings.go_btn.setText("RUN QUEUE")
                self.settings.go_btn.setStyleSheet(f"background: #333; color: #666; font-weight: bold; font-size: 18px; border-radius: 4px;")
                self.settings.go_btn.setEnabled(False)
        else:
            self.settings.go_btn.setText("MAKE IT!")
            self.settings.go_btn.setStyleSheet(f"background: {COLOR_ACCENT}; color: white; font-weight: bold; font-size: 18px; border-radius: 4px;")
            self.settings.go_btn.setEnabled(True)
        
    def toggle_log(self):
        if self._console_win.isVisible():
            self._console_win.hide()
        else:
            self._console_win.show()
            self._console_win.raise_()
            self._console_win.activateWindow()

    def _apply_iter_chart_visibility(self, visible):
        """Show or hide the iteration chart floating window."""
        self._iter_chart_visible = bool(visible)
        if self._iter_chart_visible:
            self._iter_chart_win.show()
            self._iter_chart_win.raise_()
            self._iter_chart_win.activateWindow()
        else:
            self._iter_chart_win.hide()
        self.btn_chart_toggle.setText(
            "📊 Iteration Chart  ▼" if self._iter_chart_visible else "📊 Iteration Chart  ▶"
        )

    def _toggle_iter_chart(self):
        """Toggle the iteration chart window open/closed."""
        new_state = not getattr(self, "_iter_chart_visible", False)
        self._apply_iter_chart_visibility(new_state)
        s = dict(load_app_settings() or {})
        s["show_iter_chart"] = bool(new_state)
        self._app_settings = s
        save_app_settings(s)

    def dragEnterEvent(self, e): e.acceptProposedAction()
    
    def dropEvent(self, e):
        urls = [u.toLocalFile() for u in e.mimeData().urls()]
        if self.settings.batch_en.isChecked():
            for u in urls:
                self._start_batch_import(u)
        elif urls:
            self._start_single_import(urls[0])

    # ── Async single-mode import ─────────────────────────────────────

    def _start_single_import(self, path):
        """Show ANALYZING feedback and probe the video in a background thread."""
        self.drop_zone.show_analyzing(os.path.basename(path))
        self.settings.go_btn.setEnabled(False)
        self.settings.lbl_status.setText("ANALYZING...")
        w = TaskAnalyzerWorker(path, self)
        w.finished.connect(self._on_single_imported)
        w.failed.connect(self._on_single_import_failed)
        w.finished.connect(w.deleteLater)
        w.failed.connect(w.deleteLater)
        self._import_worker = w
        w.start()

    def _on_single_imported(self, task):
        """Called when the background probe finishes successfully."""
        self._import_worker = None
        # Keep the user's CURRENT parameters instead of snapping the panel back
        # to the Task's hard-coded defaults every time a clip is loaded (v3.1.9).
        # Only the trim is reset, since it's specific to each source.
        try:
            inherited = self.settings.get_vals()
            inherited["trim_start"] = "00:00:00"
            inherited["trim_end"] = ""
            task.vals = inherited
        except Exception:
            pass
        self.current_single_task = task
        try:
            self.drop_zone.load_video(task)
            self.settings.set_current_fps(
                task.specs.get('fps', 25) or 25,
                duration_sec=task.specs.get('duration', 0) or 0,
            )
            self.settings.set_vals(task.vals)
            self.update_live_dims()
        except Exception as exc:
            self._on_single_import_failed(task.path, str(exc))
            return
        self.settings.btn_open_trimmer.setEnabled(True)
        self.settings.t_start.setEnabled(True)
        self.settings.t_end.setEnabled(True)
        self.settings.go_btn.setEnabled(True)
        self.settings.lbl_status.setText("READY")
        self.update_make_button()
        self._update_resolved_path()

    def _on_single_import_failed(self, path, msg):
        self._import_worker = None
        self.current_single_task = None
        self.drop_zone.reset()
        self.settings.set_current_fps(0, duration_sec=0)
        self.settings.clear_trim_fields()
        self.settings.btn_open_trimmer.setEnabled(False)
        self.settings.t_start.setEnabled(False)
        self.settings.t_end.setEnabled(False)
        self.settings.go_btn.setEnabled(True)
        self.settings.lbl_status.setText("READY")
        QMessageBox.warning(self, "Invalid File",
                            f"Could not analyze the dropped video file:\n{os.path.basename(path)}\n\n{msg}")

    def load_single(self, task):
        self.current_single_task = task
        try:
            self.drop_zone.load_video(task)
            self.settings.set_current_fps(
                task.specs.get('fps', 25) or 25,
                duration_sec=task.specs.get('duration', 0) or 0,
            )
            self.settings.set_vals(task.vals)
            self.settings.tabs.setCurrentIndex(0)
            self.update_live_dims()
            self.settings.btn_open_trimmer.setEnabled(True)
            self.settings.t_start.setEnabled(True)
            self.settings.t_end.setEnabled(True)
        except Exception as e:
            QMessageBox.warning(self, "Invalid File", f"Could not analyze the dropped video file: {e}")
            self.current_single_task = None
            self.drop_zone.reset()
            self.settings.set_current_fps(0, duration_sec=0)
            self.settings.clear_trim_fields()
            self.settings.btn_open_trimmer.setEnabled(False)
            self.settings.t_start.setEnabled(False)
            self.settings.t_end.setEnabled(False)

    # ── Async batch-mode import ──────────────────────────────────────

    def _start_batch_import(self, path):
        """Add a placeholder row and probe the video in background."""
        filename = os.path.basename(path)
        placeholder = type('_Placeholder', (), {
            'path': path, 'filename': filename, 'status': '⏳',
            'specs': {'w': 0, 'h': 0, 'fps': 0, 'duration': 0, 't_frames': 0, 'err': True},
            'vals': {"target": 16.0, "format": "GIF", "mode": "ITERATIVE",
                     "low": 1.5, "up": 0.5, "fps": 15, "qual": 90,
                     "dim_mode": "Original", "dim_perc": 100,
                     "dim_w": 640, "dim_h": 360, "alpha": False,
                     "prio": "Balanced", "trim_start": "00:00:00",
                     "trim_end": "", "keep_iterations": True,
                     "name_settings": True},
            'output_path': None,
        })()
        self.queue_data.append(placeholder)
        r = self.table.rowCount()
        self.table.insertRow(r)
        self._update_batch_row_analyzing(r, filename)
        self.update_make_button()
        self.lbl_batch_info.setText(f"Analyzing: {filename}...")
        self.lbl_batch_info.setStyleSheet(
            f"color: {COLOR_WARNING}; font-style: italic; font-size: 10px; "
            f"padding: 2px 4px; background: #1a1a00; border-radius: 3px;"
        )

        w = TaskAnalyzerWorker(path, self)
        w.finished.connect(lambda task, row=r: self._on_batch_imported(task, row))
        w.failed.connect(lambda p, msg, row=r: self._on_batch_import_failed(p, msg, row))
        w.finished.connect(w.deleteLater)
        w.failed.connect(w.deleteLater)
        w.start()

    def _update_batch_row_analyzing(self, r, filename):
        """Fill a batch row with an ANALYZING placeholder."""
        from PySide6.QtWidgets import QTableWidgetItem
        vals = [str(r + 1), "⏳", filename, "-", "-", "-", "-", "-", "-", "-", "-"]
        for c, v in enumerate(vals):
            it = QTableWidgetItem(v)
            it.setTextAlignment(Qt.AlignCenter)
            if c == 1:
                it.setForeground(QColor(COLOR_WARNING))
            self.table.setItem(r, c, it)

    def _on_batch_imported(self, task, row):
        """Replace the placeholder with the real Task once probing finishes."""
        if row < len(self.queue_data):
            self.queue_data[row] = task
            self.update_row(row)
            self.update_make_button()
            count = len(self.queue_data)
            self.lbl_batch_info.setText(f"Added: {task.filename}  —  {count} task(s) in queue")
            self.lbl_batch_info.setStyleSheet(
                f"color: {COLOR_SUCCESS}; font-style: italic; font-size: 10px; "
                f"padding: 2px 4px; background: #001a00; border-radius: 3px;"
            )

    def _on_batch_import_failed(self, path, msg, row):
        """Mark the placeholder row as failed."""
        if row < self.table.rowCount():
            it = self.table.item(row, 1)
            if it:
                it.setText("❌")
                it.setForeground(QColor(COLOR_DANGER))
        self.lbl_batch_info.setText(f"Failed: {os.path.basename(path)}")
        self.lbl_batch_info.setStyleSheet(
            f"color: {COLOR_DANGER}; font-style: italic; font-size: 10px; "
            f"padding: 2px 4px; background: #1a0000; border-radius: 3px;"
        )

    def add_to_batch(self, task):
        self.queue_data.append(task)
        r = self.table.rowCount(); self.table.insertRow(r)
        self.update_row(r)
        self.update_make_button()
        self.lbl_batch_info.setText(f"Added: {task.filename}  —  {len(self.queue_data)} task(s) in queue")
        self.lbl_batch_info.setStyleSheet(f"color: {COLOR_SUCCESS}; font-style: italic; font-size: 10px; padding: 2px 4px; background: #001a00; border-radius: 3px;")
        
    def update_row(self, r):
        t = self.queue_data[r]
        v = t.vals
        
        # Determine mode and target info
        is_iter = v.get("mode", "ITERATIVE") == "ITERATIVE"
        if is_iter:
            target_str = f"{v.get('target', 16.0):.2f}MB"
            mode_str = v.get("prio", "BAL")[:3].upper()  # BAL, FPS, QUA
            tgt_fps = "Auto"
        else:
            target_str = "-"
            mode_str = "MAN"
            tgt_fps = str(v.get("fps", 15))
        
        # Resolution calculation
        orig_w = t.specs.get('w', 0)
        orig_h = t.specs.get('h', 0)
        orig_res = f"{orig_w}x{orig_h}"
        
        # Calculate target dimensions using the shared helper
        tw, th = calculate_target_dims(t.specs, v)
        tgt_res = f"{tw}x{th}"
        
        orig_fps = t.specs.get("fps_display") or format_fps_for_display(
            t.specs.get("fps")
        )
        
        # Trim info — render in NLE timecode (HH:MM:SS:FF) using THIS task's fps.
        task_fps = t.specs.get('fps', 25) or 25
        raw_start = v.get("trim_start", "00:00:00")
        raw_end = v.get("trim_end", "")
        start_sec = parse_trim_to_seconds(raw_start, default=0.0, fps=task_fps)
        end_sec_excl = (
            parse_trim_to_seconds(raw_end, default=None, fps=task_fps) if raw_end else None
        )
        trim_str = "-"
        if end_sec_excl is not None or start_sec > 0.001:
            start_disp = format_seconds_as_tc_frames(start_sec, task_fps)
            if end_sec_excl is not None:
                end_disp = format_seconds_as_tc_frames(
                    inclusive_display_sec_from_exclusive_out(end_sec_excl, task_fps),
                    task_fps,
                )
            else:
                end_disp = "END"
            trim_str = f"{start_disp} - {end_disp}"
            
        # Build row data: #, Status, Filename, Format, Target, OrigRes, TgtRes, OrigFPS, TgtFPS, Mode, Trim
        vals = [
            str(r+1),
            t.status,
            t.filename,
            v.get("format", "GIF"),
            target_str,
            orig_res,
            tgt_res,
            orig_fps,
            tgt_fps,
            mode_str,
            trim_str
        ]
        
        # Determine color based on status
        status_colors = {
            "✅": COLOR_SUCCESS,
            "❌": COLOR_DANGER,
            "⚙️": COLOR_ACCENT,
            "✋": COLOR_WARNING,
            "⌛": COLOR_TEXT_BRIGHT
        }
        row_color = status_colors.get(t.status, COLOR_TEXT)
        
        color = QColor(row_color)
        for c, val in enumerate(vals):
            it = self.table.item(r, c)
            if it is None:
                it = QTableWidgetItem(val)
                it.setTextAlignment(Qt.AlignCenter)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, c, it)
            else:
                it.setText(val)
                it.setTextAlignment(Qt.AlignCenter)
            it.setForeground(color)
    
    def on_table_sel(self):
        """When user clicks a row in the batch table, load its settings into the UI panel."""
        sel_rows = sorted(set(i.row() for i in self.table.selectedItems()))
        
        # Disable trimmer if multi-selected
        is_single = len(sel_rows) <= 1
        self.settings.btn_open_trimmer.setEnabled(is_single)
        self.settings.t_start.setEnabled(is_single)
        self.settings.t_end.setEnabled(is_single)
        
        if len(sel_rows) == 1:
            r = sel_rows[0]
            if 0 <= r < len(self.queue_data):
                t = self.queue_data[r]
                # Set fps + duration BEFORE set_vals so trim fields render in
                # this task's frames AND the Length readout / OUT placeholder
                # match THIS source (different videos have different end TC).
                self.settings.set_current_fps(
                    t.specs.get('fps', 25) or 25,
                    duration_sec=t.specs.get('duration', 0) or 0,
                )
                self.settings.set_vals(t.vals)
                fps_lbl = t.specs.get("fps_display") or format_fps_for_display(
                    t.specs.get("fps")
                )
                self.lbl_batch_info.setText(
                    f"Viewing: {t.filename}  |  {t.specs.get('w','?')}x{t.specs.get('h','?')} @ {fps_lbl} fps"
                )
                self.lbl_batch_info.setStyleSheet(f"color: {COLOR_ACCENT}; font-style: italic; font-size: 10px; padding: 2px 4px; background: #0a1520; border-radius: 3px;")
                self.update_live_dims()
                self._refresh_trim_previews()
        elif len(sel_rows) > 1:
            self.lbl_batch_info.setText(f"{len(sel_rows)} tasks selected  —  Use 'Save Settings to Selected' to apply current settings to all")
            self.lbl_batch_info.setStyleSheet(f"color: {COLOR_WARNING}; font-style: italic; font-size: 10px; padding: 2px 4px; background: #1a1500; border-radius: 3px;")
            self.update_live_dims()
            self._hide_batch_trim_previews()
        else:
            self.lbl_batch_info.setText("No task selected")
            self.lbl_batch_info.setStyleSheet(f"color: #666; font-style: italic; font-size: 10px; padding: 2px 4px; background: {COLOR_BG}; border-radius: 3px;")
            self.settings.res_box.lbl_live.setText("~ x ~")
            self._hide_batch_trim_previews()
            
    def apply_settings_to_sel(self):
        """Apply current UI settings to ALL selected tasks. Protects ✅ and ⚙️ items.
        Preserves the visual selection so the user can keep working on the same set.
        Trim is intrinsically per-clip (different in/out per source) so it is
        preserved per-task and NOT clobbered by this global settings apply."""
        sel_rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not sel_rows:
            QMessageBox.information(self, "No Selection", "Select one or more tasks in the queue first.")
            return

        new_vals = self.settings.get_vals()
        # Per-clip fields that must NOT be overwritten by a global apply.
        per_clip_keys = ("trim_start", "trim_end")
        updated = 0
        skipped = 0

        self.table.blockSignals(True)
        for r in sel_rows:
            if r < 0 or r >= len(self.queue_data): continue
            t = self.queue_data[r]
            if t.status in ["✅", "⚙️"]:
                skipped += 1
                continue
            preserved = {k: t.vals.get(k) for k in per_clip_keys}
            t.vals = new_vals.copy()
            for k, v in preserved.items():
                if v is not None:
                    t.vals[k] = v
            t.status = "⌛"
            self.update_row(r)
            updated += 1
        self.table.blockSignals(False)

        self._select_rows(sel_rows)

        msg = f"Updated {updated} task(s)."
        if skipped > 0:
            msg += f" ({skipped} skipped: already finished ✅ or running ⚙️)"
        self.lbl_batch_info.setText(msg)
        self.lbl_batch_info.setStyleSheet(f"color: {COLOR_SUCCESS}; font-style: normal; font-size: 10px; padding: 2px 4px; background: #001a00; border-radius: 3px;")
        self.update_make_button()
            
    def _resolve_output_dir(self):
        """Returns (target, error_message). target is either a directory path or
        a full file path (gif/webp). None if 'Use Source Folder' is on.
        error_message is set if the user picked a destination but it's invalid."""
        if self.chk_bout.isChecked():
            return None, None
        raw = self.txt_bout.text().strip()
        if not raw:
            return None, "Custom output destination is empty. Either pick one or check 'Use Source Folder'."
        # If raw points to a file (gif/webp), accept it as a full path override
        # — the engine will use this exact path. Validate the parent directory.
        ext = os.path.splitext(raw)[1].lower()
        if ext in (".gif", ".webp"):
            parent = os.path.dirname(raw)
            if not parent or not os.path.isdir(parent):
                return None, f"Output folder does not exist:\n{parent or '(empty)'}"
            return raw, None
        # Otherwise treat raw as a directory.
        if not os.path.isdir(raw):
            return None, f"Output folder does not exist:\n{raw}"
        return raw, None

    def _open_single_output_folder(self):
        """Open the destination folder for the current single task.
        Priority: actual produced output (post-run) > configured custom target
        (pre-run, accepts both folder and file path) > source folder (fallback)."""
        if not self.current_single_task: return
        # Post-run: jump straight to the produced file's folder.
        out_path = getattr(self.current_single_task, "output_path", None)
        if out_path and os.path.exists(out_path):
            folder = os.path.dirname(out_path)
            if not open_path_in_os(folder):
                self.log(f"[ERROR] Could not open folder: {folder}")
            return
        # Pre-run: honor the global "OUTPUT DESTINATION" footer if set.
        target, err = self._resolve_output_dir()
        if err:
            QMessageBox.warning(self, "Invalid Output Folder", err)
            return
        if target:
            # _resolve_output_dir may return either a directory or a full file
            # path (gif/webp Save-As). Reduce to a directory for opening.
            target_dir = target if os.path.isdir(target) else os.path.dirname(target)
        else:
            target_dir = os.path.dirname(self.current_single_task.path)
        if os.path.isdir(target_dir):
            if not open_path_in_os(target_dir):
                self.log(f"[ERROR] Could not open folder: {target_dir}")

    def start_processing(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.settings.go_btn.setText("STOPPING...")
            return

        tasks = []
        is_batch = self.settings.batch_en.isChecked()
        # Resolve output destination ONCE for both modes — this is a global UI control,
        # not a batch-only one. Previous version silently ignored it for single tasks.
        global_out, err = self._resolve_output_dir()
        if err:
            return QMessageBox.warning(self, "Invalid Output Folder", err)
        # Cache root override (Advanced → Cache Folder). Only injected when the
        # user picked something different from the default temp location, so
        # task.vals stays clean when nothing is configured.
        active_cache = getattr(self.settings, "cache_dir", None) or DEFAULT_CACHE_DIR
        cache_override = active_cache if os.path.normpath(active_cache) != os.path.normpath(DEFAULT_CACHE_DIR) else None
        
        if is_batch:
            # We must pass the reference to the table item specifically so the worker can update its status
            for i, t in enumerate(self.queue_data):
                if t.status != "✅":
                    t._row_idx = i # Attach row index for status updating later
                    if global_out:
                         t.vals["_force_out_dir"] = global_out
                    if cache_override:
                         t.vals["_force_cache_dir"] = cache_override
                    tasks.append(t)
        elif self.current_single_task:
            # Sync current UI to task
            self.current_single_task.vals = self.settings.get_vals()
            # Remember these as the last-used settings so the next launch (and the
            # next imported clip) start from here instead of the defaults.
            self.settings.persist_last_vals()
            if global_out:
                self.current_single_task.vals["_force_out_dir"] = global_out
            if cache_override:
                self.current_single_task.vals["_force_cache_dir"] = cache_override
            # One-shot: "Volver a iterar" forces a fresh search that ignores the
            # cached iterations for this run only (cleared right after).
            if getattr(self, "_force_reencode_once", False):
                self.current_single_task.vals["force_reencode"] = True
                self._force_reencode_once = False
            tasks = [self.current_single_task]
            
        if not tasks: return QMessageBox.warning(self, "No Tasks", "Nothing to process!")
        
        self.settings.go_btn.setText("STOP"); self.settings.go_btn.setStyleSheet(f"background: {COLOR_DANGER}; color: white; font-weight: bold; border-radius: 4px;")
        # Console used to auto-pop here on every MAKE press; users found that
        # noisy when they only wanted to glance at the iter chart and progress
        # bar. Now the console stays in whatever state the user chose — they
        # can still open it via the SHOW LOG button if they want details.

        self.worker = Worker(tasks)
        self.worker.signals.log.connect(self.view.append)
        self.worker.signals.progress.connect(self.settings.pbar.setValue)
        self.worker.signals.status_text.connect(self.settings.lbl_status.setText)
        # Hack to update table directly from thread via lambda (QThread safe because qt signals marshal to main thread)
        self.worker.signals.task_started.connect(self._on_task_started)
        self.worker.signals.task_finished.connect(self._on_task_finished)
        self.worker.signals.finished.connect(self.on_finished)
        # Iterative search telemetry → full-width live chart in the bottom
        # drawer. iter_started clears + locks bounds, iter_step appends a
        # point, iter_finished freezes the trajectory with the winner
        # highlighted. The chart lives on MainWindow now (not SettingsPanel)
        # so it can stretch the full window width when expanded.
        self.worker.signals.iter_started.connect(self.iter_chart.on_iter_started)
        self.worker.signals.iter_attempt_started.connect(self.iter_chart.on_iter_attempt_started)
        self.worker.signals.iter_step.connect(self.iter_chart.on_iter_step)
        self.worker.signals.iter_finished.connect(self.iter_chart.on_iter_finished)
        self.worker.start()

    @Slot(object)
    def _on_task_started(self, task):
         if hasattr(task, '_row_idx'):
              task.status = "⚙️"
              self.update_row(task._row_idx)
              self.table.scrollToItem(self.table.item(task._row_idx, 0))

    @Slot(object, bool, str)
    def _on_task_finished(self, task, success, dest_path):
         # Track status on the Task itself so both batch-row UI and single-mode
         # dropzone can read it later (Reset Status, restart logic, etc.).
         task.status = "✅" if success else "❌"
         if success and dest_path:
             # Store output path on a separate field; do NOT overwrite task.path,
             # otherwise a subsequent re-run would feed the GIF/WebP back as input.
             task.output_path = dest_path
         if hasattr(task, '_row_idx'):
             self.update_row(task._row_idx)
             # Surface per-task completion in the batch info bar so the user
             # has a clear, visible signal that something just succeeded/failed.
             if success and dest_path:
                 try: size_mb = os.path.getsize(dest_path) / (1024 * 1024)
                 except OSError: size_mb = 0
                 self.lbl_batch_info.setText(
                     f"✅ {task.filename} → {os.path.basename(dest_path)}  ({size_mb:.2f} MB)  —  double-click row to open"
                 )
                 self.lbl_batch_info.setStyleSheet(
                     f"color: {COLOR_SUCCESS}; font-weight: bold; font-size: 10px; "
                     f"padding: 2px 4px; background: #001a00; border-radius: 3px;"
                 )
             elif not success:
                 self.lbl_batch_info.setText(f"❌ {task.filename} — failed (see console for details)")
                 self.lbl_batch_info.setStyleSheet(
                     f"color: {COLOR_DANGER}; font-weight: bold; font-size: 10px; "
                     f"padding: 2px 4px; background: #1a0000; border-radius: 3px;"
                 )
        
    def on_finished(self):
        self.settings.lbl_status.setText("READY")
        self.settings.pbar.setValue(0)
        self.view.append(">>> JOB FINISHED <<<")
        # update_make_button correctly resets the GO button in BOTH modes
        # (MAKE IT! / RUN QUEUE / ALL TASKS DONE).
        self.update_make_button()
        if self.settings.batch_en.isChecked():
            ok = sum(1 for t in self.queue_data if t.status == "✅")
            fail = sum(1 for t in self.queue_data if t.status == "❌")
            total = ok + fail
            if total > 0:
                color = COLOR_SUCCESS if fail == 0 else COLOR_WARNING
                bg = "#001a00" if fail == 0 else "#1a1500"
                self.lbl_batch_info.setText(
                    f"🏁 Batch finished — {ok}/{total} succeeded"
                    + (f", {fail} failed" if fail else "")
                    + "  —  double-click any ✅ row to open its output"
                )
                self.lbl_batch_info.setStyleSheet(
                    f"color: {color}; font-weight: bold; font-size: 11px; "
                    f"padding: 4px 6px; background: {bg}; border-radius: 3px;"
                )
        else:
            # Single mode: pick the chip based on the task outcome so failures
            # don't masquerade as DONE. Either path shows the Reset Status btn.
            if self.current_single_task:
                if self.current_single_task.status == "✅":
                    t = self.current_single_task
                    is_iter = (getattr(t, "result_mode", "") == "ITERATIVE")
                    self.drop_zone.mark_done(is_iterative=is_iter)
                    # Surface the outcome in a clear modal window (English). Modal
                    # + no inline text means nothing lingers once the user runs
                    # again — the message only exists while the dialog is open.
                    self._show_single_result_dialog(t)
                else:
                    self.drop_zone.mark_failed()

    def _reset_single_status(self):
        """Reset the current single task's status back to READY so the user can
        re-run it (with possibly tweaked settings) without having to reload the
        source file."""
        if not self.current_single_task: return
        self.current_single_task.status = "⏳"
        self.current_single_task.output_path = None
        self.drop_zone.mark_ready()
        self.update_make_button()

    def _reiterate_single(self):
        """Re-run the current single task forcing a fresh iterative search that
        ignores any cached iterations — without the user having to toggle
        'Keep iterations' or delete the _ITERATIONS folder. Triggered by the
        drop-zone 'Search Again' button or the result dialog."""
        if not self.current_single_task:
            return
        if self.worker and self.worker.isRunning():
            return
        self._force_reencode_once = True
        self.start_processing()

    def _show_single_result_dialog(self, task):
        """Clear, English, modal summary of a finished single render.

        Tells the user plainly WHAT won (Q / FPS / size) and — crucially —
        whether the result was REUSED from an earlier run (no encoding) or
        freshly searched, so an instant cache copy no longer looks like nothing
        happened. Offers a clearly-labelled 'Search again' action for cache hits
        that re-runs the search ignoring saved results."""
        from_cache = bool(getattr(task, "result_from_cache", False))
        q = getattr(task, "result_quality", None)
        fps = getattr(task, "result_fps", None)
        size = getattr(task, "result_size", None)
        is_iter = (getattr(task, "result_mode", "") == "ITERATIVE")

        parts = []
        if q is not None: parts.append(f"Q{q}")
        if fps is not None: parts.append(f"{fps} fps")
        if size:
            try: parts.append(f"{size / (1024 * 1024):.2f} MB")
            except Exception: pass
        winner = "   ·   ".join(parts) if parts else "—"

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        if from_cache:
            box.setWindowTitle("Render complete — reused a previous result")
            box.setText("A matching result from an earlier run was reused.")
            box.setInformativeText(
                "Nothing was re-encoded this time. The tool found a result from a "
                "previous run that already fits your current target size, so it "
                "reused it instantly.\n\n"
                f"Result used:   {winner}\n\n"
                "Want a brand-new encode instead? Click \"Search again\" to ignore "
                "the saved results and run the size search from scratch."
            )
        else:
            box.setWindowTitle("Render complete")
            box.setText("Encoding finished.")
            box.setInformativeText(
                f"Result:   {winner}\n\n"
                + ("The size search ran from scratch." if is_iter
                   else "Manual encode (fixed quality / FPS).")
            )

        again_btn = None
        if from_cache and is_iter:
            again_btn = box.addButton("Search again", QMessageBox.AcceptRole)
        open_btn = box.addButton("Open folder", QMessageBox.ActionRole)
        close_btn = box.addButton("Close", QMessageBox.RejectRole)
        box.setDefaultButton(close_btn)
        box.exec()

        clicked = box.clickedButton()
        if clicked is open_btn:
            self._open_single_output_folder()
        elif again_btn is not None and clicked is again_btn:
            self._reiterate_single()

if __name__ == "__main__":
    # Windows-only: tell the shell that this process is its own app
    # (not a generic "Python interpreter") so the taskbar groups
    # windows under our icon and pinning works correctly. Must be
    # called BEFORE the first window is shown.
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "MakeAGIF.WEBP.v3.1.10"
            )
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("MakeAGIF/WEBP")
    app.setApplicationDisplayName(APP_TITLE)
    _rm, _disk = clear_scene_cache_on_app_startup()
    if _disk:
        print(f"[MakeAGIF] Scene cache cleared on startup ({_disk} file(s)).")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
