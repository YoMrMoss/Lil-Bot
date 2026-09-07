#!/usr/bin/env python3
"""Safely check Lil Bot's GitHub Releases feed without installing anything."""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "companion_config.json").read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check for a Lil Bot GitHub release.")
    parser.add_argument("--download", action="store_true", help="Download the newest Windows ZIP beside this script.")
    args = parser.parse_args()
    repository = CONFIG.get("updates", {}).get("github_repository", "YoMrMoss/Lil-Bot")
    url = f"https://api.github.com/repos/{repository}/releases/latest"
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "LilBot-Updater/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            release = json.load(response)
    except Exception as exc:
        print(f"Could not check {repository}: {exc}")
        print("The repository may not have been created or released yet.")
        return 1
    print(f"Latest release: {release.get('tag_name', 'unknown')}")
    assets = release.get("assets", [])
    companion = next((asset for asset in assets if asset.get("name", "").lower().endswith(".zip")), None)
    firmware = next((asset for asset in assets if asset.get("name") == "lilbot-firmware.bin"), None)
    print("Windows companion:", companion.get("name") if companion else "not included")
    print("Board firmware:", firmware.get("name") if firmware else "not included yet")
    if args.download and companion:
        destination = ROOT / companion["name"]
        urllib.request.urlretrieve(companion["browser_download_url"], destination)
        print(f"Downloaded: {destination}")
        print("It was not installed automatically; close Lil Bot before replacing its folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
