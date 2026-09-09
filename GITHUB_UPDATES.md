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

Unattended background flashing remains disabled because the Windows PC must
have exclusive access to COM5 and the board must remain powered. The one-click
task automates the complete process while keeping the upload visible and
recoverable.
