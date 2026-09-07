# Lil Bot

Lil Bot is a low-cost ESP32-S3 desk companion that reacts to computer activity
with animated Miami Vice-inspired expressions.

The hardware target is the **LILYGO T-Display-S3 Touch**:

- ESP32-S3
- 1.9-inch ST7789 display
- 320 × 170 landscape canvas
- CST816 capacitive touch
- 16 MB flash / 8 MB PSRAM

## Current status

The project is in visual prototyping. The browser-based Test Lab lets us approve
the personality and animation system before it is ported to the physical board.

Current experiments include:

- Normal, happy, gaming, music, typing, sleepy, sleeping and surprised states
- Miami Vice cyan, hot pink and purple palette
- Pupils represented by unlit portions of the illuminated eyes
- Toggleable eye constructions
- Mouse tracking, typing reactions, touch/click reactions and idle sleep
- Optional microphone rhythm testing
- Wide-gap face studies and funny idle expressions

## Run the Screen Simulator

1. Download or clone the repository.
2. On Windows, double-click `start_lilbot.bat`.
3. The companion opens `display-preview.html` and connects it to live PC events.

The simulator includes state-specific motion, idle blinking, touch response,
sleep dimming, music bobbing, a synthetic tempo test, and optional microphone
rhythm input.

The main software intentionally opens directly into the approved 320 × 170
face simulator. It does not expose the earlier face editor or enclosure mockup.
Use **Fullscreen display** to see only the pixels that will appear on the board.

The enhanced preview keeps the emoticon mouth and larger neutral eyes while
adding idle winks, notification glances, typing reactions, loading progress,
gaming focus, music response, error glitches, and lock/sleep behavior. All
movement is drawn on the LCD; the project does not require motors or servos.

### Approved base-face geometry

| Setting | Value |
| --- | ---: |
| Eye spacing | 184 |
| Eye size | 48 |
| Eye vertical position | 87 |
| Mouth size | 42 |
| Mouth vertical position | 131 |
| Line width | 4 |
| Glow | 12 |

## Run the virtual Windows companion

Before the physical board arrives, the companion can drive the browser preview
as though it were the ESP32 display.

1. Double-click `start_lilbot.bat`.
2. Allow the initial Python packages to install.
3. The animated display opens at `http://127.0.0.1:8765/display-preview.html`.
4. Type, scroll in a configured browser, or open a configured game/media app.
5. Use the state buttons to simulate events that are not detected yet.
6. Close the command window or press `Ctrl+C` to stop it.

The current simulator is labeled **BUILD 1.1.0** at the top. When updating, close
the previous Lil Bot command window and extract the new ZIP into a new folder
instead of merging it into an older copy. If the screen still has side grips or
a USB tab, an older preview is running.

The companion only stores input timestamps. It does not record typed keys,
mouse coordinates, browser contents, or messages. Edit `companion_config.json`
to change game, browser, and media executable names or the idle timeout.

Default application reactions:

| Application/input | Display state |
| --- | --- |
| Spotify | Music |
| Google Chrome, inactive | Idle |
| Google Chrome, normal scrolling | Reading glasses |
| Google Chrome, rapid scrolling | Racing visor |
| Discord | Notification/attention |
| World of Warcraft (Retail or Classic) | Gaming |
| League of Legends (client or game) | Gaming |
| Volume up/down/mute media keys | Live ten-step volume meter |

Typing and scrolling take priority over Chrome's general browsing expression,
so those actions remain visibly reactive. The live status line also reports the
foreground process and whether it most recently detected typing, scrolling,
mouse movement, or no active input.

Merely leaving Chrome, Edge, or Firefox open no longer holds the browsing face.
Normal scroll bursts briefly show reading glasses; five or more scroll events
within 0.75 seconds trigger the racing visor. Both return to idle after the
configured `browsing_hold_seconds` delay.

The gaming expression is the compact HUD `[+..••]`. The emoticons
`≽^•⩊•^≼` and `(ദ്ദി˙ᗜ˙)` appear as curious and eager-helper idle cameos and
can also be selected manually in the simulator. The volume overlay reads the
Windows master level: fewer illuminated bars mean quieter, all ten mean loud,
and mute uses a pink strike-through.

The display preview also includes transition scenarios for music plus volume,
gaming plus Discord, and browsing plus typing/loading. These verify that a
temporary reaction returns to the correct application face.

During idle, Lil Bot alternates brief full-screen time and local-temperature
cards before returning to the approved face. Weather coordinates, units, and
refresh timing are configured under `weather` in `companion_config.json`.
Temperature data is provided by Open-Meteo under CC BY 4.0.

Public releases keep weather disabled and use blank coordinates so personal
location data is never committed to GitHub. Set `enabled` to `true` and add your
coordinates only in the local `companion_config.json` on the computer running
Lil Bot.

Presence features now include a shy startup hello, reconnect reaction, unread
notification badge, quiet hours, automatic day/night brightness, and a live
diagnostic panel explaining why each face activated. Quiet hours reduce motion
as well as brightness. Time and weather remain idle-only interruptions, so
typing, gaming, music, volume, and notification reactions take priority.

Notification count can be tested with `POST /api/notification` and cleared with
`POST /api/clear-notifications`. The test controls expose both actions. This is
currently a project-owned notification counter; reading the Windows or Discord
unread total automatically will require a later integration with their supported
notification APIs.

See `ENCLOSURE_NOTES.md` for the chonky hood-and-headphones case concept,
including the USB cable disguised as a safely strain-relieved headphone cord.

## GitHub releases and updates

The repository includes a release workflow and a prompted startup updater.
Changing `VERSION` on `main` or pushing a version tag automatically packages the
streamlined Windows companion and publishes checksums. Before Lil Bot starts, it checks GitHub Releases and offers to install
new checksum-verified builds while preserving local settings and a rollback
backup. See `GITHUB_UPDATES.md` for the staged path toward verified USB
firmware updates after the board arrives. Automatic firmware flashing remains
disabled until the physical board and recovery process can be tested safely.

All eye glyphs share the approved 48 × 48 bounding box, center positions,
4-pixel stroke, and 12-pixel glow. Expressions may change shape or fill, but
they no longer change the approved eye footprint.

To start it manually from PowerShell:

```powershell
py -m pip install -r requirements.txt
py companion.py
```

Useful endpoints while developing:

- `GET /api/state` returns the current virtual-board state.
- `GET /api/health` confirms that the companion is running.
- `GET /api/log` explains recent state activations.
- `POST /api/simulate` temporarily injects a test state.
- `POST /api/notification` adds an unread notification.
- `POST /api/clear-notifications` clears the unread count.

Example test request:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/api/simulate `
  -ContentType 'application/json' -Body '{"state":"notification","duration":2}'
```

## Design studies

- `LilBot_Enclosure_Concepts_v1.png` — round hoodie-bean, retro-computer,
  and low/wide gaming-mascot enclosure directions
Earlier face studies remain in project history; the published simulator uses
the approved wide-set face.

## Planned architecture

```text
Windows companion -> USB serial state commands -> ESP32 firmware -> animated face
```

The Windows companion will eventually detect media playback, configured game
processes, keyboard/mouse idle time, lock state and selected system events.

## Project phases

1. Approve the base face and idle-expression library
2. Implement real PC activity detection
3. Port the drawing system to the T-Display-S3 Touch
4. Add touch interaction and configuration
5. Design and print the enclosure
6. Package a beginner-friendly installer and firmware release

## Palette

| Role | Color |
| --- | --- |
| Cyan | `#19F7FF` |
| Hot pink | `#FF2DAA` |
| Purple | `#8B3DFF` |
| Deep navy | `#070A1A` |
| Unlit pixels | `#02040D` |
