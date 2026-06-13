import subprocess
import threading
import time
import os
import re
import json
import socket
import asyncio
import shutil
import platform
import glob
import select
import base64
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Callable

try:
    import websockets
    import websockets.server
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    print("[ws] 'websockets' not installed. Run: pip install websockets")

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("[ws] 'psutil' not installed. Run: pip install psutil")

BASE_DIR = Path(__file__).parent
SCRCPY_DIR = BASE_DIR / "scrcpy"
SCRCPY_BIN = SCRCPY_DIR / "scrcpy"
ADB_BIN = SCRCPY_DIR / "adb"
PAIRING_FILE = BASE_DIR / ".trusted_devices"

def get_adb() -> str:
    if ADB_BIN.exists():
        return str(ADB_BIN)
    return "adb"

def get_scrcpy() -> str:
    if SCRCPY_BIN.exists():
        return str(SCRCPY_BIN)
    return "scrcpy"

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def adb(args: list, device_serial: str = None, timeout: int = 5) -> str:
    cmd = [get_adb()]
    if device_serial:
        cmd += ["-s", device_serial]
    cmd += args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except Exception:
        return ""

def adb_shell(cmd_str: str, device_serial: str = None, timeout: int = 5) -> str:
    return adb(["shell", cmd_str], device_serial=device_serial, timeout=timeout)

def list_devices() -> list[dict]:

    output = adb(["devices", "-l"], timeout=8)
    devices = []
    for line in output.splitlines()[1:]:
        line = line.strip()
        if not line or "offline" in line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial = parts[0]
        state = parts[1]
        if state != "device":
            continue

        model_m = re.search(r"model:(\S+)", line)
        name = model_m.group(1) if model_m else serial

        conn_type = "wifi" if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", serial) else "usb"

        devices.append({
            "serial": serial,
            "state": state,
            "name": name,
            "type": conn_type,
        })
    return devices

def connect_wifi(ip: str, port: int = 5555) -> tuple[bool, str]:
    output = adb(["connect", f"{ip}:{port}"], timeout=10)
    if "connected" in output.lower():
        return True, output
    return False, output

def disconnect_wifi(serial: str) -> bool:
    output = adb(["disconnect", serial], timeout=5)
    return "disconnected" in output.lower()

class ScrcpySession:
    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        if SCRCPY_BIN.exists():
            try:
                SCRCPY_BIN.chmod(0o755)
            except Exception:
                pass

    def start(self, serial: str) -> bool:
        self.stop()
        cmd = [get_scrcpy(), "-s", serial]
        try:
            env = os.environ.copy()
            with self._lock:
                self._proc = subprocess.Popen(
                    cmd, env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            print(f"[scrcpy] Launched PID={self._proc.pid}")
            return True
        except Exception as e:
            print(f"[scrcpy] Error: {e}")
            return False

    def stop(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            self._proc = None

    def is_running(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

class ResourceMonitor:
    def __init__(self):
        self._serial: Optional[str] = None
        self._data: dict = {}
        self._data_lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable] = []
        self._interval = 3.0

    def set_serial(self, serial: str):
        self._serial = serial

    def add_callback(self, cb: Callable):
        self._callbacks.append(cb)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            if self._serial:
                data = self._fetch()
                with self._data_lock:
                    self._data = data
                for cb in self._callbacks:
                    try:
                        cb(data)
                    except Exception:
                        pass
            time.sleep(self._interval)

    def _fetch(self) -> dict:
        s = self._serial
        result: dict = {}

        with ThreadPoolExecutor(max_workers=4) as pool:
            f_cpu = pool.submit(adb_shell, "dumpsys cpuinfo | grep TOTAL", s, 4)
            f_mem = pool.submit(adb_shell, "cat /proc/meminfo", s, 4)
            f_bat = pool.submit(adb_shell, "dumpsys battery", s, 4)
            f_sto = pool.submit(adb_shell, "df /data 2>/dev/null | tail -1", s, 4)

        try:
            cpu_raw = f_cpu.result(timeout=6)
            match = re.search(r"([\d.]+)%\s+TOTAL", cpu_raw)
            if match:
                result["cpu"] = float(match.group(1))
            else:
                stat1 = adb_shell("cat /proc/stat | head -1", s, timeout=3)
                time.sleep(0.5)
                stat2 = adb_shell("cat /proc/stat | head -1", s, timeout=3)
                result["cpu"] = self._parse_cpu_stat(stat1, stat2)
        except Exception:
            result["cpu"] = 0.0

        try:
            mem_raw = f_mem.result(timeout=6)
            total = self._parse_meminfo(mem_raw, "MemTotal")
            available = self._parse_meminfo(mem_raw, "MemAvailable")
            if total and available:
                used = total - available
                result["ram_used_mb"] = round(used / 1024)
                result["ram_total_mb"] = round(total / 1024)
                result["ram_pct"] = round(used / total * 100, 1)
        except Exception:
            result["ram_used_mb"] = 0
            result["ram_total_mb"] = 0
            result["ram_pct"] = 0.0

        try:
            bat_raw = f_bat.result(timeout=6)
            level_m = re.search(r"level:\s*(\d+)", bat_raw)
            temp_m = re.search(r"temperature:\s*(\d+)", bat_raw)
            charging_m = re.search(r"status:\s*(\d+)", bat_raw)
            result["battery_pct"] = int(level_m.group(1)) if level_m else 0
            result["battery_temp"] = round(int(temp_m.group(1)) / 10, 1) if temp_m else 0.0
            result["battery_charging"] = (int(charging_m.group(1)) == 2) if charging_m else False
        except Exception:
            result["battery_pct"] = 0
            result["battery_temp"] = 0.0
            result["battery_charging"] = False

        try:
            df_raw = f_sto.result(timeout=6)
            parts = df_raw.split()
            if len(parts) >= 4:
                total_k = int(re.sub(r"[^\d]", "", parts[1]))
                used_k = int(re.sub(r"[^\d]", "", parts[2]))
                result["storage_used_gb"] = round(used_k / 1024 / 1024, 1)
                result["storage_total_gb"] = round(total_k / 1024 / 1024, 1)
                result["storage_pct"] = round(used_k / total_k * 100, 1) if total_k else 0
        except Exception:
            result["storage_used_gb"] = 0.0
            result["storage_total_gb"] = 0.0
            result["storage_pct"] = 0.0

        return result

    @staticmethod
    def _parse_cpu_stat(stat1: str, stat2: str) -> float:
        try:
            v1 = list(map(int, stat1.split()[1:]))
            v2 = list(map(int, stat2.split()[1:]))
            idle1, idle2 = v1[3], v2[3]
            total1, total2 = sum(v1), sum(v2)
            diff_total = total2 - total1
            diff_idle = idle2 - idle1
            if diff_total == 0:
                return 0.0
            return round((1 - diff_idle / diff_total) * 100, 1)
        except Exception:
            return 0.0

    @staticmethod
    def _parse_meminfo(raw: str, key: str) -> Optional[int]:
        match = re.search(rf"{key}:\s+(\d+)\s+kB", raw)
        return int(match.group(1)) if match else None

    def get_data(self) -> dict:
        with self._data_lock:
            return self._data.copy()

class NotificationMonitor:
    _APP_NAMES = {
        "com.whatsapp": "WhatsApp",
        "com.telegram.messenger": "Telegram",
        "org.telegram.messenger": "Telegram",
        "com.google.android.gm": "Gmail",
        "com.instagram.android": "Instagram",
        "com.twitter.android": "Twitter/X",
        "com.spotify.music": "Spotify",
        "com.google.android.youtube": "YouTube",
        "com.android.phone": "Phone",
        "com.google.android.apps.messaging": "Messages",
        "com.facebook.katana": "Facebook",
        "com.discord": "Discord",
    }

    def __init__(self):
        self._serial: Optional[str] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable] = []
        self._interval = 3.0

    def set_serial(self, serial: str):
        self._serial = serial

    def add_callback(self, cb: Callable):
        self._callbacks.append(cb)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            if self._serial:
                notifs = self._fetch()
                for cb in self._callbacks:
                    try:
                        cb(notifs)
                    except Exception:
                        pass
            time.sleep(self._interval)

    def _fetch(self) -> list[dict]:
        raw = adb_shell(
            "dumpsys notification --noredact 2>/dev/null",
            self._serial, timeout=8
        )
        return self._parse_notifications(raw)

    def _parse_notifications(self, raw: str) -> list[dict]:
        notifications = []
        blocks = re.split(r"NotificationRecord\(", raw)
        for block in blocks[1:]:
            try:
                pkg_m = re.search(r"pkg=(\S+)", block)
                title_m = re.search(r"android\.title[^=]*=\s*([^\n]+)", block)
                text_m = re.search(r"android\.text[^=]*=\s*([^\n]+)", block)
                id_m = re.search(r"id=(\d+)", block)

                pkg = pkg_m.group(1) if pkg_m else "unknown"
                title = title_m.group(1).strip() if title_m else ""
                text = text_m.group(1).strip() if text_m else ""
                notif_id = id_m.group(1) if id_m else ""

                if not title and not text:
                    continue

                title = re.sub(r"\s+", " ", title)[:80]
                text = re.sub(r"\s+", " ", text)[:120]

                notifications.append({
                    "id": f"{pkg}_{notif_id}",
                    "package": pkg,
                    "app": self._pkg_to_name(pkg),
                    "title": title,
                    "text": text,
                })
            except Exception:
                continue

        seen: set[str] = set()
        unique = []
        for n in notifications:
            if n["id"] not in seen:
                seen.add(n["id"])
                unique.append(n)

        return unique[:30]

    @classmethod
    def _pkg_to_name(cls, pkg: str) -> str:
        return cls._APP_NAMES.get(pkg, pkg.split(".")[-1].capitalize())

class MediaController:
    def __init__(self):
        self._serial: Optional[str] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable] = []
        self._interval = 2.0
        self._current: dict = {}
        self._current_lock = threading.Lock()

    def set_serial(self, serial: str):
        self._serial = serial

    def add_callback(self, cb: Callable):
        self._callbacks.append(cb)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            if self._serial:
                data = self._fetch_media_info()
                with self._current_lock:
                    self._current = data
                for cb in self._callbacks:
                    try:
                        cb(data)
                    except Exception:
                        pass
            time.sleep(self._interval)

    def _fetch_media_info(self) -> dict:
        result = {"title": "", "artist": "", "album": "", "playing": False, "package": ""}

        raw = adb_shell("dumpsys media_session 2>/dev/null", self._serial, timeout=7)

        if raw:
            sm = re.search(r"state=(\d+)", raw)
            if sm:
                result["playing"] = int(sm.group(1)) == 3

            pm = re.search(r"package=(\S+)", raw)
            if pm:
                result["package"] = pm.group(1)

            for meta_key, field in [("TITLE", "title"), ("ARTIST", "artist"), ("ALBUM", "album")]:
                m = re.search(
                    rf"android\.media\.metadata\.{meta_key}\s*(?:\([^)]+\))?\s*[=:]\s*(.+)",
                    raw, re.IGNORECASE
                )
                if m:
                    val = m.group(1).strip().strip(",").strip()
                    if val and val.lower() not in ("null", "none", "")\
                            and not val.startswith("size="):
                        result[field] = val[:80]

        if not result["title"]:
            notif = adb_shell(
                "dumpsys notification --noredact 2>/dev/null",
                self._serial, timeout=6
            )
            if notif:
                blocks = re.split(r"NotificationRecord\(", notif)
                for block in blocks[1:]:
                    if "MediaStyle" not in block and "mediaSession" not in block:
                        continue
                    tm = re.search(r"android\.title\b[^=\n]*=\s*([^\n]+)", block)
                    am = re.search(r"android\.text\b[^=\n]*=\s*([^\n]+)", block)
                    if tm:
                        val = tm.group(1).strip()
                        if val and "null" not in val.lower():
                            result["title"] = val[:80]
                            result["playing"] = True
                    if am:
                        val = am.group(1).strip()
                        if val and "null" not in val.lower():
                            result["artist"] = val[:60]
                    if result["title"]:
                        break

        if not result["title"] and raw:
            dm = re.search(r"\bdescription\s*=\s*([^\n,]+)", raw, re.IGNORECASE)
            if dm:
                val = dm.group(1).strip()
                if val and "null" not in val.lower() and not val.startswith("size="):
                    result["title"] = val[:80]

        return result

    def play_pause(self):
        self._keyevent(85)

    def next_track(self):
        self._keyevent(87)

    def prev_track(self):
        self._keyevent(88)

    def volume_up(self):
        self._keyevent(24)

    def volume_down(self):
        self._keyevent(25)

    def _keyevent(self, code: int):
        if self._serial:
            adb_shell(f"input keyevent {code}", self._serial)

    def get_current(self) -> dict:
        with self._current_lock:
            return self._current.copy()

class PhoneController:
    def __init__(self):
        self._serial: Optional[str] = None

    def set_serial(self, serial: str):
        self._serial = serial

    def dial(self, number: str) -> bool:
        if not self._serial:
            return False
        clean = re.sub(r"[^\d+*#()-]", "", number)
        if not clean:
            return False
        out = adb_shell(
            f"am start -a android.intent.action.CALL -d tel:{clean}",
            self._serial
        )
        return "Error" not in out

    def open_dialer(self, number: str = "") -> bool:
        if not self._serial:
            return False
        clean = re.sub(r"[^\d+*#()-]", "", number)
        uri = f"tel:{clean}" if clean else "tel:"
        out = adb_shell(
            f"am start -a android.intent.action.DIAL -d {uri}",
            self._serial
        )
        return "Error" not in out

    def end_call(self) -> bool:
        if not self._serial:
            return False
        adb_shell("input keyevent 6", self._serial)
        return True

    def send_dtmf(self, digit: str):
        dtmf_map = {
            "0": 7, "1": 8, "2": 9, "3": 10, "4": 11,
            "5": 12, "6": 13, "7": 14, "8": 15, "9": 16,
            "*": 17, "#": 18,
        }
        code = dtmf_map.get(digit)
        if code and self._serial:
            adb_shell(f"input keyevent {code}", self._serial)

class InputController:

    def __init__(self):
        self._mode: Optional[str] = None
        self._display_env: Optional[dict] = None

    def _build_display_env(self) -> dict:
        env = os.environ.copy()
        if not env.get("DISPLAY"):
            sockets = sorted(glob.glob("/tmp/.X11-unix/X*"))
            if sockets:
                num = sockets[0].replace("/tmp/.X11-unix/X", "")
                env["DISPLAY"] = f":{num}"
            else:
                env["DISPLAY"] = ":0"
        if not env.get("XAUTHORITY"):
            uid = os.getuid()
            for path in [
                os.path.expanduser("~/.Xauthority"),
                f"/run/user/{uid}/gdm/Xauthority",
                f"/run/user/{uid}/.Xauthority",
            ] + sorted(glob.glob("/tmp/.xauth*")):
                if os.path.exists(path):
                    env["XAUTHORITY"] = path
                    break
        return env

    @staticmethod
    def _find_ydotool_socket() -> Optional[str]:
        uid = os.getuid()
        for s in [
            f"/run/user/{uid}/.ydotool_socket",
            "/tmp/.ydotool_socket",
            f"/run/ydotoold/ydotoold.socket",
        ]:
            if os.path.exists(s):
                return s
        return None

    def _check_x11(self) -> bool:
        env = self._build_display_env()
        try:
            r = subprocess.run(
                ["xdpyinfo"], env=env,
                capture_output=True, timeout=1
            )
            return r.returncode == 0
        except Exception:
            return False

    def _ensure_detected(self):

        if self._mode is not None:
            return
        self._display_env = self._build_display_env()
        self._mode = "x11" if self._check_x11() else "wayland"
        print(f"[input] Detected display mode: {self._mode}")

    def _xdo(self, *args, timeout: float = 2.0):
        if not shutil.which("xdotool"):
            print("[input] Install xdotool: sudo apt install xdotool")
            return
        try:
            subprocess.run(
                ["xdotool", *args], env=self._display_env,
                capture_output=True, timeout=timeout
            )
        except Exception as e:
            print(f"[xdotool] {e}")

    def _ydo(self, *args, timeout: float = 2.0):
        if not shutil.which("ydotool"):
            print("[input] Install ydotool: sudo apt install ydotool")
            return
        sock = self._find_ydotool_socket()
        if not sock:
            print("[input] ydotoold not running — start it: ydotoold &")
            return
        env = os.environ.copy()
        env["YDOTOOL_SOCKET"] = sock
        try:
            subprocess.run(
                ["ydotool", *args], env=env,
                capture_output=True, timeout=timeout
            )
        except Exception as e:
            print(f"[ydotool] {e}")

    def _input_cmd(self, xdo_args: list, ydo_args: list):
        self._ensure_detected()
        if self._mode == "x11":
            self._xdo(*xdo_args)
        else:
            self._ydo(*ydo_args)

    def key_press(self, key: str):
        self._input_cmd(xdo_args=["key", key], ydo_args=["key", key])

    def type_text(self, text: str):
        self._input_cmd(
            xdo_args=["type", "--clearmodifiers", "--delay", "20", "--", text],
            ydo_args=["type", "--", text],
        )

    def mouse_move(self, dx: int, dy: int):
        self._input_cmd(
            xdo_args=["mousemove_relative", "--", str(dx), str(dy)],
            ydo_args=["mousemove", "--absolute", "-x", str(dx), "-y", str(dy)],
        )

    def mouse_click(self, button: str = "left"):
        btn_map = {"left": "1", "middle": "2", "right": "3"}
        xdo_btn = btn_map.get(button, "1")
        self._input_cmd(
            xdo_args=["click", xdo_btn],
            ydo_args=["click", "-b", xdo_btn],
        )

    def mouse_scroll(self, direction: str = "down"):
        if direction == "up":
            self._input_cmd(xdo_args=["click", "4"], ydo_args=["click", "-b", "4"])
        else:
            self._input_cmd(xdo_args=["click", "5"], ydo_args=["click", "-b", "5"])

    def reset_detection(self):

        self._mode = None
        self._display_env = None

class PersistentBash:

    SENTINEL = "__YELENA_CMD_DONE__"

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._start()

    def _start(self):
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["HOME"] = os.path.expanduser("~")
        self._proc = subprocess.Popen(
            ["/bin/bash", "--norc", "--noprofile"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
        )

    def _restart(self):

        try:
            if self._proc and self._proc.poll() is None:
                self._proc.stdin.close()
                self._proc.terminate()
                self._proc.wait(timeout=2)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass
        self._start()

    def run(self, cmd: str, timeout: float = 15.0) -> tuple[str, int]:
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                self._restart()

            try:
                sentinel_cmd = f'{cmd}\necho "{self.SENTINEL}:$?"\n'
                self._proc.stdin.write(sentinel_cmd)
                self._proc.stdin.flush()
            except Exception as e:
                self._restart()
                return str(e), 1

            lines: list[str] = []
            exit_code = 0
            deadline = time.time() + timeout

            try:
                while time.time() < deadline:
                    ready = select.select([self._proc.stdout], [], [], 0.1)[0]
                    if not ready:
                        continue
                    line = self._proc.stdout.readline()
                    if not line:
                        break
                    if line.startswith(self.SENTINEL + ":"):
                        exit_code = int(line.split(":")[1].strip() or "0")
                        break
                    lines.append(line.rstrip())
            except Exception as e:
                return str(e), 1

            out = "\n".join(lines).strip()
            return out or "(no output)", exit_code

    def close(self):

        with self._lock:
            try:
                if self._proc and self._proc.poll() is None:
                    self._proc.stdin.write("exit\n")
                    self._proc.stdin.flush()
                    self._proc.wait(timeout=2)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None

class ClipboardManager:

    def __init__(self):
        self._last: str = ""
        self._history: list[str] = []
        self._env: Optional[dict] = None

    def _make_env(self) -> dict:
        if self._env is not None:
            return self._env
        env = os.environ.copy()
        if not env.get("DISPLAY"):
            env["DISPLAY"] = ":0"
        if not env.get("XAUTHORITY"):
            uid = os.getuid()
            for path in [
                os.path.expanduser("~/.Xauthority"),
                f"/run/user/{uid}/gdm/Xauthority",
                f"/run/user/{uid}/.Xauthority",
                f"/tmp/.xauth-{uid}",
            ] + sorted(glob.glob("/tmp/.xauth*")) + sorted(glob.glob("/tmp/.Xauth*")):
                if os.path.exists(path):
                    env["XAUTHORITY"] = path
                    break
        self._env = env
        return env

    def get(self) -> str:
        try:
            r = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, timeout=2, env=self._make_env()
            )
            if r.returncode == 0:
                return r.stdout.decode("utf-8", errors="replace").strip()
            stderr = r.stderr.decode(errors="replace")
            if "not available" in stderr:
                return ""
            print(f"[clipboard] xclip error (rc={r.returncode}): {stderr[:80]}")
        except FileNotFoundError:
            print("[clipboard] xclip not found: sudo apt install xclip")
        except Exception as e:
            print(f"[clipboard] get error: {e}")
        return ""

    def set(self, text: str):
        try:
            r = subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode("utf-8"),
                capture_output=True, timeout=2, env=self._make_env()
            )
            if r.returncode == 0:
                self._last = text
            else:
                print(f"[clipboard] xclip -i error: {r.stderr.decode()[:60]}")
        except FileNotFoundError:
            print("[clipboard] xclip not found: sudo apt install xclip")
        except Exception as e:
            print(f"[clipboard] set error: {e}")

    def check_changed(self) -> Optional[str]:

        current = self.get()
        if current and current != self._last:
            self._last = current
            if current not in self._history:
                self._history.insert(0, current)
                if len(self._history) > 20:
                    self._history.pop()
            return current
        return None

    @property
    def history(self) -> list[str]:
        return self._history.copy()

class TrustedDeviceStore:

    def __init__(self, path: Path = PAIRING_FILE):
        self._path = path
        self._trusted: set[str] = set()
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text())
                self._trusted = set(data.get("trusted", []))
        except Exception:
            self._trusted = set()

    def _save(self):
        try:
            self._path.write_text(
                json.dumps({"trusted": list(self._trusted)}, indent=2)
            )
        except Exception as e:
            print(f"[pairing] Error saving trusted devices: {e}")

    def is_trusted(self, fingerprint: str) -> bool:
        with self._lock:
            return fingerprint in self._trusted

    def trust(self, fingerprint: str):
        with self._lock:
            self._trusted.add(fingerprint)
            self._save()

    def untrust(self, fingerprint: str):
        with self._lock:
            self._trusted.discard(fingerprint)
            self._save()

    @property
    def trusted_list(self) -> list[str]:
        with self._lock:
            return list(self._trusted)

class YelenaDiscovery:

    UDP_PORT = 1716
    INTERVAL = 3.0

    def __init__(self, ws_port: int = 8765):
        self._ws_port = ws_port
        self._running = False
        self._send_sock: Optional[socket.socket] = None
        self._recv_sock: Optional[socket.socket] = None
        self._thread_send: Optional[threading.Thread] = None
        self._thread_recv: Optional[threading.Thread] = None
        self._devices: dict[str, dict] = {}
        self._devices_lock = threading.Lock()
        self._on_found_cbs: list[Callable] = []
        self._on_lost_cbs: list[Callable] = []

    def on_device_found(self, cb: Callable):
        self._on_found_cbs.append(cb)

    def on_device_lost(self, cb: Callable):
        self._on_lost_cbs.append(cb)

    @property
    def discovered_devices(self) -> list[dict]:
        with self._devices_lock:
            return list(self._devices.values())

    def start(self):
        if self._running:
            return
        self._running = True
        try:
            self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            self._recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                self._recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except AttributeError:
                pass
            self._recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._recv_sock.bind(("", self.UDP_PORT))
            self._recv_sock.settimeout(2.0)

            self._thread_send = threading.Thread(target=self._send_loop, daemon=True)
            self._thread_recv = threading.Thread(target=self._recv_loop, daemon=True)
            self._thread_send.start()
            self._thread_recv.start()
            print(f"[udp] Discovery started — listening on :{self.UDP_PORT}")
        except Exception as e:
            print(f"[udp] Error: {e}")
            self._running = False

    def stop(self):
        self._running = False
        for s in [self._send_sock, self._recv_sock]:
            if s:
                try:
                    s.close()
                except Exception:
                    pass
        self._send_sock = None
        self._recv_sock = None

    def _make_packet(self) -> bytes:
        return json.dumps({
            "type": "yelena",
            "name": socket.gethostname(),
            "ip": get_local_ip(),
            "port": self._ws_port,
            "os": f"{platform.system()} {platform.release()}",
            "role": "pc",
            "version": "1",
        }).encode("utf-8")

    def _send_loop(self):
        while self._running:
            try:
                if self._send_sock:
                    pkt = self._make_packet()
                    self._send_sock.sendto(pkt, ("255.255.255.255", self.UDP_PORT))
            except Exception as e:
                if self._running:
                    print(f"[udp] send error: {e}")
            time.sleep(self.INTERVAL)

    def _recv_loop(self):
        print(f"[udp] Listening for broadcasts on :{self.UDP_PORT}")
        while self._running:
            try:
                if not self._recv_sock:
                    break
                data, addr = self._recv_sock.recvfrom(4096)
                src_ip = addr[0]

                print(f"[udp] Raw packet from {src_ip}: {data[:120]}")

                try:
                    payload = json.loads(data.decode("utf-8"))
                except Exception:
                    print(f"[udp] Failed to parse JSON from {src_ip}")
                    continue

                if payload.get("type") != "yelena":
                    print(f"[udp] Ignoring packet (type={payload.get('type')}) from {src_ip}")
                    continue

                if payload.get("role") == "pc":
                    print(f"[udp] Ignoring packet from another PC: {src_ip}")
                    continue

                device = {
                    "name": payload.get("name", src_ip),
                    "ip": src_ip,
                    "port": payload.get("port", 8766),
                    "os": payload.get("os", "Android"),
                    "type": "wifi",
                }

                with self._devices_lock:
                    is_new = src_ip not in self._devices
                    self._devices[src_ip] = device

                if is_new:
                    print(f"[udp] DEVICE FOUND: {device['name']} @ {src_ip}")
                    for cb in self._on_found_cbs:
                        try:
                            cb(device)
                        except Exception:
                            pass

            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    print(f"[udp] Error receiving: {e}")
                time.sleep(1)

_CLIENT_UNPAIRED = "unpaired"
_CLIENT_PENDING = "pending"
_CLIENT_PAIRED = "paired"

class YelenaWebSocketServer:

    WS_PORT = 8765

    def __init__(self, conn_manager: "ConnectionManager"):

        self._mgr = conn_manager
        self._clients: set = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_wifi_rssi: int = -1
        self._start_time = time.time()

        self._client_info: dict[str, dict] = {}
        self._client_info_lock = threading.Lock()

        self._trusted_store = TrustedDeviceStore()
        self._on_pair_request_cbs: list[Callable] = []
        self._on_pair_accepted_cbs: list[Callable] = []
        self._on_pair_rejected_cbs: list[Callable] = []
        self._on_disconnect_cbs: list[Callable] = []

        self._input = InputController()
        self._clipboard = ClipboardManager()
        self._bash = PersistentBash()

        self._handlers: dict[str, Callable] = {
            "ping":                  self._h_ping,
            "pair_response":         self._h_pair_response,
            "wifi_signal":           self._h_wifi_signal,
            "media_command":         self._h_media_command,
            "terminal":              self._h_terminal,
            "clipboard_set":         self._h_clipboard_set,
            "file_send":             self._h_file_send,
            "get_processes":         self._h_get_processes,
            "kill_process":          self._h_kill_process,
            "get_apps":              self._h_get_apps,
            "launch_app":            self._h_launch_app,
            "mouse_move":            self._h_mouse_move,
            "mouse_click":           self._h_mouse_click,
            "mouse_scroll":          self._h_mouse_scroll,
            "key_press":             self._h_key_press,
            "type_text":             self._h_type_text,
            "set_brightness":        self._h_set_brightness,
            "get_brightness":        self._h_get_brightness,
            "send_notification":     self._h_send_notification,
            "battery":               self._h_battery,
            "presentation":          self._h_presentation,
            "get_clipboard_history": self._h_clipboard_history,
        }

    def on_pair_request(self, cb: Callable):

        self._on_pair_request_cbs.append(cb)

    def on_pair_accepted(self, cb: Callable):

        self._on_pair_accepted_cbs.append(cb)

    def on_pair_rejected(self, cb: Callable):
        self._on_pair_rejected_cbs.append(cb)

    def on_client_disconnected(self, cb: Callable):
        self._on_disconnect_cbs.append(cb)

    def accept_pair(self, ip: str, trust: bool = True):

        with self._client_info_lock:
            info = self._client_info.get(ip)
            if not info or info["state"] != _CLIENT_PENDING:
                return
            info["state"] = _CLIENT_PAIRED
            ws = info["ws"]
            device_info = info["info"]

        if trust:
            fp = self._fingerprint(ip, device_info)
            self._trusted_store.trust(fp)

        asyncio.run_coroutine_threadsafe(
            self._accept_and_init(ws, trust), self._loop
        )

        for cb in self._on_pair_accepted_cbs:
            try:
                cb(device_info)
            except Exception:
                pass

    def reject_pair(self, ip: str):

        with self._client_info_lock:
            info = self._client_info.get(ip)
            if not info:
                return
            ws = info["ws"]

        asyncio.run_coroutine_threadsafe(self._reject_and_close(ws, ip), self._loop)

        for cb in self._on_pair_rejected_cbs:
            try:
                cb(ip)
            except Exception:
                pass

    async def _reject_and_close(self, ws, ip: str):
        await self._send(ws, "pair_rejected", {})
        await asyncio.sleep(0.3)
        try:
            await ws.close()
        except Exception:
            pass

    def untrust_device(self, ip: str, device_info: dict):

        fp = self._fingerprint(ip, device_info)
        self._trusted_store.untrust(fp)

    @staticmethod
    def _fingerprint(ip: str, device_info: dict) -> str:
        return ip

    def start(self):
        if self._running or not HAS_WEBSOCKETS:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"[ws] Server started on ws://{get_local_ip()}:{self.WS_PORT}")

    def stop(self):
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._bash.close()

    def has_clients(self) -> bool:
        with self._client_info_lock:
            return any(
                i["state"] == _CLIENT_PAIRED for i in self._client_info.values()
            )

    def get_clients(self) -> list[dict]:
        with self._client_info_lock:
            return [
                {"ip": ip, **info["info"], "paired": True}
                for ip, info in self._client_info.items()
                if info["state"] == _CLIENT_PAIRED
            ]

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception as e:
            print(f"[ws] Loop error: {e}")

    async def _serve(self):
        async with websockets.server.serve(
            self._handle_client, "0.0.0.0", self.WS_PORT,
            ping_interval=None,
            close_timeout=5,
            origins=None,
        ):
            print(f"[ws] Listening on ws://0.0.0.0:{self.WS_PORT}")
            loop = asyncio.get_event_loop()
            loop.create_task(self._resource_loop())
            loop.create_task(self._clipboard_loop())
            loop.create_task(self._media_loop())
            while self._running:
                await asyncio.sleep(1)

    async def _resource_loop(self):
        loop = asyncio.get_event_loop()
        while self._running:
            paired = self._get_paired_websockets()
            if paired:
                data = await loop.run_in_executor(None, self._get_pc_resources)
                await self._broadcast_to("resources", data, paired)
            await asyncio.sleep(2)

    async def _media_loop(self):
        loop = asyncio.get_event_loop()
        while self._running:
            paired = self._get_paired_websockets()
            if paired:
                data = await loop.run_in_executor(None, self._mgr.media.get_current)
                if data:
                    await self._broadcast_to("media", {
                        "title":   data.get("title",   ""),
                        "artist":  data.get("artist",  ""),
                        "album":   data.get("album",   ""),
                        "playing": data.get("playing", False),
                    }, paired)
            await asyncio.sleep(2)

    async def _clipboard_loop(self):
        while self._running:
            paired = self._get_paired_websockets()
            if paired:
                changed = self._clipboard.check_changed()
                if changed:
                    await self._broadcast_to(
                        "clipboard", {"text": changed}, paired
                    )
            await asyncio.sleep(1)

    def _get_paired_websockets(self) -> set:
        with self._client_info_lock:
            return {
                info["ws"] for info in self._client_info.values()
                if info["state"] == _CLIENT_PAIRED
            }

    async def _handle_client(self, websocket, path=None):
        if path is not None and path != "/ws":
            await websocket.close(1008, "Invalid path")
            return
        ip = websocket.remote_address[0] if websocket.remote_address else "?"

        print(f"[ws] 🔌 NEW CONNECTION ATTEMPT from {ip}")

        device_name = ip
        if hasattr(self._mgr, 'discovery') and self._mgr.discovery:
            with self._mgr.discovery._devices_lock:
                if ip in self._mgr.discovery._devices:
                    device_name = self._mgr.discovery._devices[ip].get("name", ip)

        device_info = {"name": device_name, "ip": ip, "port": 0, "type": "wifi"}
        fingerprint = self._fingerprint(ip, device_info)
        is_trusted = self._trusted_store.is_trusted(fingerprint)

        state = _CLIENT_PAIRED if is_trusted else _CLIENT_UNPAIRED

        self._clients.add(websocket)
        with self._client_info_lock:
            self._client_info[ip] = {
                "ws": websocket,
                "state": state,
                "info": device_info,
            }

        print(f"[ws] Client connected: {device_name} @ {ip} (trusted={is_trusted})")

        try:
            await self._send(websocket, "pc_info", self._pc_info())

            if state == _CLIENT_PAIRED:
                await self._send(websocket, "pair_accepted", {"trusted": True})

                for cb in self._on_pair_accepted_cbs:
                    try:
                        cb(device_info)
                    except Exception as e:
                        print(f"[ws] Error in on_pair_accepted callback: {e}")

                try:
                    loop = asyncio.get_event_loop()
                    res = await loop.run_in_executor(None, self._get_pc_resources)
                    await self._send(websocket, "resources", res)
                    clip = self._clipboard.get()
                    if clip:
                        await self._send(websocket, "clipboard", {"text": clip})
                except Exception as e:
                    print(f"[ws] Error sending initial state to {ip}: {e}")

            else:
                with self._client_info_lock:
                    self._client_info[ip]["state"] = _CLIENT_PENDING
                await self._send(websocket, "pair_request", {
                    "name": socket.gethostname(),
                    "ip": get_local_ip(),
                })
                for cb in self._on_pair_request_cbs:
                    try:
                        cb(ip, device_info.get("name", ip))
                    except Exception:
                        pass

            async for raw in websocket:
                await self._handle_message(websocket, ip, raw)

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"[ws] Error with client {ip}: {e}")
        finally:
            self._clients.discard(websocket)
            with self._client_info_lock:
                self._client_info.pop(ip, None)
            print(f"[ws] Client disconnected: {ip} (total: {len(self._clients)})")
            for cb in self._on_disconnect_cbs:
                try:
                    cb(ip)
                except Exception:
                    pass

    async def _accept_and_init(self, ws, trust: bool):
        try:
            await self._send(ws, "pair_accepted", {"trusted": trust})
            if ws.closed:
                return
            await self._send(ws, "pc_info", self._pc_info())
            if ws.closed:
                return
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, self._get_pc_resources)
            if ws.closed:
                return
            await self._send(ws, "resources", res)
            clip = self._clipboard.get()
            if clip and not ws.closed:
                await self._send(ws, "clipboard", {"text": clip})
        except Exception:
            pass

    async def _send_initial_state(self, ws):
        await self._send(ws, "pc_info", self._pc_info())
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, self._get_pc_resources)
        await self._send(ws, "resources", res)
        clip = self._clipboard.get()
        if clip:
            await self._send(ws, "clipboard", {"text": clip})

    async def _handle_message(self, ws, ip: str, raw: str):
        try:
            msg = json.loads(raw)
            mtype = msg.get("type", "")
            payload = msg.get("payload", {})

            if isinstance(payload, str) and payload:
                try:
                    payload = json.loads(payload)
                except Exception:
                    pass
            if not isinstance(payload, dict):
                payload = {"value": payload}

        except Exception as e:
            print(f"[ws] Parse error from {ip}: {e}")
            return

        with self._client_info_lock:
            info = self._client_info.get(ip)
            client_state = info["state"] if info else _CLIENT_UNPAIRED

        if client_state != _CLIENT_PAIRED and mtype not in ("ping", "pair_response"):
            print(f"[ws] Ignoring '{mtype}' from unpaired client {ip}")
            return

        handler = self._handlers.get(mtype)
        if handler:
            try:
                await handler(ws, ip, payload)
            except Exception as e:
                print(f"[ws] Handler error for '{mtype}': {e}")
        else:
            print(f"[ws] Unknown message type: '{mtype}'")

    async def _h_ping(self, ws, ip: str, payload: dict):
        await self._send(ws, "pong", "")

    async def _h_pair_response(self, ws, ip: str, payload: dict):
        accepted = payload.get("accepted", False)
        with self._client_info_lock:
            info = self._client_info.get(ip)
            if not info:
                return
            info["state"] = _CLIENT_PENDING
        if accepted:
            self.accept_pair(ip, trust=True)
        else:
            self.reject_pair(ip)

    async def _h_wifi_signal(self, ws, ip: str, payload: dict):

        rssi = payload.get("rssi", -1)
        if isinstance(rssi, (int, float)):
            self._last_wifi_rssi = int(rssi)

    async def _h_media_command(self, ws, ip: str, payload: dict):
        action = payload.get("action", "")
        if self._mgr.serial is not None:
            cmd_map = {
                "play_pause": self._mgr.media.play_pause,
                "next": self._mgr.media.next_track,
                "prev": self._mgr.media.prev_track,
                "vol_up": self._mgr.media.volume_up,
                "vol_down": self._mgr.media.volume_down,
            }
            fn = cmd_map.get(action)
            if fn:
                fn()
        else:
            pc_cmd_map = {
                "play_pause": ["playerctl", "play-pause"],
                "next": ["playerctl", "next"],
                "prev": ["playerctl", "previous"],
                "vol_up": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"],
                "vol_down": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"],
            }
            cmd = pc_cmd_map.get(action)
            if cmd:
                try:
                    subprocess.Popen(
                        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                except Exception as e:
                    print(f"[ws] media cmd error: {e}")

    async def _h_terminal(self, ws, ip: str, payload: dict):
        cmd = payload.get("command", "")
        if cmd:
            out, code = self._bash.run(cmd)
            await self._send(ws, "terminal_output", {"output": out, "exitCode": code})

    async def _h_clipboard_set(self, ws, ip: str, payload: dict):
        text = payload.get("text", "")
        if text:
            self._clipboard.set(text)

    async def _h_file_send(self, ws, ip: str, payload: dict):
        name = payload.get("name", "file")
        data = payload.get("data", "")
        if data:
            try:
                dest = os.path.join(os.path.expanduser("~"), "Downloads", name)
                decoded = base64.b64decode(data)
                with open(dest, "wb") as f:
                    f.write(decoded)
                print(f"[ws] File received: {dest}")
                await self._send(ws, "file_received", {"name": name, "path": dest})
            except Exception as e:
                print(f"[ws] Error saving file: {e}")

    async def _h_get_processes(self, ws, ip: str, payload: dict):
        procs = await asyncio.get_event_loop().run_in_executor(
            None, self._get_processes
        )
        await self._send(ws, "processes", procs)

    async def _h_kill_process(self, ws, ip: str, payload: dict):
        pid = payload.get("pid")
        if pid:
            result = self._kill_process(int(pid))
            await self._send(ws, "process_killed", {"pid": pid, "ok": result})

    async def _h_get_apps(self, ws, ip: str, payload: dict):
        apps = await asyncio.get_event_loop().run_in_executor(None, self._get_apps)
        await self._send(ws, "apps", apps)

    async def _h_launch_app(self, ws, ip: str, payload: dict):
        app = payload.get("exec", "")
        if app:
            self._launch_app(app)

    async def _h_mouse_move(self, ws, ip: str, payload: dict):
        dx = int(payload.get("dx", 0))
        dy = int(payload.get("dy", 0))
        self._input.mouse_move(dx, dy)

    async def _h_mouse_click(self, ws, ip: str, payload: dict):
        btn = payload.get("button", "left")
        self._input.mouse_click(btn)

    async def _h_mouse_scroll(self, ws, ip: str, payload: dict):
        direction = payload.get("direction", "down")
        self._input.mouse_scroll(direction)

    async def _h_key_press(self, ws, ip: str, payload: dict):
        key = payload.get("key", "")
        if key:
            self._input.key_press(key)

    async def _h_type_text(self, ws, ip: str, payload: dict):
        text = payload.get("text", "")
        if text:
            self._input.type_text(text)

    async def _h_set_brightness(self, ws, ip: str, payload: dict):
        val = int(payload.get("value", 50))
        self._set_brightness(val)

    async def _h_get_brightness(self, ws, ip: str, payload: dict):
        val = self._get_brightness()
        await self._send(ws, "brightness", {"value": val})

    async def _h_battery(self, ws, ip: str, payload: dict):
        pct      = payload.get("pct", -1)
        charging = payload.get("charging", False)
        with self._client_info_lock:
            info = self._client_info.get(ip)
            if info:
                info["battery_pct"]      = pct
                info["battery_charging"] = charging
        self._mgr.broadcast_battery(ip, pct, charging)

    async def _h_send_notification(self, ws, ip: str, payload: dict):
        title = payload.get("title", "")
        body = payload.get("body", "")
        self._desktop_notify(title, body)

    async def _h_presentation(self, ws, ip: str, payload: dict):
        action = payload.get("action", "")
        key_map = {
            "next": "Right", "prev": "Left", "start": "F5",
            "end": "Escape", "black": "b", "white": "w",
        }
        key = key_map.get(action)
        if key:
            self._input.key_press(key)

    async def _h_clipboard_history(self, ws, ip: str, payload: dict):
        await self._send(ws, "clipboard_history", {
            "items": self._clipboard.history
        })

    def broadcast(self, mtype: str, payload):

        self._broadcast(mtype, payload)

    def broadcast_media(self, data: dict):
        self._broadcast("media", {
            "title": data.get("title", ""),
            "artist": data.get("artist", ""),
            "album": data.get("album", ""),
            "playing": data.get("playing", False),
        })

    def broadcast_notifications(self, notifs: list):
        self._broadcast("phone_notifications", [
            {
                "id": n.get("id", ""),
                "app": n.get("app", ""),
                "title": n.get("title", ""),
                "body": n.get("text", ""),
                "time": int(time.time() * 1000),
            }
            for n in notifs
        ])

    def _broadcast(self, mtype: str, payload):
        if not self._loop:
            return
        paired = self._get_paired_websockets()
        if not paired:
            return
        asyncio.run_coroutine_threadsafe(
            self._broadcast_to(mtype, payload, paired), self._loop
        )

    async def _broadcast_to(self, mtype: str, payload, clients: set):
        if not clients:
            return
        msg = json.dumps({"type": mtype, "payload": json.dumps(payload)})
        dead = set()
        for ws in clients:
            try:
                await ws.send(msg)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    @staticmethod
    async def _send(ws, mtype: str, payload):
        msg = json.dumps({"type": mtype, "payload": json.dumps(payload)})
        await ws.send(msg)

    def _get_pc_resources(self) -> dict:
        if not HAS_PSUTIL:
            return {
                "cpuPercent": 0, "ramUsedGb": 0, "ramTotalGb": 0,
                "ramPercent": 0, "diskUsedGb": 0, "diskTotalGb": 0,
                "diskPercent": 0,
                "uptimeSeconds": int(time.time() - self._start_time),
            }
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            boot = psutil.boot_time()
            return {
                "cpuPercent": round(cpu, 1),
                "ramUsedGb": round(ram.used / 1024**3, 2),
                "ramTotalGb": round(ram.total / 1024**3, 2),
                "ramPercent": round(ram.percent, 1),
                "diskUsedGb": round(disk.used / 1024**3, 1),
                "diskTotalGb": round(disk.total / 1024**3, 1),
                "diskPercent": round(disk.percent, 1),
                "uptimeSeconds": int(time.time() - boot),
            }
        except Exception as e:
            print(f"[ws] psutil error: {e}")
            return {
                "cpuPercent": 0, "ramUsedGb": 0, "ramTotalGb": 0,
                "ramPercent": 0, "diskUsedGb": 0, "diskTotalGb": 0,
                "diskPercent": 0, "uptimeSeconds": 0,
            }

    @staticmethod
    def _pc_info() -> dict:
        return {
            "hostname": socket.gethostname(),
            "os": f"{platform.system()} {platform.release()}",
            "version": "Yelena Connect v0.3",
        }

    @staticmethod
    def _get_processes() -> list:
        if not HAS_PSUTIL:
            return []
        try:
            procs_map: dict = {}
            for p in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    p.cpu_percent()
                    procs_map[p.pid] = p
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            time.sleep(0.5)
            result = []
            for pid, p in procs_map.items():
                try:
                    cpu = p.cpu_percent()
                    mem = p.memory_percent()
                    result.append({
                        "pid": pid,
                        "name": p.name(),
                        "cpu": round(cpu, 1),
                        "mem": round(mem, 1),
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return sorted(result, key=lambda x: (x['cpu'], x['mem']), reverse=True)
        except Exception as e:
            print(f"[ws] get_processes error: {e}")
            return []

    @staticmethod
    def _kill_process(pid: int) -> bool:
        if not HAS_PSUTIL:
            return False
        try:
            p = psutil.Process(pid)
            p.terminate()
            return True
        except Exception as e:
            print(f"[ws] kill_process {pid}: {e}")
            return False

    @staticmethod
    def _get_apps() -> list:
        apps: list[dict] = []
        search_dirs = [
            "/usr/share/applications",
            "/usr/local/share/applications",
            os.path.expanduser("~/.local/share/applications"),
        ]
        seen: set[str] = set()
        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            for fname in os.listdir(d):
                if not fname.endswith(".desktop"):
                    continue
                path = os.path.join(d, fname)
                try:
                    name = exec_ = icon = ""
                    nodisplay = False
                    with open(path, encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("Name=") and not name:
                                name = line[5:]
                            elif line.startswith("Exec=") and not exec_:
                                exec_ = line[5:].split()[0].replace("%U", "").replace("%F", "").strip()
                            elif line.startswith("Icon=") and not icon:
                                icon = line[5:]
                            elif line == "NoDisplay=true":
                                nodisplay = True
                    if name and exec_ and not nodisplay and exec_ not in seen:
                        seen.add(exec_)
                        apps.append({"name": name, "exec": exec_, "icon": icon})
                except Exception:
                    pass
        return sorted(apps, key=lambda x: x['name'].lower())[:100]

    @staticmethod
    def _launch_app(exec_path: str):
        try:
            env = os.environ.copy()
            env.setdefault("DISPLAY", ":0")
            subprocess.Popen(
                exec_path, shell=True, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"[ws] launch_app error: {e}")

    @staticmethod
    def _get_brightness() -> int:
        try:
            r = subprocess.run(
                ["brightnessctl", "g"], capture_output=True, text=True, timeout=2
            )
            current = int(r.stdout.strip())
            m = subprocess.run(
                ["brightnessctl", "m"], capture_output=True, text=True, timeout=2
            )
            maximum = int(m.stdout.strip()) or 100
            return round(current / maximum * 100)
        except Exception:
            return -1

    @staticmethod
    def _set_brightness(percent: int):
        try:
            subprocess.run(
                ["brightnessctl", "s", f"{max(1, min(100, percent))}%"],
                capture_output=True, timeout=2
            )
        except Exception:
            pass

    @staticmethod
    def _desktop_notify(title: str, body: str):
        try:
            subprocess.Popen(
                ["notify-send", "--app-name=Yelena Connect", title, body],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    @staticmethod
    def get_connection_info() -> dict:
        return {
            "ip": get_local_ip(),
            "port": YelenaWebSocketServer.WS_PORT,
            "name": socket.gethostname(),
        }

    def get_qr_text(self) -> str:
        return json.dumps(self.get_connection_info())

class ConnectionManager:

    def __init__(self):
        self.serial: Optional[str] = None
        self.device_name: str = "No device"
        self.device_type: str = "none"

        self.scrcpy = ScrcpySession()
        self.resources = ResourceMonitor()
        self.notifications = NotificationMonitor()
        self.media = MediaController()
        self.phone = PhoneController()

        self._on_battery_cbs: list[Callable] = []
        self.ws_server = YelenaWebSocketServer(self)
        self.discovery = YelenaDiscovery(ws_port=YelenaWebSocketServer.WS_PORT)

        self._on_connect_cbs: list[Callable] = []
        self._on_disconnect_cbs: list[Callable] = []

        self.notifications.add_callback(self.ws_server.broadcast_notifications)
        self.media.add_callback(self.ws_server.broadcast_media)

        self.ws_server.start()
        self.discovery.start()

    def on_connect(self, cb: Callable):
        self._on_connect_cbs.append(cb)

    def on_disconnect(self, cb: Callable):
        self._on_disconnect_cbs.append(cb)

    def connect_device(self, device: dict) -> bool:
        self.disconnect()
        self.serial = device["serial"]
        self.device_name = device["name"]
        self.device_type = device["type"]

        self.resources.set_serial(self.serial)
        self.notifications.set_serial(self.serial)
        self.media.set_serial(self.serial)
        self.phone.set_serial(self.serial)

        self.resources.start()
        self.notifications.start()
        self.media.start()

        for cb in self._on_connect_cbs:
            try:
                cb(device)
            except Exception:
                pass
        return True

    def disconnect(self):
        self.resources.stop()
        self.notifications.stop()
        self.media.stop()
        self.scrcpy.stop()
        self.serial = None
        self.device_name = "No device"
        for cb in self._on_disconnect_cbs:
            try:
                cb()
            except Exception:
                pass

    def start_screen_mirror(self) -> bool:
        if not self.serial:
            return False
        return self.scrcpy.start(self.serial)

    def stop_screen_mirror(self):
        self.scrcpy.stop()

    def get_devices(self) -> list[dict]:
        return list_devices()

    def connect_wifi_device(self, ip: str, port: int = 5555):
        return connect_wifi(ip, port)

    def is_connected(self) -> bool:
        return self.serial is not None or self.ws_server.has_clients()

    def on_android_found(self, cb: Callable):
        self.discovery.on_device_found(cb)

    def on_android_lost(self, cb: Callable):
        self.discovery.on_device_lost(cb)

    def get_android_devices(self) -> list[dict]:
        return self.discovery.discovered_devices

    def broadcast_battery(self, ip: str, pct: int, charging: bool):
        for cb in self._on_battery_cbs:
            try:
                cb(ip, pct, charging)
            except Exception:
                pass

    def on_battery_update(self, cb: Callable):
        self._on_battery_cbs.append(cb)

    def on_wifi_connected(self, cb: Callable):
        self.ws_server.on_pair_accepted(cb)

    def on_wifi_disconnected(self, cb: Callable):
        self.ws_server.on_client_disconnected(cb)

    def is_wifi_connected(self) -> bool:
        return self.ws_server.has_clients()

    def on_pair_request(self, cb: Callable):
        self.ws_server.on_pair_request(cb)

    def accept_pair(self, ip: str, trust: bool = True):
        self.ws_server.accept_pair(ip, trust)

    def reject_pair(self, ip: str):
        self.ws_server.reject_pair(ip)

manager = ConnectionManager()