# Lil Bot enclosure brief

## Character direction

Lil Bot is a shy, curious, eager-to-help desk companion. The body should feel
chonky and friendly, with a low center of gravity, a soft hood silhouette, and
oversized headphones. There are no motors: all personality comes from the LCD.

## Front composition

- The 320 × 170 screen sits where the hood opening would be.
- The hood forms a thick rounded frame around the visible display, hiding the
  rectangular PCB and making the face feel embedded in the character.
- Headphone cups sit outside the hood so they do not cover the LCD or touch area.
- Keep the mouth and the approved wide-set eyes fully visible through the bezel.
- Use a removable tinted acrylic lens only after checking that touch still works.

## The headphone-cord USB idea

Route the USB cable out below one headphone cup so it reads as the headset cord.
Inside the body, clamp the cable jacket to the enclosure before it reaches the
USB-C plug. This strain relief is essential: pulling the decorative cord must
never pull directly on the T-Display-S3 connector. Leave a gentle cable bend and
enough slack to unplug the board during servicing.

## Practical build constraints

- Measure the delivered board, screen active area, connector, and button
  locations before finalizing the CAD dimensions.
- Use a removable rear panel and internal mounting bosses; do not glue the board.
- Leave clearance for USB-C, reset/boot buttons, touch, and airflow around the
  ESP32-S3.
- Add rubber feet and modest weight in the base so the cord cannot tip the body.
- Print the hood/bezel separately from the body for easier screen alignment.
- Avoid a tight display window until a paper/cardboard fit test confirms that no
  active pixels are hidden.

## Recommended prototype sequence

1. Print a 1:1 paper outline of the board and screen.
2. Cut a cardboard hood opening and confirm the full face is visible at desk distance.
3. Build a simple rear board tray with USB and button clearance.
4. Add a cable clamp and test a firm tug before designing the cosmetic cord path.
5. Only then sculpt the chonky body, hood, and headphone shells around that core.

