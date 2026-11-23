# -*- coding: utf-8 -*-
"""
Inferno Bin — a classic, professional burning trash bin for your desktop.
Drag any file or folder onto the bin and it burns away.

Designed & Developed by Mohammed El-Shayeb (محمد الشايب)
Computer Vision & AI Engineer — Jordan
© 2026 Mohammed El-Shayeb. All rights reserved.
"""

import json
import math
import os
import random
import shutil
import stat
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

IS_WIN = sys.platform == "win32"


def _fatal(msg):
    """Show an error even when Qt itself is unavailable, and keep a log."""
    try:
        base = os.environ.get("APPDATA") if IS_WIN else os.path.join(os.path.expanduser("~"), ".config")
        d = os.path.join(base or os.path.expanduser("~"), "InfernoBin")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "error_log.txt"), "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}]\n{msg}\n")
    except Exception:
        pass
    if IS_WIN:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg, "Inferno Bin - Error", 0x10)
            return
        except Exception:
            pass
    print(msg, file=sys.stderr)


def _excepthook(etype, value, tb):
    import traceback
    _fatal("".join(traceback.format_exception(etype, value, tb)))


sys.excepthook = _excepthook

try:
    from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QPoint, QPointF, QRectF, Qt, QTimer, QUrl, pyqtSignal
    from PyQt6.QtGui import (QAction, QActionGroup, QBrush, QColor, QDesktopServices, QFont,
                             QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                             QRadialGradient)
    from PyQt6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel, QMenu, QMessageBox,
                                 QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget)
except ImportError as _e:
    _fatal("مكتبة PyQt6 غير مثبتة.\nPyQt6 is not installed.\n\n"
           "شغّل start.bat ليتم تثبيت كل شيء تلقائياً.\n"
           "Run start.bat to install everything automatically.\n\n" + str(_e))
    sys.exit(1)

try:
    from PyQt6.QtMultimedia import QSoundEffect
except Exception:  # sound is optional
    QSoundEffect = None

try:
    from send2trash import send2trash
except ImportError:  # pragma: no cover
    send2trash = None

# ─────────────────────────── Identity ───────────────────────────
APP_NAME = "Inferno Bin"
APP_ID = "InfernoBin"
APP_VERSION = "1.0.0"
AUTHOR = "Mohammed El-Shayeb"
AUTHOR_AR = "محمد الشايب"
AUTHOR_TITLE = "Computer Vision & AI Engineer"
AUTHOR_EMAIL = "mohammed.el.shayeb.ai@gmail.com"
AUTHOR_LINKEDIN = "https://www.linkedin.com/in/mohammed-el-shayeb"
COPYRIGHT = f"© 2026 {AUTHOR}. All rights reserved."

# ─────────────────────────── Geometry (logical units) ───────────────────────────
BASE_W, BASE_H = 240, 330
CX = 120.0
RIM_Y, RIM_RX, RIM_RY = 176.0, 70.0, 15.0
BOT_Y, BOT_RX, BOT_RY = 306.0, 60.0, 12.0
SCALES = {"small": 0.7, "medium": 1.0, "large": 1.3}


def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


# Photographic fire pit (assets/) — falls back to the drawn bin if missing
USE_PHOTO = all(os.path.exists(resource_path("assets", n)) for n in ("pit.png", "flames.png", "icon.png"))
if USE_PHOTO:
    BASE_W, BASE_H = 270, 272
    IMG_X, IMG_Y, IMG_W = 10.0, 56.0, 250.0
    IMG_H = 755 * IMG_W / 900
    _S = IMG_W / 1930.0                       # source-photo pixel → logical unit
    CX = IMG_X + (1010 - 60) * _S             # centre of the pit mouth
    FLAME_X = IMG_X + (1000 - 60) * _S        # axis of the flames
    SEAM_Y = IMG_Y + (760 - 170) * _S         # where the flames leave the pit
    RIM_Y = IMG_Y + (1000 - 170) * _S
    RIM_RX, RIM_RY = 430 * _S, 14.0

# ─────────────────────────── Texts (AR / EN) ───────────────────────────
TEXT = {
    "ar": {
        "mode": "طريقة الحذف",
        "mode_recycle": "نقل إلى سلة المحذوفات (آمن)",
        "mode_permanent": "حرق نهائي (لا يمكن الاسترجاع)",
        "confirm": "تأكيد قبل الحرق",
        "on_top": "فوق كل النوافذ",
        "size": "الحجم",
        "small": "صغير", "medium": "متوسط", "large": "كبير",
        "startup": "التشغيل مع بدء ويندوز",
        "language": "اللغة / Language",
        "sound": "صوت النار",
        "volume": "مستوى الصوت",
        "open_recycle": "فتح سلة المحذوفات",
        "open_log": "سجل المحروقات",
        "hide": "إخفاء السلة", "show": "إظهار السلة",
        "about": "حول البرنامج",
        "exit": "خروج",
        "confirm_title": "تأكيد الحرق",
        "confirm_recycle": "سيتم نقل {n} عنصر إلى سلة المحذوفات:",
        "confirm_perm": "⚠ سيتم حرق {n} عنصر نهائياً ولا يمكن استرجاعه:",
        "more": "… و {n} أخرى",
        "yes": "احرق 🔥", "no": "إلغاء",
        "done": "تم حرق {ok} عنصر",
        "failed": "تعذّر حرق {n} عنصر",
        "protected": "تم تجاهل مسارات نظام محمية:",
        "tooltip": "{app} — اسحب أي ملف أو مجلد هنا لحرقه\nالوضع: {mode}\nإجمالي المحروق: {n}\nبواسطة {author}",
        "no_trash": "مكتبة send2trash غير مثبتة — لا يمكن النقل إلى سلة المحذوفات.",
        "by": "تصميم وتطوير",
        "about_desc": "سلة مهملات مشتعلة كلاسيكية لسطح المكتب.\nاسحب أي ملف أو مجلد إليها لتحرقه فوراً.",
        "close": "إغلاق",
    },
    "en": {
        "mode": "Delete mode",
        "mode_recycle": "Move to Recycle Bin (safe)",
        "mode_permanent": "Burn permanently (no undo)",
        "confirm": "Confirm before burning",
        "on_top": "Always on top",
        "size": "Size",
        "small": "Small", "medium": "Medium", "large": "Large",
        "startup": "Start with Windows",
        "language": "Language / اللغة",
        "sound": "Fire sound",
        "volume": "Volume",
        "open_recycle": "Open Recycle Bin",
        "open_log": "Burn log",
        "hide": "Hide bin", "show": "Show bin",
        "about": "About",
        "exit": "Exit",
        "confirm_title": "Confirm burn",
        "confirm_recycle": "{n} item(s) will be moved to the Recycle Bin:",
        "confirm_perm": "⚠ {n} item(s) will be burned PERMANENTLY:",
        "more": "… and {n} more",
        "yes": "Burn 🔥", "no": "Cancel",
        "done": "{ok} item(s) burned",
        "failed": "{n} item(s) could not be burned",
        "protected": "Skipped protected system paths:",
        "tooltip": "{app} — drop any file or folder here to burn it\nMode: {mode}\nTotal burned: {n}\nby {author}",
        "no_trash": "send2trash is not installed — cannot move to Recycle Bin.",
        "by": "Designed & Developed by",
        "about_desc": "A classic burning trash bin for your desktop.\nDrop any file or folder on it to burn it instantly.",
        "close": "Close",
    },
}

STYLE = """
* { font-family: 'Segoe UI', 'Tahoma', sans-serif; font-size: 10pt; }
QMenu { background: #16171b; color: #eadfc4; border: 1px solid #7a5d24; padding: 6px; }
QMenu::item { padding: 6px 26px 6px 22px; border-radius: 3px; }
QMenu::item:selected { background: #3b2a0f; color: #ffd98a; }
QMenu::item:disabled { color: #8c7c5c; }
QMenu::separator { height: 1px; background: #4a3a1a; margin: 5px 8px; }
QMenu::indicator { width: 12px; height: 12px; left: 6px; }
QMessageBox, QDialog { background: #121317; }
QMessageBox QLabel, QDialog QLabel { color: #eadfc4; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3a2c12, stop:1 #221a0b);
              color: #ffe3a3; border: 1px solid #a07a2c; border-radius: 4px; padding: 6px 18px; min-width: 70px; }
QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #5a4219, stop:1 #33260e); }
QPushButton:pressed { background: #1a1408; }
QToolTip { background: #16171b; color: #eadfc4; border: 1px solid #7a5d24; padding: 5px; }
"""


# ─────────────────────────── Settings ───────────────────────────
def config_dir() -> Path:
    base = os.environ.get("APPDATA") if IS_WIN else os.path.join(Path.home(), ".config")
    d = Path(base or Path.home()) / APP_ID
    d.mkdir(parents=True, exist_ok=True)
    return d


class Settings:
    DEFAULTS = {"v": 2, "mode": "recycle", "confirm": False, "on_top": True, "size": "medium",
                "lang": "ar", "pos": None, "burned": 0,
                "sound": True, "volume": 60}

    def __init__(self):
        self.path = config_dir() / "settings.json"
        self.data = dict(self.DEFAULTS)
        try:
            self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
        except Exception:
            pass
        if self.data.get("v", 1) < 2:  # v2: burn instantly, no question
            self.data.update(v=2, confirm=False)
            self.save()

    def __getitem__(self, k):
        return self.data.get(k, self.DEFAULTS.get(k))

    def __setitem__(self, k, v):
        self.data[k] = v
        self.save()

    def save(self):
        try:
            self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


# ─────────────────────────── Safety ───────────────────────────
def _protected_paths():
    home = Path.home().resolve()
    s = {home}
    for name in ("Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos",
                 "AppData", "OneDrive", "Library", ".config"):
        s.add(home / name)
    if IS_WIN:
        for var in ("SystemRoot", "WINDIR", "ProgramFiles", "ProgramFiles(x86)", "ProgramData",
                    "PUBLIC"):
            v = os.environ.get(var)
            if v:
                s.add(Path(v).resolve())
        s.add(Path(os.environ.get("SystemDrive", "C:") + "\\Users").resolve())
    else:
        for p in ("/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/lib64", "/opt", "/proc",
                  "/root", "/sbin", "/sys", "/usr", "/var", "/System", "/Applications",
                  "/Library", "/Users", "/Volumes"):
            s.add(Path(p))
    return s


PROTECTED = None


def is_protected(path: str) -> bool:
    global PROTECTED
    if PROTECTED is None:
        PROTECTED = _protected_paths()
    try:
        p = Path(path).resolve()
    except Exception:
        return True
    if p.parent == p:  # drive / filesystem root
        return True
    if p in PROTECTED:
        return True
    try:  # anything that contains the user's home folder
        Path.home().resolve().relative_to(p)
        return True
    except ValueError:
        return False


def _on_rm_error(func, path, _exc):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        raise


def burn_path(path: str, mode: str):
    if mode == "recycle":
        if send2trash is None:
            raise RuntimeError("send2trash missing")
        send2trash(path)
        return
    if os.path.isdir(path) and not os.path.islink(path):
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=_on_rm_error)
        else:
            shutil.rmtree(path, onerror=_on_rm_error)
    else:
        try:
            os.remove(path)
        except PermissionError:
            os.chmod(path, stat.S_IWRITE)
            os.remove(path)


class Burner(QObject):
    finished = pyqtSignal(int, list)  # ok count, [(path, error)]

    def start(self, paths, mode, log_path):
        threading.Thread(target=self._work, args=(paths, mode, log_path), daemon=True).start()

    def _work(self, paths, mode, log_path):
        ok, errors = 0, []
        lines = []
        for p in paths:
            try:
                burn_path(p, mode)
                ok += 1
                lines.append(f"{datetime.now():%Y-%m-%d %H:%M:%S}  [{mode}]  {p}")
            except Exception as e:
                errors.append((p, str(e)))
                lines.append(f"{datetime.now():%Y-%m-%d %H:%M:%S}  [FAILED]  {p}  ({e})")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass
        self.finished.emit(ok, errors)


# ─────────────────────────── Fire renderer ───────────────────────────
FLAME_STOPS = [
    (0.00, (255, 246, 215)),
    (0.15, (255, 208, 105)),
    (0.38, (255, 132, 26)),
    (0.65, (210, 50, 10)),
    (0.85, (100, 20, 8)),
    (1.00, (35, 10, 6)),
]


def flame_color(t):
    for i in range(len(FLAME_STOPS) - 1):
        t0, c0 = FLAME_STOPS[i]
        t1, c1 = FLAME_STOPS[i + 1]
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return tuple(int(c0[j] + (c1[j] - c0[j]) * k) for j in range(3))
    return FLAME_STOPS[-1][1]


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "age", "life", "size", "kind", "seed")

    def __init__(self, x, y, vx, vy, life, size, kind):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.age, self.life, self.size, self.kind = 0.0, life, size, kind
        self.seed = random.uniform(0, 6.283)


class Paper:
    """A sheet of paper that falls into the bin and chars on its way down."""
    __slots__ = ("x", "y", "vx", "vy", "rot", "vrot", "char", "w", "h", "delay")

    def __init__(self, delay):
        self.x = CX + random.uniform(-28, 28)
        self.y = 8.0
        self.vx = (CX - self.x) * random.uniform(0.6, 1.2)
        self.vy = random.uniform(30, 60)
        self.rot = random.uniform(-30, 30)
        self.vrot = random.uniform(-260, 260)
        self.char = 0.0
        self.w, self.h = random.uniform(24, 30), random.uniform(30, 36)
        self.delay = delay


def _lin(x1, x2, stops, y=0.0):
    g = QLinearGradient(x1, y, x2, y)
    for pos, col in stops:
        g.setColorAt(pos, QColor(col))
    return g


# Galvanised steel, lit from the upper-left
STEEL = [(0.00, "#25282c"), (0.07, "#4d5258"), (0.17, "#9aa0a7"), (0.25, "#d9dde1"),
         (0.29, "#f4f6f8"), (0.34, "#c3c8cd"), (0.48, "#848a91"), (0.64, "#6c7279"),
         (0.74, "#8d939a"), (0.82, "#6a7077"), (0.93, "#3a3e43"), (1.00, "#1d1f22")]
LIP = [(0.00, "#2a2d31"), (0.10, "#6a7076"), (0.24, "#e9ecef"), (0.30, "#ffffff"),
       (0.38, "#b7bcc2"), (0.60, "#7b8188"), (0.75, "#a3a9af"), (0.90, "#4a4f55"),
       (1.00, "#222427")]


def rx_at(y):
    k = (y - RIM_Y) / (BOT_Y - RIM_Y)
    return RIM_RX + (BOT_RX - RIM_RX) * k, RIM_RY + (BOT_RY - RIM_RY) * k


def band_path(y1, y2):
    r1, e1 = rx_at(y1)
    r2, e2 = rx_at(y2)
    p = QPainterPath()
    p.moveTo(CX - r1, y1)
    p.lineTo(CX - r2, y2)
    p.arcTo(QRectF(CX - r2, y2 - e2, 2 * r2, 2 * e2), 180, 180)
    p.lineTo(CX + r1, y1)
    p.arcTo(QRectF(CX - r1, y1 - e1, 2 * r1, 2 * e1), 0, -180)
    p.closeSubpath()
    return p


def front_arc(y):
    r, e = rx_at(y)
    p = QPainterPath()
    p.moveTo(CX - r, y)
    p.arcTo(QRectF(CX - r, y - e, 2 * r, 2 * e), 180, 180)
    return p


class FireRenderer:
    MAX_PARTICLES = 180

    def __init__(self):
        rnd = random.Random(11)
        self.particles, self.smoke, self.papers = [], [], []
        self.time = 0.0
        self.kick = 0  # papers that just fell in (the widget reacts with a flare)
        self._acc = self._acc_e = self._acc_s = 0.0
        self.body = band_path(RIM_Y, BOT_Y)
        self._cache = {}
        # flame tongues: (u, width, height factor, phase, speed)
        self.tongues = []
        n = 9
        for i in range(n):
            u = -0.82 + 1.64 * i / (n - 1) + rnd.uniform(-0.05, 0.05)
            self.tongues.append((u, rnd.uniform(28, 40) * (1 - 0.3 * abs(u)),
                                 (1 - 0.55 * u * u) * rnd.uniform(0.8, 1.1),
                                 rnd.uniform(0, 6.28), rnd.uniform(4.5, 8.5)))
        self.tongues.sort(key=lambda t: -abs(t[0]))
        self.coals = [(CX + rnd.uniform(-0.8, 0.8) * RIM_RX * 0.8,
                       RIM_Y + rnd.uniform(0.0, 0.6) * RIM_RY, rnd.uniform(3, 7),
                       rnd.uniform(0, 6.28)) for _ in range(14)]

    # ───── simulation ─────
    def drop_papers(self, n):
        for i in range(max(1, min(n, 5))):
            self.papers.append(Paper(i * 0.12))

    def update(self, dt, intensity):
        self.time += dt
        I = min(intensity, 3.2)
        self._acc += (20 + 28 * I) * dt
        while self._acc >= 1:
            self._acc -= 1
            if len(self.particles) < self.MAX_PARTICLES:
                self._spawn_flame(I)
        self._acc_e += (2 + 9 * I) * dt
        while self._acc_e >= 1:
            self._acc_e -= 1
            self._spawn_ember(I)
        self._acc_s += (1.2 + max(0.0, I - 0.8) * 7) * dt
        while self._acc_s >= 1:
            self._acc_s -= 1
            self.smoke.append(Particle(CX + random.uniform(-18, 18), RIM_Y - (40 + 40 * I),
                                       random.uniform(-5, 5), -random.uniform(22, 40),
                                       random.uniform(1.8, 2.8), random.uniform(10, 16), 2))

        alive = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.life:
                continue
            if p.kind == 0:
                p.vx += (math.sin(self.time * 7 + p.seed + p.y * 0.05) * 34 + (CX - p.x) * 2.0) * dt
                p.vy *= (1 - 0.25 * dt)
            else:
                p.vx += math.sin(self.time * 4 + p.seed) * 40 * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            alive.append(p)
        self.particles = alive

        sm = []
        for s in self.smoke:
            s.age += dt
            if s.age < s.life:
                s.x += (s.vx + math.sin(self.time * 0.9 + s.seed) * 9) * dt
                s.y += s.vy * dt
                sm.append(s)
        self.smoke = sm

        papers = []
        for pa in self.papers:
            if pa.delay > 0:
                pa.delay -= dt
                papers.append(pa)
                continue
            pa.vy = min(pa.vy + 520 * dt, 320)
            pa.vx += (CX - pa.x) * 3 * dt
            pa.x += pa.vx * dt
            pa.y += pa.vy * dt
            pa.rot += pa.vrot * dt
            if pa.y > RIM_Y - 95:
                pa.char = min(1.0, pa.char + dt * 3.2)
            if pa.y >= RIM_Y + 2:
                self.kick += 1
                for _ in range(14):
                    self._spawn_flame(3.0, pa.x)
                for _ in range(10):
                    self._spawn_ember(3.0, pa.x)
            else:
                papers.append(pa)
        self.papers = papers

    def _spawn_flame(self, I, x=None):
        spread = RIM_RX * 0.6
        u = max(-1.0, min(1.0, random.gauss(0, 0.45)))
        k = 0.6 + 0.4 * I
        self.particles.append(Particle(
            (x if x is not None else CX + u * spread) + random.uniform(-6, 6),
            RIM_Y - (14 + 22 * I) * random.uniform(0.3, 1.0),
            random.uniform(-6, 6), -random.uniform(40, 85) * k * (1 - 0.35 * abs(u)),
            random.uniform(0.35, 0.7) * (0.8 + 0.2 * I),
            random.uniform(5, 10) * (0.8 + 0.2 * I), 0))

    def _spawn_ember(self, I, x=None):
        self.particles.append(Particle(
            x if x is not None else CX + random.uniform(-RIM_RX * 0.5, RIM_RX * 0.5),
            RIM_Y - random.uniform(10, 40),
            random.uniform(-28, 28), -random.uniform(70, 150) * (0.7 + 0.3 * I),
            random.uniform(0.9, 1.9), random.uniform(1.0, 2.0), 1))

    # ───── static (pre-rendered) layers ─────
    def _layers(self, k):
        key = round(k, 3)
        if key not in self._cache:
            self._cache.clear()
            self._cache[key] = (self._render_layer(k, self._paint_back_lip),
                                self._render_layer(k, self._paint_front))
        return self._cache[key]

    @staticmethod
    def _render_layer(k, fn):
        pm = QPixmap(max(1, int(BASE_W * k)), max(1, int(BASE_H * k)))
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.scale(k, k)
        fn(p)
        p.end()
        pm.setDevicePixelRatio(k)
        return pm

    def _paint_back_lip(self, p):
        rim = QRectF(CX - RIM_RX, RIM_Y - RIM_RY, 2 * RIM_RX, 2 * RIM_RY)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(18, 19, 21), 8.5))
        p.drawArc(rim, 0, 180 * 16)
        p.setPen(QPen(QBrush(_lin(CX - RIM_RX, CX + RIM_RX, LIP)), 6))
        p.drawArc(rim, 0, 180 * 16)
        p.setPen(QPen(QColor(255, 255, 255, 60), 1.2))
        p.drawArc(rim.adjusted(1, -2, -1, 0), 30 * 16, 120 * 16)

    def _paint_front(self, p):
        rnd = random.Random(5)
        body = self.body
        # contact shadow on the desktop
        p.setPen(Qt.PenStyle.NoPen)
        for rr, a in ((92, 50), (76, 70), (64, 90)):
            sh = QRadialGradient(QPointF(CX, BOT_Y + 6), rr)
            sh.setColorAt(0, QColor(0, 0, 0, a))
            sh.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(sh)
            p.drawEllipse(QPointF(CX, BOT_Y + 6), rr, rr * 0.17)

        # side handles (behind the body edge)
        for side in (-1, 1):
            y = RIM_Y + 26
            x = CX + side * (rx_at(y)[0] - 2)
            h = QPainterPath()
            h.moveTo(x, y - 9)
            h.cubicTo(x + side * 19, y - 10, x + side * 19, y + 12, x, y + 11)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(20, 21, 23), 6.5, cap=Qt.PenCapStyle.RoundCap))
            p.drawPath(h)
            p.setPen(QPen(QColor("#9ea4ab"), 4.2, cap=Qt.PenCapStyle.RoundCap))
            p.drawPath(h)
            p.setPen(QPen(QColor(255, 255, 255, 150), 1.2))
            p.drawPath(h.translated(side * -0.6, -1.0))

        # body
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_lin(CX - RIM_RX, CX + RIM_RX, STEEL))
        p.drawPath(body)

        p.save()
        p.setClipPath(body)
        # galvanised mottling
        tex = QPixmap(60, 80)
        tex.fill(Qt.GlobalColor.transparent)
        tp = QPainter(tex)
        for _ in range(900):
            v = rnd.randint(0, 255)
            tp.setPen(Qt.PenStyle.NoPen)
            tp.setBrush(QColor(v, v, v, rnd.randint(4, 14)))
            s = rnd.uniform(0.8, 2.5)
            tp.drawEllipse(QPointF(rnd.uniform(0, 60), rnd.uniform(0, 80)), s, s * rnd.uniform(0.6, 1.4))
        tp.end()
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.drawPixmap(QRectF(CX - RIM_RX, RIM_Y - RIM_RY, 2 * RIM_RX, BOT_Y - RIM_Y + 2 * RIM_RY),
                     tex, QRectF(0, 0, 60, 80))
        # fine vertical brushing
        for _ in range(70):
            u = rnd.uniform(-0.98, 0.98)
            y1, y2 = sorted((rnd.uniform(RIM_Y, BOT_Y), rnd.uniform(RIM_Y, BOT_Y)))
            p.setPen(QPen(QColor(255, 255, 255, rnd.randint(6, 22)) if rnd.random() < 0.5
                          else QColor(0, 0, 0, rnd.randint(8, 25)), 0.6))
            p.drawLine(QPointF(CX + u * rx_at(y1)[0], y1), QPointF(CX + u * rx_at(y2)[0], y2))
        # corrugated ridges (embossed)
        for y in (RIM_Y + 44, BOT_Y - 44):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 70))
            p.drawPath(band_path(y - 7, y - 4))
            p.setBrush(QColor(255, 255, 255, 70))
            p.drawPath(band_path(y - 4, y))
            p.setBrush(QColor(255, 255, 255, 25))
            p.drawPath(band_path(y, y + 3))
            p.setBrush(QColor(0, 0, 0, 95))
            p.drawPath(band_path(y + 3, y + 8))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(255, 255, 255, 110), 0.9))
            p.drawPath(front_arc(y - 4))
            p.setPen(QPen(QColor(0, 0, 0, 120), 0.9))
            p.drawPath(front_arc(y + 8))
        # seam
        u = 0.62
        p.setPen(QPen(QColor(0, 0, 0, 60), 1.4))
        p.drawLine(QPointF(CX + u * RIM_RX, RIM_Y + RIM_RY * 0.8), QPointF(CX + u * BOT_RX, BOT_Y + BOT_RY * 0.8))
        p.setPen(QPen(QColor(255, 255, 255, 35), 0.8))
        p.drawLine(QPointF(CX + u * RIM_RX + 1.6, RIM_Y + RIM_RY * 0.8), QPointF(CX + u * BOT_RX + 1.4, BOT_Y + BOT_RY * 0.8))
        # soot from the fire, darkest under the lip
        p.setPen(Qt.PenStyle.NoPen)
        sg = QLinearGradient(0, RIM_Y, 0, RIM_Y + 46)
        sg.setColorAt(0, QColor(10, 8, 6, 170))
        sg.setColorAt(0.35, QColor(15, 12, 10, 70))
        sg.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(sg)
        p.drawRect(QRectF(0, RIM_Y, BASE_W, 50))
        for _ in range(16):
            x = CX + rnd.uniform(-1, 1) * RIM_RX * 0.95
            r = rnd.uniform(8, 18)
            y = RIM_Y + RIM_RY * 0.9 + rnd.uniform(0, 14)
            rg = QRadialGradient(QPointF(x, y), r)
            rg.setColorAt(0, QColor(8, 6, 5, rnd.randint(50, 110)))
            rg.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(rg)
            p.drawEllipse(QPointF(x, y), r * 0.7, r * 1.4)
        # base darkening (ambient occlusion)
        bg = QLinearGradient(0, BOT_Y - 30, 0, BOT_Y + BOT_RY)
        bg.setColorAt(0, QColor(0, 0, 0, 0))
        bg.setColorAt(1, QColor(0, 0, 0, 120))
        p.setBrush(bg)
        p.drawRect(QRectF(0, BOT_Y - 30, BASE_W, 50))
        p.restore()

        # bottom rolled edge
        p.setBrush(Qt.BrushStyle.NoBrush)
        bot = front_arc(BOT_Y - 3)
        p.setPen(QPen(QColor(20, 21, 23), 6))
        p.drawPath(bot)
        p.setPen(QPen(QBrush(_lin(CX - BOT_RX, CX + BOT_RX, LIP)), 3.6))
        p.drawPath(bot)

        # front rolled lip
        lip = front_arc(RIM_Y)
        p.setPen(QPen(QColor(16, 17, 19), 10, cap=Qt.PenCapStyle.RoundCap))
        p.drawPath(lip)
        p.setPen(QPen(QBrush(_lin(CX - RIM_RX, CX + RIM_RX, LIP)), 7.2, cap=Qt.PenCapStyle.RoundCap))
        p.drawPath(lip)
        p.setPen(QPen(QColor(255, 255, 255, 170), 1.3))
        p.drawPath(lip.translated(0, -2.0))
        p.setPen(QPen(QColor(0, 0, 0, 90), 1.0))
        p.drawPath(lip.translated(0, 3.0))

    # ───── dynamic painting ─────
    def paint(self, p: QPainter, intensity: float, shake: float = 0.0, k: float = 1.0):
        I = min(intensity, 3.2)
        t = self.time
        flick = 0.85 + 0.1 * math.sin(t * 13.0) + 0.05 * math.sin(t * 29.0 + 1.3)
        back_lip, front = self._layers(k)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.save()
        if shake > 0:
            p.translate(math.sin(t * 70) * shake * 2.5, math.cos(t * 55) * shake)
        rim = QRectF(CX - RIM_RX, RIM_Y - RIM_RY, 2 * RIM_RX, 2 * RIM_RY)
        p.setPen(Qt.PenStyle.NoPen)

        # warm light cast around the fire
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        gr = min(118.0, 80 + 12 * I)
        g = QRadialGradient(QPointF(CX, RIM_Y - 34), gr)
        g.setColorAt(0, QColor(255, 120, 30, int(min(80, (20 + 20 * I) * flick))))
        g.setColorAt(0.55, QColor(255, 90, 10, int(min(26, 6 + 7 * I))))
        g.setColorAt(1, QColor(255, 60, 0, 0))
        p.setBrush(g)
        p.drawEllipse(QPointF(CX, RIM_Y - 34), gr, gr)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # interior: charred inner wall + glowing coals
        inner = rim.adjusted(4, 3, -4, -3)
        ig = QLinearGradient(0, inner.top(), 0, inner.bottom())
        ig.setColorAt(0, QColor(36, 30, 27))
        ig.setColorAt(0.5, QColor(18, 13, 10))
        ig.setColorAt(1, QColor(8, 6, 5))
        p.setBrush(ig)
        p.drawEllipse(inner)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        heat = min(1.0, (0.45 + 0.22 * I) * flick)
        cg = QRadialGradient(QPointF(CX, RIM_Y + 5), RIM_RX * 0.85)
        cg.setColorAt(0, QColor(255, 140, 40, int(230 * heat)))
        cg.setColorAt(0.5, QColor(200, 50, 8, int(160 * heat)))
        cg.setColorAt(1, QColor(80, 10, 0, 0))
        p.setBrush(cg)
        p.drawEllipse(inner)
        for (x, y, r, ph) in self.coals:
            b = 0.55 + 0.45 * math.sin(t * 3 + ph)
            eg = QRadialGradient(QPointF(x, y), r)
            eg.setColorAt(0, QColor(255, 200, 90, int(170 * b * heat)))
            eg.setColorAt(1, QColor(255, 60, 0, 0))
            p.setBrush(eg)
            p.drawEllipse(QPointF(x, y), r, r * 0.6)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        p.drawPixmap(QPointF(0, 0), back_lip)
        # firelight on the back lip
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 120, 40, int(min(120, 40 + 30 * I) * flick)), 3))
        p.drawArc(rim.adjusted(0, 1, 0, 1), 20 * 16, 140 * 16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # smoke
        for s in self.smoke:
            st = s.age / s.life
            r = s.size * (1 + 2.2 * st)
            a = int(48 * math.sin(math.pi * st))
            sg = QRadialGradient(QPointF(s.x, s.y), r)
            sg.setColorAt(0, QColor(62, 58, 56, a))
            sg.setColorAt(1, QColor(40, 40, 40, 0))
            p.setBrush(sg)
            p.drawEllipse(QPointF(s.x, s.y), r, r)

        # papers falling in
        for pa in self.papers:
            if pa.delay <= 0:
                self._paint_paper(p, pa)

        # flames
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        H0 = min(150.0, 30 + 40 * I)
        layers = (
            (1.35, 1.08, ((255, 90, 10, 45), (220, 40, 0, 20), (120, 15, 0, 0))),     # soft halo
            (1.00, 1.00, ((255, 96, 12, 165), (230, 52, 4, 105), (130, 18, 0, 0))),   # outer
            (0.66, 0.78, ((255, 170, 45, 160), (255, 112, 15, 90), (255, 80, 0, 0))),  # mid
            (0.36, 0.50, ((255, 240, 200, 170), (255, 205, 100, 105), (255, 170, 60, 0))),  # core
        )
        for (u, w0, hf, ph, sp) in self.tongues:
            cx = CX + u * RIM_RX * 0.62
            du = (cx - CX) / RIM_RX
            base = RIM_Y + RIM_RY * math.sqrt(max(0.0, 1 - du * du)) + 2
            h = H0 * hf * (0.78 + 0.16 * math.sin(t * sp + ph) + 0.08 * math.sin(t * sp * 2.3 + ph * 1.7))
            sway = math.sin(t * 3.1 + ph) * w0 * 0.35 + math.sin(t * 7.3 + ph) * w0 * 0.12
            sway += (CX - cx) * 0.25
            wob = math.sin(t * 9.0 + ph * 2) * w0 * 0.12
            for ws, hs, cols in layers:
                w, hh = w0 * ws * (0.85 + 0.15 * min(I, 2)), h * hs
                x0, x1 = cx - w / 2, cx + w / 2
                tx, ty = cx + sway * hs, base - hh
                path = QPainterPath()
                path.moveTo(x0, base)
                path.cubicTo(x0 - w * 0.18, base - hh * 0.38, tx - w * 0.28 + wob, base - hh * 0.72, tx, ty)
                path.cubicTo(tx + w * 0.28 - wob, base - hh * 0.72, x1 + w * 0.18, base - hh * 0.38, x1, base)
                path.closeSubpath()
                fg = QLinearGradient(0, base, 0, ty)
                c0 = cols[0]
                fg.setColorAt(0.0, QColor(c0[0], int(c0[1] * 0.6), int(c0[2] * 0.5), c0[3] // 3))
                fg.setColorAt(0.22, QColor(*c0))
                fg.setColorAt(0.55, QColor(*cols[1]))
                fg.setColorAt(1.0, QColor(*cols[2]))
                p.setBrush(fg)
                p.drawPath(path)

        # flickering licks + embers
        for q in self.particles:
            qt = q.age / q.life
            if q.kind == 0:
                r = q.size * (1.0 - 0.5 * qt)
                a = int(140 * (1 - qt) ** 1.3)
                c = flame_color(min(1.0, 0.2 + qt))
                fg = QRadialGradient(QPointF(q.x, q.y), r * 1.3)
                fg.setColorAt(0, QColor(c[0], c[1], c[2], a))
                fg.setColorAt(1, QColor(c[0], c[1], c[2], 0))
                p.setBrush(fg)
                p.drawEllipse(QPointF(q.x, q.y), r * 0.8, r * 1.3)
            else:
                fl = 0.6 + 0.4 * math.sin(t * 30 + q.seed * 5)
                a = int(255 * (1 - qt) * fl)
                eg = QRadialGradient(QPointF(q.x, q.y), q.size * 3)
                eg.setColorAt(0, QColor(255, 235, 160, a))
                eg.setColorAt(0.3, QColor(255, 140, 40, a // 2))
                eg.setColorAt(1, QColor(255, 80, 0, 0))
                p.setBrush(eg)
                p.drawEllipse(QPointF(q.x, q.y), q.size * 3, q.size * 3)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # can body + front lip (pre-rendered)
        p.drawPixmap(QPointF(0, 0), front)

        # firelight reflected on the metal
        p.save()
        p.setClipPath(self.body)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        rg = QRadialGradient(QPointF(CX, RIM_Y - 22), 125)
        rg.setColorAt(0, QColor(255, 110, 25, int(min(70, (16 + 16 * I) * flick))))
        rg.setColorAt(1, QColor(255, 60, 0, 0))
        p.setBrush(rg)
        p.drawRect(QRectF(0, RIM_Y - 20, BASE_W, BOT_Y - RIM_Y + 40))
        p.restore()
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 130, 50, int(min(110, 30 + 26 * I) * flick)), 2.0))
        p.drawPath(front_arc(RIM_Y).translated(0, -2.2))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.restore()

    @staticmethod
    def _paint_paper(p, pa):
        c = pa.char
        if c < 0.5:
            k = c / 0.5
            col = QColor(int(246 - 70 * k), int(243 - 110 * k), int(236 - 160 * k))
        else:
            k = (c - 0.5) / 0.5
            col = QColor(int(176 - 150 * k), int(133 - 112 * k), int(76 - 60 * k))
        shrink = 1 - 0.35 * c
        w, h = pa.w * shrink, pa.h * shrink
        p.save()
        p.translate(pa.x, pa.y)
        p.rotate(pa.rot)
        p.setPen(QPen(QColor(0, 0, 0, 60), 0.6))
        p.setBrush(col)
        sheet = QPainterPath()
        f = w * 0.25
        sheet.moveTo(-w / 2, -h / 2)
        sheet.lineTo(w / 2 - f, -h / 2)
        sheet.lineTo(w / 2, -h / 2 + f)
        sheet.lineTo(w / 2, h / 2)
        sheet.lineTo(-w / 2, h / 2)
        sheet.closeSubpath()
        p.drawPath(sheet)
        if c < 0.6:
            p.setPen(QPen(QColor(90, 100, 120, int(150 * (1 - c / 0.6))), 0.9))
            for i in range(5):
                y = -h / 2 + h * (0.28 + 0.13 * i)
                p.drawLine(QPointF(-w / 2 + 4, y), QPointF(w / 2 - 4 - (6 if i == 4 else 0), y))
            p.setBrush(col.darker(115))
            corner = QPainterPath()
            corner.moveTo(w / 2 - f, -h / 2)
            corner.lineTo(w / 2 - f, -h / 2 + f)
            corner.lineTo(w / 2, -h / 2 + f)
            corner.closeSubpath()
            p.drawPath(corner)
        if c > 0.15:
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(255, 140, 30, int(220 * min(1.0, c * 1.5))), 1.8))
            p.drawPath(sheet)
        p.restore()


class PhotoRenderer(FireRenderer):
    """Real photographed fire pit; the flames are animated, the stones lit by them."""

    def __init__(self):
        super().__init__()
        self.pit = QPixmap(resource_path("assets", "pit.png"))
        self.flames = QPixmap(resource_path("assets", "flames.png"))
        self.flames_m = QPixmap.fromImage(self.flames.toImage().mirrored(True, False))
        # orange firelight, shaped like the stones
        self.pit_glow = QPixmap(self.pit.size())
        self.pit_glow.fill(Qt.GlobalColor.transparent)
        gp = QPainter(self.pit_glow)
        gp.drawPixmap(0, 0, self.pit)
        gp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        sx = self.pit.width() / 1930.0
        g = QRadialGradient(QPointF((1010 - 60) * sx, (960 - 170) * sx), 700 * sx)
        g.setColorAt(0, QColor(255, 130, 40, 255))
        g.setColorAt(0.5, QColor(255, 90, 20, 140))
        g.setColorAt(1, QColor(255, 60, 0, 0))
        gp.fillRect(self.pit_glow.rect(), g)
        gp.end()

    def _flame_layer(self, p, pm, rect, opacity, sx, sy, shear):
        p.save()
        p.translate(FLAME_X, SEAM_Y)
        p.shear(shear, 0)
        p.scale(sx, sy)
        p.translate(-FLAME_X, -SEAM_Y)
        p.setOpacity(opacity)
        p.drawPixmap(rect, pm, QRectF(pm.rect()))
        p.restore()

    def paint(self, p: QPainter, intensity: float, shake: float = 0.0, k: float = 1.0):
        I = min(intensity, 3.2)
        t = self.time
        flick = 0.85 + 0.1 * math.sin(t * 13.0) + 0.05 * math.sin(t * 29.0 + 1.3)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.save()
        if shake > 0:
            p.translate(math.sin(t * 70) * shake * 2.5, math.cos(t * 55) * shake)
        p.setPen(Qt.PenStyle.NoPen)
        rect = QRectF(IMG_X, IMG_Y, IMG_W, IMG_H)

        # warm light around the fire
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        gr = min(128.0, 82 + 14 * I)
        g = QRadialGradient(QPointF(FLAME_X, SEAM_Y - 8), gr)
        g.setColorAt(0, QColor(255, 120, 30, int(min(85, (22 + 20 * I) * flick))))
        g.setColorAt(0.55, QColor(255, 90, 10, int(min(26, 6 + 7 * I))))
        g.setColorAt(1, QColor(255, 60, 0, 0))
        p.setBrush(g)
        p.drawEllipse(QPointF(FLAME_X, SEAM_Y - 8), gr, gr)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # smoke
        for sm in self.smoke:
            st = sm.age / sm.life
            r = sm.size * (1 + 2.2 * st)
            a = int(42 * math.sin(math.pi * st))
            sg = QRadialGradient(QPointF(sm.x, sm.y), r)
            sg.setColorAt(0, QColor(70, 66, 64, a))
            sg.setColorAt(1, QColor(40, 40, 40, 0))
            p.setBrush(sg)
            p.drawEllipse(QPointF(sm.x, sm.y), r, r)

        # photographed flames, alive: stretch, sway and cross-fade with a mirrored copy
        grow = min(1.75, 0.78 + 0.3 * I)
        sy = grow * (1 + 0.06 * math.sin(t * 6.3) + 0.035 * math.sin(t * 13.7 + 0.7))
        sx = min(1.3, 0.93 + 0.1 * I) * (1 + 0.025 * math.sin(t * 5.1 + 1.0))
        shear = 0.07 * math.sin(t * 2.3) + 0.035 * math.sin(t * 5.7 + 2.0)
        mix = 0.5 + 0.5 * math.sin(t * 1.9)
        mrect = rect.translated(2 * (FLAME_X - (IMG_X + IMG_W / 2)), 0)
        self._flame_layer(p, self.flames, rect, 1.0, sx, sy, shear)
        self._flame_layer(p, self.flames_m, mrect, 0.6 * mix,
                          sx * (1 + 0.04 * math.sin(t * 4.4)), sy * (0.92 + 0.08 * math.sin(t * 7.9 + 1)),
                          -shear * 0.8)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        hot = max(0.0, min(0.45, (I - 0.4) * 0.18)) * flick
        if hot > 0.01:
            self._flame_layer(p, self.flames, rect, hot, sx * 1.02, sy * 1.03, shear)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # the stone pit, lit by the fire
        p.drawPixmap(rect, self.pit, QRectF(self.pit.rect()))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        p.setOpacity(min(0.6, (0.1 + 0.1 * I) * flick))
        p.drawPixmap(rect, self.pit_glow, QRectF(self.pit_glow.rect()))
        p.setOpacity(1.0)
        heat = min(1.0, (0.35 + 0.2 * I) * flick)
        cg = QRadialGradient(QPointF(CX, RIM_Y + 4), RIM_RX * 0.75)
        cg.setColorAt(0, QColor(255, 140, 40, int(120 * heat)))
        cg.setColorAt(1, QColor(255, 60, 0, 0))
        p.setBrush(cg)
        p.drawEllipse(QPointF(CX, RIM_Y + 4), RIM_RX * 0.75, RIM_RY * 1.6)

        # sparks and small licks
        for q in self.particles:
            qt = q.age / q.life
            if q.kind == 0:
                r = q.size * 0.8 * (1.0 - 0.5 * qt)
                a = int(90 * (1 - qt) ** 1.4)
                c = flame_color(min(1.0, 0.2 + qt))
                fg = QRadialGradient(QPointF(q.x, q.y), r * 1.3)
                fg.setColorAt(0, QColor(c[0], c[1], c[2], a))
                fg.setColorAt(1, QColor(c[0], c[1], c[2], 0))
                p.setBrush(fg)
                p.drawEllipse(QPointF(q.x, q.y), r * 0.7, r * 1.3)
            else:
                fl = 0.6 + 0.4 * math.sin(t * 30 + q.seed * 5)
                a = int(255 * (1 - qt) * fl)
                eg = QRadialGradient(QPointF(q.x, q.y), q.size * 3)
                eg.setColorAt(0, QColor(255, 235, 160, a))
                eg.setColorAt(0.3, QColor(255, 140, 40, a // 2))
                eg.setColorAt(1, QColor(255, 80, 0, 0))
                p.setBrush(eg)
                p.drawEllipse(QPointF(q.x, q.y), q.size * 3, q.size * 3)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        for pa in self.papers:
            if pa.delay <= 0:
                self._paint_paper(p, pa)
        p.restore()


def make_renderer():
    return PhotoRenderer() if USE_PHOTO else FireRenderer()


def render_icon(size=256) -> QPixmap:
    if USE_PHOTO:
        return QPixmap(resource_path("assets", "icon.png")).scaled(
            size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    random.seed(7)
    r = FireRenderer()
    for _ in range(90):
        r.update(1 / 30, 1.5)
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    side = 250.0
    s = size / side
    p.scale(s, s)
    p.translate(-(CX - side / 2), -(BOT_Y + 14 - side))
    r.paint(p, 1.5, 0.0, s)
    p.end()
    random.seed()
    return pm


def save_ico(path, sizes=(16, 24, 32, 48, 64, 128, 256)):
    """Multi-resolution Windows .ico with PNG-compressed entries."""
    import struct
    big = render_icon(256)
    blobs = []
    for sz in sizes:
        pm = big if sz == 256 else big.scaled(sz, sz, Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pm.save(buf, "PNG")
        buf.close()
        blobs.append((sz, bytes(ba)))
    out = struct.pack("<HHH", 0, 1, len(blobs))
    offset = 6 + 16 * len(blobs)
    for sz, data in blobs:
        out += struct.pack("<BBBBHHII", sz % 256, sz % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    with open(path, "wb") as f:
        f.write(out + b"".join(d for _, d in blobs))


# ─────────────────────────── Windows integration ───────────────────────────
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def startup_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = sys.executable
    pyw = exe.replace("python.exe", "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    return f'"{exe}" "{os.path.abspath(__file__)}"'


def startup_enabled():
    if not IS_WIN:
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_ID)
            return True
    except OSError:
        return False


def set_startup(on: bool):
    if not IS_WIN:
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, APP_ID, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(k, APP_ID)
            except OSError:
                pass


# ─────────────────────────── About dialog ───────────────────────────
class AboutDialog(QDialog):
    def __init__(self, tr, icon_pm, rtl):
        super().__init__()
        self.setWindowTitle(f"{tr['about']} — {APP_NAME}")
        self.setWindowIcon(QIcon(icon_pm))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight)
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 18)
        lay.setSpacing(6)

        img = QLabel()
        img.setPixmap(icon_pm.scaled(110, 110, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(img)

        def lbl(text, css, align=Qt.AlignmentFlag.AlignCenter):
            l = QLabel(text)
            l.setStyleSheet(css)
            l.setAlignment(align)
            l.setWordWrap(True)
            lay.addWidget(l)
            return l

        lbl(APP_NAME, "font-family: Georgia; font-size: 22pt; color: #f1d48a; letter-spacing: 2px;")
        lbl(f"Version {APP_VERSION}", "color: #9c8a64; font-size: 9pt;")
        lbl(tr["about_desc"], "color: #d8ccb0; margin: 10px 0;")
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #5a4419;")
        lay.addWidget(sep)
        lbl(tr["by"], "color: #9c8a64; font-size: 9pt; margin-top: 8px;")
        lbl(f"{AUTHOR}  •  {AUTHOR_AR}", "color: #ffe3a3; font-size: 13pt; font-weight: bold;")
        lbl(AUTHOR_TITLE, "color: #c9b88f;")
        link = lbl(f'<a style="color:#e3b65a;" href="mailto:{AUTHOR_EMAIL}">{AUTHOR_EMAIL}</a>'
                   f'&nbsp;&nbsp;|&nbsp;&nbsp;<a style="color:#e3b65a;" href="{AUTHOR_LINKEDIN}">LinkedIn</a>',
                   "margin-top: 4px;")
        link.setOpenExternalLinks(True)
        link.setTextFormat(Qt.TextFormat.RichText)
        lbl(COPYRIGHT, "color: #6f6450; font-size: 8pt; margin-top: 10px;")

        row = QHBoxLayout()
        row.addStretch()
        b = QPushButton(tr["close"])
        b.clicked.connect(self.accept)
        row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)


# ─────────────────────────── Main widget ───────────────────────────
class InfernoBin(QWidget):
    def __init__(self, settings: Settings):
        super().__init__()
        self.st = settings
        self.fire = make_renderer()
        self.sfx = None
        self.intensity = 0.35
        self.target = 0.35
        self.shake = 0.0
        self.busy = 0
        self.drag_hover = False
        self.mouse_hover = False
        self._drag_off = None
        self._last = time.perf_counter()
        self.log_path = config_dir() / "burn_log.txt"
        self.icon_pm = render_icon(256)

        self.burner = Burner()
        self.burner.finished.connect(self._on_burned)

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(self.icon_pm))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self._apply_flags()
        self._apply_size()
        self._restore_pos()
        self._update_tooltip()

        self.tray = QSystemTrayIcon(QIcon(self.icon_pm), self)
        self.tray.setToolTip(f"{APP_NAME} — {AUTHOR}")
        self.tray.activated.connect(self._tray_activated)
        self._rebuild_tray_menu()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

        self.sfx = None
        wav = resource_path("assets", "fire_loop.wav")
        if QSoundEffect is not None and os.path.exists(wav):
            self.sfx = QSoundEffect(self)
            self.sfx.setSource(QUrl.fromLocalFile(wav))
            self.sfx.setLoopCount(QSoundEffect.Loop.Infinite.value)
            self.sfx.setVolume(0.0)
            if self.st["sound"]:
                self.sfx.play()

        for _ in range(40):  # pre-warm the fire
            self.fire.update(1 / 40, self.intensity)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(20)

    # ---------- helpers ----------
    @property
    def tr(self):
        return TEXT[self.st["lang"]]

    @property
    def scale(self):
        return SCALES.get(self.st["size"], 1.0)

    def _apply_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.st["on_top"]:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        vis = self.isVisible()
        self.setWindowFlags(flags)
        if vis:
            self.show()

    def _apply_size(self):
        s = self.scale
        self.setFixedSize(int(BASE_W * s), int(BASE_H * s))

    def _restore_pos(self):
        pos = self.st["pos"]
        scr = QApplication.primaryScreen().availableGeometry()
        if pos:
            pt = QPoint(*pos)
            for sc in QApplication.screens():
                if sc.availableGeometry().contains(pt + QPoint(20, 20)):
                    self.move(pt)
                    return
        self.move(scr.right() - self.width() - 30, scr.bottom() - self.height() - 10)

    def _update_tooltip(self):
        mode = self.tr["mode_recycle"] if self.st["mode"] == "recycle" else self.tr["mode_permanent"]
        self.setToolTip(self.tr["tooltip"].format(app=APP_NAME, mode=mode, n=self.st["burned"],
                                                  author=AUTHOR))

    # ---------- animation ----------
    def _tick(self):
        now = time.perf_counter()
        dt = min(0.05, now - self._last)
        self._last = now
        if self.busy:
            self.target = 1.8
        elif self.drag_hover:
            self.target = 1.4
        elif self.mouse_hover:
            self.target = 0.6
        else:
            self.target = 0.35
        self.intensity += (self.target - self.intensity) * min(1.0, dt * 3.0)
        self.shake = max(0.0, self.shake - dt * 2.2)
        self.fire.update(dt, self.intensity)
        if self.sfx is not None:
            vol = 0.0
            if self.st["sound"]:
                vol = self.st["volume"] / 100.0 * min(1.0, 0.5 + 0.2 * self.intensity)
            if abs(self.sfx.volume() - vol) > 0.01:
                self.sfx.setVolume(vol)
        if self.fire.kick:
            self.fire.kick = 0
            self.intensity = max(self.intensity, 3.0)
            self.shake = 0.8
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.scale(self.scale, self.scale)
        self.fire.paint(p, self.intensity, self.shake, self.scale * self.devicePixelRatioF())
        p.end()

    # ---------- drag & drop ----------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(u.isLocalFile() for u in e.mimeData().urls()):
            e.acceptProposedAction()
            self.drag_hover = True
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        e.acceptProposedAction()

    def dragLeaveEvent(self, _):
        self.drag_hover = False

    def dropEvent(self, e):
        self.drag_hover = False
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        paths = [os.path.normpath(p) for p in paths if p]
        e.acceptProposedAction()
        QTimer.singleShot(0, lambda: self.request_burn(paths))

    def request_burn(self, paths):
        if not paths:
            return
        safe = [p for p in paths if not is_protected(p)]
        blocked = [p for p in paths if is_protected(p)]
        if blocked:
            self._message(QMessageBox.Icon.Warning, self.tr["protected"] + "\n\n" + "\n".join(blocked[:8]))
        if not safe:
            return
        mode = self.st["mode"]
        if mode == "recycle" and send2trash is None:
            self._message(QMessageBox.Icon.Critical, self.tr["no_trash"])
            return
        if self.st["confirm"] and not self._confirm(safe, mode):
            return
        self.busy += 1
        self.intensity = max(self.intensity, 1.8)
        self.fire.drop_papers(len(safe))
        self.burner.start(safe, mode, str(self.log_path))

    def _on_burned(self, ok, errors):
        self.busy = max(0, self.busy - 1)
        self.st["burned"] = self.st["burned"] + ok
        self._update_tooltip()
        msg = self.tr["done"].format(ok=ok)
        if errors:
            msg += "\n" + self.tr["failed"].format(n=len(errors))
            detail = "\n".join(f"• {os.path.basename(p)}: {err}" for p, err in errors[:6])
            self._message(QMessageBox.Icon.Warning, msg + "\n\n" + detail)

    # ---------- dialogs ----------
    def _box(self, icon, text, title=APP_NAME):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setIcon(icon)
        box.setText(text)
        box.setWindowIcon(QIcon(self.icon_pm))
        if self.st["lang"] == "ar":
            box.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        box.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        return box

    def _message(self, icon, text):
        self._box(icon, text).exec()

    def _confirm(self, paths, mode):
        tr = self.tr
        head = (tr["confirm_perm"] if mode == "permanent" else tr["confirm_recycle"]).format(n=len(paths))
        names = "\n".join("•  " + (os.path.basename(p) or p) for p in paths[:6])
        if len(paths) > 6:
            names += "\n" + tr["more"].format(n=len(paths) - 6)
        box = self._box(QMessageBox.Icon.Warning if mode == "permanent" else QMessageBox.Icon.Question,
                        head + "\n\n" + names, tr["confirm_title"])
        yes = box.addButton(tr["yes"], QMessageBox.ButtonRole.AcceptRole)
        no = box.addButton(tr["no"], QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(no if mode == "permanent" else yes)
        box.exec()
        return box.clickedButton() is yes

    def show_about(self):
        AboutDialog(self.tr, self.icon_pm, self.st["lang"] == "ar").exec()

    # ---------- mouse ----------
    def enterEvent(self, _):
        self.mouse_hover = True

    def leaveEvent(self, _):
        self.mouse_hover = False

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_off = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_off is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_off)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._drag_off is not None:
            self._drag_off = None
            self.st["pos"] = [self.x(), self.y()]

    def mouseDoubleClickEvent(self, _):
        self.open_recycle_bin()

    def contextMenuEvent(self, e):
        self._build_menu().exec(e.globalPos())

    # ---------- menus ----------
    def _build_menu(self, for_tray=False):
        tr = self.tr
        m = QMenu(self)
        if self.st["lang"] == "ar":
            m.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        title = m.addAction(f"🔥  {APP_NAME}  —  {AUTHOR}")
        title.setEnabled(False)
        m.addSeparator()

        mm = m.addMenu(tr["mode"])
        grp = QActionGroup(mm)
        for key in ("recycle", "permanent"):
            a = mm.addAction(tr["mode_" + key])
            a.setCheckable(True)
            a.setChecked(self.st["mode"] == key)
            a.triggered.connect(lambda _, k=key: self._set("mode", k))
            grp.addAction(a)

        a = m.addAction(tr["confirm"])
        a.setCheckable(True)
        a.setChecked(self.st["confirm"])
        a.triggered.connect(lambda v: self._set("confirm", v))

        a = m.addAction(tr["on_top"])
        a.setCheckable(True)
        a.setChecked(self.st["on_top"])
        a.triggered.connect(lambda v: (self._set("on_top", v), self._apply_flags()))

        sm = m.addMenu(tr["size"])
        g2 = QActionGroup(sm)
        for key in ("small", "medium", "large"):
            a = sm.addAction(tr[key])
            a.setCheckable(True)
            a.setChecked(self.st["size"] == key)
            a.triggered.connect(lambda _, k=key: (self._set("size", k), self._apply_size()))
            g2.addAction(a)

        if IS_WIN:
            a = m.addAction(tr["startup"])
            a.setCheckable(True)
            a.setChecked(startup_enabled())
            a.triggered.connect(set_startup)

        if self.sfx is not None:
            a = m.addAction("🔊  " + tr["sound"])
            a.setCheckable(True)
            a.setChecked(self.st["sound"])
            a.triggered.connect(self._toggle_sound)
            vm = m.addMenu(tr["volume"])
            g3 = QActionGroup(vm)
            for v in (25, 50, 75, 100):
                a = vm.addAction(f"{v}%")
                a.setCheckable(True)
                a.setChecked(self.st["volume"] == v)
                a.triggered.connect(lambda _, val=v: self._set("volume", val))
                g3.addAction(a)

        lm = m.addMenu(tr["language"])
        for key, name in (("ar", "العربية"), ("en", "English")):
            a = lm.addAction(name)
            a.setCheckable(True)
            a.setChecked(self.st["lang"] == key)
            a.triggered.connect(lambda _, k=key: self._set("lang", k))

        m.addSeparator()
        if IS_WIN:
            m.addAction(tr["open_recycle"]).triggered.connect(self.open_recycle_bin)
        m.addAction(tr["open_log"]).triggered.connect(self.open_log)
        m.addAction(tr["hide"] if self.isVisible() else tr["show"]).triggered.connect(self.toggle_visible)
        m.addAction(tr["about"]).triggered.connect(self.show_about)
        m.addSeparator()
        m.addAction(tr["exit"]).triggered.connect(QApplication.quit)
        return m

    def _rebuild_tray_menu(self):
        self._tray_menu = self._build_menu(True)
        self._tray_menu.aboutToShow.connect(self._refresh_tray_menu)
        self.tray.setContextMenu(self._tray_menu)

    def _refresh_tray_menu(self):
        new = self._build_menu(True)
        self._tray_menu.clear()
        for a in new.actions():
            a.setParent(self._tray_menu)
            self._tray_menu.addAction(a)
        self._tray_keep = new  # keep sub-menus alive

    def _toggle_sound(self, on):
        self._set("sound", on)
        if on:
            self.sfx.play()
        else:
            self.sfx.stop()

    def _set(self, key, value):
        self.st[key] = value
        self._update_tooltip()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visible()

    def toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()

    def open_recycle_bin(self):
        if IS_WIN:
            os.startfile("shell:RecycleBinFolder")

    def open_log(self):
        if not self.log_path.exists():
            self.log_path.write_text(f"{APP_NAME} — burn log\n", encoding="utf-8")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.log_path)))


# ─────────────────────────── Entry point ───────────────────────────
def main():
    if IS_WIN:
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"ElShayeb.{APP_ID}.{APP_VERSION}")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(AUTHOR)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(STYLE)

    if len(sys.argv) >= 3 and sys.argv[1] == "--export-icon":
        if sys.argv[2].lower().endswith(".ico"):
            save_ico(sys.argv[2])
        else:
            render_icon(256).save(sys.argv[2])
        return 0

    w = InfernoBin(Settings())
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
