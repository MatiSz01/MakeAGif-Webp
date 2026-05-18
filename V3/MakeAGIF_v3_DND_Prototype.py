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
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
from datetime import datetime

from PySide6.QtWidgets import (QApplication, QScrollArea, QDialog, QDialogButtonBox, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QFrame, QTabWidget,
                               QSlider, QRadioButton, QGroupBox, QPushButton, QComboBox,
                               QCheckBox, QStackedWidget, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QSpinBox, QDoubleSpinBox, QTextEdit, QButtonGroup,
                               QAbstractItemView, QFileDialog, QMessageBox, QSizePolicy, QProgressBar, QLineEdit, QMenu)
from PySide6.QtCore import Qt, QUrl, QSize, QThread, Signal, QObject, Slot, QTimer, QItemSelection, QItemSelectionModel
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
# from PySide6.QtGui import QColor, QFont, QPalette, QIcon, QDragEnterEvent, QDropEvent # (Unused imports commented out for cleanliness)
from PySide6.QtGui import QIcon, QColor, QImage, QPixmap, QShortcut, QKeySequence, QColor

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
SCRIPT_VERSION = "v3.0 Studio"
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
    """Return cached cuts (list[float]) for this (content, threshold) or None."""
    if not content_key: return None
    # RAM tier first — survives across multiple TrimDialog open/close in one session.
    ram = _SCENE_RAM_CACHE.get(content_key, {})
    if threshold in ram:
        return list(ram[threshold])
    # Disk tier — survives across app restarts.
    p = _scene_cache_path(content_key, threshold)
    try:
        if os.path.isfile(p):
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
            cuts = data.get("cuts") or []
            cuts = [float(c) for c in cuts if isinstance(c, (int, float))]
            # Promote disk hit into RAM so the next open doesn't touch the disk.
            _SCENE_RAM_CACHE.setdefault(content_key, {})[threshold] = list(cuts)
            return cuts
    except Exception:
        pass
    return None

def save_scene_cache(content_key, threshold, cuts, src_path=None):
    """Persist cuts for this (content, threshold) to RAM + disk. Best-effort."""
    if not content_key: return
    cuts = sorted(set(round(float(c), 3) for c in cuts))
    _SCENE_RAM_CACHE.setdefault(content_key, {})[threshold] = list(cuts)
    try:
        os.makedirs(SCENE_CACHE_DIR, exist_ok=True)
        with open(_scene_cache_path(content_key, threshold), 'w', encoding='utf-8') as f:
            json.dump({
                "cuts": cuts,
                "threshold": float(threshold),
                "src_seen": src_path or "",
                "saved_at": time.time(),
            }, f)
    except Exception:
        pass

# App-level settings live alongside the script (next to /presets/) so the user's
# choice of cache folder, etc. survives across runs without polluting their
# preset library. Falls back silently to defaults on any I/O error.
def _app_settings_path():
    try:
        base = os.path.dirname(os.path.abspath(__file__))
    except NameError:
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

# --- Stylesheet ---
GLOBAL_STYLE = f"""
    QMainWindow {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; }}
    QWidget {{ font-family: 'Segoe UI', sans-serif; font-size: 11px; color: {COLOR_TEXT}; }}
    
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
def get_tool_path(name):
    base_path = os.path.dirname(os.path.abspath(__file__))
    # Check "tools" subfolder first
    p = os.path.join(base_path, "tools", name)
    if os.path.exists(p): return p
    # Check portable MEIPASS
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        p = os.path.join(base_path, "tools", name)
        if os.path.exists(p): return p
    # Fallback to system
    return name

FFMPEG_PATH = get_tool_path("ffmpeg.exe")
GIFSKI_PATH = get_tool_path("gifski.exe")
MAGICK_PATH = get_tool_path("magick.exe") # Optional

def get_video_specs(path):
    specs = {"w": 0, "h": 0, "fps": 0.0, "dur": "0:00", "duration": 0.0, "t_frames": 0, "err": True}
    if not os.path.exists(path): return specs
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
                fps_int = max(1, int(round(fps_f)))
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
    fps_int = max(1, int(round(fps_f)))
    ff = total_frames % fps_int
    total_seconds = total_frames // fps_int
    s = total_seconds % 60
    m = (total_seconds // 60) % 60
    h = total_seconds // 3600
    return f"{h:02d}:{m:02d}:{s:02d}:{ff:02d}"

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
        # Filter None and convert to string
        cmd_str = ' '.join(f'"{x}"' if ' ' in str(x) else str(x) for x in cmd if x is not None)
        self.log(f"  CMD: {cmd_str}")
        flags = 0x08000000 if os.name == 'nt' else 0
        shell = any("*" in str(x) for x in cmd if x is not None)
        
        self.current_proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', creationflags=flags, shell=shell
        )
        
        while True:
            self.check_cancel()
            line = self.current_proc.stdout.readline()
            if not line and self.current_proc.poll() is not None: break
            if line: self.log(f"    {line.strip()}")
            
        rc = self.current_proc.poll()
        self.current_proc = None
        return rc

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
            if keep_iter:
                iter_folder = os.path.join(dest_dir, f"{base_name}_ITERATIONS")
                os.makedirs(iter_folder, exist_ok=True)
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
        #   v6 — back to EXCLUSIVE OUT: duration = out - in. The OUT marker is
        #        the boundary, not the last extracted frame. Old v5 caches
        #        contain one extra frame and must be invalidated.
        CACHE_VER = "v6"
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
        duration_sec = (out_sec_v - in_sec_v) if (out_sec_v is not None) else None
        if duration_sec is not None and duration_sec <= 0:
            duration_sec = None  # treat as "no end" (full source from in_sec)
        expected_frames = (
            max(0, int(round(duration_sec * float(fps))))
            if duration_sec is not None else None
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
                self.log(
                    f"  Trim verify: in={in_sec_v:.3f}s out={out_sec_v:.3f}s (excl) "
                    f"(Δ={duration_sec:.3f}s @ {fps}fps) → expected={expected_frames} frames, got {extracted} [{marker_label}]"
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
            if params.get("has_alpha") and MAGICK_PATH:
                delay = max(1, int(round(100.0 / fps)))
                cmd = [MAGICK_PATH, "-delay", str(delay), os.path.join(cpath, "f_*.png"), "-dispose", "Background", "-loop", "1" if params.get("play_once") else "0"]
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
            res.update({"status": "Success", "file_path": dest, "file_size": os.path.getsize(dest)})
            self.signals.step.emit("✅", f"{out_fmt} Rendered!")
        return res

    # ---------- Knowledge cache (warm-start support) ----------
    def _build_knowledge_cache(self, iter_dir, base, w, h, ext):
        """Scan a persistent iterations folder and build {(fps, q, w, h): {size, path}}.
        Filenames are expected in the form: tmp_p[12]_q{Q}_fps{F}_dim{W}x{H}{ext}.
        Files from older runs without the dim suffix are ignored to avoid mixing
        outputs at different resolutions."""
        cache = {}
        if not iter_dir or not os.path.isdir(iter_dir): return cache
        dim_str = f"{w}x{h}"
        pat = re.compile(
            rf"^tmp_p[12]_q(\d+)_fps(\d+)_dim{re.escape(dim_str)}{re.escape(ext)}$",
            re.IGNORECASE,
        )
        found = []
        try:
            entries = os.listdir(iter_dir)
        except OSError:
            return cache
        for f in entries:
            if INPROGRESS_SUFFIX in f: continue
            m = pat.match(f)
            if not m: continue
            q_v, f_v = int(m.group(1)), int(m.group(2))
            path = os.path.join(iter_dir, f)
            try: sz = os.path.getsize(path)
            except OSError: continue
            cache[(f_v, q_v, w, h)] = {"size": sz, "path": path}
            found.append(f"[Cache] Q{q_v} F{f_v} {sz/(1024*1024):.2f}MB → {f}")
        if found:
            self.log(f"--- Knowledge cache: found {len(found)} prior iteration(s) for {base} @ {dim_str} ---")
            for line in found: self.log(line)
        return cache

    def _proactive_cache_scan(self, cache, target_size, low_b, high_b, target_fps):
        """If cache contains a file already in size bracket AND within ±1 FPS of
        target intent, return it directly so we can skip the search entirely."""
        if not cache: return None
        candidates = []
        for (f_v, q_v, w_v, h_v), info in cache.items():
            sz = info["size"]
            in_bracket = low_b <= sz <= high_b
            fps_ok = abs(f_v - target_fps) <= 1
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
        cache = self._build_knowledge_cache(
            common["iter_attempts_main_folder"], common["source_basename_no_ext"], w, h, ext,
        ) if common.get("iter_keep") else {}

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
            return {"status": "Success", "file_path": final_out_path, "file_size": tier1["size"]}

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
        
        attempts = 0
        max_attempts = 10
        fps = target_fps
        seed_used = False  # we only seed mid_q on the very first attempt
        
        # Phase 1: Binary Search on Quality
        while low_q <= high_q and attempts < max_attempts:
            self.check_cancel(); attempts += 1
            # Warm-start: if we have cache hints at this fps/dim, seed mid_q with
            # an interpolation-based guess; otherwise fall back to midpoint.
            if not seed_used:
                hint = self._seed_q_from_cache(cache, fps, w, h, common["target_size_bytes"], low_q, high_q)
                if hint is not None:
                    mid_q = hint
                    self.log(f"    Warm-start: seeding Q{mid_q} from prior iterations.")
                else:
                    mid_q = (low_q + high_q) // 2
                seed_used = True
            else:
                mid_q = (low_q + high_q) // 2
            
            self.signals.progress.emit(int((attempts/15)*100))
            self.log(f"  > Attempt {attempts}: Testing Q{mid_q}...")
            
            fname = f"tmp_p1_q{mid_q}_fps{fps}_dim{w}x{h}"
            opath = os.path.join(common["iter_attempts_main_folder"], fname + ext)
            
            params = {**common, "fps": fps, "quality": mid_q, "width": w, "height": h, "output_path_for_iter": opath}
            res = self.generate_animation(params)
            if res["status"] != "Success": break
            
            sz = res["file_size"]
            res_obj = {'file_path': opath, 'size': sz, 'fps': fps, 'quality': mid_q, 'diff': abs(sz - common['target_size_bytes'])}
            
            if res_obj['diff'] < closest_any['diff']: closest_any = res_obj
            
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
            
        # Phase 2: drop FPS and re-bisect Q (instead of forcing Q=40, which
        # massacres quality). Single FPS step at the midpoint of the lower
        # band — usually enough; if still no fit, we keep closest_any.
        if not best_res and closest_any['file_path']:
            self.signals.step.emit("📉", "Phase II: FPS Adjust...")
            mid_fps = max(min_fps, (min_fps + max(min_fps, target_fps - 1)) // 2)
            self.log(f"--- P2: Quality Binary Search at lower FPS={mid_fps} ---")
            low_q2, high_q2 = 40, 100
            attempts2 = 0
            max_attempts2 = 8
            while low_q2 <= high_q2 and attempts2 < max_attempts2:
                self.check_cancel(); attempts2 += 1
                mid_q2 = (low_q2 + high_q2) // 2
                self.log(f"  > Attempt {attempts + attempts2}: Testing Q{mid_q2} @ F{mid_fps}...")
                fname = f"tmp_p2_q{mid_q2}_fps{mid_fps}_dim{w}x{h}"
                opath = os.path.join(common["iter_attempts_main_folder"], fname + ext)
                params = {**common, "fps": mid_fps, "quality": mid_q2, "width": w, "height": h, "output_path_for_iter": opath}
                res = self.generate_animation(params)
                if res["status"] != "Success": break
                sz = res["file_size"]
                res_obj = {'file_path': opath, 'size': sz, 'fps': mid_fps, 'quality': mid_q2, 'diff': abs(sz - common['target_size_bytes'])}
                if res_obj['diff'] < closest_any['diff']: closest_any = res_obj
                if common['strict_lower_bound'] <= sz <= common['strict_upper_bound']:
                    successful.append(res_obj)
                    best_res = res_obj
                    break
                elif sz > common['strict_upper_bound']: high_q2 = mid_q2 - 1
                else: low_q2 = mid_q2 + 1

        # Finalize
        winner = None
        if successful:
             def p_sort(item): return (abs(item['fps'] - target_fps) * 1000, -item['quality'], item['diff'])
             successful.sort(key=p_sort)
             winner = successful[0]
        else:
             winner = closest_any

        if winner and winner.get('file_path') and os.path.exists(winner['file_path']):
             self.log(f"  WINNER: Q{winner['quality']} F{winner['fps']} ({winner['size']/(1024*1024):.2f}MB)")
             if os.path.exists(final_out_path): os.remove(final_out_path)
             shutil.copy2(winner['file_path'], final_out_path)
             return {"status": "Success", "file_path": final_out_path, "file_size": winner['size']}

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
    progress (0-100) parsed from ffmpeg's `time=HH:MM:SS` lines.

    Cancellable mid-run; cleans up the spawned ffmpeg process."""
    cuts_ready = Signal(list)  # list[float]
    progress = Signal(int)     # 0-100
    failed = Signal(str)

    _re_pts = re.compile(r"pts_time:(\d+(?:\.\d+)?)")
    _re_time = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})")

    def __init__(self, video_path, duration_sec, threshold=0.30, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.duration_sec = max(0.001, float(duration_sec or 0))
        self.threshold = float(threshold)
        self._cancel = False
        self._proc = None

    def cancel(self):
        self._cancel = True
        proc = self._proc
        if proc is not None:
            try: proc.terminate()
            except Exception: pass

    def run(self):
        cuts = []
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
                    try: cuts.append(float(m_pts.group(1)))
                    except ValueError: pass
                m_t = self._re_time.search(line)
                if m_t and self.duration_sec > 0:
                    cur = int(m_t.group(1))*3600 + int(m_t.group(2))*60 + int(m_t.group(3))
                    pct = int(min(100, max(0, (cur / self.duration_sec) * 100)))
                    self.progress.emit(pct)
            try: self._proc.wait(timeout=2)
            except Exception: pass
            if self._cancel:
                return
            self.progress.emit(100)
            self.cuts_ready.emit(sorted(set(round(c, 3) for c in cuts)))
        except FileNotFoundError:
            self.failed.emit("FFmpeg not found")
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            if self._proc and self._proc.poll() is None:
                try: self._proc.kill()
                except Exception: pass



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

    # Tightest allowed view span = ~0.1% of source. Zooming in further would
    # round all distinct frames at typical fps onto the same pixel anyway.
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
        return max(self.MIN_VIEW_SPAN, self.view_end_r - self.view_start_r)

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
        if self.cut_ratios:
            cut_color = QColor("#ffab00"); cut_color.setAlpha(180)
            p.setPen(cut_color)
            for cr in self.cut_ratios:
                # Skip cuts outside the visible viewport — drawing them would
                # paint at negative x or past the right edge and waste cycles.
                if not (self.view_start_r <= cr <= self.view_end_r):
                    continue
                xc = self._src_to_x(cr, w)
                p.drawLine(xc, 4, xc, h - 4)

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
        if self.cut_ratios:
            snap_px = 6
            span = self._view_span()
            nearest = min(self.cut_ratios, key=lambda r: abs(r - ratio))
            if (abs(nearest - ratio) / span) * w <= snap_px:
                ratio = nearest
        self.seeked.emit(ratio)

    def mouseMoveEvent(self, e):
        w = self.width()
        if w <= 0:
            return
        ratio = self._x_to_src(e.x(), w)
        shift = bool(e.modifiers() & Qt.ShiftModifier)

        # Hover preview: only when the user is "in segment-select gesture"
        # (Shift held OR select_mode toggled on) AND we have segments to pick.
        new_hover = None
        if (shift or self.select_mode) and self._has_segments():
            idx = self._segment_index_at(ratio)
            if idx >= 0:
                new_hover = self._compute_target_range(idx, shift)
        if new_hover != self.hover_seg_range:
            self.hover_seg_range = new_hover
            self.update()

        # Drag-scrub: only when left button is held AND we're not in a select
        # gesture, otherwise dragging would emit spurious seeks while the user
        # is composing a Shift+Click range.
        if (e.buttons() & Qt.LeftButton) and not (shift or self.select_mode):
            self.seeked.emit(ratio)

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
        new_span = max(self.MIN_VIEW_SPAN, min(1.0, new_span))
        # Anchor the cursor's source position at its current screen x so the
        # frame under the cursor doesn't visually slide during zoom.
        anchor_frac = cursor_x / w
        new_start = cursor_src - anchor_frac * new_span
        self._set_view(new_start, new_start + new_span)
        e.accept()

    def leaveEvent(self, e):
        # Drop the hover overlay when the cursor leaves the timeline so the
        # widget doesn't keep a stale ghost rectangle.
        if self.hover_seg_range is not None:
            self.hover_seg_range = None
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
        """
        self.select_mode = bool(on)
        if not self.select_mode:
            self.sel_seg_range = None
            self.sel_anchor_idx = None
            self.hover_seg_range = None
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
        span = max(self.MIN_VIEW_SPAN, min(1.0, end_r - start_r))
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

    def zoom_in(self, factor=1.25):
        """Programmatic zoom in centered on the playhead — used by the +
        button so the keyboard/button flow doesn't depend on mouse position."""
        center = max(self.view_start_r, min(self.view_end_r, self.pos_ratio))
        new_span = max(self.MIN_VIEW_SPAN, self._view_span() / factor)
        self._set_view(center - new_span / 2.0, center + new_span / 2.0)

    def zoom_out(self, factor=1.25):
        center = max(self.view_start_r, min(self.view_end_r, self.pos_ratio))
        new_span = min(1.0, self._view_span() * factor)
        self._set_view(center - new_span / 2.0, center + new_span / 2.0)


class TrimDialog(QDialog):
    """NLE-style trim dialog. Returns in_sec / out_sec (float seconds, framerate-agnostic)."""
    def __init__(self, task, parent=None, initial_in_sec=0.0, initial_out_sec=None):
        super().__init__(parent)
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

        # Internal pointers stored as SECONDS (framerate-agnostic)
        self.in_sec  = float(initial_in_sec or 0.0)
        self.out_sec = float(initial_out_sec) if initial_out_sec else self.duration_sec
        self.current_sec = 0.0
        self.jkl_speed = 1.0   # for JKL variable speed

        # Scene detection state
        self.cuts_sec = []          # list[float] — detected scene-change times
        self.scene_worker = None    # active SceneDetectorWorker, if any
        self.snap_threshold_sec = 0.30  # max distance to snap-correct in/out to a cut
        self._scene_threshold = 0.30
        # Content-fingerprint key for the persistent scene cache (RAM + disk).
        # Computed once in __init__ so cache reads/writes don't re-hash on every
        # detect cycle. May be None if we can't read the file.
        self._scene_content_key = _video_content_key(task.path)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # --- Video Widget ---
        self.video_widget = QVideoWidget()
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
        self.audio_output.setVolume(0.0)
        layout.addWidget(self.video_widget, 1)

        # --- Custom Timeline ---
        self.timeline = TimelineWidget()
        layout.addWidget(self.timeline)

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

        # --- Timecode + In/Out Labels ---
        tc_row = QHBoxLayout()
        self.lbl_in  = QLabel("IN:  --:--:--")
        self.lbl_tc  = QLabel("00:00:00:00")
        self.lbl_out = QLabel("OUT: --:--:--")
        for lbl in [self.lbl_in, self.lbl_tc, self.lbl_out]:
            lbl.setStyleSheet(f"font-size: 14px; font-family: Consolas; font-weight: bold; color: {COLOR_ACCENT};")
        self.lbl_in.setStyleSheet(f"font-size: 13px; font-family: Consolas; color: #00c853;")
        self.lbl_out.setStyleSheet(f"font-size: 13px; font-family: Consolas; color: #ff4444;")
        tc_row.addWidget(self.lbl_in)
        tc_row.addStretch()
        tc_row.addWidget(self.lbl_tc)
        tc_row.addStretch()
        tc_row.addWidget(self.lbl_out)
        layout.addLayout(tc_row)

        # --- Controls ---
        ctrl_row = QHBoxLayout()
        btn_style = "background: #2a2a3a; font-weight: bold; font-size: 12px; padding: 6px 12px; border-radius: 3px; border: 1px solid #333;"

        self.btn_play = QPushButton("▶ PLAY")
        self.btn_in   = QPushButton("[ SET IN  (I)")
        self.btn_out  = QPushButton("SET OUT ] (O)")
        self.btn_clr  = QPushButton("↺ CLEAR TRIM")
        for b in [self.btn_play, self.btn_in, self.btn_out, self.btn_clr]:
            b.setStyleSheet(btn_style)
        self.btn_in.setStyleSheet(btn_style + " color: #00c853;")
        self.btn_out.setStyleSheet(btn_style + " color: #ff4444;")
        
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
        self.lbl_vol.setStyleSheet("color: #888; font-size: 11px; font-family: Consolas;")
        self.lbl_vol.setAlignment(Qt.AlignCenter)

        self.btn_mute.clicked.connect(self._on_mute_clicked)
        self.vol_slider.valueChanged.connect(self._on_volume_slider)

        # JKL hint label
        hint = QLabel(
            "◀◀ J  |  K Pause  |  L ▶▶      ←/→ frame  |  Shift+←/→ ×10      "
            "[ / ] or PgUp / PgDn = prev / next cut      "
            "+/− zoom · 0 fit · M mute"
        )
        hint.setStyleSheet("color: #555; font-size: 10px;")

        ctrl_row.addWidget(self.btn_in)
        ctrl_row.addWidget(self.btn_play)
        ctrl_row.addWidget(self.btn_out)
        ctrl_row.addWidget(self.btn_clr)
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
            "Auto-detect scene changes via FFmpeg. Cuts appear as orange marks on the timeline; "
            "with 'Snap to cuts' enabled, SET IN / SET OUT will snap to the nearest cut."
        )
        self.chk_snap = QCheckBox("Snap to cuts")
        self.chk_snap.setChecked(True)
        self.chk_snap.setToolTip(f"When setting IN/OUT, snap to the nearest detected cut within ±{self.snap_threshold_sec:.2f}s.")
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

        scene_row.addWidget(self.btn_detect)
        scene_row.addWidget(self.chk_snap)
        scene_row.addWidget(self.btn_seg_mode)
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
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

        # --- Connections ---
        self.timeline.seeked.connect(self._seek_ratio)
        self.timeline.segment_selected.connect(self._on_segment_selected)
        self.btn_seg_mode.toggled.connect(self.timeline.set_select_mode)
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_in.clicked.connect(self.set_in)
        self.btn_out.clicked.connect(self.set_out)
        self.btn_clr.clicked.connect(self.clear_trim)
        self.btn_detect.clicked.connect(self._toggle_scene_detection)
        self.player.positionChanged.connect(self._on_pos_changed)

        # --- Keyboard Shortcuts ---
        QShortcut(QKeySequence("Space"), self, self.toggle_play)
        QShortcut(QKeySequence("I"),     self, self.set_in)
        QShortcut(QKeySequence("O"),     self, self.set_out)
        # J/K/L — classic NLE
        QShortcut(QKeySequence("J"),     self, self._jkl_j)
        QShortcut(QKeySequence("K"),     self, self._jkl_k)
        QShortcut(QKeySequence("L"),     self, self._jkl_l)
        # Arrow frame stepping
        QShortcut(QKeySequence("Left"),              self, lambda: self._step_sec(-1/self.fps))
        QShortcut(QKeySequence("Right"),             self, lambda: self._step_sec( 1/self.fps))
        QShortcut(QKeySequence("Shift+Left"),        self, lambda: self._step_sec(-10/self.fps))
        QShortcut(QKeySequence("Shift+Right"),       self, lambda: self._step_sec( 10/self.fps))
        # Cut navigation (active only after a scene detection has produced cuts).
        # PgUp = prev cut, PgDown = next cut — same direction as scrolling /
        # most NLE timelines (up = backwards, down = forwards).
        QShortcut(QKeySequence("["),                 self, lambda: self._jump_to_cut(-1))
        QShortcut(QKeySequence("]"),                 self, lambda: self._jump_to_cut(+1))
        QShortcut(QKeySequence(Qt.Key_PageUp),       self, lambda: self._jump_to_cut(-1))
        QShortcut(QKeySequence(Qt.Key_PageDown),     self, lambda: self._jump_to_cut(+1))
        # Audio
        QShortcut(QKeySequence("M"),                 self, self._on_mute_clicked)
        # Zoom (NLE-style: = zooms in even without Shift; 0 fits)
        QShortcut(QKeySequence("="),                 self, lambda: self.timeline.zoom_in())
        QShortcut(QKeySequence("+"),                 self, lambda: self.timeline.zoom_in())
        QShortcut(QKeySequence("-"),                 self, lambda: self.timeline.zoom_out())
        QShortcut(QKeySequence("0"),                 self, self.timeline.reset_view)

        # Restore previous trim markers
        self._restore_markers()

        # Load first frame
        self.player.play()
        self.player.pause()
        self._seek_ratio(self.in_sec / self.duration_sec)
        self._refresh_tc(self.in_sec)

        # Warm-start from persistent scene cache. If we've detected scenes for
        # this exact source content (size + first 1MB sha1) at this threshold
        # before, load those cuts now so the user sees the orange ticks
        # immediately without re-running ffmpeg.
        self._try_warm_start_scenes()

    # ---- helpers ----

    def _sec_to_tc(self, sec):
        # Delegate to the module-level frame-aware formatter to keep the
        # NLE-style HH:MM:SS:FF display rule in ONE place. The previous local
        # implementation used int(sec) for the seconds field (raw total
        # seconds) instead of seconds modulo 60, so e.g. 111.46s rendered as
        # "00:01:111:14" instead of "00:01:51:14".
        return format_seconds_as_tc_frames(max(0.0, sec), self.fps) or "00:00:00:00"

    def _refresh_tc(self, sec):
        self.current_sec = sec
        self.lbl_tc.setText(self._sec_to_tc(sec))
        ratio = sec / self.duration_sec
        self.timeline.set_position(ratio)

    def _restore_markers(self):
        """Apply previous in/out to the visual timeline immediately."""
        in_r  = self.in_sec  / self.duration_sec
        out_r = self.out_sec / self.duration_sec
        self.timeline.set_in(in_r)
        self.timeline.set_out(out_r)
        self.lbl_in.setText(f"IN:  {self._sec_to_tc(self.in_sec)}")
        self.lbl_out.setText(f"OUT: {self._sec_to_tc(self.out_sec)}")

    def _seek_ratio(self, ratio):
        ms = int(ratio * self.duration_sec * 1000)
        self.player.setPosition(ms)

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
            self.lbl_vol.setStyleSheet("color: #777; font-size: 11px; font-family: Consolas; font-style: italic;")
        else:
            self.lbl_vol.setText(f"{self._last_volume}%")
            self.lbl_vol.setStyleSheet("color: #ccc; font-size: 11px; font-family: Consolas;")

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
        """Safety net for the QVideoWidget: on Windows it can use a native
        overlay surface that doesn't always propagate wheel events up to the
        QDialog. Installing this filter guarantees wheel-over-video also
        controls volume, satisfying the 'works anywhere in the trim panel'
        requirement."""
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Wheel and watched is self.video_widget:
            if self._adjust_volume_by_wheel(event):
                return True
        return super().eventFilter(watched, event)

    def _step_sec(self, delta):
        self.player.pause()
        self.btn_play.setText("▶ PLAY")
        new_ms = max(0, min(int((self.current_sec + delta) * 1000),
                            int(self.duration_sec * 1000)))
        self.player.setPosition(new_ms)

    def _on_pos_changed(self, pos_ms):
        sec = pos_ms / 1000.0
        self._refresh_tc(sec)

    # ---- JKL ----

    def _jkl_j(self):
        """J = play backward (simulate by seeking back repeatedly). Simple impl: step -5 frames."""
        self.player.pause()
        self.btn_play.setText("▶ PLAY")
        self._step_sec(-5 / self.fps)

    def _jkl_k(self):
        """K = pause."""
        self.player.pause()
        self.btn_play.setText("▶ PLAY")

    def _jkl_l(self):
        """L = play forward / speed up (simple: toggle play or resume)."""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶ PLAY")
        else:
            self.player.play()
            self.btn_play.setText("⏸ PAUSE")

    # ---- Actions ----

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶ PLAY")
        else:
            self.player.play()
            self.btn_play.setText("⏸ PAUSE")

    def _quantize_to_source_frame(self, sec):
        """Round a timestamp to the nearest source-frame boundary (1/fps step).
        Critical for frame-perfect trim: QMediaPlayer reports milliseconds, not
        frames, so without quantization the stored in/out can land between two
        source frames and produce off-by-one frame results downstream."""
        if not self.fps or self.fps <= 0:
            return sec
        # Clamp to [0, duration] then snap to nearest source frame.
        sec = max(0.0, min(float(sec), self.duration_sec))
        return round(sec * self.fps) / self.fps

    def set_in(self):
        snapped = self._snap_sec(self.current_sec)            # snap to detected cut, if any
        snapped = self._quantize_to_source_frame(snapped)      # then snap to exact source frame
        self.in_sec = snapped
        self.timeline.set_in(self.in_sec / self.duration_sec)
        self.lbl_in.setText(f"IN:  {self._sec_to_tc(self.in_sec)}")

    def set_out(self):
        snapped = self._snap_sec(self.current_sec)
        snapped = self._quantize_to_source_frame(snapped)
        self.out_sec = snapped
        self.timeline.set_out(self.out_sec / self.duration_sec)
        self.lbl_out.setText(f"OUT: {self._sec_to_tc(self.out_sec)}")

    def clear_trim(self):
        self.in_sec  = 0.0
        self.out_sec = self.duration_sec
        self._restore_markers()

    @Slot(float, float)
    def _on_segment_selected(self, start_ratio, end_ratio):
        """Apply a Shift+Click segment selection to in_sec/out_sec. Both
        endpoints come from the segment-boundary cut PTSs (exclusive OUT, so
        the next scene's first frame is NOT included). We still frame-quantize
        for robustness against any sub-frame drift that snuck in via the cut
        timestamps coming from ffmpeg."""
        new_in  = self._quantize_to_source_frame(start_ratio * self.duration_sec)
        new_out = self._quantize_to_source_frame(end_ratio   * self.duration_sec)
        if new_out <= new_in:
            return
        self.in_sec  = new_in
        self.out_sec = new_out
        # Update the timeline marker positions WITHOUT touching the segment
        # overlay state (manual=False), so the green selection stays painted
        # while the I/O markers move into place.
        self.timeline.set_in (self.in_sec  / self.duration_sec, manual=False)
        self.timeline.set_out(self.out_sec / self.duration_sec, manual=False)
        self.lbl_in .setText(f"IN:  {self._sec_to_tc(self.in_sec)}")
        self.lbl_out.setText(f"OUT: {self._sec_to_tc(self.out_sec)}")
        # Snap playhead to the IN of the selection so the user immediately
        # previews what they just picked.
        self.player.pause()
        self.btn_play.setText("▶ PLAY")
        self.player.setPosition(int(self.in_sec * 1000))

    # ---- Scene detection ----

    def _snap_sec(self, sec):
        """Snap to the nearest detected cut within `snap_threshold_sec`. If snap is
        disabled or no cut is close enough, return `sec` unchanged."""
        if not self.chk_snap.isChecked() or not self.cuts_sec:
            return sec
        # cuts_sec is sorted; do a quick linear scan (small lists in practice).
        nearest = min(self.cuts_sec, key=lambda c: abs(c - sec))
        return nearest if abs(nearest - sec) <= self.snap_threshold_sec else sec

    def _jump_to_cut(self, direction):
        """Move the playhead to the previous (-1) or next (+1) detected cut."""
        if not self.cuts_sec:
            return
        cur = self.current_sec
        if direction < 0:
            candidates = [c for c in self.cuts_sec if c < cur - 0.05]
            target = candidates[-1] if candidates else self.cuts_sec[0]
        else:
            candidates = [c for c in self.cuts_sec if c > cur + 0.05]
            target = candidates[0] if candidates else self.cuts_sec[-1]
        self.player.pause()
        self.btn_play.setText("▶ PLAY")
        self.player.setPosition(int(target * 1000))

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
        self.lbl_scene.setText("Analyzing… 0%")
        worker = SceneDetectorWorker(self.task.path, self.duration_sec, threshold=0.30, parent=self)
        worker.progress.connect(self._on_scene_progress)
        worker.cuts_ready.connect(self._on_scene_done)
        worker.failed.connect(self._on_scene_failed)
        worker.finished.connect(self._on_scene_finished)
        self.scene_worker = worker
        worker.start()

    @Slot(int)
    def _on_scene_progress(self, pct):
        self.lbl_scene.setText(f"Analyzing… {pct}%")

    @Slot(list)
    def _on_scene_done(self, cuts):
        self.cuts_sec = [c for c in cuts if 0.0 <= c <= self.duration_sec]
        ratios = [c / self.duration_sec for c in self.cuts_sec]
        self.timeline.set_cuts(ratios)
        self.lbl_scene.setText(f"{len(self.cuts_sec)} cut(s) detected — use [ / ] to jump")
        # Persist results so reopening the trimmer doesn't re-run ffmpeg.
        save_scene_cache(self._scene_content_key, self._scene_threshold, self.cuts_sec, src_path=self.task.path)

    def _try_warm_start_scenes(self):
        """If the persistent cache has cuts for this source+threshold, load them
        immediately so the user sees the markers without clicking DETECT.
        Silently no-ops when the file can't be fingerprinted or cache is empty."""
        cached = load_scene_cache(self._scene_content_key, self._scene_threshold)
        if not cached:
            return
        self.cuts_sec = [c for c in cached if 0.0 <= c <= self.duration_sec]
        ratios = [c / self.duration_sec for c in self.cuts_sec] if self.duration_sec > 0 else []
        self.timeline.set_cuts(ratios)
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
        if self.scene_worker is not None:
            try: self.scene_worker.deleteLater()
            except Exception: pass
            self.scene_worker = None

    def closeEvent(self, ev):
        # Avoid orphan ffmpeg if the user closes mid-detection.
        if self.scene_worker is not None and self.scene_worker.isRunning():
            self.scene_worker.cancel()
            self.scene_worker.wait(2000)
        self.player.stop()
        super().closeEvent(ev)



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

        info_col.addWidget(self._lbl_chip)
        info_col.addWidget(self._lbl_filename)
        info_col.addWidget(self._lbl_meta)
        info_col.addWidget(self._lbl_filesize)

        top_row.addLayout(info_col, 1)
        lv.addLayout(top_row)
        lv.addStretch(1)
        lv.addSpacing(16)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #1a1a1a;")
        lv.addWidget(divider)
        lv.addSpacing(10)

        bottom_row = QHBoxLayout()
        self.btn_change = QPushButton("↩  Change Video")
        self.btn_change.setStyleSheet(
            f"background: #1a1a1a; border: 1px solid #333; color: #777; border-radius: 3px; padding: 5px 14px;"
        )
        # Reset Status: only meaningful after a run completes (✅/❌). Mirrors
        # the right-click "Reset Status" entry in the batch table so the user
        # can re-run a finished single-mode task without reloading the source.
        self.btn_reset_status = QPushButton("🔄  Reset Status")
        self.btn_reset_status.setStyleSheet(
            f"background: #1a1a1a; border: 1px solid #333; color: {COLOR_WARNING}; "
            f"border-radius: 3px; padding: 5px 14px; font-weight: bold;"
        )
        self.btn_reset_status.hide()
        self.btn_open_out = QPushButton("📂  Open Output Folder")
        self.btn_open_out.setStyleSheet(
            f"background: {COLOR_SUCCESS}; color: white; border-radius: 3px; "
            f"padding: 5px 14px; font-weight: bold;"
        )
        self.btn_open_out.hide()
        bottom_row.addWidget(self.btn_change)
        bottom_row.addStretch()
        bottom_row.addWidget(self.btn_reset_status)
        bottom_row.addWidget(self.btn_open_out)
        lv.addLayout(bottom_row)
        self._stack.addWidget(self._w_loaded)

    # ── Public API ──────────────────────────────────────────────────

    def load_video(self, task):
        """Switch to loaded state showing thumbnail + video metadata."""
        self._lbl_filename.setText(task.filename)
        s = task.specs
        dur = s.get('duration', 0)
        m, sec = divmod(int(dur), 60)
        h_v, m = divmod(m, 60)
        dur_str = f"{h_v:02d}:{m:02d}:{sec:02d}" if h_v > 0 else f"{m:02d}:{sec:02d}"
        self._lbl_meta.setText(
            f"{s.get('w', '?')} × {s.get('h', '?')}  ·  {s.get('fps', '?')} fps  ·  {dur_str}"
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

        self._lbl_chip.setText("  READY  ")
        self._lbl_chip.setStyleSheet(
            f"background: {COLOR_ACCENT}; color: white; border-radius: 3px; "
            f"font-size: 10px; font-weight: bold; padding: 0 6px;"
        )
        self.btn_open_out.hide()
        self.btn_reset_status.hide()
        self._stack.setCurrentIndex(1)

    def mark_done(self):
        """Show the DONE chip and open-output button."""
        self._lbl_chip.setText("  ✅  DONE  ")
        self._lbl_chip.setStyleSheet(
            f"background: {COLOR_SUCCESS}; color: white; border-radius: 3px; "
            f"font-size: 10px; font-weight: bold; padding: 0 6px;"
        )
        self.btn_open_out.show()
        self.btn_reset_status.show()

    def mark_failed(self):
        """Show a failure chip and the reset button so the user can retry."""
        self._lbl_chip.setText("  ❌  FAILED  ")
        self._lbl_chip.setStyleSheet(
            f"background: {COLOR_DANGER}; color: white; border-radius: 3px; "
            f"font-size: 10px; font-weight: bold; padding: 0 6px;"
        )
        self.btn_open_out.hide()
        self.btn_reset_status.show()

    def mark_ready(self):
        """Restore the READY state (used by Reset Status)."""
        self._lbl_chip.setText("  READY  ")
        self._lbl_chip.setStyleSheet(
            f"background: {COLOR_ACCENT}; color: white; border-radius: 3px; "
            f"font-size: 10px; font-weight: bold; padding: 0 6px;"
        )
        self.btn_open_out.hide()
        self.btn_reset_status.hide()

    def reset(self):
        """Return to empty drop state."""
        self._thumb.clear()
        self._thumb.setText("🎬")
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


class Task:
    def __init__(self, path):
        self.path = path; self.filename = os.path.basename(path); self.status = "⌛"
        self.specs = get_video_specs(path)
        # Result of last successful render; kept SEPARATE from `path` so re-runs
        # (Reset Status, Apply settings to selection) still encode the original source.
        self.output_path = None
        # Default Params
        self.vals = {"target": 16.0, "format": "GIF", "mode": "ITERATIVE", "low": 1.5, "up": 0.5, "fps": 15, "qual": 90, "dim_mode": "Original", "dim_perc": 100, "dim_w": 640, "dim_h": 360, "alpha": False, "prio": "Balanced", "trim_start": "00:00:00", "trim_end": "", "keep_iterations": False}

class MiniMath(QHBoxLayout):
    def __init__(self, label, span, step=0.1):
        super().__init__(); self.setSpacing(5); lbl = QLabel(label); lbl.setStyleSheet("color: #aaa; font-size: 10px;")
        span.setButtonSymbols(span.ButtonSymbols.NoButtons)
        bm = QPushButton("-"); bp = QPushButton("+")
        for b in [bm, bp]: 
            b.setFixedSize(24, 24)
            b.setStyleSheet("background: #333; border: 1px solid #666; border-radius: 3px; color: white; font-weight: bold; font-size: 14px; padding: 0px;")
        self.addWidget(lbl, 1); self.addWidget(bm); self.addWidget(span); self.addWidget(bp)
        bm.clicked.connect(lambda: span.setValue(span.value() - step)); bp.clicked.connect(lambda: span.setValue(span.value() + step))

class ResizeBox(QGroupBox):
    def __init__(self, title="📏 OUTPUT DIMENSIONS"):
        super().__init__(title)
        l = QVBoxLayout(self); l.setContentsMargins(10, 15, 10, 10); l.setSpacing(4)
        self.opt = QComboBox(); self.opt.addItems(["Original", "Percentage (%)", "Lock Width", "Lock Height", "Manual WxH"])
        l.addWidget(self.opt)
        
        # Percentage with Slider
        self.p_ctr = QWidget(); p_l = QHBoxLayout(self.p_ctr); p_l.setContentsMargins(0, 0, 0, 0)
        self.slider_perc = QSlider(Qt.Horizontal); self.slider_perc.setRange(1, 100)
        self.s_perc = QSpinBox(); self.s_perc.setRange(1, 100); self.s_perc.setSuffix("%"); self.s_perc.setFixedWidth(60)
        p_l.addWidget(self.slider_perc); p_l.addWidget(self.s_perc)
        self.s_perc.valueChanged.connect(self.slider_perc.setValue); self.slider_perc.valueChanged.connect(self.s_perc.setValue)
        self.s_perc.setValue(100)
        
        self.s_w = QSpinBox(); self.s_w.setRange(1, 7680)
        self.s_h = QSpinBox(); self.s_h.setRange(1, 4320)
        
        for w in [self.p_ctr, self.s_w, self.s_h]: l.addWidget(w)
        
        self.lbl_live = QLabel("-- x --"); self.lbl_live.setAlignment(Qt.AlignCenter)
        self.lbl_live.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 11px; font-weight: bold; padding: 4px; background: #0a1014; border-radius: 3px;")
        l.addWidget(self.lbl_live)
        
        self.opt.currentIndexChanged.connect(self.refresh); self.refresh()
        
    def refresh(self):
        m = self.opt.currentIndex()
        self.p_ctr.setVisible(m == 1); self.s_w.setVisible(m in [2, 4]); self.s_h.setVisible(m in [3, 4])
        
    def get_dict(self):
        return {"dim_mode": self.opt.currentText(), "dim_perc": self.s_perc.value(), "dim_w": self.s_w.value(), "dim_h": self.s_h.value()}
    
    def set_dict(self, d):
        idx = self.opt.findText(d.get("dim_mode", "Original")); self.opt.setCurrentIndex(idx if idx>=0 else 0)
        self.s_perc.setValue(d.get("dim_perc", 100)); self.s_w.setValue(d.get("dim_w", 640)); self.s_h.setValue(d.get("dim_h", 360))

class SettingsPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(440)
        self.setMaximumWidth(500)
        self.setObjectName("settings_panel")
        self.setStyleSheet(f"#settings_panel {{ background: {COLOR_PANEL}; border: 1px solid {COLOR_BORDER}; border-radius: 4px; }}")
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
        l.setContentsMargins(6, 8, 6, 8)   # tighter side margins so buttons don't clip
        l.setSpacing(8)
        
        self.scroll.setWidget(self.content_widget)
        root_l.addWidget(self.scroll)
        
        # --- 0. PRESETS ---
        gb_pre = QFrame(); gb_pre.setStyleSheet(f"background: #1a1a1a; border-radius: 4px; border: 1px solid #333;"); l_pre = QHBoxLayout(gb_pre); l_pre.setContentsMargins(6, 6, 6, 6)
        l_pre.addWidget(QLabel("📂 PRESET:"))
        self.preset = QComboBox(); self.preset.setStyleSheet("font-weight: bold; font-size: 11px; padding: 4px;")
        l_pre.addWidget(self.preset, 1)
        
        self.btn_save_pre = QPushButton("➕"); self.btn_save_pre.setToolTip("Save as NEW Preset")
        self.btn_upd_pre = QPushButton("💾"); self.btn_upd_pre.setToolTip("Update CURRENT Preset (Overwrite)")
        self.btn_del_pre = QPushButton("🗑️"); self.btn_del_pre.setToolTip("Delete Selected Preset")
        self.btn_open_pre = QPushButton("📂"); self.btn_open_pre.setToolTip("Open Presets Folder")
        for b in [self.btn_save_pre, self.btn_upd_pre, self.btn_del_pre, self.btn_open_pre]:
            b.setFixedWidth(28); b.setStyleSheet("border: none; background: #333; border-radius: 3px; padding: 4px;"); l_pre.addWidget(b)
            
        l.addWidget(gb_pre)
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
        self.b_at.setStyleSheet(f"background: #1a1a1a; color: {COLOR_ACCENT}; border: 1px solid {COLOR_ACCENT}; font-size: 10px; font-weight: bold;")
        v_fmt.addWidget(self.b_at)
        
        l.addWidget(self.gb_fmt)
        
        # --- 2. DIMENSIONS & TRIM ---
        self.res_box = ResizeBox("2. OUTPUT DIMENSIONS 📏")
        self.res_box.setStyleSheet(gb_style)
        l.addWidget(self.res_box)
        
        # Trim Box
        self.gb_trim = QGroupBox("✂️ TRIM VIDEO")
        self.gb_trim.setStyleSheet(gb_style)
        v_trim = QVBoxLayout(self.gb_trim)
        
        self.btn_open_trimmer = QPushButton("✂️ OPEN TRIMMER")
        self.btn_open_trimmer.setStyleSheet(f"""
            QPushButton {{ background-color: {COLOR_STATE_INFO}; color: white; font-weight: bold; padding: 6px; border-radius: 3px; }}
            QPushButton:disabled {{ background-color: {COLOR_BG}; color: #555; border: 1px solid #333; }}
        """)
        self.btn_open_trimmer.setToolTip("Open video to precisely set In and Out points")
        
        h_trim_vals = QHBoxLayout()
        # Frame-aware tracking of the active task's fps. Used to render trim
        # values in NLE timecode (HH:MM:SS:FF) for the In/Out fields. Defaults
        # to 25 until a task is loaded; `set_current_fps()` updates it.
        self._current_fps = 25.0
        self.t_start = QLineEdit("00:00:00:00"); self.t_start.setPlaceholderText("Start")
        self.t_start.setToolTip("HH:MM:SS:FF, HH:MM:SS, or seconds (e.g. 5.234). Auto-formats to frames on blur.")
        self.t_start.setMaximumWidth(95)
        self.t_end = QLineEdit(); self.t_end.setPlaceholderText("End")
        self.t_end.setToolTip("HH:MM:SS:FF, HH:MM:SS, or seconds. Empty = end of clip.")
        self.t_end.setMaximumWidth(95)
        # Auto-normalize manual input to HH:MM:SS.ms when the user leaves the field;
        # this keeps storage consistent regardless of how the user typed it.
        self.t_start.editingFinished.connect(lambda: self._normalize_trim_field(self.t_start, "00:00:00"))
        self.t_end.editingFinished.connect(lambda: self._normalize_trim_field(self.t_end, ""))

        h_trim_vals.addWidget(QLabel("In:")); h_trim_vals.addWidget(self.t_start)
        h_trim_vals.addStretch()
        h_trim_vals.addWidget(QLabel("Out:")); h_trim_vals.addWidget(self.t_end)
        
        v_trim.addWidget(self.btn_open_trimmer)
        v_trim.addLayout(h_trim_vals)
        
        # --- 3. ENCODING MODE ---
        self.gb_mode = QGroupBox("3. ENCODING MODE")
        self.gb_mode.setStyleSheet(gb_style)
        v_mode = QVBoxLayout(self.gb_mode); v_mode.setContentsMargins(5, 10, 5, 5)
        self.tabs = QTabWidget(); self.tabs.setObjectName("mode_tabs")
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {COLOR_BORDER}; background: transparent; top: -1px; }}
            QTabBar::tab {{ background: #1a1a1a; color: #888; padding: 6px 16px; border: 1px solid #333; margin-right: 4px; border-top-left-radius: 4px; border-top-right-radius: 4px; font-weight: bold; }}
            QTabBar::tab:selected {{ background: {COLOR_ACCENT}; color: white; border: 1px solid {COLOR_ACCENT}; border-bottom-color: {COLOR_ACCENT}; }}
            QTabBar::tab:!selected:hover {{ background: #2a2a2a; color: white; }}
        """)
        
        # ITERATIVE TAB
        it = QWidget(); iv = QVBoxLayout(it); iv.setContentsMargins(5, 5, 5, 5)
        self.mb_sp = QDoubleSpinBox(); self.mb_sp.setRange(0.01, 2000.0); self.mb_sp.setDecimals(2); self.mb_sp.setValue(16.0); self.mb_sp.setToolTip("Target file size to maintain across the batch (in Megabytes).")
        self.low_sp = QDoubleSpinBox(); self.up_sp = QDoubleSpinBox(); [s.setRange(0.0, 1000.0) for s in [self.low_sp, self.up_sp]]; [s.setDecimals(2) for s in [self.low_sp, self.up_sp]]
        self.low_sp.setToolTip("Minimum buffer size (lower values give tighter size control but worse quality fluctuations).")
        self.up_sp.setToolTip("Maximum buffer size (higher values give more quality leeway).")
        
        iv.addLayout(MiniMath("TARGET SIZE (MB):", self.mb_sp, 0.5))
        
        # Optimize Priority
        pb = QFrame(); pl = QHBoxLayout(pb); pl.setContentsMargins(0, 5, 0, 5)
        pl.addWidget(QLabel("Optimizing for:"))
        self.bg_prio = QButtonGroup(self)
        self.p_bal = QRadioButton("Balanced"); self.p_bal.setToolTip("Balance both visual quality and smooth framerate.")
        self.p_fps = QRadioButton("FPS"); self.p_fps.setToolTip("Prioritize maintaining a high framerate during heavy compression.")
        self.p_ql = QRadioButton("Quality"); self.p_ql.setToolTip("Prioritize visual fidelity, sacrificing frame rate if needed.")
        self.p_bal.setChecked(True); 
        
        rdo_style = """
            QRadioButton { color: white; font-weight: bold; spacing: 5px; font-size: 11px; }
            QRadioButton::indicator { width: 14px; height: 14px; border-radius: 8px; }
            QRadioButton::indicator:unchecked { background-color: #333; border: 2px solid #ddd; }
            QRadioButton::indicator:checked { background-color: #25a0ff; border: 2px solid #fff; }
        """
        for i, r in enumerate([self.p_bal, self.p_fps, self.p_ql]): 
            r.setStyleSheet(rdo_style)
            pl.addWidget(r); self.bg_prio.addButton(r, i)
        iv.addWidget(pb)
        
        # Advanced buffers (collapsible-ish via layout)
        adv_f = QFrame(); adv_l = QVBoxLayout(adv_f); adv_l.setContentsMargins(0, 0, 0, 0)
        adv_l.addLayout(MiniMath("LOWER BUFFER (MB):", self.low_sp, 0.1))
        adv_l.addLayout(MiniMath("UPPER BUFFER (MB):", self.up_sp, 0.1))
        iv.addWidget(adv_f)

        # Knowledge cache toggle: when on, the search engine keeps every iteration
        # on disk inside <source>_ITERATIONS/ and uses them on subsequent runs to
        # warm-start the binary search (or skip it entirely on Tier-1 matches).
        self.chk_keep_iter = QCheckBox("Keep iterations (use as warm-start hint)")
        self.chk_keep_iter.setChecked(False)
        self.chk_keep_iter.setToolTip(
            "Save every attempted iteration in <source>_ITERATIONS/ and use them as\n"
            "a starting hint on the NEXT run for the same source. If a previous file\n"
            "already matches the requested size and FPS, the search is skipped."
        )
        self.chk_keep_iter.setStyleSheet(
            f"QCheckBox {{ color: {COLOR_TEXT}; font-size: 10px; padding: 4px 0; }}"
            f"QCheckBox::indicator {{ width: 13px; height: 13px; border-radius: 3px; }}"
            f"QCheckBox::indicator:unchecked {{ background-color: #2a2a2a; border: 1px solid #555; }}"
            f"QCheckBox::indicator:checked {{ background-color: {COLOR_ACCENT}; border: 1px solid #fff; }}"
        )
        iv.addWidget(self.chk_keep_iter)

        self.tabs.addTab(it, "AUTO OPTIMIZE")
        
        # MANUAL TAB
        mt = QWidget(); mv = QVBoxLayout(mt); mv.setContentsMargins(5, 5, 5, 5)
        self.fps_sp = QSpinBox(); self.qual_sp = QSpinBox(); self.fps_sp.setRange(1, 60); self.qual_sp.setRange(1, 100); self.fps_sp.setValue(15); self.qual_sp.setValue(90)
        self.fps_sp.setToolTip("Force a specific frames per second regardless of file size.")
        self.qual_sp.setToolTip("Force a static quality parameter (1 is worst, 100 is lossless).")
        mv.addLayout(MiniMath("TARGET FPS:", self.fps_sp, 1)); mv.addLayout(MiniMath("QUALITY (1-100):", self.qual_sp, 5)); mv.addStretch()
        self.tabs.addTab(mt, "MANUAL (Fixed)")
        
        v_mode.addWidget(self.tabs)
        l.addWidget(self.gb_mode)
        l.addWidget(self.gb_trim) # Position TRIM below ENCODING MODE natively
        
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
        
        # MAKE IT
        self.go_btn = QPushButton("MAKE IT!"); self.go_btn.setFixedHeight(45)
        self.go_btn.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: white; font-size: 16px; font-weight: bold; border-radius: 4px;")
        root_l.addWidget(self.go_btn)
        
        # --- Advanced: Frame Cache location ---
        # Persistent override for the PNG frame cache root. Default is the OS
        # temp directory; users can point it at a fast SSD or a project folder
        # to keep extracted frames close to the source. Stored in app_settings.json.
        self._app_settings = load_app_settings()
        cfg_cache = self._app_settings.get("cache_dir")
        self.cache_dir = cfg_cache if (cfg_cache and isinstance(cfg_cache, str)) else DEFAULT_CACHE_DIR

        h_cache = QHBoxLayout(); h_cache.setSpacing(4)
        h_cache.addWidget(QLabel("📦 Cache:"))
        self.lbl_cache_path = QLabel(self._cache_label_text())
        self.lbl_cache_path.setStyleSheet("font-size: 9px; color: #888; font-style: italic;")
        self.lbl_cache_path.setToolTip(self.cache_dir)
        self.lbl_cache_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        h_cache.addWidget(self.lbl_cache_path, 1)
        self.btn_cache_set = QPushButton("SET")
        self.btn_cache_open = QPushButton("OPEN")
        self.btn_cache_reset = QPushButton("RESET")
        for b in [self.btn_cache_set, self.btn_cache_open, self.btn_cache_reset]:
            b.setFixedHeight(20); b.setStyleSheet("font-size: 9px; color: #aaa; background: #2a2a2a; border: 1px solid #333; border-radius: 3px; padding: 2px 6px;")
            h_cache.addWidget(b)
        self.btn_cache_set.setToolTip("Choose a custom folder for the PNG frame cache.")
        self.btn_cache_open.setToolTip("Open the cache folder in the file explorer.")
        self.btn_cache_reset.setToolTip(f"Reset back to the default ({DEFAULT_CACHE_DIR}).")
        root_l.addLayout(h_cache)

        # Console & Cache
        h_tools = QHBoxLayout()
        self.c_btn = QPushButton("System Console"); self.btn_purge_cache = QPushButton("Purge Cache")
        for b in [self.c_btn, self.btn_purge_cache]:
            b.setStyleSheet("font-size: 9px; color: #666; border: none; background: transparent;")
            h_tools.addWidget(b)
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
        
        # Presets logic
        self.presets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets")
        if not os.path.exists(self.presets_dir): os.makedirs(self.presets_dir, exist_ok=True)
        self.btn_save_pre.clicked.connect(self.save_preset)
        self.btn_open_pre.clicked.connect(self.open_presets_folder)
        self.preset.currentIndexChanged.connect(self.load_preset)
        self.refresh_presets()
        
        QTimer.singleShot(100, self.load_initial_state)

    def load_initial_state(self):
        self.refresh_presets()
        last = os.path.join(self.presets_dir, "_last_session.json")
        if os.path.exists(last):
            try: 
                with open(last, 'r') as f: self.set_vals(json.load(f))
            except: pass

    def delete_preset(self):
        name = self.preset.currentText()
        if not name or name == "Select Preset..." or name == "Standard Default": return
        path = os.path.join(self.presets_dir, name + ".json")
        if os.path.exists(path):
            try: 
                os.remove(path)
                self.refresh_presets()
            except: pass

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
                 self.gb_mode.setTitle(f"3. ENCODING MODE (Auto: {self.mb_sp.value():.1f}MB | {prio})")
            else: # Manual
                 self.gb_mode.setTitle(f"3. ENCODING MODE (Fix: {self.fps_sp.value()}fps | Q:{self.qual_sp.value()})")
        except: pass

    def open_presets_folder(self):
        os.startfile(self.presets_dir) if os.name == 'nt' else None

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
        customized anything (cleaner sync across machines)."""
        s = dict(self._app_settings or {})
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
            if os.name == 'nt':
                os.startfile(target)
            elif sys.platform == 'darwin':
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        except Exception as e:
            QMessageBox.warning(self, "Open Cache Folder", str(e))

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

    def save_preset(self):
        import PySide6.QtWidgets as qw
        name, ok = qw.QInputDialog.getText(self, "Save New Preset", "Enter preset name:")
        if ok and name.strip():
            clean_name = "".join([c for c in name if c.isalnum() or c in " -_"]).strip()
            path = os.path.join(self.presets_dir, clean_name + ".json")
            try:
                with open(path, 'w') as f: json.dump(self.get_vals(), f, indent=4)
                self.refresh_presets()
                self.preset.setCurrentText(clean_name)
            except: pass

    def update_preset(self):
        name = self.preset.currentText()
        if not name or name == "Select Preset..." or name == "Standard Default": return
        path = os.path.join(self.presets_dir, name + ".json")
        try:
            with open(path, 'w') as f: json.dump(self.get_vals(), f, indent=4)
            QMessageBox.information(self, "Preset Updated", f"Preset '{name}' updated successfully.")
        except Exception as e: QMessageBox.critical(self, "Error", f"Failed to update preset:\n{e}")

    def save_session(self):
        path = os.path.join(self.presets_dir, "_last_session.json")
        try:
            with open(path, 'w') as f: json.dump(self.get_vals(), f, indent=4)
        except: pass

    def set_current_fps(self, fps):
        """Update the fps used to render trim values as HH:MM:SS:FF in the
        manual In/Out fields. Should be called BEFORE set_vals whenever the
        active task changes (load_single, on_table_sel single-row case).
        We do NOT re-format the existing field text here — set_vals is always
        called immediately after, which writes the proper frame-formatted value."""
        try: fps = float(fps)
        except (ValueError, TypeError): fps = 0.0
        if fps > 0:
            self._current_fps = fps

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
            sec_end = parse_trim_to_seconds(raw_end, default=None, fps=self._current_fps)
            trim_end_ms = format_seconds_as_tc(sec_end) if sec_end is not None else ""
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
            self.chk_keep_iter.setChecked(bool(get_val("keep_iterations", "-KEEP_ALL_ITER-", False)))
            
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
            
            # Trim — stored as HH:MM:SS.ms (or legacy seconds string), but displayed
            # in the manual In/Out fields as HH:MM:SS:FF using the active fps.
            raw_start = get_val("trim_start", "-TRIM_START-", "00:00:00")
            raw_end = get_val("trim_end", "-TRIM_END-", "")
            sec_start = parse_trim_to_seconds(raw_start, default=0.0, fps=self._current_fps)
            self.t_start.setText(format_seconds_as_tc_frames(sec_start, self._current_fps) or "00:00:00:00")
            if raw_end:
                sec_end = parse_trim_to_seconds(raw_end, default=None, fps=self._current_fps)
                self.t_end.setText(format_seconds_as_tc_frames(sec_end, self._current_fps) if sec_end is not None else "")
            else:
                self.t_end.setText("")
            
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
        super().__init__(); self.setWindowTitle(f"MakeAGIF {SCRIPT_VERSION} - DEBUG VER"); self.setMinimumSize(1000, 880); self.setStyleSheet(GLOBAL_STYLE)
        cw = QWidget(); self.setCentralWidget(cw); 
        
        # Main Vertical Layout
        main_v = QVBoxLayout(cw); main_v.setContentsMargins(10, 10, 10, 10); main_v.setSpacing(10)
        
        # Content Area (Stack + Settings)
        content_h = QHBoxLayout(); content_h.setSpacing(10)
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
        
        # Table - 11 columns to match v2.7 + Trim. ReorderableTable enables full-row DnD.
        self.table = ReorderableTable(0, 11)
        self.table.setHorizontalHeaderLabels(["#", "Status", "Source File", "Format", "Target MB", "Orig Res", "Tgt Res", "Orig FPS", "Tgt FPS", "Mode", "Trim"])
        self.table.setColumnWidth(0, 28)   # #
        self.table.setColumnWidth(1, 45)   # Status
        self.table.setColumnWidth(2, 200)  # Filename
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
        self.table.horizontalHeader().setStretchLastSection(True)
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
        self.up_btn = QPushButton("💾 Apply settings to selection")
        self.up_btn.setToolTip("Apply current right-panel settings to selected rows")
        self.up_btn.setStyleSheet(f"background: {COLOR_SUCCESS}; color: white; font-weight: bold; {toolbar_style}")
        b_row1.addWidget(self.up_btn)
        
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
        footer = QFrame(); footer.setStyleSheet(f"background: #1a1a1a; border-top: 1px solid {COLOR_BORDER};"); fl = QHBoxLayout(footer); fl.setContentsMargins(10, 8, 10, 8)
        
        self.lbl_bout = QLabel("OUTPUT DESTINATION:"); self.lbl_bout.setStyleSheet("color: #888; font-weight: bold; font-size: 11px;")
        self.chk_bout = QCheckBox("Use Source Folder"); self.chk_bout.setChecked(True); self.chk_bout.setStyleSheet(f"color: {COLOR_ACCENT}; font-weight: bold;")
        self.txt_bout = QLineEdit(); self.txt_bout.setPlaceholderText("Select output folder (batch) or file (single)..."); self.txt_bout.setEnabled(False)
        self.txt_bout.setStyleSheet("padding: 4px;")
        self.txt_bout.setToolTip(
            "Single mode: pick an exact output file (you can rename it).\n"
            "Batch mode: pick a folder; each task auto-derives its filename from its source."
        )
        self.btn_bout = QPushButton("📂 Browse..."); self.btn_bout.setStyleSheet("padding: 4px 8px;"); self.btn_bout.setEnabled(False)
        
        fl.addWidget(self.lbl_bout); fl.addWidget(self.chk_bout); fl.addWidget(self.txt_bout, 1); fl.addWidget(self.btn_bout)
        
        # --- Add layouts to Main Vertical ---
        
        # Content Row (Stack + Settings + Log)
        self.settings = SettingsPanel()
        content_h.addWidget(self.settings)
        
        # Log
        self.log_p = QFrame(); self.log_p.setFixedWidth(260); ll = QVBoxLayout(self.log_p)
        self.view = QTextEdit(); self.view.setReadOnly(True)
        self.view.setStyleSheet(f"background: {COLOR_BG}; color: {COLOR_SUCCESS}; font-family: Consolas; font-size: 10px; border: 1px solid {COLOR_BORDER};")
        
        log_tools = QHBoxLayout()
        self.btn_clr_log = QPushButton("Clear Console"); self.btn_cpy_log = QPushButton("Copy")
        log_tools.addWidget(self.btn_clr_log, 1); log_tools.addWidget(self.btn_cpy_log)
        
        ll.addLayout(log_tools); ll.addWidget(self.view); content_h.addWidget(self.log_p); self.log_p.hide()
        
        main_v.addLayout(content_h, 1) # Content takes available space
        main_v.addWidget(footer) # Footer fixed at bottom
        
        self.setAcceptDrops(True)
        self.worker = None
        self.queue_data = [] # List of Tasks
        self.current_single_task = None
        
        # Connections
        self.settings.batch_en.toggled.connect(self.toggle_mode)
        self.settings.btn_open_trimmer.clicked.connect(self.open_trimmer)
        self.settings.c_btn.clicked.connect(self.toggle_log)
        self.table.itemSelectionChanged.connect(self.on_table_sel)
        self.up_btn.clicked.connect(self.apply_settings_to_sel)
        self.settings.go_btn.clicked.connect(self.start_processing)
        
        # Live Dimension Updates
        self.settings.res_box.opt.currentIndexChanged.connect(self.update_live_dims)
        self.settings.res_box.s_perc.valueChanged.connect(self.update_live_dims)
        self.settings.res_box.s_w.valueChanged.connect(self.update_live_dims)
        self.settings.res_box.s_h.valueChanged.connect(self.update_live_dims)
        
        self.drop_zone.btn_browse.clicked.connect(self.browse_single)
        self.drop_zone.btn_change.clicked.connect(self.browse_single)
        self.drop_zone.btn_open_out.clicked.connect(self._open_single_output_folder)
        self.drop_zone.btn_reset_status.clicked.connect(self._reset_single_status)
        self.drop_zone.file_dropped.connect(lambda p: self.load_single(Task(p)))
        self.btn_clr_log.clicked.connect(self.view.clear)
        self.btn_cpy_log.clicked.connect(self.view.selectAll) # Hacky copy
        self.btn_cpy_log.clicked.connect(self.view.copy)
        
        # Batch panel connections
        self._connect_batch_buttons()
        
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
        
        # Recover existing trim points to restore them in the dialog. Accepts both
        # raw seconds ('5.234') and HH:MM:SS strings, since the user can type either
        # format in the manual field.
        existing_in = parse_trim_to_seconds(task.vals.get("trim_start"), default=0.0)
        raw_end = task.vals.get("trim_end")
        existing_out = parse_trim_to_seconds(raw_end, default=None) if raw_end else None
            
        dlg = TrimDialog(task, self, initial_in_sec=existing_in, initial_out_sec=existing_out)
        if dlg.exec() == QDialog.Accepted:
            in_sec  = dlg.in_sec
            out_sec = dlg.out_sec
            task_fps = task.specs.get('fps', 25) or 25
            # Storage format (HH:MM:SS.ms) — passed verbatim to ffmpeg.
            # Display format (HH:MM:SS:FF) — what the user sees in the manual fields.
            if in_sec <= 0.001 and out_sec >= dlg.duration_sec - 0.001:
                start_storage, end_storage = "00:00:00", ""
                start_display, end_display = "00:00:00:00", ""
            else:
                start_storage = format_seconds_as_tc(in_sec) or "00:00:00"
                end_storage = format_seconds_as_tc(out_sec) if out_sec < dlg.duration_sec else ""
                start_display = format_seconds_as_tc_frames(in_sec, task_fps) or "00:00:00:00"
                end_display = format_seconds_as_tc_frames(out_sec, task_fps) if out_sec < dlg.duration_sec else ""
            self.settings.t_start.setText(start_display)
            self.settings.t_end.setText(end_display)
            if task and hasattr(task, 'vals'):
                task.vals["trim_start"] = start_storage
                task.vals["trim_end"]   = end_storage

            if sel_row is not None:
                self.update_row(sel_row)

    def browse_single(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video Files (*.mp4 *.mov *.avi *.mkv *.webm)")
        if f: self.load_single(Task(f))
        
    def _connect_batch_buttons(self):
        """Called from __init__ to connect batch-related signals."""
        self.chk_bout.toggled.connect(lambda c: (self.txt_bout.setEnabled(not c), self.btn_bout.setEnabled(not c)))
        self.btn_bout.clicked.connect(self.browse_batch_out)
        self.btn_b_add.clicked.connect(self.batch_add_files)
        self.btn_b_rem.clicked.connect(self.batch_remove_sel)
        self.btn_b_rst.clicked.connect(self.batch_reset_sel)
        self.btn_b_clr.clicked.connect(self.batch_clear)
        self.btn_b_sel_all.clicked.connect(self.table.selectAll)
        self.btn_b_sel_inv.clicked.connect(self.invert_selection)
        self.btn_b_up.clicked.connect(lambda: self.move_rows(-1))
        self.btn_b_dn.clicked.connect(lambda: self.move_rows(1))
        self.table.rows_reordered.connect(self.on_rows_dropped)

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
            for f in files: self.add_to_batch(Task(f))
            
    def batch_remove_sel(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()), reverse=True)
        for r in rows:
            self.table.removeRow(r)
            del self.queue_data[r]
        # Refresh row numbers and button state
        for i in range(len(self.queue_data)): self.update_row(i)
        self.update_make_button()
        self.lbl_batch_info.setText(f"{len(self.queue_data)} task(s) remaining")
            
    def batch_reset_sel(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        for r in rows:
            self.queue_data[r].status = "⌛"
            self.update_row(r)
        self.update_make_button()
            
    def batch_clear(self):
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
        
        menu.addAction("📂 Open Source Folder", lambda: os.startfile(os.path.dirname(t.path)) if os.name=='nt' else None)
        menu.addAction("📋 Copy Source Path", lambda: QApplication.clipboard().setText(t.path))
        menu.addSeparator()
        
        # Output actions appear only for tasks that finished successfully
        if t.status == "✅" and getattr(t, "output_path", None) and os.path.exists(t.output_path):
            out_path = t.output_path
            menu.addAction("▶ Open Output File", lambda: self._open_output_path(out_path))
            menu.addAction("📂 Open Output Folder", lambda: os.startfile(os.path.dirname(out_path)) if os.name=='nt' else None)
            menu.addAction("📋 Copy Output Path", lambda: QApplication.clipboard().setText(out_path))
            menu.addSeparator()
             
        menu.addAction("🔄 Reset Status", self.batch_reset_sel)
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
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path], check=False)
            else:
                subprocess.run(['xdg-open', path], check=False)
        except Exception as e:
            self.log(f"[ERROR] Could not open '{path}': {e}")

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
            self.settings.res_box.lbl_live.setText(f"Target: {tw} x {th}")
            self.settings.res_box.lbl_live.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 13px; font-weight: bold; padding: 4px; background: #0a1014; border-radius: 3px;")
        else:
             self.settings.res_box.lbl_live.setText("Invalid Dims")

    def toggle_mode(self, checked):
        mode = self.settings.batch_en.isChecked()
        self.stack.setCurrentIndex(1 if mode else 0)
        
        self.resize(1300 if mode else 1000, 880)
        
        if mode:
            # Batch Mode logic
            self.update_make_button()
            self.on_table_sel()
        else:
            # Single Mode logic
            self.settings.btn_open_trimmer.setEnabled(True)
            self.settings.t_start.setEnabled(True)
            self.settings.t_end.setEnabled(True)
            self.update_live_dims() # Update live dims for single mode
        
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
        # `resize` keeps the window resizable. Using setFixedWidth here would
        # lock the user out of resizing after toggling the console.
        cur_w, cur_h = self.width(), self.height()
        if self.log_p.isVisible():
            self.log_p.hide()
            self.resize(max(self.minimumWidth(), cur_w - 260), cur_h)
        else:
            self.log_p.show()
            self.resize(cur_w + 260, cur_h)
        
    def dragEnterEvent(self, e): e.acceptProposedAction()
    
    def dropEvent(self, e):
        urls = [u.toLocalFile() for u in e.mimeData().urls()]
        if self.settings.batch_en.isChecked():
            for u in urls: self.add_to_batch(Task(u))
        elif urls:
            self.load_single(Task(urls[0]))

    def load_single(self, task):
        self.current_single_task = task
        try:
            self.drop_zone.load_video(task)
            # IMPORTANT: set fps BEFORE set_vals so trim values render with the
            # correct frame count for THIS task.
            self.settings.set_current_fps(task.specs.get('fps', 25) or 25)
            self.settings.set_vals(task.vals)
            self.settings.tabs.setCurrentIndex(0)
            self.update_live_dims()
        except Exception as e:
            QMessageBox.warning(self, "Invalid File", f"Could not analyze the dropped video file: {e}")
            self.current_single_task = None
            self.drop_zone.reset()
        
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
        
        orig_fps = str(t.specs.get('fps', '?'))
        
        # Trim info — render in NLE timecode (HH:MM:SS:FF) using THIS task's fps.
        task_fps = t.specs.get('fps', 25) or 25
        raw_start = v.get("trim_start", "00:00:00")
        raw_end = v.get("trim_end", "")
        start_sec = parse_trim_to_seconds(raw_start, default=0.0, fps=task_fps)
        end_sec   = parse_trim_to_seconds(raw_end,   default=None, fps=task_fps) if raw_end else None
        trim_str = "-"
        if end_sec is not None or start_sec > 0.001:
            start_disp = format_seconds_as_tc_frames(start_sec, task_fps)
            end_disp   = format_seconds_as_tc_frames(end_sec, task_fps) if end_sec is not None else "END"
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
                it.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, c, it)
            else:
                it.setText(val)
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
                # Set fps BEFORE set_vals so the trim fields render in this task's frames.
                self.settings.set_current_fps(t.specs.get('fps', 25) or 25)
                self.settings.set_vals(t.vals)
                self.lbl_batch_info.setText(f"Viewing: {t.filename}  |  {t.specs.get('w','?')}x{t.specs.get('h','?')} @ {t.specs.get('fps','?')} fps")
                self.lbl_batch_info.setStyleSheet(f"color: {COLOR_ACCENT}; font-style: italic; font-size: 10px; padding: 2px 4px; background: #0a1520; border-radius: 3px;")
                self.update_live_dims() # Update live dims for selected batch item
        elif len(sel_rows) > 1:
            self.lbl_batch_info.setText(f"{len(sel_rows)} tasks selected  —  Use 'Save Settings to Selected' to apply current settings to all")
            self.lbl_batch_info.setStyleSheet(f"color: {COLOR_WARNING}; font-style: italic; font-size: 10px; padding: 2px 4px; background: #1a1500; border-radius: 3px;")
            self.update_live_dims() # Update live dims to show multi-selection indicator
        else:
            self.lbl_batch_info.setText("No task selected")
            self.lbl_batch_info.setStyleSheet(f"color: #666; font-style: italic; font-size: 10px; padding: 2px 4px; background: {COLOR_BG}; border-radius: 3px;")
            self.settings.res_box.lbl_live.setText("~ x ~") # Clear live dims
            
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
            try: os.startfile(os.path.dirname(out_path))
            except Exception as e: self.log(f"[ERROR] Could not open folder: {e}")
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
            try: os.startfile(target_dir)
            except Exception as e: self.log(f"[ERROR] Could not open folder: {e}")

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
            if global_out:
                self.current_single_task.vals["_force_out_dir"] = global_out
            if cache_override:
                self.current_single_task.vals["_force_cache_dir"] = cache_override
            tasks = [self.current_single_task]
            
        if not tasks: return QMessageBox.warning(self, "No Tasks", "Nothing to process!")
        
        self.settings.go_btn.setText("STOP"); self.settings.go_btn.setStyleSheet(f"background: {COLOR_DANGER}; color: white; font-weight: bold; border-radius: 4px;")
        if not self.log_p.isVisible(): self.toggle_log()
        
        self.worker = Worker(tasks)
        self.worker.signals.log.connect(self.view.append)
        self.worker.signals.progress.connect(self.settings.pbar.setValue)
        self.worker.signals.status_text.connect(self.settings.lbl_status.setText)
        # Hack to update table directly from thread via lambda (QThread safe because qt signals marshal to main thread)
        self.worker.signals.task_started.connect(self._on_task_started)
        self.worker.signals.task_finished.connect(self._on_task_finished)
        self.worker.signals.finished.connect(self.on_finished)
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
                    self.drop_zone.mark_done()
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
