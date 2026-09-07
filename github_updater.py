#!/usr/bin/env python3
"""Prompted, checksum-verified GitHub Release updater for Lil Bot."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "companion_config.json"
VERSION_PATH = ROOT / "VERSION"
PRESERVE = {"companion_config.json"}
REQUIRED = {"companion.py", "display-preview.html", "start_lilbot.bat", "VERSION"}


def version_tuple(value: str) -> tuple[int, ...]:
    clean = value.strip().lower().lstrip("v").split("-", 1)[0]
    try:
        return tuple(int(part) for part in clean.split("."))
    except ValueError:
        return (0,)


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "LilBot-Updater/1.0"})
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.load(response)


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "LilBot-Updater/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def ask(message: str) -> bool:
    if os.name == "nt":
        return ctypes.windll.user32.MessageBoxW(None, message, "Lil Bot Update", 0x24) == 6
    answer = input(f"{message} [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def locate_payload(extracted: Path) -> Path:
    candidates = [extracted / "LilBot", extracted]
    for candidate in candidates:
        if REQUIRED.issubset({path.name for path in candidate.iterdir() if path.is_file()}):
            return candidate
    raise RuntimeError("release does not contain a valid Lil Bot installation")


def apply_payload(payload: Path) -> None:
    backup = ROOT / ".update-backup"
    if backup.exists():
        shutil.rmtree(backup)
    backup.mkdir()
    changed: list[Path] = []
    try:
        for source in payload.iterdir():
            if source.name in PRESERVE or source.name.startswith("."):
                continue
            destination = ROOT / source.name
            if destination.exists():
                target_backup = backup / source.name
                if destination.is_dir():
                    shutil.copytree(destination, target_backup)
                else:
                    shutil.copy2(destination, target_backup)
            if source.is_dir():
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(source, destination)
            else:
                temporary = destination.with_suffix(destination.suffix + ".new")
                shutil.copy2(source, temporary)
                os.replace(temporary, destination)
            changed.append(destination)
    except Exception:
        for destination in reversed(changed):
            saved = backup / destination.name
            if saved.exists():
                if saved.is_dir():
                    if destination.exists():
                        shutil.rmtree(destination)
                    shutil.copytree(saved, destination)
                else:
                    shutil.copy2(saved, destination)
        raise


def main() -> int:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    settings = config.get("updates", {})
    if not settings.get("enabled", True) or not settings.get("check_on_start", True):
        return 0
    repository = settings.get("github_repository", "YoMrMoss/Lil-Bot")
    current = VERSION_PATH.read_text(encoding="utf-8").strip() if VERSION_PATH.exists() else "0.0.0"
    try:
        release = fetch_json(f"https://api.github.com/repos/{repository}/releases/latest")
        latest = str(release.get("tag_name", "0.0.0")).lstrip("v")
        if version_tuple(latest) <= version_tuple(current):
            print(f"Lil Bot {current} is current.")
            return 0
        assets = release.get("assets", [])
        package = next((asset for asset in assets if asset.get("name", "").startswith("LilBot-Windows-") and asset.get("name", "").endswith(".zip")), None)
        checksums = next((asset for asset in assets if asset.get("name") == "SHA256SUMS.txt"), None)
        if not package or not checksums:
            raise RuntimeError("release is missing its Windows package or checksum file")
        if not ask(f"Lil Bot {latest} is available. Update from {current} now?"):
            print("Update postponed.")
            return 0
        with tempfile.TemporaryDirectory(prefix="lilbot-update-") as temporary:
            temp = Path(temporary)
            archive = temp / package["name"]
            checksum_file = temp / "SHA256SUMS.txt"
            download(package["browser_download_url"], archive)
            download(checksums["browser_download_url"], checksum_file)
            expected = None
            for line in checksum_file.read_text(encoding="utf-8").splitlines():
                digest, _, name = line.partition("  ")
                if name.strip() == archive.name:
                    expected = digest.strip().lower()
                    break
            actual = hashlib.sha256(archive.read_bytes()).hexdigest()
            if not expected or actual != expected:
                raise RuntimeError("download checksum did not match the GitHub release")
            extracted = temp / "extracted"
            with zipfile.ZipFile(archive) as package_zip:
                for member in package_zip.infolist():
                    target = (extracted / member.filename).resolve()
                    if extracted.resolve() not in target.parents and target != extracted.resolve():
                        raise RuntimeError("release archive contains an unsafe path")
                package_zip.extractall(extracted)
            apply_payload(locate_payload(extracted))
        print(f"Updated Lil Bot to {latest}. Your companion_config.json was preserved.")
        return 0
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print("No GitHub release exists yet; continuing with the installed version.")
            return 0
        print(f"Update check failed: {exc}")
        return 0
    except Exception as exc:
        print(f"Update was not installed: {exc}")
        print("The existing Lil Bot installation will continue unchanged.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
