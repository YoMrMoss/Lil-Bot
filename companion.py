#!/usr/bin/env python3
"""Lil Bot Windows companion and virtual-board server.

Detects activity without recording key contents, serves the browser preview,
and exposes the same state messages the future ESP32 serial transport will use.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import mimetypes
import os
import platform
import threading
import time
import webbrowser
import urllib.parse
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "companion_config.json"
BUILD_VERSION = "0.9"
VALID_STATES = {"idle", "typing", "browsing", "browsing_fast", "music", "gaming", "notification", "loading", "error", "sleep", "volume", "startup", "reconnect"}


def load_config() -> dict:
    defaults = {
        "host": "127.0.0.1",
        "port": 8765,
        "typing_hold_seconds": 1.1,
        "browsing_hold_seconds": 1.4,
        "sleep_after_seconds": 300,
        "application_states": {
            "spotify.exe": "music",
            "discord.exe": "notification",
            "wow.exe": "gaming",
            "wowclassic.exe": "gaming",
            "wowclassic_t.exe": "gaming",
            "leagueclient.exe": "gaming",
            "leagueclientux.exe": "gaming",
            "league of legends.exe": "gaming",
        },
        "game_processes": ["wow.exe", "steam.exe"],
        "browser_processes": ["chrome.exe", "msedge.exe", "firefox.exe"],
        "media_processes": ["spotify.exe", "musicbee.exe", "vlc.exe"],
        "open_browser_on_start": True,
        "weather": {
            "enabled": False,
            "location_label": "Set your location",
            "latitude": 0.0,
            "longitude": 0.0,
            "temperature_unit": "fahrenheit",
            "refresh_seconds": 900,
        },
        "ambient_card_interval_seconds": 60,
        "ambient_card_duration_seconds": 6,
        "quiet_hours": {"enabled": True, "start": "22:30", "end": "07:00", "brightness": 20},
        "automatic_brightness": {
            "enabled": True,
            "day_start": "07:00",
            "night_start": "19:30",
            "day_brightness": 100,
            "night_brightness": 45,
        },
        "personality": "shy-curious-helper",
    }
    if CONFIG_PATH.exists():
        try:
            defaults.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Warning: could not read {CONFIG_PATH.name}: {exc}")
    return defaults


@dataclass
class Runtime:
    state: str = "idle"
    reason: str = "companion starting"
    active_process: str = "unknown"
    idle_seconds: float = 0.0
    last_key: float = 0.0
    last_mouse: float = 0.0
    last_scroll: float = 0.0
    last_volume: float = 0.0
    volume_direction: str = "none"
    manual_state: str | None = None
    manual_until: float = 0.0
    connected_at: float = field(default_factory=time.time)
    sequence: int = 0
    temperature: float | None = None
    temperature_unit: str = "°F"
    weather_location: str = ""
    weather_updated: float = 0.0
    weather_error: str = ""
    unread_notifications: int = 0
    events: deque = field(default_factory=lambda: deque(maxlen=120), repr=False)
    scroll_events: deque = field(default_factory=lambda: deque(maxlen=40), repr=False)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def snapshot(self) -> dict:
        with self.lock:
            profile = current_display_profile(APP_CONFIG)
            now = time.monotonic()
            return {
                "build": BUILD_VERSION,
                "state": self.state,
                "reason": self.reason,
                "active_process": self.active_process,
                "idle_seconds": round(self.idle_seconds, 1),
                "sequence": self.sequence,
                "server_time": time.time(),
                "protocol": f"STATE:{self.state.upper()}",
                "volume_direction": self.volume_direction,
                "ambient": {
                    "temperature": self.temperature,
                    "temperature_unit": self.temperature_unit,
                    "location": self.weather_location,
                    "weather_updated": self.weather_updated,
                    "weather_error": self.weather_error,
                },
                "display": profile,
                "unread_notifications": self.unread_notifications,
                "personality": APP_CONFIG.get("personality", "shy-curious-helper"),
                "activity": {
                    "key_age": round(max(0.0, now - self.last_key), 2) if self.last_key else None,
                    "mouse_age": round(max(0.0, now - self.last_mouse), 2) if self.last_mouse else None,
                    "scroll_age": round(max(0.0, now - self.last_scroll), 2) if self.last_scroll else None,
                },
            }

    def set_state(self, state: str, reason: str) -> None:
        with self.lock:
            if state != self.state or reason != self.reason:
                self.state, self.reason = state, reason
                self.sequence += 1
                self.events.appendleft({"time": time.time(), "state": state, "reason": reason, "sequence": self.sequence})

    def diagnostic_log(self) -> list[dict]:
        with self.lock:
            return list(self.events)

    def add_notification(self) -> int:
        with self.lock:
            self.unread_notifications += 1
            return self.unread_notifications

    def clear_notifications(self) -> None:
        with self.lock:
            self.unread_notifications = 0
            self.events.appendleft({"time": time.time(), "state": self.state, "reason": "notifications cleared", "sequence": self.sequence})


RUNTIME = Runtime()
APP_CONFIG: dict = {}


def clock_minutes(value: str) -> int:
    try:
        hour, minute = (int(part) for part in value.split(":", 1))
        return hour * 60 + minute
    except (TypeError, ValueError):
        return 0


def in_clock_range(now: int, start: int, end: int) -> bool:
    return start <= now < end if start <= end else now >= start or now < end


def current_display_profile(config: dict) -> dict:
    local = time.localtime()
    now = local.tm_hour * 60 + local.tm_min
    quiet = config.get("quiet_hours", {})
    auto = config.get("automatic_brightness", {})
    quiet_active = bool(quiet.get("enabled")) and in_clock_range(now, clock_minutes(quiet.get("start", "22:30")), clock_minutes(quiet.get("end", "07:00")))
    if quiet_active:
        brightness = int(quiet.get("brightness", 20))
        period = "quiet"
    elif auto.get("enabled"):
        night = in_clock_range(now, clock_minutes(auto.get("night_start", "19:30")), clock_minutes(auto.get("day_start", "07:00")))
        brightness = int(auto.get("night_brightness", 45) if night else auto.get("day_brightness", 100))
        period = "night" if night else "day"
    else:
        brightness, period = 100, "manual"
    return {"quiet_hours": quiet_active, "brightness": max(10, min(100, brightness)), "period": period}


def windows_idle_seconds() -> float:
    if platform.system() != "Windows":
        return min(time.monotonic(), 60.0)

    class LastInputInfo(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    info = LastInputInfo()
    info.cbSize = ctypes.sizeof(info)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        tick = ctypes.windll.kernel32.GetTickCount()
        return max(0.0, (tick - info.dwTime) / 1000.0)
    return 0.0


def active_process_name() -> str:
    if platform.system() != "Windows":
        return "browser-preview"
    try:
        import psutil  # type: ignore

        hwnd = ctypes.windll.user32.GetForegroundWindow()
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return psutil.Process(pid.value).name().lower()
    except Exception:
        return "unknown"


def install_activity_listeners() -> None:
    """Listen only for event timestamps; never inspect or store key values."""
    try:
        from pynput import keyboard, mouse  # type: ignore

        volume_keys = {
            getattr(keyboard.Key, "media_volume_up", None): "up",
            getattr(keyboard.Key, "media_volume_down", None): "down",
            getattr(keyboard.Key, "media_volume_mute", None): "mute",
        }
        volume_keys.pop(None, None)

        def key_event(key):
            now = time.monotonic()
            if key in volume_keys:
                RUNTIME.last_volume = now
                RUNTIME.volume_direction = volume_keys[key]
                return
            RUNTIME.last_key = now

        def mouse_event(*_args):
            RUNTIME.last_mouse = time.monotonic()

        def scroll_event(*_args):
            now = time.monotonic()
            with RUNTIME.lock:
                RUNTIME.last_mouse = RUNTIME.last_scroll = now
                RUNTIME.scroll_events.append(now)

        keyboard.Listener(on_press=key_event).start()
        mouse.Listener(on_move=mouse_event, on_click=mouse_event, on_scroll=scroll_event).start()
        print("Activity listeners ready (timestamps only; no key contents are stored).")
    except Exception as exc:
        print(f"Activity listeners unavailable: {exc}")
        print("Install requirements.txt to enable typing and scrolling detection.")


def detection_loop(config: dict, stop: threading.Event) -> None:
    app_states = {name.lower(): state.lower() for name, state in config.get("application_states", {}).items()}
    games = {x.lower() for x in config["game_processes"]}
    browsers = {x.lower() for x in config["browser_processes"]}
    media = {x.lower() for x in config["media_processes"]}
    while not stop.wait(0.12):
        now = time.monotonic()
        process = active_process_name()
        idle = windows_idle_seconds()
        with RUNTIME.lock:
            RUNTIME.active_process, RUNTIME.idle_seconds = process, idle
            manual = RUNTIME.manual_state if now < RUNTIME.manual_until else None
            scroll_burst = sum(event >= now - 0.75 for event in RUNTIME.scroll_events)
            if not manual:
                RUNTIME.manual_state = None

        if manual:
            RUNTIME.set_state(manual, "temporary simulated event")
        elif now - RUNTIME.last_volume <= 0.9:
            RUNTIME.set_state("volume", f"system volume {RUNTIME.volume_direction}")
        elif idle >= float(config["sleep_after_seconds"]):
            RUNTIME.set_state("sleep", "computer idle timeout")
        elif process in games or app_states.get(process) == "gaming":
            RUNTIME.set_state("gaming", f"configured game active: {process}")
        elif process in media or app_states.get(process) == "music":
            RUNTIME.set_state("music", f"configured media app active: {process}")
        elif now - RUNTIME.last_key <= float(config["typing_hold_seconds"]):
            RUNTIME.set_state("typing", "recent keyboard activity")
        elif process in browsers and now - RUNTIME.last_scroll <= float(config["browsing_hold_seconds"]):
            if scroll_burst >= 5:
                RUNTIME.set_state("browsing_fast", f"rapid browser scrolling: {scroll_burst} events")
            else:
                RUNTIME.set_state("browsing", "browser reading scroll")
        elif process in app_states and app_states[process] in VALID_STATES:
            RUNTIME.set_state(app_states[process], f"application active: {process}")
        else:
            RUNTIME.set_state("idle", f"foreground: {process}")


def weather_loop(config: dict, stop: threading.Event) -> None:
    weather = config.get("weather", {})
    if not weather.get("enabled", False):
        return
    refresh = max(300, int(weather.get("refresh_seconds", 900)))
    while not stop.is_set():
        try:
            params = urllib.parse.urlencode({
                "latitude": weather["latitude"],
                "longitude": weather["longitude"],
                "current": "temperature_2m",
                "temperature_unit": weather.get("temperature_unit", "fahrenheit"),
                "timezone": "auto",
            })
            request = urllib.request.Request(
                f"https://api.open-meteo.com/v1/forecast?{params}",
                headers={"User-Agent": "LilBot/0.2 (personal desk display)"},
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.load(response)
            current = payload.get("current", {})
            units = payload.get("current_units", {})
            with RUNTIME.lock:
                RUNTIME.temperature = float(current["temperature_2m"])
                RUNTIME.temperature_unit = units.get("temperature_2m", "°F")
                RUNTIME.weather_location = str(weather.get("location_label", "Local"))
                RUNTIME.weather_updated = time.time()
                RUNTIME.weather_error = ""
        except Exception as exc:
            with RUNTIME.lock:
                RUNTIME.weather_error = str(exc)
        stop.wait(refresh)


class Handler(SimpleHTTPRequestHandler):
    server_version = "LilBotCompanion/0.1"

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        relative = urlparse(path).path.lstrip("/") or "display-preview.html"
        safe = (ROOT / relative).resolve()
        if ROOT not in safe.parents and safe != ROOT:
            return str(ROOT / "display-preview.html")
        return str(safe)

    def send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/api/state":
            self.send_json(RUNTIME.snapshot())
            return
        if urlparse(self.path).path == "/api/health":
            self.send_json({"ok": True, "version": 1})
            return
        if urlparse(self.path).path == "/api/log":
            self.send_json({"events": RUNTIME.diagnostic_log()})
            return
        super().do_GET()

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route == "/api/notification":
            count = RUNTIME.add_notification()
            with RUNTIME.lock:
                RUNTIME.manual_state = "notification"
                RUNTIME.manual_until = time.monotonic() + 1.4
            RUNTIME.set_state("notification", f"new notification; {count} unread")
            self.send_json(RUNTIME.snapshot())
            return
        if route == "/api/clear-notifications":
            RUNTIME.clear_notifications()
            self.send_json(RUNTIME.snapshot())
            return
        if route != "/api/simulate":
            self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 4096)
            payload = json.loads(self.rfile.read(length) or b"{}")
            state = str(payload.get("state", "")).lower()
            duration = max(0.2, min(float(payload.get("duration", 2.0)), 30.0))
            if state not in VALID_STATES:
                raise ValueError(f"state must be one of {sorted(VALID_STATES)}")
            with RUNTIME.lock:
                RUNTIME.manual_state = state
                RUNTIME.manual_until = time.monotonic() + duration
            RUNTIME.set_state(state, "temporary simulated event")
            self.send_json(RUNTIME.snapshot())
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args) -> None:
        if not self.path.startswith("/api/state"):
            super().log_message(format, *args)


def main() -> int:
    global APP_CONFIG
    parser = argparse.ArgumentParser(description="Run the Lil Bot companion and virtual display.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the preview automatically.")
    parser.add_argument("--host", help="Override configured host.")
    parser.add_argument("--port", type=int, help="Override configured port.")
    args = parser.parse_args()
    config = APP_CONFIG = load_config()
    RUNTIME.set_state("startup", "Lil Bot woke up and is ready to help")
    with RUNTIME.lock:
        RUNTIME.manual_state = "startup"
        RUNTIME.manual_until = time.monotonic() + 3.2
    host = args.host or config["host"]
    port = args.port or int(config["port"])
    stop = threading.Event()
    install_activity_listeners()
    detector = threading.Thread(target=detection_loop, args=(config, stop), daemon=True)
    detector.start()
    weather_worker = threading.Thread(target=weather_loop, args=(config, stop), daemon=True)
    weather_worker.start()
    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/display-preview.html?v={BUILD_VERSION}"
    print(f"Lil Bot companion running at {url}")
    print("Press Ctrl+C to stop.")
    if config.get("open_browser_on_start", True) and not args.no_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Lil Bot companion.")
    finally:
        stop.set()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
