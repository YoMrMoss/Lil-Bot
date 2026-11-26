"""Stop this installation's companion and supervisor, including older versions."""
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
import psutil

ROOT = Path(__file__).resolve().parent
SCRIPTS = {"companion.py", "background_lilbot.pyw"}


def belongs_to_installation(process):
    try:
        args = process.cmdline()
        cwd = Path(process.cwd())
        return any(Path(arg).name.lower() in SCRIPTS and
                   (cwd / arg).resolve().parent == ROOT for arg in args[1:])
    except (psutil.Error, OSError):
        return False


def main():
    processes = [p for p in psutil.process_iter() if p.pid != os.getpid() and belongs_to_installation(p)]
    config = json.loads((ROOT / "companion_config.json").read_text())
    # Always use loopback for local control, even when the Lab is LAN-accessible.
    url = f"http://127.0.0.1:{config.get('port', 8765)}/api/shutdown"
    request = urllib.request.Request(url, data=b"", headers={"X-LilBot-Control": "1"})
    try:
        with urllib.request.urlopen(request, timeout=2):
            pass
    except (OSError, urllib.error.URLError):
        pass
    # Old releases lack the shutdown endpoint. Only stop processes whose script
    # resolves to this exact installation, with the supervisor stopped first.
    def supervisor_first(process):
        try:
            return "background_lilbot.pyw" not in " ".join(process.cmdline())
        except psutil.Error:
            return True
    processes.sort(key=supervisor_first)
    for process in processes:
        try:
            if not process.is_running():
                continue
            process.wait(timeout=1)
        except psutil.TimeoutExpired:
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                pass
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(processes, timeout=5)
    if alive:
        print("Lil-Bot is still stopping. Wait a moment and try again.")
        return 1
    print("Lil-Bot stopped. Its USB connection is released.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
