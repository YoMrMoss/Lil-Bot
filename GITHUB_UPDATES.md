# GitHub update design

The repository is the source of truth for both halves of Lil Bot:

1. **Windows companion:** detects PC activity and sends face states.
2. **ESP32-S3 firmware:** receives those states and draws the face on the board.

Pushing a version tag such as `v0.8.0` runs the included GitHub Actions workflow.
It creates a Windows ZIP, generates SHA-256 checksums, and publishes a GitHub
Release. Once firmware development begins, the same release can also contain
`lilbot-firmware.bin`.

## Safe update stages

- **Now:** `start_lilbot.bat` checks GitHub Releases before launching. When a
  newer checksum-verified version exists, it asks before installing it, keeps a
  local backup, preserves `companion_config.json`, and then starts the update.
- **Connected-board workflow:** run `update_flash_start_lilbot.bat`, or choose
  **Terminal > Run Build Task > Lil Bot: Sync GitHub, flash, and start** in VS
  Code. It checks the signed release path, builds the current firmware, flashes
  the USB-connected board, and starts the companion.
- **Later:** offer one-click updates only after verifying the release checksum,
  board model, firmware protocol version, power state, and successful backup.
- **Optional future:** Wi-Fi over-the-air firmware updates. USB should remain the
  recovery path if an OTA update is interrupted.

Before flashing, quit Lil Bot from the tray and close Serial Monitor so the
updater has exclusive access to the display. PlatformIO detects the upload
port each run.

If esptool says the detected COM port does not exist, enter upload mode before
retrying. With the board plugged in, hold **BOOT**, tap **RST**, then release
**BOOT**. In Windows Device Manager, look under **Ports (COM & LPT)** for the
port that appeared. From Command Prompt in the Lil Bot folder, run these two
commands with that port in place of `COM7`.

```bat
set "PLATFORMIO_UPLOAD_PORT=COM7"
update_flash_start_lilbot.bat
```

The override applies only to this Command Prompt and its child processes.
Clear it with `set "PLATFORMIO_UPLOAD_PORT="` once the upload finishes. If the
display stays in upload mode after a successful flash, tap **RST** to start
the firmware.
