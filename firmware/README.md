# Lil Bot firmware

This is the first hardware-ready firmware for the LILYGO T-Display-S3 Touch (320×170). It renders original Lil Bot face assets, accepts live state frames over the board's straight USB-C connection, reports touch gestures, applies brightness and music-bob modifiers, and falls back to a reconnect face when the PC companion disappears.

## First flash

1. Install [Visual Studio Code](https://code.visualstudio.com/) and the PlatformIO extension.
2. Open this `firmware` folder as the PlatformIO project.
3. Connect the T-Display-S3 Touch directly with a data-capable USB-C cable.
4. Choose **Upload**, then **Monitor** at 115200 baud.
5. Start the Windows companion from the repository root. It discovers Espressif USB serial ports automatically.

If upload cannot find the board, hold **BOOT**, tap **RESET**, release **BOOT**, and upload again. The screen's power rail is enabled through GPIO 15 before the display initializes.

## Asset pipeline

Run `python tools/generate_face_assets.py` from the repository root. It creates original 1-bit `.lbf` files and the compile-time C header. Each `.lbf` contains a small `LBF1` header, frame metadata, and row-major packed pixels. This is a Lil Bot format; it does not contain QBIT code or artwork.

## Current safety foundations

- Dual OTA application partitions plus OTA metadata
- Eight-second task watchdog
- Protocol version validation and frame sequence handling
- 2.5-second PC heartbeat timeout with a local reconnect state
- Persistent brightness setting namespace
- Touch events travel back to the companion as `TOUCH:tap`, `TOUCH:double`, or `TOUCH:hold`

Touch orientation and the physical enclosure opening must be verified on the actual board before a final case is printed.
