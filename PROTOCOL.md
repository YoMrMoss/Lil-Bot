# Lil Bot display protocol v1

The Windows companion is the source of truth. The browser simulator and future
ESP32-S3 firmware consume the same resolved display frame from `GET /api/frame`.

```json
{
  "protocol_version": 1,
  "sequence": 42,
  "state": "gaming",
  "display": {"quiet_hours": false, "brightness": 100, "period": "day"},
  "modifiers": {"music_bob": true, "quiet_hours": false, "brightness": 100, "pixel_shift": true, "transition_ms": 240},
  "volume_level": 0.5,
  "volume_muted": false,
  "unread_notifications": 0
}
```

## Transport

During browser testing this is JSON over HTTP. Firmware 1.5 streams the same
compact JSON as newline-delimited messages over USB CDC at 115200 baud.

The board answers with `READY:LILBOT/1`, repeats `HELLO:LILBOT/1` as its link
heartbeat, acknowledges accepted frames with `ACK:<sequence>`, and reports
screen interaction as `TOUCH:tap`, `TOUCH:double`, `TOUCH:hold`,
`TOUCH:swipe_left`, or `TOUCH:swipe_right`. The Windows
bridge auto-discovers Espressif USB serial ports and reconnects without restart.

The USB firmware transport will
send the same object as one UTF-8 JSON line terminated by `\n`. A receiver must
ignore duplicate `sequence` values, retain the last valid frame during a brief
disconnect, and show `reconnect` after communication resumes.

## Arbitration

Only the companion chooses the base state. Current priority is manual gesture,
after-reaction, volume, sleep, gaming, typing, browsing, application, then idle.
Modifiers such as Spotify bobbing, quiet-hours dimming, and pixel shifting are
applied independently without replacing the base emotion.

## Touch input

Firmware sends tap, double-tap, hold, and horizontal swipes to the companion.
The compact USB frame also includes a final gaze field (`-1`, `0`, or `1`). It
represents only mouse direction and never transmits cursor coordinates.

Until serial is
implemented, the simulator sends the equivalent JSON to `POST /api/touch`:

```json
{"gesture": "tap"}
```

Tap clears notifications and triggers the table flip. Double tap shows the
helper face. Hold temporarily shows sleep. Left/right swipes cycle through the
curated face collection without clearing notifications. Unknown gestures
receive HTTP 400.

Automatic firmware flashing remains disabled until board identity, recovery, and power-
loss behavior are verified on the physical T-Display-S3.
