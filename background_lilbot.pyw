"""Windowless, per-user Lil-Bot supervisor with optional tray controls."""
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent


def main():
    ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p
    ctypes.windll.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\LilBotBackground")
    if ctypes.windll.kernel32.GetLastError() == 183:
        return
    log_dir = Path(os.environ["LOCALAPPDATA"]) / "LilBot" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    child = None
    paused = False
    guard = threading.Lock()
    config_path = ROOT / "companion_config.json"
    import json
    config = json.loads(config_path.read_text(encoding="utf-8"))
    url = f"http://{config.get('host', '127.0.0.1')}:{config.get('port', 8765)}"

    def running():
        try:
            with urllib.request.urlopen(url + "/api/health", timeout=2) as response:
                return json.load(response)
        except Exception:
            return None

    def halt():
        nonlocal child
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
        child = None

    def supervise():
        nonlocal child
        retry = 2
        while not stop.wait(retry):
            with guard:
                if paused or (child is not None and child.poll() is None):
                    continue
                if running():
                    continue
                # Rotate supervisor output between launches, never on every tick.
                path = log_dir / "background.log"
                if path.exists() and path.stat().st_size > 1_000_000:
                    path.replace(log_dir / "background.previous.log")
                with path.open("ab") as output:
                    child = subprocess.Popen(
                        [sys.executable, str(ROOT / "companion.py"), "--no-browser"],
                        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=output,
                        creationflags=subprocess.CREATE_NO_WINDOW)
                retry = min(30, retry * 2)

    worker = threading.Thread(target=supervise, daemon=True)
    worker.start()
    try:
        import pystray
        from PIL import Image, ImageDraw
        image = Image.new("RGB", (64, 64), "#02040d")
        draw = ImageDraw.Draw(image)
        draw.ellipse((10, 19, 24, 33), fill="#19f7ff")
        draw.ellipse((40, 19, 54, 33), fill="#19f7ff")
        draw.rectangle((25, 43, 39, 48), fill="#ff2daa")

        def toggle(icon, item):
            nonlocal paused
            with guard:
                paused = not paused
                if paused:
                    halt()
        def restart(icon, item):
            nonlocal paused
            with guard:
                paused = False
                halt()
        def quit_bot(icon, item):
            stop.set()
            icon.stop()
        def status(item):
            health = running()
            if paused:
                return "Paused"
            if not health:
                return "Starting / recovering"
            usb = health.get("usb", {})
            return "Connected" if usb.get("connected") else "Waiting for USB"
        icon = pystray.Icon("LilBot", image, "Lil-Bot", pystray.Menu(
            pystray.MenuItem(status, None, enabled=False),
            pystray.MenuItem("Open preview", lambda: webbrowser.open(url + "/display-preview.html")),
            pystray.MenuItem("Health", lambda: webbrowser.open(url + "/api/health")),
            pystray.MenuItem("Pause / resume", toggle),
            pystray.MenuItem("Restart", restart),
            pystray.MenuItem("Quit before firmware update", quit_bot)))
        icon.run()
    finally:
        stop.set()
        with guard:
            halt()
        ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
