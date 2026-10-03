# Quiet startup and recovery — prepared update

This update is prepared locally. Windows tray/startup behavior and the ESP32
build still require a hardware acceptance run before publishing.

1. Close the existing companion console and Serial Monitor.
2. Keep the project in a permanent folder and double-click `install_background.bat`.
3. Installation adds the tray dependencies, creates a shortcut in your own
   Windows Startup folder, and starts `background_lilbot.pyw` without a console.
4. Open the tray menu for preview, health, pause/resume, restart, or quit.
5. Quit through the tray before building or flashing firmware. Use the existing
   update-and-flash launcher separately; maintenance stays visible.

The background launcher waits for USB and restarts an exited companion with
increasing delays. It uses the configured localhost host/port. It does not
start a second companion if a health endpoint is already responding. Quit
an older console instance first; the tray only controls its own child process.

Logs live in `%LOCALAPPDATA%\LilBot\logs`. Companion logs rotate at 1 MB with
three backups. The health endpoint reports build, uptime, USB status, successful
session count, last outgoing frame, and last serial error. The last error is
retained after recovery as diagnostic history. No firmware version is reported
until the handshake protocol provides one.

Check on Windows: sign out/in, unplug/replug USB, sleep/wake the PC, launch twice,
pause/resume, and quit before flashing. Confirm only one companion owns the port
and the preview opens only on request. Verify failed-connection retries slow
down and the physical screen returns to idle after its reconnect animation.

To remove automatic startup, delete `Lil-Bot.lnk` from the folder opened by
Windows Run → `shell:startup`, then quit from the tray.

Halloween B and D, the pixel spider, and countdown are now implemented in
the prepared 2.6.0 update. See HALLOWEEN_UPDATE.md for settings and testing.
