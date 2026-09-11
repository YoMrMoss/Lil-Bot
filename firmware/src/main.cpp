#include <Arduino.h>
#include <ArduinoJson.h>
#include <Arduino_GFX_Library.h>
#include <Wire.h>
#include "face_assets.h"

namespace {
constexpr uint8_t POWER_PIN = 15;
constexpr uint8_t BACKLIGHT_PIN = 38;
constexpr uint8_t TOUCH_SDA = 18;
constexpr uint8_t TOUCH_SCL = 17;
constexpr uint8_t TOUCH_RESET = 21;
constexpr uint8_t TOUCH_ADDRESS = 0x15;
constexpr int LEFT_EYE_X = 68;
constexpr int RIGHT_EYE_X = 252;
constexpr int EYE_Y = 87;
constexpr int EYE_SIZE = 48;
constexpr int MOUTH_X = 160;
constexpr int MOUTH_Y = 131;
constexpr int MOUTH_SIZE = 42;
constexpr uint32_t LINK_TIMEOUT_MS = 3000;

Arduino_DataBus *bus = new Arduino_ESP32PAR8Q(
    7, 6, 8, 9, 39, 40, 41, 42, 45, 46, 47, 48);
Arduino_GFX *display = new Arduino_ST7789(
    bus, 5, 0, true, 170, 320, 35, 0, 35, 0);
Arduino_Canvas *frameCanvas = nullptr;
Arduino_GFX *gfx = display;

String activeState = "startup";
String serialLine;
uint32_t sequence = 0;
uint32_t lastFrameAt = 0;
uint32_t lastHelloAt = 0;
uint32_t lastDrawAt = 0;
uint32_t stateChangedAt = 0;
uint32_t nextBlinkAt = 0;
uint32_t blinkUntil = 0;
uint32_t nextWinkAt = 0;
uint32_t winkUntil = 0;
String lastRenderedState;
int lastRenderedOffset = 999;
int lastRenderedGaze = 999;
bool lastBlink = false;
bool lastWink = false;
uint32_t touchStartedAt = 0;
uint32_t lastTapAt = 0;
float volumeLevel = 0.5f;
bool volumeMuted = false;
bool musicBob = false;
bool pixelShift = true;
uint16_t unreadNotifications = 0;
String clockText = "--:--";
String temperatureText = "--";
String locationText = "LOCAL";
bool linked = false;
bool touchDown = false;
uint8_t brightness = 80;
uint16_t cyan;
uint16_t pink;
uint16_t purple;
uint16_t cyanDark;
uint16_t pinkDark;
uint16_t purpleDark;

const FaceAsset *findFaceAsset(const String &name) {
  for (size_t i = 0; i < FACE_ASSET_COUNT; ++i) {
    if (name == FACE_ASSETS[i].name) return &FACE_ASSETS[i];
  }
  return nullptr;
}

bool drawAssetFace(const String &name, int yOffset, uint16_t color) {
  const FaceAsset *asset = findFaceAsset(name);
  if (!asset) return false;
  // Offset color layers give every bitmap face the same Miami Vice depth.
  gfx->drawBitmap(2, yOffset + 2, asset->data, asset->width, asset->height, purple);
  gfx->drawBitmap(1, yOffset + 1, asset->data, asset->width, asset->height,
                  color == pink ? cyanDark : pinkDark);
  gfx->drawBitmap(0, yOffset, asset->data, asset->width, asset->height, color);
  return true;
}

bool isGlowColor(uint16_t color) {
  return color == cyanDark || color == pinkDark || color == purpleDark;
}

void spreadPixelGlow(uint16_t core, uint16_t inner, uint16_t outer) {
  if (!frameCanvas || brightness <= 20) return;
  uint16_t *pixels = frameCanvas->getFramebuffer();
  if (!pixels) return;
  constexpr int width = 320;
  constexpr int height = 170;
  for (int y = 0; y < height; ++y) {
    for (int x = 0; x < width; ++x) {
      if (pixels[y * width + x] != core) continue;
      for (int dy = -2; dy <= 2; ++dy) {
        for (int dx = -2; dx <= 2; ++dx) {
          if (dx == 0 && dy == 0) continue;
          const int px = x + dx;
          const int py = y + dy;
          if (px < 0 || px >= width || py < 0 || py >= height) continue;
          uint16_t &target = pixels[py * width + px];
          if (target != BLACK && !isGlowColor(target)) continue;
          const bool near = abs(dx) <= 1 && abs(dy) <= 1;
          if (near || target == BLACK) target = near ? inner : outer;
        }
      }
    }
  }
}

void applyColorTreatment() {
  if (!frameCanvas) return;
  // Dark stepped halos read as glow on the small LCD without costly alpha effects.
  spreadPixelGlow(cyan, purpleDark, cyanDark);
  spreadPixelGlow(pink, purpleDark, pinkDark);
  spreadPixelGlow(purple, pinkDark, purpleDark);
}

void thickLine(int x1, int y1, int x2, int y2, uint16_t color, int width = 4) {
  for (int offset = -width / 2; offset <= width / 2; ++offset) {
    gfx->drawLine(x1, y1 + offset, x2, y2 + offset, color);
  }
}

void pixelDisc(int x, int y, int radius, uint16_t color) {
  // Three rectangles form a crisp stepped circle on the 320x170 panel.
  const int inset = max(4, radius / 4);
  gfx->fillRect(x - radius + inset, y - radius, (radius - inset) * 2 + 1, radius * 2 + 1, color);
  gfx->fillRect(x - radius, y - radius + inset, radius * 2 + 1, (radius - inset) * 2 + 1, color);
}

void drawSmile(int x, int y, int size, uint16_t color) {
  // Filled five-block smile: chunky, readable, and shared by every face.
  const int unit = max(4, size / 7);
  gfx->fillRect(x - unit * 3, y - unit, unit, unit, color);
  gfx->fillRect(x - unit * 2, y, unit, unit, color);
  gfx->fillRect(x - unit, y + unit, unit * 2, unit, color);
  gfx->fillRect(x + unit, y, unit, unit, color);
  gfx->fillRect(x + unit * 2, y - unit, unit, unit, color);
}

void drawBaseEyes(int yOffset = 0, int gazeX = 0) {
  // Approved simulator geometry: solid cyan emoticon dots, without pupils.
  pixelDisc(LEFT_EYE_X + gazeX, EYE_Y + yOffset, EYE_SIZE / 2, cyan);
  pixelDisc(RIGHT_EYE_X + gazeX, EYE_Y + yOffset, EYE_SIZE / 2, cyan);
}

void drawClosedEyes(int yOffset = 0, bool happy = false) {
  if (happy) {
    gfx->drawArc(LEFT_EYE_X, EYE_Y + 8 + yOffset, 24, 19, 190, 350, cyan);
    gfx->drawArc(RIGHT_EYE_X, EYE_Y + 8 + yOffset, 24, 19, 190, 350, cyan);
  } else {
    thickLine(LEFT_EYE_X - 24, EYE_Y + yOffset, LEFT_EYE_X + 24, EYE_Y + yOffset, cyan);
    thickLine(RIGHT_EYE_X - 24, EYE_Y + yOffset, RIGHT_EYE_X + 24, EYE_Y + yOffset, cyan);
  }
}

void drawReadingGlasses(int yOffset) {
  // Substantial 8 px frames with colored brow and temple blocks.
  gfx->fillRect(31, 54 + yOffset, 75, 8, purple);
  gfx->fillRect(31, 62 + yOffset, 8, 54, cyan);
  gfx->fillRect(98, 62 + yOffset, 8, 54, cyan);
  gfx->fillRect(39, 108 + yOffset, 59, 8, cyan);
  gfx->fillRect(214, 54 + yOffset, 75, 8, purple);
  gfx->fillRect(214, 62 + yOffset, 8, 54, cyan);
  gfx->fillRect(281, 62 + yOffset, 8, 54, cyan);
  gfx->fillRect(222, 108 + yOffset, 59, 8, cyan);
  gfx->fillRect(106, 73 + yOffset, 108, 8, pink);
  gfx->fillRect(15, 63 + yOffset, 16, 8, pink);
  gfx->fillRect(289, 63 + yOffset, 16, 8, pink);
}

void drawRaceVisor(int yOffset, float progress) {
  const int slide = static_cast<int>((1.0f - progress) * -58.0f);
  // Pixel helmet crown and ear blocks.
  gfx->fillRect(58, 20 + yOffset, 204, 8, pink);
  gfx->fillRect(38, 28 + yOffset, 20, 12, purple);
  gfx->fillRect(262, 28 + yOffset, 20, 12, purple);
  gfx->fillRect(22, 40 + yOffset, 16, 82, pink);
  gfx->fillRect(282, 40 + yOffset, 16, 82, pink);
  gfx->fillRect(150, 20 + yOffset, 20, 20, purple);
  // Layered visor: purple glass, cyan rim, magenta lower trim.
  gfx->fillRect(38, 48 + yOffset + slide, 244, 64, purpleDark);
  gfx->fillRect(30, 56 + yOffset + slide, 8, 48, cyan);
  gfx->fillRect(282, 56 + yOffset + slide, 8, 48, cyan);
  gfx->fillRect(38, 48 + yOffset + slide, 244, 8, cyan);
  gfx->fillRect(38, 104 + yOffset + slide, 244, 8, pink);
  // Speed D keeps Lil Bot's familiar wide, chunky eyes inside the visor.
  pixelDisc(82, 80 + yOffset + slide, 22, cyan);
  pixelDisc(238, 80 + yOffset + slide, 22, cyan);
  gfx->fillRect(82, 72 + yOffset + slide, 10, 18, BLACK);
  gfx->fillRect(228, 72 + yOffset + slide, 10, 18, BLACK);
  const int streak = (millis() / 55) % 18;
  gfx->fillRect(2, 58 + streak, 21, 5, cyan);
  gfx->fillRect(297, 90 - streak, 21, 5, pink);
}

void drawHelperFace(int yOffset) {
  pixelDisc(88, 82 + yOffset, 20, cyan);
  pixelDisc(232, 82 + yOffset, 20, cyan);
  // Absence-of-light pupils lean inward with a curious, eager focus.
  gfx->fillRect(92, 76 + yOffset, 9, 14, BLACK);
  gfx->fillRect(219, 76 + yOffset, 9, 14, BLACK);
  drawSmile(160, 122 + yOffset, 42, pink);
  // Helper B: the approval check draws itself, then emits two pixel sparks.
  const uint32_t age = millis() - stateChangedAt;
  if (age > 120) gfx->fillRect(139, 35 + yOffset, 9, 16, pink);
  if (age > 260) thickLine(144, 48 + yOffset, 157, 59 + yOffset, pink, 8);
  if (age > 400) thickLine(157, 59 + yOffset, 184, 29 + yOffset, pink, 8);
  if (age > 560 && ((age / 260) % 2 == 0)) {
    gfx->fillRect(124, 31 + yOffset, 8, 8, purple);
    gfx->fillRect(190, 24 + yOffset, 8, 8, purple);
  }
  gfx->fillRect(48, 111 + yOffset, 22, 7, pink);
  gfx->fillRect(250, 111 + yOffset, 22, 7, pink);
}

void drawShowoffFace(int yOffset) {
  // Solid shades, lens glints, and a confident asymmetric grin.
  gfx->fillRect(43, 59 + yOffset, 76, 16, cyan);
  gfx->fillRect(51, 75 + yOffset, 60, 28, purpleDark);
  gfx->fillRect(201, 59 + yOffset, 76, 16, cyan);
  gfx->fillRect(209, 75 + yOffset, 60, 28, purpleDark);
  gfx->fillRect(119, 67 + yOffset, 82, 9, pink);
  gfx->fillRect(59, 83 + yOffset, 20, 8, pink);
  gfx->fillRect(241, 83 + yOffset, 20, 8, pink);
  gfx->fillRect(59, 78 + yOffset, 9, 9, cyan);
  gfx->fillRect(241, 78 + yOffset, 9, 9, cyan);
  gfx->fillRect(135, 122 + yOffset, 36, 8, pink);
  gfx->fillRect(171, 114 + yOffset, 17, 8, pink);
  gfx->fillRect(22, 40 + yOffset, 26, 7, purple);
  gfx->fillRect(31, 31 + yOffset, 7, 25, purple);
}

void drawCatFace(int yOffset) {
  // Cat ears are stepped into the same wide-set face instead of using a font glyph.
  gfx->fillRect(40, 43 + yOffset, 10, 30, purple);
  gfx->fillRect(50, 51 + yOffset, 10, 22, cyan);
  gfx->fillRect(60, 59 + yOffset, 14, 14, cyan);
  gfx->fillRect(270, 43 + yOffset, 10, 30, purple);
  gfx->fillRect(260, 51 + yOffset, 10, 22, cyan);
  gfx->fillRect(246, 59 + yOffset, 14, 14, cyan);
  pixelDisc(92, 83 + yOffset, 16, cyan);
  pixelDisc(228, 83 + yOffset, 16, cyan);
  gfx->fillRect(154, 105 + yOffset, 12, 8, pink);
  thickLine(160, 113 + yOffset, 147, 124 + yOffset, pink, 5);
  thickLine(160, 113 + yOffset, 173, 124 + yOffset, pink, 5);
  gfx->fillRect(28, 105 + yOffset, 43, 5, purple);
  gfx->fillRect(249, 105 + yOffset, 43, 5, purple);
  gfx->fillRect(34, 116 + yOffset, 37, 5, purple);
  gfx->fillRect(249, 116 + yOffset, 37, 5, purple);
}

void drawNervousFace(int yOffset, int xOffset) {
  // Nervous B: inward-looking square eyes and a whole-face one-pixel tremble.
  gfx->fillRect(57 + xOffset, 57 + yOffset, 55, 48, cyan);
  gfx->fillRect(208 + xOffset, 57 + yOffset, 55, 48, cyan);
  gfx->fillRect(92 + xOffset, 70 + yOffset, 14, 25, BLACK);
  gfx->fillRect(214 + xOffset, 70 + yOffset, 14, 25, BLACK);
  gfx->fillRect(50 + xOffset, 111 + yOffset, 24, 7, pink);
  gfx->fillRect(246 + xOffset, 111 + yOffset, 24, 7, pink);
  const int x[] = {132, 141, 150, 159, 168, 177};
  for (int i = 0; i < 5; ++i) thickLine(x[i] + xOffset, 127 + (i % 2 ? -5 : 5) + yOffset,
                                        x[i + 1] + xOffset, 127 + (i % 2 ? 5 : -5) + yOffset, pink, 4);
  const int drop = static_cast<int>((millis() / 170) % 13);
  gfx->fillRect(284 + xOffset, 48 + drop + yOffset, 8, 15, purple);
  gfx->fillRect(280 + xOffset, 61 + drop + yOffset, 16, 8, purple);
}

void drawCryingFace(int yOffset) {
  // Heavy pixel lids keep the emotion readable; cyan tears animate as light blocks.
  gfx->fillRect(48, 67 + yOffset, 72, 9, purple);
  gfx->fillRect(200, 67 + yOffset, 72, 9, purple);
  gfx->fillRect(58, 76 + yOffset, 52, 8, cyan);
  gfx->fillRect(210, 76 + yOffset, 52, 8, cyan);
  const int tear = (millis() / 180) % 16;
  gfx->fillRect(78, 91 + tear + yOffset, 12, 25, cyan);
  gfx->fillRect(230, 96 + ((tear + 8) % 16) + yOffset, 12, 25, cyan);
  gfx->fillRect(139, 133 + yOffset, 8, 8, pink);
  gfx->fillRect(147, 125 + yOffset, 26, 8, pink);
  gfx->fillRect(173, 133 + yOffset, 8, 8, pink);
}

void drawSleepFace(int yOffset) {
  // Sleep B: relaxed lids breathe slowly beneath a pulsing pixel moon.
  gfx->fillRect(49, 83 + yOffset, 64, 8, purple);
  gfx->fillRect(207, 83 + yOffset, 64, 8, purple);
  gfx->fillRect(57, 91 + yOffset, 48, 7, cyan);
  gfx->fillRect(215, 91 + yOffset, 48, 7, cyan);
  gfx->fillRect(153, 124 + yOffset, 14, 10, pink);
  const bool moonPulse = ((millis() / 700) % 2) == 0;
  pixelDisc(224, 35, moonPulse ? 18 : 16, purple);
  pixelDisc(232, 29, moonPulse ? 14 : 12, BLACK);
  gfx->fillRect(194, 28, 7, 18, cyan);
  gfx->fillRect(188, 34, 19, 7, cyan);
  const int snore = static_cast<int>((millis() / 760) % 4);
  if (snore >= 1) gfx->fillRect(272, 70 - snore * 4, 13, 5, pink);
  if (snore >= 2) gfx->fillRect(280, 75 - snore * 4, 5, 8, pink);
  if (snore >= 3) gfx->fillRect(272, 83 - snore * 4, 13, 5, pink);
}

void drawNotificationIcon(int yOffset) {
  // Robot-style envelope alert from the approved concept sheet.
  gfx->fillRect(76, 45 + yOffset, 168, 10, cyan);
  gfx->fillRect(66, 55 + yOffset, 10, 82, cyan);
  gfx->fillRect(244, 55 + yOffset, 10, 82, cyan);
  gfx->fillRect(76, 137 + yOffset, 168, 10, cyan);
  thickLine(76, 55 + yOffset, 160, 113 + yOffset, pink, 8);
  thickLine(244, 55 + yOffset, 160, 113 + yOffset, pink, 8);
  gfx->fillRect(270, 37 + yOffset, 24, 24, purple);
  gfx->fillRect(278, 29 + yOffset, 8, 40, purple);
}

void drawBarEye(int x, int yOffset);
void drawClosedEyes(int yOffset, bool happy);

void drawGaming(int yOffset) {
  gfx->setTextSize(5);
  gfx->setTextColor(cyan);
  gfx->setCursor(30, 65 + yOffset);
  gfx->print("[+..");
  gfx->setTextColor(pink);
  gfx->print("oo]");
}

void drawGamingLife(int yOffset, bool blinkNow) {
  const uint32_t age = millis() - stateChangedAt;
  const uint32_t scene = age % 24000;
  int reaction = 0;
  if (scene >= 4800 && scene < 5900) reaction = 1;       // target sight
  else if (scene >= 9800 && scene < 10900) reaction = 2; // victory
  else if (scene >= 14400 && scene < 15500) reaction = 3;// low health
  else if (scene >= 18800 && scene < 20000) reaction = 4;// discovery
  else if (scene >= 22400 && scene < 23500) reaction = 5;// cooldown
  if (!reaction) {
    if (!drawAssetFace("gaming", yOffset, cyan)) drawGaming(yOffset);
    return;
  }
  if (blinkNow) {
    drawBarEye(LEFT_EYE_X, yOffset);
    drawBarEye(RIGHT_EYE_X, yOffset);
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
    return;
  }
  if (reaction == 2) {
    drawClosedEyes(yOffset, true);
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
    gfx->fillRect(28, 34 + yOffset, 9, 25, purple);
    gfx->fillRect(20, 42 + yOffset, 25, 9, purple);
    gfx->fillRect(283, 34 + yOffset, 9, 25, purple);
    gfx->fillRect(275, 42 + yOffset, 25, 9, purple);
    return;
  }
  if (reaction == 5) {
    gfx->fillRect(40, 75 + yOffset, 56, 10, cyan);
    gfx->fillRect(224, 75 + yOffset, 56, 10, cyan);
    gfx->fillRect(144, 130 + yOffset, 32, 7, pink);
    gfx->drawCircle(160, 28, 14, purple);
    gfx->fillRect(160, 12, 5, 12, cyan);
    return;
  }
  pixelDisc(LEFT_EYE_X, EYE_Y + yOffset, reaction == 4 ? 27 : 24, cyan);
  pixelDisc(RIGHT_EYE_X, EYE_Y + yOffset, reaction == 4 ? 27 : 24, cyan);
  const int look = reaction == 1 ? 7 : 0;
  gfx->fillRect(LEFT_EYE_X - 5 + look, EYE_Y - 9 + yOffset, 10, 18, BLACK);
  gfx->fillRect(RIGHT_EYE_X - 5 + look, EYE_Y - 9 + yOffset, 10, 18, BLACK);
  if (reaction == 1) {
    // A chunky sight briefly locks over the right eye.
    gfx->drawCircle(RIGHT_EYE_X, EYE_Y + yOffset, 34, purple);
    gfx->drawCircle(RIGHT_EYE_X, EYE_Y + yOffset, 32, cyan);
    gfx->fillRect(RIGHT_EYE_X - 3, EYE_Y - 43 + yOffset, 6, 15, pink);
    gfx->fillRect(RIGHT_EYE_X - 3, EYE_Y + 28 + yOffset, 6, 15, pink);
    gfx->fillRect(RIGHT_EYE_X - 43, EYE_Y - 3 + yOffset, 15, 6, pink);
    gfx->fillRect(RIGHT_EYE_X + 28, EYE_Y - 3 + yOffset, 15, 6, pink);
  } else if (reaction == 3) {
    gfx->fillRect(151, 20, 18, 18, pink);
    gfx->fillRect(145, 14, 12, 12, pink);
    gfx->fillRect(163, 14, 12, 12, pink);
  } else if (reaction == 4) {
    gfx->fillRect(155, 19, 10, 30, purple);
    gfx->fillRect(145, 29, 30, 10, purple);
    gfx->fillRect(151, 25, 18, 18, cyan);
  }
  if (reaction == 3) {
    thickLine(144, 134 + yOffset, 160, 126 + yOffset, pink, 5);
    thickLine(160, 126 + yOffset, 176, 134 + yOffset, pink, 5);
  } else drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
}

void drawVerticalEyes(int yOffset, int compression = 0) {
  const int height = 48 - compression;
  gfx->fillRoundRect(LEFT_EYE_X - 8, EYE_Y - height / 2 + yOffset, 16, height, 5, cyan);
  gfx->fillRoundRect(RIGHT_EYE_X - 8, EYE_Y - height / 2 + yOffset, 16, height, 5, cyan);
}

void drawBarEye(int x, int yOffset) {
  thickLine(x - 24, EYE_Y + yOffset, x + 24, EYE_Y + yOffset, cyan, 4);
}

void drawCircleEye(int x, int yOffset) {
  gfx->drawCircle(x, EYE_Y + yOffset, EYE_SIZE / 2, cyan);
  gfx->drawCircle(x, EYE_Y + yOffset, EYE_SIZE / 2 - 1, cyan);
}

void drawXEye(int x, int yOffset) {
  thickLine(x - 18, EYE_Y - 18 + yOffset, x + 18, EYE_Y + 18 + yOffset, cyan, 5);
  thickLine(x - 18, EYE_Y + 18 + yOffset, x + 18, EYE_Y - 18 + yOffset, cyan, 5);
}

void drawOMouth(int yOffset) {
  gfx->drawEllipse(MOUTH_X, MOUTH_Y + yOffset, 12, 15, pink);
  gfx->drawEllipse(MOUTH_X, MOUTH_Y + yOffset, 11, 14, pink);
}

void drawNotificationBadge() {
  gfx->fillCircle(290, 20, 13, pink);
  gfx->setTextColor(BLACK);
  gfx->setTextSize(1);
  gfx->setCursor(unreadNotifications > 9 ? 284 : 287, 17);
  gfx->print(unreadNotifications > 99 ? 99 : unreadNotifications);
}

void drawCenteredText(const String &text, int y, uint8_t size, uint16_t color) {
  gfx->setTextSize(size);
  gfx->setTextColor(color);
  int16_t x1, y1;
  uint16_t width, height;
  gfx->getTextBounds(text, 0, y, &x1, &y1, &width, &height);
  gfx->setCursor((320 - static_cast<int>(width)) / 2, y);
  gfx->print(text);
}

void drawInformationCard(bool weatherCard) {
  if (weatherCard) {
    drawCenteredText(temperatureText + " F", 48, 7, cyan);
    drawCenteredText("CURRENT TEMPERATURE", 118, 1, pink);
    drawCenteredText(locationText, 138, 1, purple);
  } else {
    drawCenteredText(clockText, 48, 5, cyan);
    drawCenteredText("JUST A QUICK TIME CHECK", 116, 1, pink);
    drawCenteredText("READY IF YOU NEED ME", 138, 1, purple);
  }
}

void drawVolumeStatus() {
  const int bars = volumeMuted ? 0 : constrain(static_cast<int>(volumeLevel * 8.0f + 0.5f), 1, 8);
  for (int i = 0; i < 8; ++i) {
    int height = 4 + i * 2;
    uint16_t color = i < bars ? cyan : purple;
    gfx->fillRect(111 + i * 13, 25 - height, 8, height, color);
  }
  if (volumeMuted) {
    thickLine(128, 8, 192, 26, pink, 4);
    thickLine(192, 8, 128, 26, pink, 4);
  }
}

void drawLoadingStatus() {
  gfx->drawRoundRect(75, 8, 170, 13, 4, purple);
  int width = 18 + ((millis() / 70) % 145);
  gfx->fillRoundRect(78, 11, width, 7, 3, cyan);
}

void drawMusicNotes() {
  int travel = (millis() / 35) % 28;
  int left = 38 + travel;
  int right = 282 - travel;
  gfx->fillCircle(left, 20, 5, pink);
  thickLine(left + 5, 20, left + 5, 5, pink, 3);
  thickLine(left + 5, 5, left + 15, 8, pink, 3);
  gfx->fillCircle(right, 24, 5, cyan);
  thickLine(right + 5, 24, right + 5, 9, cyan, 3);
  thickLine(right + 5, 9, right + 15, 12, cyan, 3);
}

void drawRageFace(int yOffset) {
  // Rage B: familiar wide eyes plus a playful pulsing comic anger vessel.
  const int phase = (millis() / 180) % 4;
  const int pulse = phase < 2 ? phase : 4 - phase;
  pixelDisc(LEFT_EYE_X, EYE_Y + yOffset, 24 + pulse, cyan);
  pixelDisc(RIGHT_EYE_X, EYE_Y + yOffset, 24 + pulse, cyan);
  gfx->fillRect(LEFT_EYE_X + 2, EYE_Y - 9 + yOffset, 11, 18, BLACK);
  gfx->fillRect(RIGHT_EYE_X - 13, EYE_Y - 9 + yOffset, 11, 18, BLACK);
  thickLine(35, 51 + yOffset, 105, 67 + yOffset, pink, 7 + pulse);
  thickLine(285, 51 + yOffset, 215, 67 + yOffset, pink, 7 + pulse);
  gfx->fillRect(43 - pulse, 119 + yOffset, 35 + pulse * 2, 7 + pulse, pink);
  gfx->fillRect(242 - pulse, 119 + yOffset, 35 + pulse * 2, 7 + pulse, pink);
  const int mouthY = 137 + yOffset;
  thickLine(126, mouthY, 138, mouthY - 7, pink, 6 + pulse);
  thickLine(138, mouthY - 7, 150, mouthY + 5, pink, 6 + pulse);
  thickLine(150, mouthY + 5, 162, mouthY - 7, pink, 6 + pulse);
  thickLine(162, mouthY - 7, 174, mouthY + 5, pink, 6 + pulse);
  thickLine(174, mouthY + 5, 190, mouthY - 2, pink, 6 + pulse);
  gfx->fillRect(276 - pulse, 18 - pulse, 10 + pulse, 24 + pulse * 2, purple);
  gfx->fillRect(286, 26 - pulse, 22 + pulse, 10 + pulse, purple);
  gfx->fillRect(262 - pulse, 8 - pulse, 10 + pulse, 22 + pulse, purple);
  gfx->fillRect(270, 8 - pulse, 22 + pulse, 10 + pulse, purple);
}

void drawFace() {
  const uint32_t now = millis();
  if (static_cast<int32_t>(now - nextBlinkAt) >= 0 && now >= blinkUntil) {
    blinkUntil = now + 105;
    nextBlinkAt = now + random(2600, 6100);
  }
  if (static_cast<int32_t>(now - nextWinkAt) >= 0 && now >= winkUntil) {
    winkUntil = now + 520;
    nextWinkAt = now + random(11000, 22000);
  }
  const bool blinkEligible = activeState == "idle" || activeState == "typing" ||
                             activeState == "browsing" || activeState == "gaming";
  const bool blinkNow = blinkEligible && now < blinkUntil;
  const bool winkNow = activeState == "idle" && !blinkNow && now < winkUntil;
  const bool quietMotion = brightness <= 20;
  const bool animated = musicBob || activeState == "music" ||
                        activeState == "loading" || activeState == "reconnect" ||
                        activeState == "browsing_fast" || activeState == "cat" ||
                        activeState == "helper" || activeState == "showoff" ||
                        activeState == "nervous" || activeState == "crying" ||
                        activeState == "sleep" || activeState == "rage" ||
                        activeState == "typing" || activeState == "browsing" ||
                        activeState == "gaming" || activeState == "idle" ||
                        blinkNow != lastBlink || winkNow != lastWink;
  if (animated && millis() - lastDrawAt < 90) return;
  int bobStrength = quietMotion ? 1 : 2 + static_cast<int>(volumeLevel * 2.0f);
  int bob = musicBob ? -static_cast<int>((millis() / 125) % 3) * bobStrength : 0;
  const bool lifeMotion = activeState == "idle" || activeState == "typing" ||
                          activeState == "browsing" || activeState == "gaming";
  if (lifeMotion && !quietMotion) {
    const int breathPhase = (now / 700) % 4;
    bob += (breathPhase == 1 || breathPhase == 2) ? 1 : 0;
  }
  int drift = pixelShift ? static_cast<int>((millis() / 25000) % 3) - 1 : 0;
  int yOffset = bob + drift;
  if (activeState == "sleep") yOffset += static_cast<int>((now / 650) % 3);
  if (activeState == "nervous") yOffset += static_cast<int>((now / 140) % 3) - 1;
  const int nervousShakeX = activeState == "nervous"
      ? static_cast<int>((now / 85) % 3) - 1 : 0;
  int gazeX = ((activeState == "idle" || activeState == "browsing") && !quietMotion)
      ? (static_cast<int>((millis() / 4200) % 3) - 1) * 4 : 0;
  if (!animated && activeState == lastRenderedState && yOffset == lastRenderedOffset && gazeX == lastRenderedGaze) return;
  lastDrawAt = millis();
  lastRenderedState = activeState;
  lastRenderedOffset = yOffset;
  lastRenderedGaze = gazeX;
  lastBlink = blinkNow;
  lastWink = winkNow;
  gfx->fillScreen(BLACK);

  if (activeState == "time" || activeState == "weather") {
    drawInformationCard(activeState == "weather");
  } else if (activeState == "gaming") {
    drawGamingLife(yOffset, blinkNow);
  } else if (activeState == "browsing_fast") {
    float progress = constrain((now - stateChangedAt) / 420.0f, 0.0f, 1.0f);
    drawRaceVisor(yOffset, progress);
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
  } else if (activeState == "sleep") {
    drawSleepFace(yOffset);
  } else if (activeState == "music") {
    drawClosedEyes(yOffset, true);
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
  } else if (activeState == "typing") {
    if (blinkNow) {
      drawBarEye(LEFT_EYE_X, yOffset);
      drawBarEye(RIGHT_EYE_X, yOffset);
    } else {
      const int compression = static_cast<int>((now / 180) % 3) * 2;
      drawVerticalEyes(yOffset, compression);
    }
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
  } else if (activeState == "notification") {
    drawNotificationIcon(yOffset);
  } else if (activeState == "error") {
    drawXEye(LEFT_EYE_X, yOffset);
    drawXEye(RIGHT_EYE_X, yOffset);
    thickLine(139, MOUTH_Y, 147, MOUTH_Y - 6, pink, 3);
    thickLine(147, MOUTH_Y - 6, 155, MOUTH_Y + 6, pink, 3);
    thickLine(155, MOUTH_Y + 6, 164, MOUTH_Y - 6, pink, 3);
    thickLine(164, MOUTH_Y - 6, 173, MOUTH_Y + 5, pink, 3);
    thickLine(173, MOUTH_Y + 5, 181, MOUTH_Y, pink, 3);
  } else if (activeState == "startup") {
    drawBarEye(LEFT_EYE_X, yOffset);
    pixelDisc(RIGHT_EYE_X, EYE_Y + yOffset, EYE_SIZE / 2, cyan);
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
  } else if (activeState == "reconnect") {
    drawCircleEye(LEFT_EYE_X, yOffset);
    pixelDisc(RIGHT_EYE_X, EYE_Y + yOffset, EYE_SIZE / 2, cyan);
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
  } else if (activeState == "helper") {
    drawHelperFace(yOffset);
  } else if (activeState == "showoff") {
    drawShowoffFace(yOffset);
  } else if (activeState == "cat") {
    drawCatFace(yOffset);
  } else if (activeState == "nervous") {
    drawNervousFace(yOffset, nervousShakeX);
  } else if (activeState == "crying") {
    drawCryingFace(yOffset);
  } else if (activeState == "rage") {
    drawRageFace(yOffset);
  } else {
    if ((activeState == "idle" || activeState == "browsing") && (blinkNow || winkNow)) {
      if (blinkNow) {
        drawBarEye(LEFT_EYE_X, yOffset);
        drawBarEye(RIGHT_EYE_X, yOffset);
      } else {
        pixelDisc(LEFT_EYE_X, EYE_Y + yOffset, EYE_SIZE / 2, cyan);
        drawBarEye(RIGHT_EYE_X, yOffset);
      }
    } else {
      drawBaseEyes(yOffset, gazeX);
    }
    if (activeState == "browsing") drawReadingGlasses(yOffset);
    if (activeState == "crying") {
      gfx->fillTriangle(LEFT_EYE_X, 115, LEFT_EYE_X - 6, 128, LEFT_EYE_X + 6, 128, cyan);
      gfx->drawArc(MOUTH_X, MOUTH_Y + 10, 21, 17, 200, 340, pink);
    } else if (activeState == "nervous") {
      thickLine(139, MOUTH_Y, 147, MOUTH_Y - 6, pink, 3);
      thickLine(147, MOUTH_Y - 6, 155, MOUTH_Y + 6, pink, 3);
      thickLine(155, MOUTH_Y + 6, 164, MOUTH_Y - 6, pink, 3);
      thickLine(164, MOUTH_Y - 6, 173, MOUTH_Y + 5, pink, 3);
      thickLine(173, MOUTH_Y + 5, 181, MOUTH_Y, pink, 3);
    } else {
      drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
    }
  }

  if (activeState == "volume") drawVolumeStatus();
  if (activeState == "loading" || activeState == "reconnect") drawLoadingStatus();
  if (musicBob || activeState == "music") drawMusicNotes();
  if (unreadNotifications > 0) drawNotificationBadge();
  if (!linked) gfx->fillCircle(308, 12, 3, purple);
  if (frameCanvas && gfx == frameCanvas) {
    applyColorTreatment();
    frameCanvas->flush();
  }
}

void setBrightness(uint8_t percent) {
  brightness = constrain(percent, 10, 100);
  ledcWrite(0, map(brightness, 0, 100, 0, 255));
}

void acceptFrame(const String &line) {
  StaticJsonDocument<768> doc;
  if (deserializeJson(doc, line) || (doc["protocol_version"] | 0) != 1) return;
  const uint32_t incoming = doc["sequence"] | sequence;
  if (incoming >= sequence) {
    sequence = incoming;
    activeState = String(static_cast<const char *>(doc["state"] | "idle"));
  }
  volumeLevel = doc["volume_level"] | volumeLevel;
  volumeMuted = doc["volume_muted"] | volumeMuted;
  musicBob = doc["modifiers"]["music_bob"] | false;
  pixelShift = doc["modifiers"]["pixel_shift"] | true;
  setBrightness(doc["modifiers"]["brightness"] | brightness);
  linked = true;
  lastFrameAt = millis();
  Serial.printf("ACK:%lu\n", static_cast<unsigned long>(sequence));
}

void acceptWireFrame(const String &line) {
  // LILBOT|protocol|sequence|state|volume%|muted|musicBob|brightness|pixelShift|unread
  String fields[13];
  int start = 0;
  for (int i = 0; i < 13; ++i) {
    int separator = line.indexOf('|', start);
    if (separator < 0) separator = line.length();
    fields[i] = line.substring(start, separator);
    start = separator + 1;
  }
  if (fields[0] != "LILBOT" || fields[1] != "1" || fields[3].isEmpty()) {
    Serial.println("ERR:FRAME");
    return;
  }
  const String incomingState = fields[3];
  const float incomingVolume = constrain(fields[4].toInt(), 0, 100) / 100.0f;
  const bool incomingMuted = fields[5].toInt() != 0;
  const bool incomingMusicBob = fields[6].toInt() != 0;
  const bool incomingPixelShift = fields[8].toInt() != 0;
  const uint16_t incomingUnread = constrain(fields[9].toInt(), 0, 999);
  const String incomingClock = fields[10];
  const String incomingTemperature = fields[11];
  const String incomingLocation = fields[12];
  const bool visualChanged = incomingState != activeState ||
      incomingMusicBob != musicBob || incomingPixelShift != pixelShift ||
      incomingUnread != unreadNotifications || incomingClock != clockText ||
      incomingTemperature != temperatureText || incomingLocation != locationText ||
      (incomingState == "volume" &&
       (incomingMuted != volumeMuted || abs(incomingVolume - volumeLevel) >= 0.01f));
  sequence = static_cast<uint32_t>(fields[2].toInt());
  if (incomingState != activeState) stateChangedAt = millis();
  activeState = incomingState;
  volumeLevel = incomingVolume;
  volumeMuted = incomingMuted;
  musicBob = incomingMusicBob;
  setBrightness(constrain(fields[7].toInt(), 10, 100));
  pixelShift = incomingPixelShift;
  unreadNotifications = incomingUnread;
  clockText = incomingClock;
  temperatureText = incomingTemperature;
  locationText = incomingLocation;
  linked = true;
  lastFrameAt = millis();
  // Heartbeats keep the link alive without clearing a static LCD frame.
  if (visualChanged) lastRenderedState = "";
  Serial.printf("ACK:%lu:%s\n", static_cast<unsigned long>(sequence), activeState.c_str());
}

void pollSerial() {
  while (Serial.available()) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\n') {
      serialLine.trim();
      if (serialLine.startsWith("LILBOT|")) acceptWireFrame(serialLine);
      else if (serialLine.length()) acceptFrame(serialLine);
      serialLine = "";
    } else if (c != '\r' && serialLine.length() < 1024) {
      serialLine += c;
    }
  }
  if (millis() - lastHelloAt >= 1000) {
    lastHelloAt = millis();
    Serial.println("HELLO:LILBOT/1");
  }
}

bool touchPressed() {
  Wire.beginTransmission(TOUCH_ADDRESS);
  Wire.write(0x02);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(TOUCH_ADDRESS, static_cast<uint8_t>(1)) != 1) return false;
  return (Wire.read() & 0x0F) > 0;
}

void pollTouch() {
  static uint32_t lastPoll = 0;
  if (millis() - lastPoll < 25) return;
  lastPoll = millis();
  const bool pressed = touchPressed();
  if (pressed && !touchDown) {
    touchDown = true;
    touchStartedAt = millis();
  } else if (!pressed && touchDown) {
    touchDown = false;
    if (millis() - touchStartedAt >= 650) Serial.println("TOUCH:hold");
    else if (millis() - lastTapAt <= 320) {
      lastTapAt = 0;
      Serial.println("TOUCH:double");
    } else {
      lastTapAt = millis();
      Serial.println("TOUCH:tap");
    }
  }
}
}  // namespace

void setup() {
  pinMode(POWER_PIN, OUTPUT);
  digitalWrite(POWER_PIN, HIGH);
  pinMode(BACKLIGHT_PIN, OUTPUT);
  digitalWrite(BACKLIGHT_PIN, HIGH);
  delay(250);
  display->begin();
  display->setRotation(1);
  frameCanvas = new Arduino_Canvas(320, 170, display);
  if (frameCanvas && frameCanvas->begin(GFX_SKIP_OUTPUT_BEGIN)) {
    gfx = frameCanvas;
  }
  cyan = gfx->color565(25, 247, 255);
  pink = gfx->color565(255, 45, 170);
  purple = gfx->color565(139, 61, 255);
  cyanDark = gfx->color565(3, 48, 58);
  pinkDark = gfx->color565(55, 8, 35);
  purpleDark = gfx->color565(48, 25, 82);
  gfx->fillScreen(BLACK);
  ledcSetup(0, 5000, 8);
  ledcAttachPin(BACKLIGHT_PIN, 0);
  setBrightness(brightness);
  Wire.begin(TOUCH_SDA, TOUCH_SCL);
  pinMode(TOUCH_RESET, OUTPUT);
  digitalWrite(TOUCH_RESET, LOW);
  delay(5);
  digitalWrite(TOUCH_RESET, HIGH);
  Serial.begin(115200);
  randomSeed(esp_random());
  nextBlinkAt = millis() + random(1800, 4200);
  nextWinkAt = millis() + random(7000, 14000);
  stateChangedAt = millis();
  delay(100);
  Serial.println("READY:LILBOT/1");
}

void loop() {
  pollSerial();
  pollTouch();
  if (linked && millis() - lastFrameAt > LINK_TIMEOUT_MS) {
    linked = false;
    activeState = "reconnect";
  }
  drawFace();
  delay(2);
}
