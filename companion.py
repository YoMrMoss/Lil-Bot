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
BUILD_VERSION = "1.11.0"
PROTOCOL_VERSION = 1
VALID_STATES = {"idle", "typing", "browsing", "browsing_fast", "music", "gaming", "cat", "helper", "showoff", "crying", "nervous", "rage", "notification", "loading", "error", "sleep", "volume", "startup", "reconnect", "time", "weather"}
REACTION_PRIORITY = {"idle": 0, "application": 30, "browsing": 40, "typing": 50, "gaming": 60, "sleep": 70, "volume": 80, "after": 90, "manual": 100}


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
                "enabled": True,
                "location_label": "Central Connecticut",
                "latitude": 41.6612,
                "longitude": -72.7795,
            "temperature_unit": "fahrenheit",
            "refresh_seconds": 900,
        },
        "ambient_card_interval_seconds": 60,
        "ambient_card_duration_seconds": 6,
        "idle_cameo_first_seconds": 15,
        "idle_cameo_duration_seconds": 3.2,
        "quiet_hours": {"enabled": True, "start": "22:30", "end": "07:00", "brightness": 20},
        "automatic_brightness": {
            "enabled": True,
            "day_start": "07:00",
            "night_start": "19:30",
            "day_brightness": 100,
            "night_brightness": 45,
        },
        "personality": "shy-curious-helper",
        "animation": {"transition_ms": 240, "pixel_shift": True, "after_reactions": True},
        "serial": {"enabled": True, "port": "auto", "baud": 115200, "heartbeat_seconds": 0.5},
    }
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            # Migrate the original placeholder to this Lil Bot's local forecast.
            weather = saved.get("weather", {})
            if weather.get("location_label") == "Set your location" and not weather.get("latitude"):
                saved["weather"] = defaults["weather"].copy()
            defaults.update(saved)
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
    volume_level: float = 0.5
    volume_muted: bool = False
    music_playing: bool = False
    manual_state: str | None = None
    manual_until: float = 0.0
    after_state: str | None = None
    after_until: float = 0.0
    source: str = "startup"
    priority: int = 0
    connected_at: float = field(default_factory=time.time)
    sequence: int = 0
    temperature: float | None = None
    temperature_unit: str = "°F"
    weather_location: str = ""
    weather_updated: float = 0.0
    weather_error: str = ""
    unread_notifications: int = 0
    next_idle_cameo: float = 0.0
    idle_cameo_index: int = 0
    device_connected: bool = False
    device_port: str = ""
    device_last_seen: float = 0.0
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
                "protocol": f"LILBOT/{PROTOCOL_VERSION} STATE:{self.state.upper()} SEQ:{self.sequence}",
                "protocol_version": PROTOCOL_VERSION,
                "volume_direction": self.volume_direction,
                "volume_level": round(self.volume_level, 3),
                "volume_muted": self.volume_muted,
                "music_playing": self.music_playing,
                "ambient": {
                    "temperature": self.temperature,
                    "temperature_unit": self.temperature_unit,
                    "location": self.weather_location,
                    "weather_updated": self.weather_updated,
                    "weather_error": self.weather_error,
                },
                "display": profile,
                "unread_notifications": self.unread_notifications,
                "device": {
                    "connected": self.device_connected,
                    "port": self.device_port,
                    "last_seen": self.device_last_seen,
                },
                "personality": APP_CONFIG.get("personality", "shy-curious-helper"),
                "reaction": {"source": self.source, "priority": self.priority},
                "modifiers": {
                    "music_bob": self.music_playing,
                    "quiet_hours": profile["quiet_hours"],
                    "brightness": profile["brightness"],
                    "pixel_shift": bool(APP_CONFIG.get("animation", {}).get("pixel_shift", True)),
                    "transition_ms": int(APP_CONFIG.get("animation", {}).get("transition_ms", 240)),
                },
                "activity": {
                    "key_age": round(max(0.0, now - self.last_key), 2) if self.last_key else None,
                    "mouse_age": round(max(0.0, now - self.last_mouse), 2) if self.last_mouse else None,
                    "scroll_age": round(max(0.0, now - self.last_scroll), 2) if self.last_scroll else None,
                },
            }

    def display_frame(self) -> dict:
        snapshot = self.snapshot()
        keys = ("protocol_version", "sequence", "state", "display", "modifiers", "volume_level", "volume_muted", "unread_notifications", "ambient")
        return {key: snapshot[key] for key in keys}

    def wire_frame(self) -> str:
        """Return the deliberately simple USB frame understood by the display.

        Keeping the hardware transport free of nested JSON makes it easy to
        diagnose in a serial terminal and avoids parser/memory differences
        between desktop Python and the ESP32.
        """
        frame = self.display_frame()
        modifiers = frame["modifiers"]
        clock = time.strftime("%I:%M %p").lstrip("0")
        temperature = "--" if frame["ambient"]["temperature"] is None else str(round(float(frame["ambient"]["temperature"])))
        location = str(frame["ambient"]["location"] or "LOCAL").replace("|", "/")[:24]
        return "LILBOT|1|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}\n".format(
            frame["sequence"],
            frame["state"],
            int(round(float(frame["volume_level"]) * 100)),
            int(bool(frame["volume_muted"])),
            int(bool(modifiers["music_bob"])),
            int(modifiers["brightness"]),
            int(bool(modifiers["pixel_shift"])),
            int(frame["unread_notifications"]),
            clock,
            temperature,
            location,
        )

    def device_status(self, connected: bool, port: str = "", reason: str = "") -> None:
        with self.lock:
            changed = connected != self.device_connected or port != self.device_port
            self.device_connected = connected
            self.device_port = port if connected else ""
            if connected:
                self.device_last_seen = time.time()
            if changed:
                self.events.appendleft({"time": time.time(), "state": self.state, "reason": reason or ("display connected" if connected else "display disconnected"), "source": "device", "priority": self.priority, "sequence": self.sequence})

    def set_state(self, state: str, reason: str, source: str = "application", priority: int | None = None) -> None:
        with self.lock:
            resolved_priority = REACTION_PRIORITY.get(source, 0) if priority is None else priority
            if state != self.state or reason != self.reason or source != self.source:
                self.state, self.reason, self.source, self.priority = state, reason, source, resolved_priority
                self.sequence += 1
                self.events.appendleft({"time": time.time(), "state": state, "reason": reason, "source": source, "priority": resolved_priority, "sequence": self.sequence})

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

    def touch_reaction(self, gesture: str = "tap") -> int:
        """Handle tap/double/hold while keeping tap as notification clear."""
        with self.lock:
            cleared = self.unread_notifications
            now = time.monotonic()
            if gesture == "hold":
                state, duration, reason = "sleep", 3.0, "touchscreen hold; taking a shy little rest"
            elif gesture == "double":
                state, duration, reason = "helper", 2.2, "touchscreen double tap; eager helper check-in"
            else:
                gesture = "tap"
                self.unread_notifications = 0
                state, duration = "rage", 2.4
                reason = f"touchscreen table flip; cleared {cleared} notification{'s' if cleared != 1 else ''}"
            self.manual_state = state
            self.manual_until = now + duration
            if gesture == "tap" and APP_CONFIG.get("animation", {}).get("after_reactions", True):
                self.after_state = "nervous"
                self.after_until = now + duration + 1.2
            else:
                self.after_state = None
                self.after_until = 0.0
            self.state = state
            self.reason = reason
            self.source = "manual"
            self.priority = REACTION_PRIORITY["manual"]
            self.sequence += 1
            self.events.appendleft({"time": time.time(), "state": self.state, "reason": self.reason, "source": "touch", "priority": self.priority, "sequence": self.sequence})
            return cleared


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


def read_system_volume(fallback_level: float, fallback_muted: bool) -> tuple[float, bool]:
    """Read Windows master volume through Core Audio, with a safe fallback."""
    if platform.system() != "Windows":
        return fallback_level, fallback_muted
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

        device = AudioUtilities.GetSpeakers()
        endpoint = getattr(device, "EndpointVolume", None)
        if endpoint is None:
            from comtypes import CLSCTX_ALL  # type: ignore

            interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            endpoint = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
        return max(0.0, min(1.0, float(endpoint.GetMasterVolumeLevelScalar()))), bool(endpoint.GetMute())
    except Exception:
        return fallback_level, fallback_muted


def spotify_is_playing() -> bool:
    """Return true only when Spotify owns an active Windows audio session."""
    if platform.system() != "Windows":
        return False
    try:
        from pycaw.pycaw import AudioUtilities  # type: ignore

        for session in AudioUtilities.GetAllSessions():
            process = session.Process
            state = getattr(session.State, "value", session.State)
            if process and process.name().lower() == "spotify.exe" and int(state) == 1:
                return True
    except Exception:
        return False
    return False


def install_activity_listeners() -> None:
    """Listen only for event timestamps; never inspect or store key values."""
    try:
        from pynput import keyboard, mouse  # type: ignore

        RUNTIME.volume_level, RUNTIME.volume_muted = read_system_volume(0.5, False)

        volume_keys = {
            getattr(keyboard.Key, "media_volume_up", None): "up",
            getattr(keyboard.Key, "media_volume_down", None): "down",
            getattr(keyboard.Key, "media_volume_mute", None): "mute",
        }
        volume_keys.pop(None, None)

        def key_event(key):
            now = time.monotonic()
            if key in volume_keys:
                direction = volume_keys[key]
                with RUNTIME.lock:
                    RUNTIME.last_volume = now
                    RUNTIME.volume_direction = direction
                    if direction == "up":
                        RUNTIME.volume_level = min(1.0, RUNTIME.volume_level + 0.02)
                        RUNTIME.volume_muted = False
                    elif direction == "down":
                        RUNTIME.volume_level = max(0.0, RUNTIME.volume_level - 0.02)
                    else:
                        RUNTIME.volume_muted = not RUNTIME.volume_muted

                def refresh_volume():
                    level, muted = read_system_volume(RUNTIME.volume_level, RUNTIME.volume_muted)
                    with RUNTIME.lock:
                        RUNTIME.volume_level, RUNTIME.volume_muted = level, muted

                threading.Timer(0.08, refresh_volume).start()
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


def choose_reaction(*, now: float, process: str, idle: float, manual: str | None,
                    after: str | None, volume_recent: bool, volume_level: float,
                    volume_muted: bool, last_key: float, last_scroll: float,
                    scroll_burst: int, config: dict, games: set[str],
                    browsers: set[str], media: set[str], app_states: dict[str, str]) -> tuple[str, str, str, int]:
    """Resolve competing inputs by explicit priority, then return one reaction."""
    candidates: list[tuple[int, str, str, str]] = []

    def add(source: str, state: str, reason: str) -> None:
        candidates.append((REACTION_PRIORITY[source], state, reason, source))

    add("idle", "idle", f"foreground: {process}")
    mapped = app_states.get(process)
    if mapped in VALID_STATES:
        add("application", mapped, f"application active: {process}")
    if process in media:
        add("application", "music", f"configured media app active: {process}")
    if process in browsers and now - last_scroll <= float(config["browsing_hold_seconds"]):
        if scroll_burst >= 5:
            add("browsing", "browsing_fast", f"rapid browser scrolling: {scroll_burst} events")
        else:
            add("browsing", "browsing", "browser reading scroll")
    if now - last_key <= float(config["typing_hold_seconds"]):
        add("typing", "typing", "recent keyboard activity")
    if process in games or mapped == "gaming":
        add("gaming", "gaming", f"configured game active: {process}")
    if idle >= float(config["sleep_after_seconds"]):
        add("sleep", "sleep", "computer idle timeout")
    if volume_recent:
        muted = " muted" if volume_muted else ""
        add("volume", "volume", f"system volume {round(volume_level * 100)}%{muted}")
    if after:
        add("after", after, "bashful after-reaction following touchscreen table flip")
    if manual:
        add("manual", manual, "temporary simulated event")
    priority, state, reason, source = max(candidates, key=lambda item: item[0])
    return state, reason, source, priority


def detection_loop(config: dict, stop: threading.Event) -> None:
    app_states = {name.lower(): state.lower() for name, state in config.get("application_states", {}).items()}
    games = {x.lower() for x in config["game_processes"]}
    browsers = {x.lower() for x in config["browser_processes"]}
    media = {x.lower() for x in config["media_processes"]}
    last_media_check = 0.0
    cameo_states = ("time", "weather", "cat", "helper", "showoff")
    first_cameo = max(5.0, float(config.get("idle_cameo_first_seconds", 15)))
    cameo_interval = max(20.0, float(config.get("ambient_card_interval_seconds", 60)))
    cameo_duration = max(1.5, min(float(config.get("idle_cameo_duration_seconds", 3.2)), 8.0))
    with RUNTIME.lock:
        RUNTIME.next_idle_cameo = time.monotonic() + first_cameo
    if platform.system() == "Windows":
        try:
            import comtypes  # type: ignore

            comtypes.CoInitialize()
        except Exception:
            pass
    while not stop.wait(0.12):
        now = time.monotonic()
        if now - last_media_check >= 0.8:
            playing = spotify_is_playing()
            with RUNTIME.lock:
                RUNTIME.music_playing = playing
            last_media_check = now
        process = active_process_name()
        idle = windows_idle_seconds()
        with RUNTIME.lock:
            RUNTIME.active_process, RUNTIME.idle_seconds = process, idle
            manual = RUNTIME.manual_state if now < RUNTIME.manual_until else None
            after = RUNTIME.after_state if now >= RUNTIME.manual_until and now < RUNTIME.after_until else None
            scroll_burst = sum(event >= now - 0.75 for event in RUNTIME.scroll_events)
            last_key, last_scroll = RUNTIME.last_key, RUNTIME.last_scroll
            volume_recent = now - RUNTIME.last_volume <= 0.9
            volume_level, volume_muted = RUNTIME.volume_level, RUNTIME.volume_muted
            if not manual:
                RUNTIME.manual_state = None
            if not after:
                RUNTIME.after_state = None

        state, reason, source, priority = choose_reaction(
            now=now, process=process, idle=idle, manual=manual, after=after,
            volume_recent=volume_recent, volume_level=volume_level,
            volume_muted=volume_muted, last_key=last_key, last_scroll=last_scroll,
            scroll_burst=scroll_burst, config=config, games=games,
            browsers=browsers, media=media, app_states=app_states,
        )
        if state == "idle":
            with RUNTIME.lock:
                if now >= RUNTIME.next_idle_cameo:
                    cameo = cameo_states[RUNTIME.idle_cameo_index % len(cameo_states)]
                    if cameo == "weather" and RUNTIME.temperature is None:
                        cameo = "helper"
                    RUNTIME.idle_cameo_index += 1
                    RUNTIME.manual_state = cameo
                    duration = float(config.get("ambient_card_duration_seconds", 6)) if cameo in {"time", "weather"} else cameo_duration
                    RUNTIME.manual_until = now + duration
                    RUNTIME.next_idle_cameo = now + cameo_interval
                    state, reason, source, priority = (
                        cameo,
                        f"shy-curious idle cameo: {cameo}",
                        "manual",
                        REACTION_PRIORITY["manual"],
                    )
        else:
            with RUNTIME.lock:
                if not manual and now >= RUNTIME.next_idle_cameo:
                    RUNTIME.next_idle_cameo = now + cameo_interval
        RUNTIME.set_state(state, reason, source, priority)


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


def candidate_serial_ports(preferred: str) -> list[str]:
    """Return explicit or likely Espressif ports without opening unrelated devices."""
    if preferred and preferred.lower() != "auto":
        return [preferred]
    try:
        from serial.tools import list_ports  # type: ignore

        likely = []
        for port in list_ports.comports():
            description = f"{port.description} {port.manufacturer or ''}".lower()
            if port.vid == 0x303A or any(token in description for token in ("espressif", "esp32", "usb jtag", "usb serial")):
                likely.append(port.device)
        return likely
    except Exception:
        return []


def serial_bridge_loop(config: dict, stop: threading.Event) -> None:
    """Stream compact display frames and receive touch gestures over USB CDC."""
    serial_config = config.get("serial", {})
    if not serial_config.get("enabled", True):
        return
    try:
        import serial  # type: ignore
    except ImportError:
        print("USB display bridge unavailable: install requirements.txt (pyserial).")
        return
    baud = int(serial_config.get("baud", 115200))
    interval = max(0.1, float(serial_config.get("heartbeat_seconds", 0.5)))
    preferred = str(serial_config.get("port", "auto"))
    while not stop.is_set():
        connection = None
        port = ""
        for port in candidate_serial_ports(preferred):
            try:
                connection = serial.Serial()
                connection.port = port
                connection.baudrate = baud
                connection.timeout = 0.10
                connection.write_timeout = 2.0
                connection.dtr = False
                connection.rts = False
                connection.open()
                break
            except (OSError, serial.SerialException):
                connection = None
        if connection is None:
            RUNTIME.device_status(False, reason="waiting for Lil Bot USB display")
            stop.wait(1.0)
            continue
        print(f"Found {port}; waiting for Lil Bot firmware handshake.")
        handshake_deadline = time.monotonic() + 5.0
        next_send = 0.0
        handshake = False
        try:
            while not stop.is_set():
                now = time.monotonic()
                if handshake and now >= next_send:
                    connection.write(RUNTIME.wire_frame().encode("ascii"))
                    next_send = now + interval
                line = connection.readline().decode("utf-8", errors="replace").strip()
                if line:
                    if line.startswith(("READY:LILBOT/1", "HELLO:LILBOT/1")) and not handshake:
                        handshake = True
                        next_send = 0.0
                        RUNTIME.device_status(True, port, f"Lil Bot display connected on {port}")
                        print(f"Lil Bot display connected on {port}.")
                    with RUNTIME.lock:
                        RUNTIME.device_last_seen = time.time()
                    if line.startswith("TOUCH:"):
                        gesture = line.partition(":")[2].lower()
                        if gesture in {"tap", "double", "hold"}:
                            RUNTIME.touch_reaction(gesture)
                if not handshake and now >= handshake_deadline:
                    raise serial.SerialTimeoutException("firmware handshake timeout")
                stop.wait(0.01)
        except (OSError, serial.SerialException) as exc:
            print(f"Lil Bot display disconnected: {exc}")
        finally:
            connection.close()
            RUNTIME.device_status(False, reason=f"Lil Bot display disconnected from {port}")


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
        if urlparse(self.path).path == "/api/frame":
            self.send_json(RUNTIME.display_frame())
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
            RUNTIME.set_state("notification", f"new notification; {count} unread", "manual")
            self.send_json(RUNTIME.snapshot())
            return
        if route == "/api/clear-notifications":
            RUNTIME.clear_notifications()
            self.send_json(RUNTIME.snapshot())
            return
        if route == "/api/touch":
            try:
                length = min(int(self.headers.get("Content-Length", "0")), 512)
                payload = json.loads(self.rfile.read(length) or b"{}")
                gesture = str(payload.get("gesture", "tap")).lower()
                if gesture not in {"tap", "double", "hold"}:
                    raise ValueError("gesture must be tap, double, or hold")
                RUNTIME.touch_reaction(gesture)
                self.send_json(RUNTIME.snapshot())
            except (ValueError, json.JSONDecodeError) as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
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
            RUNTIME.set_state(state, "temporary simulated event", "manual")
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
    RUNTIME.set_state("startup", "Lil Bot woke up and is ready to help", "manual")
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
    serial_worker = threading.Thread(target=serial_bridge_loop, args=(config, stop), daemon=True)
    serial_worker.start()
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
