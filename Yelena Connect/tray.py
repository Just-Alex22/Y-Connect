import os, sys, json, time, hashlib, threading, subprocess, tempfile, asyncio
import zipfile, io, re, logging, fnmatch, weakref
from pathlib import Path
from collections import defaultdict, OrderedDict
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable

from PySide6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QMainWindow,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QStackedWidget, QListWidget, QListWidgetItem,
    QFrame, QScrollArea, QProgressBar, QMessageBox, QTextEdit,
    QSizePolicy, QToolButton, QGridLayout, QLineEdit, QComboBox,
    QCheckBox, QSpinBox, QSlider, QToolTip, QGroupBox
)
from PySide6.QtGui import (
    QIcon, QPixmap, QAction, QCloseEvent, QPalette, QColor, QFont,
    QKeySequence, QShortcut, QTextCursor, QPainter
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QSize, QElapsedTimer

from engine import manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("yconnect")

BASE_DIR    = Path(__file__).parent
ASSETS_DIR  = BASE_DIR / "assets"
LOGO_PATH   = ASSETS_DIR / "logo.svg"
CONFIG_DIR  = Path.home() / ".config" / "y-connect"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
DEVICE_DB   = CONFIG_DIR / "devices.json"
PREFS_FILE  = CONFIG_DIR / "prefs.json"
TRANSFER_DIR= CONFIG_DIR / "transfers"
TRANSFER_DIR.mkdir(exist_ok=True)

class _Sig(QObject):
    connected         = Signal(dict)
    disconnected      = Signal(str)
    resources         = Signal(dict)
    media             = Signal(dict)
    notifs            = Signal(list)
    phone_notifs      = Signal(list)
    transfer_progress = Signal(dict)
    toast             = Signal(str, str)
    clipboard_sync    = Signal(str)
    battery           = Signal(dict)
    suggestion        = Signal(list)
    reconn_status     = Signal(str, int)
    net_quality       = Signal(str)
    pair_request      = Signal(str, str)
    wifi_connected    = Signal(dict)
    wifi_disconnected = Signal(str)
SIG = _Sig()

STRINGS = {
"es": {
    "title":"Y-Connect","connected":"Conectado","disconnected":"Desconectado",
    "no_device":"Sin dispositivos","qr_scan":"Escanea con Y-Connect en Android",
    "qr_ip":"IP: {}   Puerto: {}",
    "qr_nolib":"Instala qrcode:\npip install qrcode[pil]",
    "instructions":"1. Abre Y-Connect en Android\n2. Toca Conectar\n3. Escanea el QR",
    "send_file":"Enviar archivo","no_media":"Sin reproduccion",
    "no_notifs":"Sin notificaciones","about":"Acerca de","quit":"Salir","show":"Mostrar",
    "about_text":"Y-Connect v2.0\n 2026 CuerdOS\nLicencia GPL 3.0",
    "pc_media":"Reproduccion del PC","phone_media":"Reproduccion del telefono",
    "phone_vol":"Volumen","pc_notifs":"Notificaciones del PC",
    "phone_notifs":"Notificaciones del telefono","files":"Archivos",
    "transfer_log":"Historial de transferencias",
    "grant_perm":"Requiere permiso en el telefono",
    "connect_tab":"Conectar","status_tab":"Estado","media_tab":"Multimedia",
    "notif_tab":"Notificaciones","files_tab":"Archivos","phone_tab":"Telefono",
    "cpu":"CPU","ram":"RAM","disk":"Disco","uptime":"Tiempo activo",
    "battery":"Bateria","charging":"Cargando","discharging":"Descargando",
    "clipboard_tab":"Portapapeles","clipboard_sent":"Portapapeles sincronizado",
    "clipboard_send":"Enviar al telefono","clipboard_recv":"Recibido del telefono",
    "reconn":"Reconectando... intento {}","reconn_fail":"No se pudo reconectar",
    "reconn_ok":"Reconectado","net_excellent":"Red excelente","net_good":"Red buena",
    "net_fair":"Red regular","net_poor":"Red deficiente",
    "sug_send_recent":"Enviar archivo reciente","sug_open_phone":"Abrir en el telefono",
    "sug_mute_phone":"Silenciar telefono","sug_battery_low":"Bateria baja del telefono",
    "compress":"Comprimir antes de enviar","chunked":"Transferencia por bloques",
    "resume":"Reanudar transferencia","cancel":"Cancelar",
    "cmd_palette":"Paleta de comandos (Ctrl+K)","cmd_hint":"Escribe un comando...",
    "group_apps":"Agrupar por aplicacion","priority_only":"Solo prioridad alta",
    "quick_reply":"Respuesta rapida","reply_placeholder":"Escribe una respuesta...",
    "toast_connected":"Conectado a {}","toast_disconnected":"Desconectado",
    "toast_file_sent":"Archivo enviado: {}","toast_file_recv":"Archivo recibido: {}",
    "toast_clipboard":"Portapapeles sincronizado",
    "toast_battery":"Bateria del telefono: {}%",
    "phone_battery":"Bateria: {}%","phone_charging":"Cargando",
    "settings":"Ajustes","auto_reconnect":"Auto-reconectar","clipboard_auto":"Auto-sincronizar portapapeles",
    "notif_filter":"Filtrar notificaciones","battery_alert":"Alerta bateria baja (%)",
    "trusted_device":"Dispositivo confiable","last_seen":"Ultima conexion: {}",
    "never_seen":"Nunca conectado","device_found":"Dispositivo conocido: {}",
    "nearby":"{} esta cerca","sent_label":"Enviado","recv_label":"Recibido",
    "trusted_mark":"Confiable","last_label":"Ultima: {}",
},
"en": {
    "title":"Y-Connect","connected":"Connected","disconnected":"Disconnected",
    "no_device":"No devices","qr_scan":"Scan with Y-Connect on Android",
    "qr_ip":"IP: {}   Port: {}",
    "qr_nolib":"Install qrcode:\npip install qrcode[pil]",
    "instructions":"1. Open Y-Connect on Android\n2. Tap Connect\n3. Scan the QR",
    "send_file":"Send file","no_media":"No playback",
    "no_notifs":"No notifications","about":"About","quit":"Quit","show":"Show",
    "about_text":"Y-Connect v2.0\n 2026 CuerdOS\nGPL 3.0 License",
    "pc_media":"PC Playback","phone_media":"Phone Playback",
    "phone_vol":"Volume","pc_notifs":"PC Notifications",
    "phone_notifs":"Phone Notifications","files":"Files",
    "transfer_log":"Transfer history",
    "grant_perm":"Permission required on phone",
    "connect_tab":"Connect","status_tab":"Status","media_tab":"Media",
    "notif_tab":"Notifications","files_tab":"Files","phone_tab":"Phone",
    "cpu":"CPU","ram":"RAM","disk":"Disk","uptime":"Uptime",
    "battery":"Battery","charging":"Charging","discharging":"Discharging",
    "clipboard_tab":"Clipboard","clipboard_sent":"Clipboard synced",
    "clipboard_send":"Send to phone","clipboard_recv":"Received from phone",
    "reconn":"Reconnecting... attempt {}","reconn_fail":"Could not reconnect",
    "reconn_ok":"Reconnected","net_excellent":"Network excellent","net_good":"Network good",
    "net_fair":"Network fair","net_poor":"Network poor",
    "sug_send_recent":"Send recent file","sug_open_phone":"Open on phone",
    "sug_mute_phone":"Mute phone","sug_battery_low":"Phone battery low",
    "compress":"Compress before sending","chunked":"Chunked transfer",
    "resume":"Resume transfer","cancel":"Cancel",
    "cmd_palette":"Command palette (Ctrl+K)","cmd_hint":"Type a command...",
    "group_apps":"Group by app","priority_only":"High priority only",
    "quick_reply":"Quick reply","reply_placeholder":"Type a reply...",
    "toast_connected":"Connected to {}","toast_disconnected":"Disconnected",
    "toast_file_sent":"File sent: {}","toast_file_recv":"File received: {}",
    "toast_clipboard":"Clipboard synced",
    "toast_battery":"Phone battery: {}%",
    "phone_battery":"Battery: {}%","phone_charging":"Charging",
    "settings":"Settings","auto_reconnect":"Auto-reconnect","clipboard_auto":"Auto-sync clipboard",
    "notif_filter":"Filter notifications","battery_alert":"Low battery alert (%)",
    "trusted_device":"Trusted device","last_seen":"Last seen: {}",
    "never_seen":"Never connected","device_found":"Known device: {}",
    "nearby":"{} is nearby","sent_label":"Sent","recv_label":"Received",
    "trusted_mark":"Trusted","last_label":"Last: {}",
},
}

def _detect_lang():
    for var in ("LANG","LANGUAGE","LC_ALL","LC_MESSAGES"):
        v = os.environ.get(var,"")
        if v:
            c = v.split("_")[0].split(".")[0].lower()
            if c in STRINGS: return c
    return "en"

BG      = QColor("#242424")
BG_SIDE = QColor("#1e1e1e")
BG_CARD = QColor("#2e2e2e")
BG_HOVER= QColor("#3a3a3a")
FG      = QColor("#ffffff")
FG_DIM  = QColor("#9a9996")
ACCENT  = QColor("#5a7a22")
ACCENT2 = QColor("#3584e4")
WARN    = QColor("#e5a50a")
ERR     = QColor("#c01c28")
BORDER  = QColor("#383838")
DIS     = QColor("#5c5c5c")
TOAST_BG= QColor("#3584e4")

def _apply_palette(app):
    p = QPalette()
    p.setColor(QPalette.Window,          BG)
    p.setColor(QPalette.WindowText,      FG)
    p.setColor(QPalette.Base,            BG_CARD)
    p.setColor(QPalette.AlternateBase,   BG)
    p.setColor(QPalette.Text,            FG)
    p.setColor(QPalette.BrightText,      FG)
    p.setColor(QPalette.Button,          BG_CARD)
    p.setColor(QPalette.ButtonText,      FG)
    p.setColor(QPalette.Highlight,       ACCENT)
    p.setColor(QPalette.HighlightedText, FG)
    p.setColor(QPalette.PlaceholderText, DIS)
    p.setColor(QPalette.Mid,             BORDER)
    p.setColor(QPalette.Dark,            BORDER)
    p.setColor(QPalette.Shadow,          QColor("#000000"))
    p.setColor(QPalette.ToolTipBase,     BG_CARD)
    p.setColor(QPalette.ToolTipText,     FG)
    p.setColor(QPalette.Disabled, QPalette.WindowText, DIS)
    p.setColor(QPalette.Disabled, QPalette.Text,       DIS)
    p.setColor(QPalette.Disabled, QPalette.ButtonText, DIS)
    app.setPalette(p)

def _themed_icon(icon_name, size=QSize(24, 24), color=None):
    if color is None:
        color = FG
    base = QIcon.fromTheme(icon_name)
    pixmap = base.pixmap(size)
    if pixmap.isNull():
        fallback = QPixmap(size)
        fallback.fill(Qt.transparent)
        painter = QPainter(fallback)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        m = 4
        painter.drawRoundedRect(m, m, size.width()-2*m, size.height()-2*m, 4, 4)
        painter.end()
        return QIcon(fallback)
    colored = QPixmap(pixmap.size())
    colored.fill(Qt.transparent)
    painter = QPainter(colored)
    painter.drawPixmap(0, 0, pixmap)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(colored.rect(), color)
    painter.end()
    return QIcon(colored)

def _themed_pixmap(icon_name, size=QSize(24, 24), color=None):
    return _themed_icon(icon_name, size, color).pixmap(size)

def _lbl(text="", size=13, bold=False, dim=False, wrap=False, accent=False, warn=False, err=False):
    l = QLabel(text)
    f = l.font(); f.setPointSize(size)
    if bold: f.setBold(True)
    l.setFont(f)
    color = FG_DIM if dim else (ERR if err else (WARN if warn else (ACCENT if accent else FG)))
    p = l.palette(); p.setColor(QPalette.WindowText, color); l.setPalette(p)
    if wrap: l.setWordWrap(True)
    return l

def _sep():
    f = QFrame(); f.setFrameShape(QFrame.HLine); return f

def _vsep():
    f = QFrame(); f.setFrameShape(QFrame.VLine); return f

def _media_btn(icon_name, size=40):
    btn = QToolButton()
    btn.setIcon(_themed_icon(icon_name, QSize(size//2, size//2)))
    btn.setIconSize(QSize(size//2, size//2))
    btn.setFixedSize(size, size)
    btn.setAutoRaise(True)
    return btn

def _ws_send(mtype, payload):
    if hasattr(manager, 'ws_server') and manager.ws_server:
        manager.ws_server.broadcast(mtype, payload)

def _scrolled(widget):
    s = QScrollArea()
    s.setWidgetResizable(True)
    s.setFrameShape(QFrame.NoFrame)
    s.setWidget(widget)
    return s

def _icon_for_signal(connected, rssi):

    _FALLBACKS = {
        "stat0": ("network-cellular-offline-symbolic",    FG_DIM),
        "stat1": ("network-cellular-signal-weak-symbolic", FG),
        "stat2": ("network-cellular-signal-ok-symbolic",   FG),
        "stat3": ("network-cellular-signal-good-symbolic", FG),
        "stat4": ("network-cellular-signal-excellent-symbolic", FG),
    }
    if not connected or rssi == -1:
        name = "stat0"
    elif rssi >= -60:
        name = "stat4"
    elif rssi >= -70:
        name = "stat3"
    elif rssi >= -80:
        name = "stat2"
    else:
        name = "stat1"

    svg = ASSETS_DIR / f"{name}.svg"
    if svg.exists():
        return QIcon(str(svg))
    icon_name, color = _FALLBACKS[name]
    return _themed_icon(icon_name, QSize(22, 22), color)

def _net_quality(rssi) -> str:
    if rssi >= -55: return "excellent"
    if rssi >= -65: return "good"
    if rssi >= -75: return "fair"
    return "poor"

def _rssi_bars(rssi) -> str:
    if rssi >= -60: return "||||"
    if rssi >= -70: return "|||"
    if rssi >= -80: return "||"
    return "|"

def _priority_dot(priority_level):
    colors = {5: ERR, 4: QColor("#ff7800"), 3: WARN, 2: ACCENT2, 1: FG_DIM, 0: DIS}
    color = colors.get(priority_level, FG_DIM)
    dot = QLabel()
    dot.setFixedSize(10, 10)
    dot.setAutoFillBackground(True)
    p = dot.palette()
    p.setColor(QPalette.Window, color)
    dot.setPalette(p)
    dot.setStyleSheet(f"background-color: {color.name()}; border-radius: 5px;")
    return dot

class DeviceMemory:
    def __init__(self):
        self._db: Dict[str, dict] = {}
        self._load()

    def _load(self):
        try:
            if DEVICE_DB.exists():
                self._db = json.loads(DEVICE_DB.read_text())
                log.info("Device memory loaded: %d devices", len(self._db))
        except Exception as e:
            log.warning("Failed to load device memory: %s", e)
            self._db = {}

    def _save(self):
        try:
            DEVICE_DB.write_text(json.dumps(self._db, indent=2, ensure_ascii=False))
        except Exception as e:
            log.warning("Failed to save device memory: %s", e)

    def _fingerprint(self, device: dict) -> str:
        raw = f"{device.get('name','')}|{device.get('mac','')}|{device.get('model','')}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def remember(self, device: dict):
        fp = self._fingerprint(device)
        entry = self._db.setdefault(fp, {
            "name": device.get("name",""), "mac": device.get("mac",""),
            "model": device.get("model",""), "ip": device.get("ip",""),
            "trusted": False, "first_seen": time.time(),
            "last_seen": time.time(), "connect_count": 0,
            "total_bytes_sent": 0, "total_bytes_recv": 0, "preferred_tab": 0,
        })
        entry["name"] = device.get("name", entry["name"])
        entry["ip"]   = device.get("ip", entry["ip"])
        entry["last_seen"] = time.time()
        entry["connect_count"] += 1
        self._save()
        log.info("Device remembered: %s (fp=%s)", entry["name"], fp)
        return fp

    def lookup(self, device: dict) -> Optional[dict]:
        fp = self._fingerprint(device)
        return self._db.get(fp)

    def is_trusted(self, device: dict) -> bool:
        entry = self.lookup(device)
        return entry.get("trusted", False) if entry else False

    def set_trusted(self, device: dict, trusted: bool = True):
        fp = self._fingerprint(device)
        if fp in self._db:
            self._db[fp]["trusted"] = trusted
            self._save()

    def update_transfer_stats(self, device: dict, sent: int = 0, recv: int = 0):
        fp = self._fingerprint(device)
        if fp in self._db:
            self._db[fp]["total_bytes_sent"] += sent
            self._db[fp]["total_bytes_recv"] += recv
            self._save()

    def update_preferred_tab(self, device: dict, tab_idx: int):
        fp = self._fingerprint(device)
        if fp in self._db:
            self._db[fp]["preferred_tab"] = tab_idx
            self._save()

    def get_preferred_tab(self, device: dict) -> int:
        entry = self.lookup(device)
        return entry.get("preferred_tab", 0) if entry else 0

    def last_seen_str(self, device: dict) -> str:
        entry = self.lookup(device)
        if not entry: return ""
        ts = entry.get("last_seen", 0)
        if ts == 0: return ""
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M")

    @property
    def all_devices(self) -> Dict[str, dict]:
        return dict(self._db)

class SmartReconnector:
    BASE_DELAY    = 1.5
    MAX_DELAY     = 60.0
    MAX_ATTEMPTS  = 0
    JITTER        = 0.3

    def __init__(self):
        self._attempt = 0
        self._active  = False
        self._timer   = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._try_reconnect)
        self._last_device: Optional[dict] = None

    @property
    def active(self): return self._active
    @property
    def attempt(self): return self._attempt

    def start(self, device: dict = None):
        if self._active: return
        self._active = True
        self._attempt = 0
        self._last_device = device
        log.info("Smart reconnector started for %s",
                 device.get("name","?") if device else "?")
        self._schedule_next()

    def stop(self):
        self._active = False
        self._timer.stop()
        self._attempt = 0
        log.info("Smart reconnector stopped")

    def _schedule_next(self):
        if not self._active: return
        self._attempt += 1
        if self.MAX_ATTEMPTS > 0 and self._attempt > self.MAX_ATTEMPTS:
            SIG.reconn_status.emit("fail", self._attempt)
            SIG.toast.emit("Y-Connect", "Could not reconnect")
            self.stop()
            return
        delay = min(self.BASE_DELAY * (2 ** (self._attempt - 1)), self.MAX_DELAY)
        import random
        jitter = delay * self.JITTER * (random.random() * 2 - 1)
        delay = max(0.5, delay + jitter)
        SIG.reconn_status.emit("trying", self._attempt)
        log.info("Reconnect attempt %d in %.1fs", self._attempt, delay)
        self._timer.start(int(delay * 1000))

    def _try_reconnect(self):
        if not self._active: return
        if manager.is_connected() or manager.is_wifi_connected():
            log.info("Already connected, stopping reconnector")
            SIG.reconn_status.emit("ok", self._attempt)
            self.stop()
            return
        try:
            if hasattr(manager, 'discovery') and manager.discovery:
                getattr(manager.discovery, 'scan_once', lambda: None)()
            if hasattr(manager, 'ensure_wifi_server'):
                manager.ensure_wifi_server()
        except Exception as e:
            log.warning("Reconnect attempt %d failed: %s", self._attempt, e)
        self._schedule_next()

class NetworkMonitor:
    HISTORY_SIZE = 10
    def __init__(self):
        self._history: List[float] = []
        self._quality = "unknown"

    def update_rssi(self, rssi: float):
        self._history.append(rssi)
        if len(self._history) > self.HISTORY_SIZE:
            self._history.pop(0)
        avg = sum(self._history) / len(self._history)
        self._quality = _net_quality(avg)
        SIG.net_quality.emit(self._quality)

    @property
    def quality(self) -> str: return self._quality
    @property
    def avg_rssi(self) -> float:
        return sum(self._history)/len(self._history) if self._history else -1

    def should_compress(self) -> bool:
        return self._quality in ("fair", "poor")

    def chunk_size(self) -> int:
        sizes = {"excellent": 512*1024, "good": 256*1024,
                 "fair": 128*1024, "poor": 64*1024, "unknown": 256*1024}
        return sizes.get(self._quality, 256*1024)

    def poll_interval_ms(self) -> int:
        intervals = {"excellent": 4000, "good": 5000,
                     "fair": 8000, "poor": 12000, "unknown": 6000}
        return intervals.get(self._quality, 6000)

class ContextEngine:
    def __init__(self, device_memory: DeviceMemory):
        self._dm = device_memory
        self._recent_files: List[str] = []
        self._media_playing = False
        self._phone_battery: Optional[int] = None
        self._battery_low_threshold = 15
        self._last_notif_app: Optional[str] = None
        self._active_tab = 0
        self._last_activity = time.time()

    def touch(self): self._last_activity = time.time()

    @property
    def is_idle(self) -> bool:
        return (time.time() - self._last_activity) > 120

    def record_file_sent(self, path: str):
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:20]
        self.touch()

    def set_media_state(self, playing: bool):
        self._media_playing = playing; self.touch()

    def set_phone_battery(self, pct: int): self._phone_battery = pct

    def set_active_tab(self, idx: int): self._active_tab = idx

    def record_notif(self, app: str): self._last_notif_app = app

    def get_suggestions(self, connected: bool) -> List[dict]:
        sugs = []
        if not connected: return sugs
        if self._phone_battery is not None and self._phone_battery <= self._battery_low_threshold:
            sugs.append({"icon": "battery-caution-symbolic",
                         "text": f"Phone battery at {self._phone_battery}%",
                         "action": "battery_alert"})
        if self._recent_files:
            recent = self._recent_files[0]
            name = Path(recent).name
            sugs.append({"icon": "document-send-symbolic",
                         "text": f"Send {name} again",
                         "action": f"send_recent:{recent}"})
        if self._media_playing:
            sugs.append({"icon": "media-playback-pause-symbolic",
                         "text": "Pause playback", "action": "media_pause"})
        if self._last_notif_app:
            sugs.append({"icon": "mail-reply-sender-symbolic",
                         "text": f"Reply to {self._last_notif_app}",
                         "action": f"reply:{self._last_notif_app}"})
        hour = datetime.now().hour
        if hour >= 22 or hour < 7:
            sugs.append({"icon": "audio-volume-muted-symbolic",
                         "text": "Mute phone (night mode)", "action": "mute_phone"})
        return sugs[:5]

class NotificationAI:
    PRIORITY_APP = {
        "whatsapp": 3, "telegram": 3, "signal": 3, "sms": 4, "phone": 5,
        "gmail": 2, "email": 2, "outlook": 2,
        "discord": 2, "slack": 2, "teams": 2,
        "spotify": 1, "youtube": 1, "netflix": 0,
    }

    def __init__(self):
        self._seen_hashes: OrderedDict[str, float] = OrderedDict()
        self._dedup_window = 30.0
        self._group_by_app = True
        self._priority_filter = 0
        self._last_notif_app: Optional[str] = None

    def set_group_by_app(self, on: bool): self._group_by_app = on
    def set_priority_filter(self, level: int): self._priority_filter = level

    def _hash_notif(self, n: dict) -> str:
        raw = f"{n.get('app','')}|{n.get('title','')}|{n.get('body','')}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _score_priority(self, n: dict) -> int:
        app = n.get("app","").lower()
        base = self.PRIORITY_APP.get(app, 1)
        text = f"{n.get('title','')} {n.get('body','')}".lower()
        if any(w in text for w in ("urgent", "importante")): base += 2
        if any(w in text for w in ("call", "llamada", "ring")): base += 2
        return min(base, 5)

    def process(self, notifs: List[dict]) -> List[dict]:
        now = time.time()
        expired = [k for k, t in self._seen_hashes.items() if now - t > self._dedup_window]
        for k in expired: del self._seen_hashes[k]
        result = []
        for n in notifs:
            h = self._hash_notif(n)
            if h in self._seen_hashes: continue
            self._seen_hashes[h] = now
            n["_priority"] = self._score_priority(n)
            n["_time"] = now
            result.append(n)
        if self._priority_filter > 0:
            result = [n for n in result if n.get("_priority", 0) >= self._priority_filter]
        result.sort(key=lambda n: (-n.get("_priority", 0), -n.get("_time", 0)))
        if self._group_by_app and result:
            groups: Dict[str, list] = defaultdict(list)
            ordered_apps = []
            for n in result:
                app = n.get("app", "Other")
                if app not in groups: ordered_apps.append(app)
                groups[app].append(n)
            grouped = []
            for app in ordered_apps:
                grouped.append({"_is_header": True, "app": app,
                                "count": len(groups[app]),
                                "_priority": max(n.get("_priority",0) for n in groups[app])})
                grouped.extend(groups[app])
            result = grouped
        return result

class TransferManager:
    MAX_SIZE = 100 * 1024 * 1024
    COMPRESS_THRESHOLD = 256 * 1024

    def __init__(self, net_monitor: NetworkMonitor):
        self._nm = net_monitor
        self._active: Dict[str, dict] = {}
        self._log_entries: List[dict] = []

    def send_file(self, path: str, on_progress=None, on_done=None,
                  compress: bool = None) -> Optional[str]:
        try:
            fsize = os.path.getsize(path)
            if fsize > self.MAX_SIZE:
                err = f"File too large ({fsize//1024//1024}MB, max {self.MAX_SIZE//1024//1024}MB)"
                self._log_entries.append({"time": datetime.now(), "file": Path(path).name,
                                          "status": "error", "error": err})
                return None
            fname = Path(path).name
            transfer_id = hashlib.md5(f"{path}{time.time()}".encode()).hexdigest()[:8]
            chunk_size = self._nm.chunk_size()
            if compress is None:
                compress = (fsize > self.COMPRESS_THRESHOLD and self._nm.should_compress())
            with open(path, "rb") as f: data = f.read()
            original_size = len(data)
            if compress:
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr(fname, data)
                data = buf.getvalue()
                fname += ".zip"
            total_chunks = max(1, (len(data) + chunk_size - 1) // chunk_size)
            self._active[transfer_id] = {
                "file": Path(path).name, "total": total_chunks,
                "original_size": original_size, "compressed": compress,
                "sent": 0, "started": time.time()
            }
            import base64
            for i in range(total_chunks):
                start = i * chunk_size
                end = min(start + chunk_size, len(data))
                chunk = data[start:end]
                is_last = (i == total_chunks - 1)
                payload = {
                    "transfer_id": transfer_id, "name": fname,
                    "chunk_index": i, "total_chunks": total_chunks,
                    "data": base64.b64encode(chunk).decode(),
                    "is_last": is_last, "compressed": compress,
                    "original_name": Path(path).name,
                }
                _ws_send("file_chunk", payload)
                self._active[transfer_id]["sent"] = i + 1
                progress = (i + 1) / total_chunks
                SIG.transfer_progress.emit({
                    "id": transfer_id, "progress": progress,
                    "file": Path(path).name, "done": is_last
                })
                if on_progress: on_progress(progress)
                if is_last and on_done: on_done(transfer_id)
            elapsed = time.time() - self._active[transfer_id]["started"]
            speed = original_size / elapsed if elapsed > 0 else 0
            self._log_entries.append({
                "time": datetime.now(), "file": Path(path).name,
                "size": original_size, "status": "sent",
                "compressed": compress, "speed": speed, "elapsed": elapsed
            })
            del self._active[transfer_id]
            return transfer_id
        except Exception as e:
            log.error("Transfer error: %s", e)
            self._log_entries.append({"time": datetime.now(), "file": Path(path).name,
                                      "status": "error", "error": str(e)})
            return None

    @property
    def log(self) -> List[dict]: return list(self._log_entries)
    @property
    def active_transfers(self) -> Dict[str, dict]: return dict(self._active)

class ClipboardSync:
    def __init__(self):
        self._app: Optional[QApplication] = None
        self._last_sent = ""
        self._last_recv = ""
        self._auto_sync = False
        self._timer = QTimer()
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self._poll_clipboard)
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(500)

    def init(self, app: QApplication): self._app = app

    @property
    def auto_sync(self) -> bool: return self._auto_sync

    @auto_sync.setter
    def auto_sync(self, on: bool):
        self._auto_sync = on
        if on: self._timer.start()
        else: self._timer.stop()

    def send_clipboard(self, text: str = None):
        if not text and self._app:
            mime = self._app.clipboard().mimeData()
            if mime and mime.hasText(): text = mime.text()
        if text and text != self._last_sent:
            self._last_sent = text
            _ws_send("clipboard", {"text": text})
            log.info("Clipboard sent (%d chars)", len(text))

    def receive_clipboard(self, text: str):
        if text != self._last_recv and text != self._last_sent:
            self._last_recv = text
            if self._app: self._app.clipboard().setText(text)
            SIG.clipboard_sync.emit(text)
            SIG.toast.emit("Y-Connect", "Clipboard synced from phone")
            log.info("Clipboard received (%d chars)", len(text))

    def _poll_clipboard(self):
        if not self._auto_sync or not self._app: return
        if not manager.is_connected(): return
        mime = self._app.clipboard().mimeData()
        if mime and mime.hasText():
            text = mime.text()
            if text != self._last_sent and text != self._last_recv:
                self._debounce.timeout.disconnect()
                self._debounce.timeout.connect(lambda: self.send_clipboard(text))
                if not self._debounce.isActive(): self._debounce.start()

class Preferences:
    DEFAULTS = {
        "auto_reconnect": True, "clipboard_auto": False,
        "battery_alert_threshold": 15, "notif_group_by_app": True,
        "notif_priority_filter": 0, "compress_auto": True, "lang": "",
    }
    def __init__(self):
        self._data = dict(self.DEFAULTS); self._load()

    def _load(self):
        try:
            if PREFS_FILE.exists():
                self._data.update(json.loads(PREFS_FILE.read_text()))
        except Exception as e:
            log.warning("Failed to load preferences: %s", e)

    def _save(self):
        try: PREFS_FILE.write_text(json.dumps(self._data, indent=2))
        except Exception as e:
            log.warning("Failed to save preferences: %s", e)

    def get(self, key, default=None):
        return self._data.get(key, default if default is not None else self.DEFAULTS.get(key))

    def set(self, key, value): self._data[key] = value; self._save()

class ToastWidget(QFrame):
    def __init__(self, title: str, body: str, duration_ms=3500):
        super().__init__()
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.addWidget(_lbl(title, 11, bold=True))
        layout.addWidget(_lbl(body, 10, wrap=True))
        self.setFixedWidth(300)
        self.adjustSize()
        pal = self.palette()
        pal.setColor(QPalette.Window, TOAST_BG)
        pal.setColor(QPalette.WindowText, FG)
        self.setPalette(pal)
        self._timer = QTimer(); self._timer.setSingleShot(True)
        self._timer.setInterval(duration_ms); self._timer.timeout.connect(self.fade_out)
        self._opacity = 1.0
        self._fade_timer = QTimer(); self._fade_timer.setInterval(30)
        self._fade_timer.timeout.connect(self._tick_fade)

    def show_toast(self, parent=None):
        if parent:
            geo = parent.geometry()
            self.move(geo.right() - self.width() - 16, geo.top() + 16)
        self.show(); self._timer.start()

    def fade_out(self): self._timer.stop(); self._fade_timer.start()

    def _tick_fade(self):
        self._opacity -= 0.05
        if self._opacity <= 0:
            self._fade_timer.stop(); self.close(); self.deleteLater()
        else:
            self.setWindowOpacity(self._opacity)

class CommandPalette(QFrame):
    action_triggered = Signal(str)
    COMMANDS = [
        ("send file",       "document-send-symbolic",     "send_file"),
        ("send clipboard",  "edit-paste-symbolic",        "send_clipboard"),
        ("pause media",     "media-playback-pause-symbolic","media_pause"),
        ("next track",      "media-skip-forward-symbolic", "media_next"),
        ("previous track",  "media-skip-backward-symbolic","media_prev"),
        ("volume up",       "audio-volume-high-symbolic",  "vol_up"),
        ("volume down",     "audio-volume-low-symbolic",   "vol_down"),
        ("mute phone",      "audio-volume-muted-symbolic", "mute_phone"),
        ("connect",         "network-wireless-symbolic",   "tab_connect"),
        ("status",          "computer-symbolic",           "tab_status"),
        ("media",           "media-playback-start-symbolic","tab_media"),
        ("notifications",   "notification-symbolic",       "tab_notif"),
        ("files",           "folder-symbolic",             "tab_files"),
        ("phone",           "phone-symbolic",              "tab_phone"),
        ("settings",        "preferences-system-symbolic", "settings"),
        ("about",           "help-about-symbolic",         "about"),
        ("quit",            "application-exit-symbolic",   "quit"),
    ]
    def __init__(self, tr):
        super().__init__()
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(420)
        self._ = tr
        v = QVBoxLayout(self); v.setContentsMargins(8,8,8,8); v.setSpacing(4)
        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("cmd_hint"))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter)
        v.addWidget(self._search)
        self._list = QListWidget()
        self._list.setIconSize(QSize(20, 20)); self._list.setSpacing(2)
        self._list.itemClicked.connect(self._on_select)
        v.addWidget(self._list)
        self._populate()

    def _populate(self, query=""):
        self._list.clear(); q = query.lower().strip()
        for label, icon, action in self.COMMANDS:
            if q and q not in label.lower(): continue
            item = QListWidgetItem(_themed_icon(icon, QSize(20,20)), label)
            item.setData(Qt.UserRole, action)
            self._list.addItem(item)

    def _filter(self, text): self._populate(text)

    def _on_select(self, item):
        self.action_triggered.emit(item.data(Qt.UserRole)); self.close()

    def show_palette(self, parent=None):
        self._search.clear(); self._populate()
        if parent:
            geo = parent.geometry()
            self.move(geo.center().x() - self.width()//2, geo.top() + 60)
        self.show(); self._search.setFocus()

class ConnectTab(QWidget):
    def __init__(self, tr, device_memory: DeviceMemory):
        super().__init__()
        self._ = tr; self._dm = device_memory
        h = QHBoxLayout(self); h.setContentsMargins(24,24,24,24); h.setSpacing(24)
        left = QVBoxLayout(); left.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self._qr = QLabel(); self._qr.setFixedSize(180,180)
        self._qr.setAlignment(Qt.AlignCenter); self._qr.setAutoFillBackground(True)
        p = self._qr.palette(); p.setColor(QPalette.Window, QColor("#ffffff"))
        self._qr.setPalette(p)
        left.addWidget(self._qr)
        info = manager.ws_server.get_connection_info()
        ip = _lbl(tr("qr_ip", info["ip"], info["port"]), 11, dim=True)
        ip.setAlignment(Qt.AlignCenter)
        ip.setTextInteractionFlags(Qt.TextSelectableByMouse)
        left.addWidget(ip); h.addLayout(left)
        right = QVBoxLayout(); right.setAlignment(Qt.AlignTop); right.setSpacing(12)
        right.addWidget(_lbl(tr("qr_scan"), 13)); right.addWidget(_sep())
        instr = _lbl(tr("instructions"), 12, dim=True, wrap=True)
        right.addWidget(instr)
        right.addWidget(_sep())
        right.addWidget(_lbl(tr("trusted_device") + "s", 12, bold=True))
        self._known_list = QListWidget()
        self._known_list.setFrameShape(QFrame.NoFrame)
        self._known_list.setSpacing(2); self._known_list.setMaximumHeight(150)
        self._refresh_known(); right.addWidget(self._known_list)
        right.addStretch(); h.addLayout(right)
        self._load_qr()

    def _refresh_known(self):
        self._known_list.clear()
        for fp, dev in self._dm.all_devices.items():
            name = dev.get("name", "Unknown")
            last = dev.get("last_seen", 0)
            trusted = "[v]" if dev.get("trusted") else "[ ]"
            last_str = datetime.fromtimestamp(last).strftime("%m/%d %H:%M") if last else "--"
            item = QListWidgetItem(_themed_icon(
                "security-high-symbolic" if dev.get("trusted") else "phone-symbolic",
                QSize(16,16)), f"{trusted} {name}  ({last_str})")
            item.setData(Qt.UserRole, fp)
            self._known_list.addItem(item)

    def _load_qr(self):
        try:
            import qrcode as _qr
            img = _qr.make(manager.ws_server.get_qr_text())
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img.save(tmp.name); tmp.close()
            pix = QPixmap(tmp.name).scaled(170,170, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            os.unlink(tmp.name); self._qr.setPixmap(pix)
        except Exception:
            self._qr.setText(self._("qr_nolib")); self._qr.setWordWrap(True)
            p = self._qr.palette(); p.setColor(QPalette.Window, BG_CARD)
            self._qr.setPalette(p)

class StatusTab(QWidget):
    def __init__(self, tr, prefs: Preferences):
        super().__init__()
        self._ = tr; self._prefs = prefs
        v = QVBoxLayout(self); v.setContentsMargins(24,24,24,24); v.setSpacing(16)
        bat_h = QHBoxLayout()
        self._bat_icon_lbl = QLabel()
        self._bat_icon_lbl.setPixmap(_themed_pixmap("battery-full-symbolic", QSize(18,18)))
        bat_h.addWidget(self._bat_icon_lbl)
        bat_h.addWidget(_lbl(tr("battery"), 12))
        self._bat_val = _lbl("--", 12, dim=True)
        bat_h.addWidget(self._bat_val); bat_h.addStretch(); v.addLayout(bat_h)
        self._bat_bar = QProgressBar(); self._bat_bar.setRange(0,100)
        self._bat_bar.setTextVisible(False); self._bat_bar.setFixedHeight(6)
        v.addWidget(self._bat_bar)
        v.addWidget(_sep())
        net_h = QHBoxLayout(); net_h.addWidget(_lbl("Network", 12))
        self._net_lbl = _lbl("--", 12, accent=True)
        net_h.addWidget(self._net_lbl); net_h.addStretch(); v.addLayout(net_h)
        self._sig = _lbl("", 11, dim=True); v.addWidget(self._sig)
        self._reconn_lbl = _lbl("", 11, dim=True); v.addWidget(self._reconn_lbl)
        v.addStretch()
        SIG.net_quality.connect(self._on_net_quality)
        SIG.reconn_status.connect(self._on_reconn_status)
        SIG.battery.connect(self._on_battery)

    def _on_net_quality(self, q):
        colors = {"excellent": ACCENT, "good": ACCENT2, "fair": WARN, "poor": ERR}
        c = colors.get(q, FG_DIM)
        p = self._net_lbl.palette(); p.setColor(QPalette.WindowText, c)
        self._net_lbl.setPalette(p)
        key = f"net_{q}"
        self._net_lbl.setText(self._(key) if key in STRINGS.get(
            os.environ.get("_yconnect_lang","en"),{}) else q.title())

    def _on_reconn_status(self, status, attempt):
        if status == "trying": self._reconn_lbl.setText(self._("reconn", attempt))
        elif status == "ok":
            self._reconn_lbl.setText(self._("reconn_ok"))
            QTimer.singleShot(3000, lambda: self._reconn_lbl.setText(""))
        elif status == "fail": self._reconn_lbl.setText(self._("reconn_fail"))

    def _on_battery(self, info):
        pct = info.get("pct", info.get("percent", -1)); charging = info.get("charging", False)
        if pct >= 0:
            self._bat_bar.setValue(pct)
            text = f"{pct}%"
            if charging: text += " " + self._("phone_charging")
            self._bat_val.setText(text)
            if pct > 80: icon = "battery-full-symbolic"
            elif pct > 50: icon = "battery-good-symbolic"
            elif pct > 20: icon = "battery-low-symbolic"
            else: icon = "battery-caution-symbolic"
            self._bat_icon_lbl.setPixmap(_themed_pixmap(icon, QSize(18,18),
                WARN if pct <= 15 else FG))
            threshold = self._prefs.get("battery_alert_threshold", 15)
            if pct <= threshold and not charging:
                SIG.toast.emit("Battery", f"Phone battery at {pct}%")

    def update_resources(self, r):
        pass

    def update_signal(self, rssi):
        if rssi == -1: self._sig.setText("")
        else: self._sig.setText(f"{_rssi_bars(rssi)}  {rssi} dBm")

    def reset(self):
        self._bat_bar.setValue(0)
        for lbl in (self._bat_val, self._net_lbl, self._reconn_lbl): lbl.setText("--")
        self._sig.setText("")

class MediaTab(QWidget):
    def __init__(self, tr):
        super().__init__()
        self._ = tr
        v = QVBoxLayout(self); v.setContentsMargins(24,24,24,24); v.setSpacing(20)
        self._title  = _lbl("--", 15, bold=True, wrap=True)
        self._artist = _lbl("--", 12, dim=True)
        v.addWidget(self._title); v.addWidget(self._artist); v.addWidget(_sep())
        v.addWidget(_lbl(tr("pc_media"), 11, dim=True))
        pc_row = QHBoxLayout()
        self._prev  = _media_btn("media-skip-backward-symbolic", 40)
        self._play  = _media_btn("media-playback-start-symbolic", 48)
        self._next  = _media_btn("media-skip-forward-symbolic", 40)
        self._vdown = _media_btn("audio-volume-low-symbolic", 36)
        self._vup   = _media_btn("audio-volume-high-symbolic", 36)
        for b in (self._prev, self._play, self._next, self._vdown, self._vup):
            b.setEnabled(False); pc_row.addWidget(b)
        pc_row.addStretch(); v.addLayout(pc_row)
        self._prev.clicked.connect(lambda: _ws_send("media_command",{"action":"prev"}))
        self._play.clicked.connect(lambda: _ws_send("media_command",{"action":"play_pause"}))
        self._next.clicked.connect(lambda: _ws_send("media_command",{"action":"next"}))
        self._vdown.clicked.connect(lambda: _ws_send("media_command",{"action":"vol_down"}))
        self._vup.clicked.connect(lambda: _ws_send("media_command",{"action":"vol_up"}))
        v.addWidget(_sep())
        v.addWidget(_lbl(tr("phone_media"), 11, dim=True))
        ph_row = QHBoxLayout()
        self._pp = _media_btn("media-skip-backward-symbolic", 40)
        self._ppl= _media_btn("media-playback-start-symbolic", 48)
        self._pn = _media_btn("media-skip-forward-symbolic", 40)
        for b in (self._pp, self._ppl, self._pn):
            b.setEnabled(False); ph_row.addWidget(b)
        ph_row.addStretch(); v.addLayout(ph_row)
        self._pp.clicked.connect(lambda: _ws_send("phone_media_command",{"action":"prev"}))
        self._ppl.clicked.connect(lambda: _ws_send("phone_media_command",{"action":"play_pause"}))
        self._pn.clicked.connect(lambda: _ws_send("phone_media_command",{"action":"next"}))
        v.addStretch()

    def update_media(self, m):
        t = m.get("title",""); self._title.setText(t or "--")
        self._artist.setText(m.get("artist","--"))
        icon = "media-playback-pause-symbolic" if m.get("playing")\
               else "media-playback-start-symbolic"
        self._play.setIcon(_themed_icon(icon, QSize(24,24)))

    def set_enabled(self, on):
        for b in (self._prev,self._play,self._next,self._vdown,self._vup,
                  self._pp,self._ppl,self._pn): b.setEnabled(on)

class NotifsTab(QWidget):
    def __init__(self, tr, notif_ai: NotificationAI):
        super().__init__()
        self._ = tr; self._ai = notif_ai
        v = QVBoxLayout(self); v.setContentsMargins(24,24,24,24); v.setSpacing(12)
        ctrl = QHBoxLayout()
        self._group_cb = QCheckBox(tr("group_apps")); self._group_cb.setChecked(True)
        self._group_cb.toggled.connect(self._on_group_toggle)
        ctrl.addWidget(self._group_cb)
        self._priority_cb = QCheckBox(tr("priority_only"))
        self._priority_cb.toggled.connect(self._on_priority_toggle)
        ctrl.addWidget(self._priority_cb); ctrl.addStretch(); v.addLayout(ctrl)
        v.addWidget(_lbl(tr("pc_notifs"), 11, dim=True))
        self._cont = QWidget(); self._lay = QVBoxLayout(self._cont)
        self._lay.setAlignment(Qt.AlignTop); self._lay.setSpacing(6)
        self._lay.addWidget(_lbl(tr("no_notifs"), 12, dim=True))
        v.addWidget(_scrolled(self._cont), 1)

    def _on_group_toggle(self, on): self._ai.set_group_by_app(on)
    def _on_priority_toggle(self, on): self._ai.set_priority_filter(3 if on else 0)

    def update_notifs(self, notifs):
        while self._lay.count():
            w = self._lay.takeAt(0).widget()
            if w: w.deleteLater()
        processed = self._ai.process(notifs)
        if not processed:
            self._lay.addWidget(_lbl(self._("no_notifs"), 12, dim=True)); return
        for n in processed:
            if n.get("_is_header"):
                hdr_row = QHBoxLayout()
                hdr_row.addWidget(_priority_dot(n.get("_priority",1)))
                hdr_row.addWidget(_lbl(f"{n['app']} ({n['count']})", 11, bold=True, accent=True))
                hdr_row.addStretch()
                hdr_w = QWidget(); hdr_w.setLayout(hdr_row)
                self._lay.addWidget(hdr_w)
                continue
            item = QWidget(); item.setAutoFillBackground(True)
            p = item.palette(); p.setColor(QPalette.Window, BG_CARD); item.setPalette(p)
            iv = QVBoxLayout(item); iv.setContentsMargins(12,8,12,8); iv.setSpacing(2)
            row = QHBoxLayout()
            row.addWidget(_priority_dot(n.get("_priority", 1)))
            row.addWidget(_lbl(n.get("app",""), 10, dim=True))
            row.addStretch()
            row.addWidget(_lbl(n.get("time",""), 10, dim=True))
            iv.addLayout(row)
            iv.addWidget(_lbl(n.get("title",""), 12, bold=True, wrap=True))
            iv.addWidget(_lbl(n.get("body",""), 12, wrap=True))
            app_lower = n.get("app","").lower()
            if any(m in app_lower for m in ("whatsapp","telegram","signal","sms","messages")):
                reply_row = QHBoxLayout()
                reply_input = QLineEdit()
                reply_input.setPlaceholderText(self._("reply_placeholder"))
                reply_input.setFrame(False)
                send_btn = QToolButton()
                send_btn.setIcon(_themed_icon("mail-send-symbolic", QSize(16,16)))
                send_btn.setAutoRaise(True)
                reply_row.addWidget(reply_input, 1); reply_row.addWidget(send_btn)
                iv.addLayout(reply_row)
                def make_reply_handler(inp, notif=n):
                    def handler():
                        text = inp.text().strip()
                        if text:
                            _ws_send("phone_reply", {
                                "app": notif.get("app",""), "title": notif.get("title",""),
                                "reply": text})
                            inp.setText(""); inp.setPlaceholderText("Sent!")
                    return handler
                send_btn.clicked.connect(make_reply_handler(reply_input))
                reply_input.returnPressed.connect(make_reply_handler(reply_input))
            self._lay.addWidget(item)
            if n.get("app"): self._ai._last_notif_app = n["app"]

class FilesTab(QWidget):
    def __init__(self, tr, transfer_mgr: TransferManager, prefs: Preferences,
                 context_engine: ContextEngine, net_monitor: NetworkMonitor):
        super().__init__()
        self._ = tr; self._tm = transfer_mgr; self._prefs = prefs
        self._ctx = context_engine; self._nm = net_monitor
        v = QVBoxLayout(self); v.setContentsMargins(24,24,24,24); v.setSpacing(12)
        send_row = QHBoxLayout()
        self._btn = QPushButton(
            _themed_icon("document-send-symbolic", QSize(18,18)), tr("send_file"))
        self._btn.setMinimumHeight(36); self._btn.setEnabled(False)
        self._btn.clicked.connect(self._on_send)
        send_row.addWidget(self._btn, 1)
        self._compress_cb = QCheckBox(tr("compress"))
        self._compress_cb.setChecked(True); send_row.addWidget(self._compress_cb)
        v.addLayout(send_row)
        v.addWidget(_sep())
        v.addWidget(_lbl(tr("transfer_log"), 11, dim=True))
        self._log = QTextEdit(); self._log.setReadOnly(True)
        self._log.setFrameShape(QFrame.NoFrame)
        p = self._log.palette(); p.setColor(QPalette.Base, BG_CARD)
        self._log.setPalette(p)
        v.addWidget(self._log, 1)
        SIG.transfer_progress.connect(self._on_progress)

    def set_enabled(self, on): self._btn.setEnabled(on)

    def _on_send(self):
        path, _ = QFileDialog.getOpenFileName(self, self._("send_file"))
        if not path: return
        compress = self._compress_cb.isChecked()
        if self._nm.should_compress() and not compress:
            compress = True; self._compress_cb.setChecked(True)
        self._btn.setEnabled(False)
        threading.Thread(target=self._do_send, args=(path, compress), daemon=True).start()

    def _do_send(self, path, compress):
        fname = Path(path).name
        self._ctx.record_file_sent(path)
        def on_done(tid):
            QTimer.singleShot(0, lambda: self._btn.setEnabled(True))
        tid = self._tm.send_file(path, on_done=on_done, compress=compress)
        if tid:
            self._log.append(f"[>] {fname}")
        else:
            self._log.append(f"[X] Failed: {fname}")
            QTimer.singleShot(0, lambda: self._btn.setEnabled(True))

    def _on_progress(self, info):
        if info.get("done"):
            self._log.append(f"[v] {info.get('file','?')}")
            SIG.toast.emit("Y-Connect", f"Sent: {info.get('file','?')}")

class PhoneTab(QWidget):
    def __init__(self, tr, prefs: Preferences, context_engine: ContextEngine):
        super().__init__()
        self._ = tr; self._prefs = prefs; self._ctx = context_engine
        v = QVBoxLayout(self); v.setContentsMargins(24,24,24,24); v.setSpacing(16)
        bat_box = QWidget(); bat_box.setAutoFillBackground(True)
        bp = bat_box.palette(); bp.setColor(QPalette.Window, BG_CARD); bat_box.setPalette(bp)
        bv = QVBoxLayout(bat_box); bv.setContentsMargins(12,8,12,8); bv.setSpacing(4)
        bat_title = QHBoxLayout()
        self._bat_icon_lbl = QLabel()
        self._bat_icon_lbl.setPixmap(_themed_pixmap("battery-full-symbolic", QSize(20,20)))
        bat_title.addWidget(self._bat_icon_lbl)
        bat_title.addWidget(_lbl(tr("battery"), 12, bold=True))
        self._bat_label = _lbl("--", 14, bold=True)
        bat_title.addWidget(self._bat_label); bat_title.addStretch(); bv.addLayout(bat_title)
        self._bat_bar = QProgressBar(); self._bat_bar.setRange(0,100)
        self._bat_bar.setTextVisible(False); self._bat_bar.setFixedHeight(8)
        bv.addWidget(self._bat_bar); v.addWidget(bat_box)
        v.addWidget(_lbl(tr("phone_vol"), 11, dim=True))
        vrow = QHBoxLayout()
        self._vd = _media_btn("audio-volume-low-symbolic", 40)
        self._vm = _media_btn("audio-volume-muted-symbolic", 40)
        self._vu = _media_btn("audio-volume-high-symbolic", 40)
        for b in (self._vd,self._vm,self._vu): b.setEnabled(False); vrow.addWidget(b)
        vrow.addStretch(); v.addLayout(vrow)
        self._vd.clicked.connect(lambda: _ws_send("phone_control",{"action":"vol_down"}))
        self._vm.clicked.connect(lambda: _ws_send("phone_control",{"action":"vol_mute"}))
        self._vu.clicked.connect(lambda: _ws_send("phone_control",{"action":"vol_up"}))
        v.addWidget(_sep())
        v.addWidget(_lbl(tr("phone_notifs"), 11, dim=True))
        self._nc = QWidget(); self._nl = QVBoxLayout(self._nc)
        self._nl.setAlignment(Qt.AlignTop); self._nl.setSpacing(6)
        self._nl.addWidget(_lbl(tr("no_notifs"), 12, dim=True))
        v.addWidget(_scrolled(self._nc), 1)
        SIG.battery.connect(self._on_battery)

    def set_enabled(self, on):
        for b in (self._vd,self._vm,self._vu): b.setEnabled(on)

    def _on_battery(self, info):
        pct = info.get("pct", info.get("percent", -1)); charging = info.get("charging", False)
        if pct >= 0:
            self._bat_bar.setValue(pct)
            text = f"{pct}%"
            if charging: text += " " + self._("phone_charging")
            self._bat_label.setText(text)
            self._ctx.set_phone_battery(pct)
            if pct > 80: icon = "battery-full-symbolic"
            elif pct > 50: icon = "battery-good-symbolic"
            elif pct > 20: icon = "battery-low-symbolic"
            else: icon = "battery-caution-symbolic"
            self._bat_icon_lbl.setPixmap(
                _themed_pixmap(icon, QSize(20,20), WARN if pct <= 15 else FG))

    def update_phone_notifs(self, notifs):
        while self._nl.count():
            w = self._nl.takeAt(0).widget()
            if w: w.deleteLater()
        if not notifs:
            self._nl.addWidget(_lbl(self._("no_notifs"), 12, dim=True)); return
        for n in notifs:
            item = QWidget(); item.setAutoFillBackground(True)
            p = item.palette(); p.setColor(QPalette.Window, BG_CARD); item.setPalette(p)
            iv = QVBoxLayout(item); iv.setContentsMargins(12,8,12,8); iv.setSpacing(2)
            iv.addWidget(_lbl(n.get("title",""), 12, bold=True, wrap=True))
            iv.addWidget(_lbl(n.get("body",""), 12, wrap=True))
            app_lower = n.get("app","").lower()
            if any(m in app_lower for m in ("whatsapp","telegram","signal","sms")):
                reply_row = QHBoxLayout()
                reply_input = QLineEdit()
                reply_input.setPlaceholderText(self._("reply_placeholder"))
                reply_input.setFrame(False)
                send_btn = QToolButton()
                send_btn.setIcon(_themed_icon("mail-send-symbolic", QSize(16,16)))
                send_btn.setAutoRaise(True)
                reply_row.addWidget(reply_input, 1); reply_row.addWidget(send_btn)
                iv.addLayout(reply_row)
                def make_handler(inp, notif=n):
                    def handler():
                        text = inp.text().strip()
                        if text:
                            _ws_send("phone_reply", {
                                "app": notif.get("app",""), "title": notif.get("title",""),
                                "reply": text})
                            inp.setText(""); inp.setPlaceholderText("Sent!")
                    return handler
                send_btn.clicked.connect(make_handler(reply_input))
                reply_input.returnPressed.connect(make_handler(reply_input))
            self._nl.addWidget(item)

class ClipboardTab(QWidget):
    def __init__(self, tr, clipboard_sync: ClipboardSync, prefs: Preferences):
        super().__init__()
        self._ = tr; self._cs = clipboard_sync; self._prefs = prefs
        v = QVBoxLayout(self); v.setContentsMargins(24,24,24,24); v.setSpacing(16)
        ctrl = QHBoxLayout()
        self._auto_cb = QCheckBox(tr("clipboard_auto"))
        self._auto_cb.setChecked(prefs.get("clipboard_auto", False))
        self._auto_cb.toggled.connect(self._on_auto_toggle)
        ctrl.addWidget(self._auto_cb); ctrl.addStretch(); v.addLayout(ctrl)
        self._send_btn = QPushButton(
            _themed_icon("edit-paste-symbolic", QSize(18,18)), tr("clipboard_send"))
        self._send_btn.setMinimumHeight(36); self._send_btn.setEnabled(False)
        self._send_btn.clicked.connect(lambda: self._cs.send_clipboard())
        v.addWidget(self._send_btn)
        v.addWidget(_sep())
        v.addWidget(_lbl(tr("clipboard_recv"), 11, dim=True))
        self._preview = QTextEdit(); self._preview.setReadOnly(True)
        self._preview.setFrameShape(QFrame.NoFrame); self._preview.setMaximumHeight(200)
        p = self._preview.palette(); p.setColor(QPalette.Base, BG_CARD)
        self._preview.setPalette(p); v.addWidget(self._preview)
        v.addWidget(_lbl("Send text to phone:", 11, dim=True))
        self._input = QLineEdit(); self._input.setFrame(False)
        self._input.setPlaceholderText("Type text to send...")
        self._input.returnPressed.connect(self._on_manual_send)
        v.addWidget(self._input); v.addStretch()
        SIG.clipboard_sync.connect(self._on_clipboard_recv)

    def set_enabled(self, on): self._send_btn.setEnabled(on)

    def _on_auto_toggle(self, on): self._cs.auto_sync = on; self._prefs.set("clipboard_auto", on)

    def _on_manual_send(self):
        text = self._input.text().strip()
        if text:
            _ws_send("clipboard", {"text": text}); self._input.clear()
            self._preview.append(f"[>] {text[:100]}")

    def _on_clipboard_recv(self, text):
        self._preview.append(f"[<] {text[:200]}")
        self._preview.moveCursor(QTextCursor.End)

class SettingsTab(QWidget):
    def __init__(self, tr, prefs: Preferences):
        super().__init__()
        self._ = tr; self._prefs = prefs
        v = QVBoxLayout(self); v.setContentsMargins(24,24,24,24); v.setSpacing(16)
        v.addWidget(_lbl(tr("settings"), 16, bold=True)); v.addWidget(_sep())
        self._reconn_cb = QCheckBox(tr("auto_reconnect"))
        self._reconn_cb.setChecked(prefs.get("auto_reconnect", True))
        self._reconn_cb.toggled.connect(lambda on: prefs.set("auto_reconnect", on))
        v.addWidget(self._reconn_cb)
        self._clip_cb = QCheckBox(tr("clipboard_auto"))
        self._clip_cb.setChecked(prefs.get("clipboard_auto", False))
        v.addWidget(self._clip_cb)
        bat_h = QHBoxLayout(); bat_h.addWidget(_lbl(tr("battery_alert"), 12))
        self._bat_spin = QSpinBox(); self._bat_spin.setRange(5, 50)
        self._bat_spin.setValue(prefs.get("battery_alert_threshold", 15))
        self._bat_spin.setSuffix("%")
        self._bat_spin.valueChanged.connect(lambda val: prefs.set("battery_alert_threshold", val))
        bat_h.addWidget(self._bat_spin); bat_h.addStretch(); v.addLayout(bat_h)
        v.addStretch()

class DevicePanel(QWidget):
    def __init__(self, tr, ai_modules: dict):
        super().__init__()
        self._ = tr
        self._dm = ai_modules["device_memory"]
        self._ctx = ai_modules["context_engine"]
        self._nm = ai_modules["net_monitor"]
        self._prefs = ai_modules["prefs"]
        self._cs = ai_modules["clipboard_sync"]
        self._tm = ai_modules["transfer_mgr"]
        self._notif_ai = ai_modules["notif_ai"]
        self._current_device: Optional[dict] = None

        v = QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(0)

        tab_bar = QWidget(); tab_bar.setFixedHeight(40); tab_bar.setAutoFillBackground(True)
        tp = tab_bar.palette(); tp.setColor(QPalette.Window, BG_CARD); tab_bar.setPalette(tp)
        th = QHBoxLayout(tab_bar); th.setContentsMargins(8,0,8,0); th.setSpacing(0)
        self._tab_btns = []
        tab_defs = [
            ("connect_tab","network-wireless-symbolic"),
            ("status_tab","computer-symbolic"),
            ("media_tab","media-playback-start-symbolic"),
            ("notif_tab","notification-symbolic"),
            ("files_tab","folder-symbolic"),
            ("phone_tab","phone-symbolic"),
            ("clipboard_tab","edit-paste-symbolic"),
            ("settings","preferences-system-symbolic"),
        ]
        for i, (key, icon) in enumerate(tab_defs):
            btn = QToolButton()
            btn.setIcon(_themed_icon(icon, QSize(16,16)))
            btn.setIconSize(QSize(16,16))
            btn.setText(tr(key))
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            btn.setAutoRaise(True); btn.setCheckable(True); btn.setFixedHeight(32)
            btn.clicked.connect(lambda _, idx=i: self._switch(idx))
            th.addWidget(btn); self._tab_btns.append(btn)
        th.addStretch(); v.addWidget(tab_bar); v.addWidget(_sep())

        self._connect_tab = ConnectTab(tr, self._dm)
        self._status_tab  = StatusTab(tr, self._prefs)
        self._media_tab   = MediaTab(tr)
        self._notifs_tab  = NotifsTab(tr, self._notif_ai)
        self._files_tab   = FilesTab(tr, self._tm, self._prefs, self._ctx, self._nm)
        self._phone_tab   = PhoneTab(tr, self._prefs, self._ctx)
        self._clipboard_tab = ClipboardTab(tr, self._cs, self._prefs)
        self._settings_tab = SettingsTab(tr, self._prefs)
        self._stack = QStackedWidget()
        for tab in (self._connect_tab, self._status_tab, self._media_tab,
                    self._notifs_tab, self._files_tab, self._phone_tab,
                    self._clipboard_tab, self._settings_tab):
            self._stack.addWidget(tab)
        v.addWidget(self._stack, 1)

        self._sug_frame = QWidget(); self._sug_frame.setAutoFillBackground(True)
        sp = self._sug_frame.palette(); sp.setColor(QPalette.Window, BG_SIDE)
        self._sug_frame.setPalette(sp); self._sug_frame.setFixedHeight(36)
        sug_h = QHBoxLayout(self._sug_frame)
        sug_h.setContentsMargins(12,0,12,0); sug_h.setSpacing(8)
        self._sug_icon = QLabel()
        self._sug_icon.setPixmap(_themed_pixmap("dialog-information-symbolic", QSize(14,14)))
        sug_h.addWidget(self._sug_icon)
        self._sug_buttons: List[QToolButton] = []
        for _ in range(3):
            b = QToolButton(); b.setAutoRaise(True)
            b.setToolButtonStyle(Qt.ToolButtonTextOnly)
            b.setFixedHeight(28); b.setVisible(False)
            b.setStyleSheet("QToolButton { color: #99c1f1; padding: 2px 8px; }")
            sug_h.addWidget(b); self._sug_buttons.append(b)
        sug_h.addStretch(); v.addWidget(self._sug_frame)

        self._switch(0)

        SIG.resources.connect(self._status_tab.update_resources)
        SIG.media.connect(self._on_media)
        SIG.notifs.connect(self._notifs_tab.update_notifs)
        SIG.phone_notifs.connect(self._phone_tab.update_phone_notifs)
        SIG.battery.connect(self._on_battery)
        SIG.suggestion.connect(self._on_suggestions)

        self._sug_timer = QTimer(); self._sug_timer.setInterval(8000)
        self._sug_timer.timeout.connect(self._generate_suggestions)

    def _switch(self, idx):
        for i, btn in enumerate(self._tab_btns): btn.setChecked(i == idx)
        self._stack.setCurrentIndex(idx)
        self._ctx.set_active_tab(idx)
        if self._current_device: self._dm.update_preferred_tab(self._current_device, idx)

    def _on_media(self, m):
        self._media_tab.update_media(m)
        self._ctx.set_media_state(m.get("playing", False))

    def _on_battery(self, info):
        self._ctx.set_phone_battery(info.get("pct", info.get("percent", -1)))

    def _on_suggestions(self, suggestions):
        for i, btn in enumerate(self._sug_buttons):
            if i < len(suggestions):
                s = suggestions[i]; btn.setText(s["text"]); btn.setVisible(True)
                try: btn.clicked.disconnect()
                except Exception: pass
                btn.clicked.connect(lambda _, a=s["action"]: self._execute_suggestion(a))
            else: btn.setVisible(False)

    def _execute_suggestion(self, action: str):
        self._ctx.touch()
        if action == "battery_alert": self._switch(5)
        elif action == "media_pause": _ws_send("media_command", {"action": "play_pause"})
        elif action == "mute_phone": _ws_send("phone_control", {"action": "vol_mute"})
        elif action.startswith("send_recent:"):
            path = action.split(":", 1)[1]
            threading.Thread(target=self._tm.send_file, args=(path,), daemon=True).start()
        elif action.startswith("reply:"): self._switch(3)

    def _generate_suggestions(self):
        connected = self._current_device is not None
        sugs = self._ctx.get_suggestions(connected)
        if sugs: SIG.suggestion.emit(sugs[:3])

    def set_connected(self, name, rssi, device: dict = None):
        self._current_device = device; self.update_signal(rssi)
        for w in (self._media_tab, self._files_tab, self._phone_tab, self._clipboard_tab):
            w.set_enabled(True)
        if device:
            pref = self._dm.get_preferred_tab(device)
            if pref > 0: self._switch(min(pref, self._stack.count()-1))
        self._sug_timer.start()

    def set_disconnected(self):
        self._current_device = None; self._status_tab.reset()
        for w in (self._media_tab, self._files_tab, self._phone_tab, self._clipboard_tab):
            w.set_enabled(False)
        self._sug_timer.stop()
        for b in self._sug_buttons: b.setVisible(False)

    def update_signal(self, rssi):
        if rssi != -1:
            self._status_tab.update_signal(rssi); self._nm.update_rssi(rssi)

class MainWindow(QMainWindow):
    def __init__(self, tr, ai_modules: dict):
        super().__init__()
        self._ = tr; self._rssi = -1; self._connected = False
        self._current_device: Optional[dict] = None; self._ai = ai_modules
        self.setWindowTitle("Y-Connect")
        self.setMinimumSize(1080, 600)
        if LOGO_PATH.exists(): self.setWindowIcon(QIcon(str(LOGO_PATH)))

        root = QHBoxLayout(); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        central = QWidget(); central.setLayout(root); self.setCentralWidget(central)

        left = QWidget(); left.setFixedWidth(220); left.setAutoFillBackground(True)
        lp = left.palette(); lp.setColor(QPalette.Window, BG_SIDE); left.setPalette(lp)
        lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0); lv.setSpacing(0)

        lheader = QWidget(); lheader.setFixedHeight(60); lheader.setAutoFillBackground(True)
        lhp = lheader.palette(); lhp.setColor(QPalette.Window, BG_CARD); lheader.setPalette(lhp)
        lhh = QHBoxLayout(lheader); lhh.setContentsMargins(16,0,16,0); lhh.setSpacing(10)
        if LOGO_PATH.exists():
            logo = QLabel()
            logo.setPixmap(QPixmap(str(LOGO_PATH)).scaled(26,26, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            lhh.addWidget(logo)
        lhh.addWidget(_lbl("Y-Connect", 14, bold=True)); lhh.addStretch()
        lv.addWidget(lheader); lv.addWidget(_sep())

        self._dev_list = QListWidget(); self._dev_list.setFrameShape(QFrame.NoFrame)
        self._dev_list.setIconSize(QSize(24,24)); self._dev_list.setSpacing(2)
        lv.addWidget(self._dev_list, 1)
        self._dev_item = QListWidgetItem(
            _themed_icon("phone-symbolic", QSize(24,24)), tr("no_device"))
        self._dev_item.setSizeHint(QSize(220, 52))
        self._dev_list.addItem(self._dev_item); self._dev_list.setCurrentItem(self._dev_item)

        lv.addWidget(_sep())
        self._left_info = _lbl("", 10, dim=True, wrap=True)
        self._left_info.setContentsMargins(12,8,12,8); lv.addWidget(self._left_info)

        root.addWidget(left); root.addWidget(_vsep())

        self._panel = DevicePanel(tr, ai_modules); root.addWidget(self._panel, 1)

        self._cmd_palette = CommandPalette(tr)
        self._cmd_palette.action_triggered.connect(self._execute_command)
        QShortcut(QKeySequence("Ctrl+K"), self).activated.connect(
            lambda: self._cmd_palette.show_palette(self))

        SIG.connected.connect(self._on_connected)
        SIG.disconnected.connect(self._on_disconnected)
        SIG.toast.connect(self._show_toast)

    def _on_connected(self, device):
        self._connected = True; self._current_device = device
        name = device.get("name", device.get("ip","Android"))
        self._dev_item.setText(name)
        self._dev_item.setIcon(_themed_icon("phone-symbolic", QSize(24,24), ACCENT))
        dm = self._ai["device_memory"]; fp = dm.remember(device)
        trusted = dm.is_trusted(device); last_seen = dm.last_seen_str(device)
        info_text = ""
        if trusted: info_text += "[" + self._("trusted_mark") + "]\n"
        if last_seen: info_text += self._("last_label", last_seen) + "\n"
        self._left_info.setText(info_text)
        self._panel.set_connected(name, self._rssi, device)
        self._show_toast("Y-Connect", self._("toast_connected", name))

    def _on_disconnected(self, _):
        self._connected = False; self._current_device = None; self._rssi = -1
        self._dev_item.setText(self._("no_device"))
        self._dev_item.setIcon(_themed_icon("phone-symbolic", QSize(24,24), FG_DIM))
        self._left_info.setText("")
        self._panel.set_disconnected()
        self._show_toast("Y-Connect", self._("toast_disconnected"))
        prefs = self._ai["prefs"]; reconn = self._ai["reconnector"]
        if prefs.get("auto_reconnect", True) and not reconn.active:
            reconn.start(self._current_device or {})

    def update_signal(self, rssi):
        self._rssi = rssi
        if self._connected:
            self._panel.update_signal(rssi)

    def _show_toast(self, title, body):
        toast = ToastWidget(title, body); toast.show_toast(self)

    def _execute_command(self, action):
        if action == "send_file": self._panel._switch(4)
        elif action == "send_clipboard": self._ai["clipboard_sync"].send_clipboard()
        elif action == "media_pause": _ws_send("media_command", {"action": "play_pause"})
        elif action == "media_next": _ws_send("media_command", {"action": "next"})
        elif action == "media_prev": _ws_send("media_command", {"action": "prev"})
        elif action == "vol_up": _ws_send("media_command", {"action": "vol_up"})
        elif action == "vol_down": _ws_send("media_command", {"action": "vol_down"})
        elif action == "mute_phone": _ws_send("phone_control", {"action": "vol_mute"})
        elif action.startswith("tab_"):
            tab_map = {"tab_connect":0, "tab_status":1, "tab_media":2,
                       "tab_notif":3, "tab_files":4, "tab_phone":5}
            self._panel._switch(tab_map.get(action, 0))
        elif action == "settings": self._panel._switch(7)
        elif action == "about": self._on_about()
        elif action == "quit": QApplication.quit()

    def _on_about(self):
        box = QMessageBox()
        box.setWindowTitle(self._("about"))
        box.setText("<b>Y-Connect v2.0</b>")
        box.setInformativeText(self._("about_text"))
        if LOGO_PATH.exists():
            box.setIconPixmap(QPixmap(str(LOGO_PATH)).scaled(
                64,64,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        box.exec()

    def closeEvent(self, event): event.ignore(); self.hide()

class YelenaTray:
    def __init__(self):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)
        _apply_palette(self._app)
        self._lang = _detect_lang()
        self._connected = False; self._rssi = -1

        self._prefs       = Preferences()
        self._device_mem  = DeviceMemory()
        self._net_monitor = NetworkMonitor()
        self._reconnector = SmartReconnector()
        self._notif_ai    = NotificationAI()
        self._transfer_mgr= TransferManager(self._net_monitor)
        self._clipboard   = ClipboardSync()
        self._context     = ContextEngine(self._device_mem)
        self._ai_modules = {
            "device_memory":  self._device_mem,
            "net_monitor":    self._net_monitor,
            "reconnector":    self._reconnector,
            "notif_ai":       self._notif_ai,
            "transfer_mgr":   self._transfer_mgr,
            "clipboard_sync": self._clipboard,
            "context_engine": self._context,
            "prefs":          self._prefs,
        }
        self._clipboard.init(self._app)
        self._clipboard.auto_sync = self._prefs.get("clipboard_auto", False)
        os.environ["_yconnect_lang"] = self._lang

        manager.on_wifi_connected(self._cb_wifi_connected)
        manager.on_wifi_disconnected(self._cb_wifi_disconnected)
        manager.on_android_found(self._cb_found)
        manager.on_pair_request(self._cb_pair_request)
        manager.on_battery_update(lambda ip, pct, charging: SIG.battery.emit({"pct": pct, "charging": charging}))
        manager.on_rssi_changed(lambda rssi: self._panel.update_signal(rssi))
        manager.on_resources_changed(lambda data: SIG.resources.emit(data))
        manager.on_phone_media_changed(lambda data: SIG.media.emit(data))

        self._window = MainWindow(self._, self._ai_modules)
        self._build_tray()

        self._sig_timer = QTimer(); self._sig_timer.timeout.connect(self._update_signal)
        self._sig_timer.start(6_000)
        self._poll_timer = QTimer(); self._poll_timer.timeout.connect(self._adaptive_poll)
        self._poll_timer.start(5_000)

        SIG.reconn_status.connect(self._on_reconn_status)
        SIG.pair_request.connect(self._handle_pair_request)
        SIG.wifi_connected.connect(self._handle_wifi_connected)
        SIG.wifi_disconnected.connect(self._handle_wifi_disconnected)
        self._window.show()
        log.info("Y-Connect v2.0 started")

    def _(self, key, *args):
        tmpl = STRINGS.get(self._lang, STRINGS["en"]).get(key, key)
        return tmpl.format(*args) if args else tmpl

    def _build_tray(self):
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(_icon_for_signal(False,-1))
        self._tray.setToolTip("Y-Connect")
        self._tray.activated.connect(
            lambda r: (self._window.show(), self._window.raise_(),
                       self._window.activateWindow())
            if r == QSystemTrayIcon.Trigger else None)
        menu = QMenu()
        a = QAction(self._("show"), menu)
        a.triggered.connect(lambda: (self._window.show(), self._window.raise_()))
        menu.addAction(a); menu.addSeparator()
        clip_action = QAction(
            _themed_icon("edit-paste-symbolic", QSize(16,16)),
            self._("clipboard_send"), menu)
        clip_action.triggered.connect(lambda: self._clipboard.send_clipboard())
        menu.addAction(clip_action); menu.addSeparator()
        ab = QAction(self._("about"), menu); ab.triggered.connect(self._on_about)
        menu.addAction(ab)
        q = QAction(self._("quit"), menu); q.triggered.connect(self._on_quit)
        menu.addAction(q)
        self._tray.setContextMenu(menu); self._tray.setVisible(True)
    def _cb_wifi_connected(self, device):
        print("[tray] WiFi connected callback from backend, emitting signal...")
        SIG.wifi_connected.emit(device)

    def _cb_wifi_disconnected(self, ip):
        print("[tray] WiFi disconnected callback from backend, emitting signal...")
        SIG.wifi_disconnected.emit(ip)

    def _handle_wifi_connected(self, device):
        print(f"[tray] Updating UI for connected device: {device}")
        self._connected = True
        self._rssi = -1

        SIG.connected.emit(device)
        self._tray.setIcon(_icon_for_signal(True, -1))

        if self._reconnector.active:
            self._reconnector.stop()
            SIG.reconn_status.emit("ok", 0)

        if hasattr(self._window._panel, '_connect_tab'):
            self._window._panel._connect_tab._refresh_known()

    def _handle_wifi_disconnected(self, ip):
        if not manager.is_connected() and not manager.is_wifi_connected():
            self._connected = False
            self._rssi = -1
            SIG.disconnected.emit(ip)
            self._tray.setIcon(_icon_for_signal(False, -1))
    def _cb_found(self, device):
        name = device.get("name", "Android"); ip = device.get("ip", "?")
        log.info("Android found on network: %s @ %s", name, ip)
        entry = self._device_mem.lookup(device)
        if entry:
            log.info("Known device: %s (trusted=%s, last=%s)",
                     name, entry.get("trusted"), self._device_mem.last_seen_str(device))
            SIG.toast.emit("Y-Connect", self._("nearby", name))

    def _update_signal(self):
        rssi = getattr(manager.ws_server,"_last_wifi_rssi",-1)
        if rssi != self._rssi:
            self._rssi = rssi
            self._tray.setIcon(_icon_for_signal(self._connected,rssi))
            self._window.update_signal(rssi)

    def _adaptive_poll(self):
        interval = self._net_monitor.poll_interval_ms()
        if self._sig_timer.interval() != interval:
            self._sig_timer.setInterval(interval)

    def _on_reconn_status(self, status, attempt):
        if status == "ok" and self._reconnector.active: self._reconnector.stop()

    def _on_about(self):
        box = QMessageBox()
        box.setWindowTitle(self._("about"))
        box.setText("<b>Y-Connect v2.0</b>")
        box.setInformativeText(self._("about_text"))
        if LOGO_PATH.exists():
            box.setIconPixmap(QPixmap(str(LOGO_PATH)).scaled(
                64,64,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        box.exec()

    def _on_quit(self):
        self._reconnector.stop()
        try: manager.discovery.stop()
        except Exception: pass
        self._tray.setVisible(False); self._app.quit()

    def run(self):
        sys.exit(self._app.exec())

    def _cb_pair_request(self, ip, device_name):

        SIG.pair_request.emit(ip, device_name)

    def _handle_pair_request(self, ip, device_name):

        box = QMessageBox(self._window)
        box.setWindowTitle("Y-Connect — Pairing Request")
        box.setText(f"Device <b>{device_name}</b> ({ip}) wants to connect.")
        box.setInformativeText("Do you want to allow this device to connect?")

        btn_trust  = box.addButton("Trust Always", QMessageBox.AcceptRole)
        btn_accept = box.addButton("Accept Once", QMessageBox.AcceptRole)
        btn_reject = box.addButton("Reject", QMessageBox.RejectRole)
        box.setDefaultButton(btn_trust)

        box.exec()

        clicked = box.clickedButton()
        if clicked == btn_trust:
            manager.accept_pair(ip, trust=True)
        elif clicked == btn_accept:
            manager.accept_pair(ip, trust=False)
        else:
            manager.reject_pair(ip)

if __name__ == "__main__":
    YelenaTray().run()