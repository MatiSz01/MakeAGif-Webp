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
from PySide6.QtCore import Qt, QUrl, QSize, QThread, Signal, QObject, Slot, QTimer
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

    /* Checkboxes */
    QCheckBox {{ color: {COLOR_TEXT_BRIGHT}; spacing: 8px; font-weight: bold; font-size: 12px; }}

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
    try:
        cmd = [FFMPEG_PATH, "-hide_banner", "-i", path]
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, creationflags=0x08000000 if os.name == 'nt' else 0)
        _, err = proc.communicate()
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
    except: pass
    return specs

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
        d = force_dir if force_dir else os.path.dirname(inp)
        n = os.path.splitext(os.path.basename(inp))[0]
        fmt_upper = fmt.upper()
        ext = ".gif" if fmt_upper == "GIF" else ".webp"
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
            iter_folder = os.path.join(dest_dir, f"{base_name}_ITERATIONS")
            os.makedirs(iter_folder, exist_ok=True)
            
            common = {
                "input_path": task.path,
                "source_basename_no_ext": base_name,
                "output_format": p["format"].upper(),  # normalize to uppercase (GIF/WEBP)
                "has_alpha": p.get("alpha", False),
                "play_once": p.get("play_once", False),
                "faster_encode": p.get("fast", False),
                "webp_lossless": p.get("lossless", False),
                "iter_attempts_main_folder": iter_folder, 
                "cache_dir": DEFAULT_CACHE_DIR,
                "target_mb": target_mb,
                "strict_lower_bound": (target_mb - low_m) * 1024 * 1024,
                "strict_upper_bound": (target_mb + up_m) * 1024 * 1024,
                "target_size_bytes": target_mb * 1024 * 1024
            }
            
            final_res = None
            
            self.log(f"  Mode: {p['mode']}  Format: {p.get('format','?').upper()}")
            if p["mode"] == "ITERATIVE":
                final_res = self.run_iterative_search(p, tw, th, common, task.specs, out_path)
            else:
                res = self.generate_animation({**common, "fps": p["fps"], "quality": p["qual"], "width": tw, "height": th, "output_path_for_iter": out_path})
                if res["status"] == "Success": final_res = res
            
            # Cleanup temp dir for iterations
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
        ckey = hashlib.md5(f"{params['input_path']}_{fps}_{w}_{h}_{params.get('has_alpha', False)}".encode()).hexdigest()
        cpath = os.path.join(params["cache_dir"], f"cache_{ckey}")
        marker = os.path.join(cpath, "_SUCCESS.txt")
        
        if not (os.path.exists(cpath) and os.path.exists(marker)):
            self.signals.step.emit("⚙️", "Extracting Frames...")
            if os.path.exists(cpath): shutil.rmtree(cpath)
            os.makedirs(cpath, exist_ok=True)
            vf = [f"fps={fps}"]
            if w > 0 and h > 0: vf.append(f"scale={w}:{h}:flags=lanczos")
            elif w > 0: vf.append(f"scale={w}:-2:flags=lanczos")
            elif h > 0: vf.append(f"scale=-2:{h}:flags=lanczos")
            if params.get("has_alpha"): vf.append("format=rgba")
            
            ff_cmd = [FFMPEG_PATH, "-y"]
            t_start = params.get("trim_start", "").strip()
            t_end = params.get("trim_end", "").strip()
            if t_start and t_start != "00:00:00":
                ff_cmd.extend(["-ss", t_start])
            if t_end:
                ff_cmd.extend(["-to", t_end])
            
            ff_cmd.extend(["-i", params["input_path"], "-vf", ",".join(vf), os.path.join(cpath, "f_%06d.png")])
            if self.run_cmd(ff_cmd) != 0: return res
            with open(marker, 'w') as f: f.write('ok')

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

    def run_iterative_search(self, ui_vals, w, h, common, specs, final_out_path):
        prio = ui_vals.get("prio", "Balanced").lower()
        src_fps = specs.get('fps', 25)
        
        # Determine intent FPS (v2.7 parity)
        if prio == "fps": target_fps = min(50, int(round(src_fps)))
        elif prio == "quality": target_fps = max(8, min(15, int(round(src_fps * 0.6))))
        else: target_fps = max(12, min(22, int(round(src_fps * 0.8))))
        
        min_fps = max(8, min(12, target_fps)) # basic floor
        
        low_q, high_q = 40, 100
        best_res = None
        closest_any = {'file_path': None, 'size': 0, 'diff': float('inf')}
        successful = []
        
        self.signals.step.emit("🔎", "Phase I: Quality Search...")
        self.log(f"--- P1: Quality Binary Search (Target: {common['target_mb']}MB, FPS: {target_fps}) ---")
        
        attempts = 0
        max_attempts = 10
        fps = target_fps
        ext = ".webp" if common["output_format"] == "WEBP" else ".gif"
        
        # Phase 1: Binary Search on Quality
        while low_q <= high_q and attempts < max_attempts:
            self.check_cancel(); attempts += 1
            mid_q = (low_q + high_q) // 2
            
            self.signals.progress.emit(int((attempts/15)*100))
            self.log(f"  > Attempt {attempts}: Testing Q{mid_q}...")
            
            fname = f"tmp_p1_q{mid_q}_fps{fps}"
            opath = os.path.join(common["iter_attempts_main_folder"], fname + ext)
            
            params = {**common, "fps": fps, "quality": mid_q, "width": w, "height": h, "output_path_for_iter": opath}
            res = self.generate_animation(params)
            if res["status"] != "Success": break
            
            sz = res["file_size"]
            res_obj = {'file_path': opath, 'size': sz, 'fps': fps, 'quality': mid_q, 'diff': abs(sz - common['target_size_bytes'])}
            
            if res_obj['diff'] < closest_any['diff']: closest_any = res_obj
            
            if common['strict_lower_bound'] <= sz <= common['strict_upper_bound']:
                successful.append(res_obj)
                best_res = res_obj
                break
            elif sz > common['strict_upper_bound']: high_q = mid_q - 1
            else: low_q = mid_q + 1
            
        # Phase 2: Binary Search on FPS if necessary
        if not best_res and closest_any['file_path']:
             self.signals.step.emit("📉", "Phase II: FPS Adjust...")
             self.log("--- P2: FPS Binary Search ---")
             low_fps, high_fps = min_fps, target_fps - 1
             q_to_use = 40 # Force lower bound quality for fps search
             
             attempts2 = 0
             while low_fps <= high_fps and attempts2 < 8:
                 self.check_cancel(); attempts2 += 1
                 mid_f = (low_fps + high_fps) // 2
                 
                 self.log(f"  > Attempt {attempts + attempts2}: Testing F{mid_f}...")
                 fname = f"tmp_p2_q{q_to_use}_fps{mid_f}"
                 opath = os.path.join(common["iter_attempts_main_folder"], fname + ext)
                 
                 params = {**common, "fps": mid_f, "quality": q_to_use, "width": w, "height": h, "output_path_for_iter": opath}
                 res = self.generate_animation(params)
                 if res["status"] != "Success": break
                 
                 sz = res["file_size"]
                 res_obj = {'file_path': opath, 'size': sz, 'fps': mid_f, 'quality': q_to_use, 'diff': abs(sz - common['target_size_bytes'])}
                 
                 if res_obj['diff'] < closest_any['diff']: closest_any = res_obj
                 
                 if common['strict_lower_bound'] <= sz <= common['strict_upper_bound']:
                     successful.append(res_obj)
                     best_res = res_obj
                     # Could do a secondary Q search here, but keeping it concise
                     break
                 elif sz > common['strict_upper_bound']: high_fps = mid_f - 1
                 else: low_fps = mid_f + 1

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





class TimelineWidget(QWidget):
    """Custom timeline bar that draws In/Out markers and scrub position."""
    seeked = Signal(float)  # 0.0-1.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.pos_ratio = 0.0   # current playhead 0-1
        self.in_ratio  = 0.0   # in point 0-1
        self.out_ratio = 1.0   # out point 0-1

    def paintEvent(self, ev):
        from PySide6.QtGui import QPainter, QLinearGradient, QBrush
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Track background
        p.setBrush(QBrush(QColor("#1a1a2a")))
        p.setPen(Qt.NoPen)
        p.drawRect(0, 0, w, h)

        # Active region (between in-out)
        x_in  = int(self.in_ratio  * w)
        x_out = int(self.out_ratio * w)
        p.setBrush(QBrush(QColor("#1e3a8c")))
        p.drawRect(x_in, 0, x_out - x_in, h)

        # In marker (green)
        p.setPen(QColor("#00c853"))
        p.setBrush(QBrush(QColor("#00c853")))
        p.drawRect(x_in, 0, 3, h)

        # Out marker (red)
        p.setPen(QColor("#ff4444"))
        p.setBrush(QBrush(QColor("#ff4444")))
        p.drawRect(x_out - 3, 0, 3, h)

        # Playhead (white)
        x_ph = int(self.pos_ratio * w)
        p.setPen(QColor("#ffffff"))
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawRect(x_ph - 1, 0, 2, h)
        # Triangle head
        from PySide6.QtGui import QPolygon
        from PySide6.QtCore import QPoint
        tri = QPolygon([QPoint(x_ph-5, 0), QPoint(x_ph+5, 0), QPoint(x_ph, 8)])
        p.drawPolygon(tri)

    def mousePressEvent(self, e):
        ratio = max(0.0, min(1.0, e.x() / self.width()))
        self.seeked.emit(ratio)

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            ratio = max(0.0, min(1.0, e.x() / self.width()))
            self.seeked.emit(ratio)

    def set_position(self, ratio):
        self.pos_ratio = ratio; self.update()

    def set_in(self, ratio):
        self.in_ratio = ratio; self.update()

    def set_out(self, ratio):
        self.out_ratio = ratio; self.update()


class TrimDialog(QDialog):
    """NLE-style trim dialog. Returns in_sec / out_sec (float seconds, framerate-agnostic)."""
    def __init__(self, task, parent=None, initial_in_sec=0.0, initial_out_sec=None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle(f"✂️ Trim NLE — {task.filename}")
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

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # --- Video Widget ---
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background: black;")
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
        
        self.chk_mute = QCheckBox("Mute Audio")
        self.chk_mute.setChecked(True)
        self.chk_mute.setStyleSheet("color: #aaa; font-weight: bold; margin-left: 10px;")
        self.chk_mute.toggled.connect(lambda c: self.audio_output.setVolume(0.0 if c else 0.7))

        # JKL hint label
        hint = QLabel("◀◀ J  |  K Pause  |  L ▶▶      ←/→ frame  |  Shift+←/→ ×10")
        hint.setStyleSheet("color: #555; font-size: 10px;")

        ctrl_row.addWidget(self.btn_in)
        ctrl_row.addWidget(self.btn_play)
        ctrl_row.addWidget(self.btn_out)
        ctrl_row.addWidget(self.btn_clr)
        ctrl_row.addWidget(self.chk_mute)
        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)
        layout.addWidget(hint)

        # --- Dialog buttons ---
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

        # --- Connections ---
        self.timeline.seeked.connect(self._seek_ratio)
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_in.clicked.connect(self.set_in)
        self.btn_out.clicked.connect(self.set_out)
        self.btn_clr.clicked.connect(self.clear_trim)
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

        # Restore previous trim markers
        self._restore_markers()

        # Load first frame
        self.player.play()
        self.player.pause()
        self._seek_ratio(self.in_sec / self.duration_sec)
        self._refresh_tc(self.in_sec)

    # ---- helpers ----

    def _sec_to_tc(self, sec):
        sec = max(0.0, sec)
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        ff = int((sec - int(sec)) * self.fps)
        return f"{int(h):02d}:{int(m):02d}:{int(sec):02d}:{ff:02d}"

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

    def set_in(self):
        self.in_sec = self.current_sec
        self.timeline.set_in(self.in_sec / self.duration_sec)
        self.lbl_in.setText(f"IN:  {self._sec_to_tc(self.in_sec)}")

    def set_out(self):
        self.out_sec = self.current_sec
        self.timeline.set_out(self.out_sec / self.duration_sec)
        self.lbl_out.setText(f"OUT: {self._sec_to_tc(self.out_sec)}")

    def clear_trim(self):
        self.in_sec  = 0.0
        self.out_sec = self.duration_sec
        self._restore_markers()

    def closeEvent(self, ev):
        self.player.stop()
        super().closeEvent(ev)



# --- UI Classes ---


class Task:
    def __init__(self, path):
        self.path = path; self.filename = os.path.basename(path); self.status = "⌛"
        self.specs = get_video_specs(path)
        # Default Params
        self.vals = {"target": 16.0, "format": "GIF", "mode": "ITERATIVE", "low": 1.5, "up": 0.5, "fps": 15, "qual": 90, "dim_mode": "Original", "dim_perc": 100, "dim_w": 640, "dim_h": 360, "alpha": False, "prio": "Balanced", "trim_start": "00:00:00", "trim_end": ""}

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
        
        self.btn_open_trimmer = QPushButton("✂️ OPEN TRIMMER (NLE)")
        self.btn_open_trimmer.setStyleSheet(f"""
            QPushButton {{ background-color: {COLOR_STATE_INFO}; color: white; font-weight: bold; padding: 6px; border-radius: 3px; }}
            QPushButton:disabled {{ background-color: {COLOR_BG}; color: #555; border: 1px solid #333; }}
        """)
        self.btn_open_trimmer.setToolTip("Open video to precisely set In and Out points")
        
        h_trim_vals = QHBoxLayout()
        self.t_start = QLineEdit("00:00:00"); self.t_start.setPlaceholderText("Start")
        self.t_start.setToolTip("Time HH:MM:SS or Frame #"); self.t_start.setMaximumWidth(70)
        self.t_end = QLineEdit(); self.t_end.setPlaceholderText("End")
        self.t_end.setToolTip("Time HH:MM:SS or Frame #"); self.t_end.setMaximumWidth(70)
        
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

    def purge_cache(self):
        try:
            if os.path.exists(DEFAULT_CACHE_DIR):
                shutil.rmtree(DEFAULT_CACHE_DIR)
                os.makedirs(DEFAULT_CACHE_DIR, exist_ok=True)
                QMessageBox.information(self, "Cache Purged", "Temporary cache files cleared.")
        except: pass

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

    def get_vals(self): # Return ALL values
        prio_map = {0:"Balanced", 1:"FPS", 2:"Quality"}
        return {
            "target": self.mb_sp.value(), "format": "GIF" if self.b_gif.isChecked() else "WebP",
            "low": self.low_sp.value(), "up": self.up_sp.value(), "prio": prio_map.get(self.bg_prio.checkedId(), "Balanced"),
            "mode": "ITERATIVE" if self.tabs.currentIndex() == 0 else "MANUAL",
            "fps": self.fps_sp.value(), "qual": self.qual_sp.value(),
            "play_once": not self.chk_loop.isChecked(), "fast": self.chk_fast.isChecked(), "alpha": self.chk_alpha.isChecked(), "lossless": self.chk_loss.isChecked(),
            "trim_start": self.t_start.text(), "trim_end": self.t_end.text(),
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
            
            # Trim
            self.t_start.setText(get_val("trim_start", "-TRIM_START-", "00:00:00"))
            self.t_end.setText(get_val("trim_end", "-TRIM_END-", ""))
            
            print(f"DEBUG set_vals SUCCESS: GIF={is_gif}, Iter={is_iter}, Prio={pm}")
            
        except Exception as e:
            print(f"Error setting values: {e}")
        finally:
            self.update_ui()

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(f"MakeAGIF {SCRIPT_VERSION} - DEBUG VER"); self.setMinimumSize(1000, 880); self.setStyleSheet(GLOBAL_STYLE)
        cw = QWidget(); self.setCentralWidget(cw); 
        
        # Main Vertical Layout
        main_v = QVBoxLayout(cw); main_v.setContentsMargins(10, 10, 10, 10); main_v.setSpacing(10)
        
        # Content Area (Stack + Settings)
        content_h = QHBoxLayout(); content_h.setSpacing(10)
        self.stack = QStackedWidget(); content_h.addWidget(self.stack, 1)
        
        # Panels
        self.single = QFrame()
        self.single.setObjectName("single_frame")
        self.single.setStyleSheet(f"QFrame#single_frame {{ background: {COLOR_BG}; border: 2px dashed #444; border-radius: 8px; }}")
        sl = QVBoxLayout(self.single)
        self.s_info = QLabel("🎬 DROP VIDEO HERE"); self.s_info.setAlignment(Qt.AlignCenter)
        self.s_info.setStyleSheet("font-size: 24px; color: #888; font-weight: bold; border: none;")
        self.btn_browse_single = QPushButton("...or Browse File")
        self.btn_open_out_single = QPushButton("📂 Open Output Folder"); self.btn_open_out_single.hide()
        self.btn_open_out_single.setStyleSheet(f"background: {COLOR_SUCCESS}; color: white; margin-top: 10px; font-weight: bold; border-radius: 4px;")
        
        sl.addStretch(); sl.addWidget(self.s_info); sl.addWidget(self.btn_browse_single, 0, Qt.AlignCenter); sl.addWidget(self.btn_open_out_single, 0, Qt.AlignCenter); sl.addStretch();
        self.stack.addWidget(self.single)
        
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
        
        # Table - 11 columns to match v2.7 + Trim
        self.table = QTableWidget(0, 11)
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
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"QTableWidget {{ alternate-background-color: #0e0e0e; gridline-color: #1a1a1a; }}")
        
        self.table.setColumnHidden(0, True) # Hide redundant # internal column
        
        # Enable drag-drop reordering via vertical header
        self.table.verticalHeader().setSectionsMovable(True)
        self.table.verticalHeader().setDragEnabled(True)
        self.table.verticalHeader().setDragDropMode(QAbstractItemView.InternalMove)
        
        bl.addWidget(self.table, 1)  # Stretch to fill
        
        # --- Batch Toolbar ---
        toolbar_style = "font-size: 11px; padding: 4px 10px;"
        
        b_row1 = QHBoxLayout(); b_row1.setSpacing(5)
        # Add Files (prominent)
        self.btn_b_add = QPushButton("➕ Add Files"); self.btn_b_add.setToolTip("Add video files to queue")
        self.btn_b_add.setStyleSheet(f"background: {COLOR_ACCENT}; color: white; font-weight: bold; {toolbar_style}")
        b_row1.addWidget(self.btn_b_add)
        
        # Save Settings to Selected Taks
        self.up_btn = QPushButton("💾 Apply Settings to Sel")
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
        self.txt_bout = QLineEdit(); self.txt_bout.setPlaceholderText("Select output folder..."); self.txt_bout.setEnabled(False)
        self.txt_bout.setStyleSheet("padding: 4px;")
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
        
        self.btn_browse_single.clicked.connect(self.browse_single)
        self.btn_open_out_single.clicked.connect(lambda: os.startfile(os.path.dirname(self.current_single_task.path)) if self.current_single_task else None)
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
        
        # Recover existing trim points to restore them in the dialog
        try:
            existing_in  = float(task.vals.get("trim_start", 0) or 0)
        except (ValueError, TypeError):
            existing_in = 0.0
        try:
            existing_out = float(task.vals.get("trim_end", 0) or 0)
        except (ValueError, TypeError):
            existing_out = None
            
        dlg = TrimDialog(task, self, initial_in_sec=existing_in, initial_out_sec=existing_out)
        if dlg.exec() == QDialog.Accepted:
            in_sec  = dlg.in_sec
            out_sec = dlg.out_sec
            # Write back to the settings UI fields
            if in_sec <= 0.001 and out_sec >= dlg.duration_sec - 0.001:
                # Full clear
                self.settings.t_start.setText("00:00:00")
                self.settings.t_end.setText("")
                if task and hasattr(task, 'vals'):
                    task.vals["trim_start"] = "00:00:00"
                    task.vals["trim_end"]   = ""
            else:
                self.settings.t_start.setText(f"{in_sec:.3f}")
                self.settings.t_end.setText(f"{out_sec:.3f}" if out_sec < dlg.duration_sec else "")
                if task and hasattr(task, 'vals'):
                    task.vals["trim_start"] = f"{in_sec:.3f}"
                    task.vals["trim_end"]   = f"{out_sec:.3f}" if out_sec < dlg.duration_sec else ""
                    
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
        # Drag-drop reordering via vertical header
        self.table.verticalHeader().sectionMoved.connect(self.on_rows_moved)

    def closeEvent(self, event):
        self.settings.save_session()
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        event.accept()

    def invert_selection(self):
        """Properly invert selection using QItemSelectionModel."""
        total_rows = self.table.rowCount()
        if total_rows == 0: return

        # Get currently selected rows
        current_sel = set(i.row() for i in self.table.selectedItems())
        
        # Determine inverted set
        inverted = [r for r in range(total_rows) if r not in current_sel]
        
        self.table.clearSelection()
        if not inverted: return

        sel_model = self.table.selectionModel()
        for r in inverted:
            for c in range(self.table.columnCount()):
                idx = self.table.model().index(r, c)
                sel_model.select(idx, sel_model.SelectionFlag.Select)
    
    def on_rows_moved(self, logical_index, old_visual, new_visual):
        """Handle row reordering when user drags via vertical header."""
        if old_visual == new_visual: return
        # Move item in queue_data
        item = self.queue_data.pop(old_visual)
        self.queue_data.insert(new_visual, item)
        # Refresh all row numbers
        for i in range(len(self.queue_data)):
            num_item = self.table.item(i, 0)
            if num_item: num_item.setText(str(i + 1))

    # --- Batch Logic ---
    def browse_batch_out(self):
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
        if direction == -1 and rows[0] == 0: return # Can't move up
        if direction == 1 and rows[-1] == len(self.queue_data)-1: return # Can't move down
        
        # Block selection signal during reorder to prevent flickering
        self.table.blockSignals(True)
        
        # Swap data - order depends on direction to avoid index conflicts
        iter_rows = rows if direction == -1 else list(reversed(rows))
        
        new_sel = []
        for r in iter_rows:
            swap_r = r + direction
            self.queue_data[r], self.queue_data[swap_r] = self.queue_data[swap_r], self.queue_data[r]
            new_sel.append(swap_r)
            
        # Refresh all rows
        for i in range(len(self.queue_data)): self.update_row(i)
        
        self.table.blockSignals(False)
        
        def restore_sel():
            self.table.clearSelection()
            self.table.setSelectionMode(QAbstractItemView.MultiSelection)
            for r in new_sel:
                self.table.selectRow(r)
            self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
                
        QTimer.singleShot(40, restore_sel)

    def move_rows_extreme(self, direction):
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows: return
        
        self.table.blockSignals(True)
        
        others = [x for x in range(len(self.queue_data)) if x not in rows]
        
        if direction == -1: # Top
            new_order = rows + others
        else: # Bottom
            new_order = others + rows
            
        # Rebuild list
        new_data = [self.queue_data[i] for i in new_order]
        self.queue_data = new_data
        
        # Refresh
        for i in range(len(self.queue_data)): self.update_row(i)
        
        self.table.blockSignals(False)
        
        def restore_sel_extreme():
            self.table.clearSelection()
            self.table.setSelectionMode(QAbstractItemView.MultiSelection)
            start_idx = 0 if direction == -1 else len(others)
            for i in range(len(rows)):
                self.table.selectRow(start_idx + i)
            self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
                
        QTimer.singleShot(40, restore_sel_extreme)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not rows: return
        
        t = self.queue_data[rows[0]]
        
        menu.addAction("📂 Open Source Folder", lambda: os.startfile(os.path.dirname(t.path)) if os.name=='nt' else None)
        menu.addAction("📋 Copy File Path", lambda: QApplication.clipboard().setText(t.path))
        menu.addSeparator()
        
        if t.status == "✅" and "file_path" in t.__dict__: # Check if we stored result path
             # Requires storing result path in Task object after success, implied todo
             pass
             
        menu.addAction("🔄 Reset Status", self.batch_reset_sel)
        menu.addAction("❌ Remove Selected", self.batch_remove_sel)
        
        menu.exec(self.table.viewport().mapToGlobal(pos))
    
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
        if self.log_p.isVisible(): self.log_p.hide(); self.setFixedWidth(self.width()-260)
        else: self.setFixedWidth(self.width()+260); self.log_p.show()
        
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
            s = task.specs
            self.s_info.setText(f"🎥 {self.current_single_task.filename}\n{s['w']}x{s['h']}  |  {s['fps']} FPS  |  {s['duration']:.1f}s")
            self.s_info.setStyleSheet(f"font-size: 16px; color: {COLOR_SUCCESS}; font-weight: bold;")
            self.settings.set_vals(task.vals) # Apply task's settings to UI
            self.settings.tabs.setCurrentIndex(0) # Switch to auto-optimize
            self.update_live_dims()
        except Exception as e:
            QMessageBox.warning(self, "Invalid File", f"Could not analyze the dropped video file: {e}")
            self.current_single_task = None # Clear task if invalid
            self.s_info.setText("Drop a video here or click Browse")
            self.s_info.setStyleSheet(f"font-size: 18px; color: {COLOR_TEXT_BRIGHT};")
            self.settings.reset_vals() # Reset UI settings
        
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
        
        # Trim info
        t_start = v.get("trim_start", "00:00:00")
        t_end = v.get("trim_end", "")
        trim_str = "-"
        if t_end or t_start != "00:00:00":
            trim_str = f"{t_start} - {t_end if t_end else 'END'}"
            
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
        
        for c, val in enumerate(vals): 
            it = QTableWidgetItem(val)
            it.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            it.setForeground(QColor(row_color))
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)  # Read-only
            self.table.setItem(r, c, it)
    
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
        """Apply current UI settings to ALL selected tasks (v2.7 behavior). Protects ✅ and ⚙️ items."""
        sel_rows = sorted(set(i.row() for i in self.table.selectedItems()))
        if not sel_rows:
            QMessageBox.information(self, "No Selection", "Select one or more tasks in the queue first.")
            return
        
        new_vals = self.settings.get_vals()
        updated = 0
        skipped = 0
        
        for r in sel_rows:
            if r < 0 or r >= len(self.queue_data): continue
            t = self.queue_data[r]
            # Protect finished or running items
            if t.status in ["✅", "⚙️"]:
                skipped += 1
                continue
            t.vals = new_vals.copy()
            t.status = "⌛"  # Reset status since settings changed
            self.update_row(r)
            updated += 1
        
        # Feedback
        msg = f"Updated {updated} task(s)."
        if skipped > 0:
            msg += f" ({skipped} skipped: already finished ✅ or running ⚙️)"
        self.lbl_batch_info.setText(msg)
        self.lbl_batch_info.setStyleSheet(f"color: {COLOR_SUCCESS}; font-style: normal; font-size: 10px; padding: 2px 4px; background: #001a00; border-radius: 3px;")
        self.update_make_button()
            
    def start_processing(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.settings.go_btn.setText("STOPPING...")
            return

        tasks = []
        is_batch = self.settings.batch_en.isChecked()
        global_out = self.txt_bout.text() if self.chk_bout.isChecked() == False and self.txt_bout.text() else None
        
        if is_batch:
            # We must pass the reference to the table item specifically so the worker can update its status
            for i, t in enumerate(self.queue_data):
                if t.status != "✅":
                    t._row_idx = i # Attach row index for status updating later
                    if global_out and os.path.exists(global_out):
                         t.vals["_force_out_dir"] = global_out
                    tasks.append(t)
        elif self.current_single_task:
            # Sync current UI to task
            self.current_single_task.vals = self.settings.get_vals()
            # If not batch but using the folder anyway? In single mode there's no UI for global_out, it uses same dir.
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
         if hasattr(task, '_row_idx'):
             task.status = "✅" if success else "❌"
             if success and dest_path: task.path = dest_path # save output path
             self.update_row(task._row_idx)
        
    def on_finished(self):
        self.settings.go_btn.setText("MAKE IT!"); self.settings.go_btn.setStyleSheet(f"background: {COLOR_ACCENT}; color: white; font-weight: bold; font-size: 18px; border-radius: 4px;")
        self.settings.lbl_status.setText("READY")
        self.settings.pbar.setValue(0)
        self.view.append(">>> JOB FINISHED <<<")
        if not self.settings.batch_en.isChecked() and self.current_single_task:
            self.btn_open_out_single.show()
            self.s_info.setText(f"✅ DONE: {self.current_single_task.filename}")
            self.s_info.setStyleSheet(f"font-size: 18px; color: {COLOR_SUCCESS};")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
