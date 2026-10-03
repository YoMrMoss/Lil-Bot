# Lil-Bot 2.6.0 — Halloween and quiet background operation

Approved seasonal artwork: B (Happy Jack) and D (Bat Groove). A is excluded.
Happy Jack uses full, stepped orange happy eyes and a small filled pixel smile;
Bat Groove keeps the cyan happy eyes, pink smile, purple bats and orange music
notes. There are no pupils in these seasonal eyes. The tiny purple spider
bobs on a dotted thread in the upper corner.

The companion automatically enables Halloween in October using the PC's local
date. Set `seasonal.halloween` in `companion_config.json` to `off`, `on`, or
`auto` (default), then restart the companion. Normal music becomes Bat Groove.
Other active reactions keep their own expressions and music bobbing.

One in three idle cameos becomes Happy Jack, spider, or countdown in turn.
The countdown temporarily replaces the face for the existing short cameo
window, then yields to normal activity. It counts days until October 31 and
shows HALLOWEEN! on the day. No network request is needed. The board receives
the date text from the companion; it does not keep its own calendar.

The animation lab has four dedicated Halloween test buttons. Both renderers
use the same stepped eye geometry, spider and bat shapes, and orange palette.
Desktop glow and font rendering may differ slightly from the LCD.

For quiet login startup, use `install_background.bat` after closing the existing
companion and Serial Monitor. See BACKGROUND_SETUP.md for tray controls and
removal. Flashing stays a separate visible maintenance action. GitHub updates
cannot reach the board while the PC is off or the board is disconnected.

Validation before release: firmware compilation, physical artwork review,
USB unplug/replug, PC sleep/wake, duplicate launch, and tray startup on Windows.
Python tests and preview syntax checks alone cannot confirm those behaviors.

## Shared presence across personalities

Every face now shares a gentle 6.4-second breathing cycle (up to 2 pixels) and
occasional short side glances (up to 3 pixels), with existing mouse-direction
hints taking priority. The entire expression moves together, including glasses,
tusks and hands; this adds attention cues without inserting pupils. Sleep only
breathes. Quiet brightness reduces breathing to 1 pixel and suppresses glances.
Time, weather, countdown cards and application logos keep their readable layout.
Volume/loading bars and notification badges remain anchored on the hardware.

Music bobbing and face-specific effects remain layered on top. Firmware bounds
shared motion to the artwork's available screen margin and reuses the existing
framebuffer, rather than allocating a second one. Frame rate remains capped at
the existing 90 ms draw interval. The preview also now passes animation time to
custom face renderers, fixing their previously missing time argument.

Additional checks: `node test_presence.js` checks shared motion, quiet/sleep
behavior and displacement limits. A native C++ harness checks the actual
framebuffer translation in every shift direction, including edge protection.
Full ESP32 build and physical smoothness still need testing before release.
