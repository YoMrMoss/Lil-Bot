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

const FaceAsset *findFaceAsset(const String &name) {
  for (size_t i = 0; i < FACE_ASSET_COUNT; ++i) {
    if (name == FACE_ASSETS[i].name) return &FACE_ASSETS[i];
  }
  return nullptr;
}

bool drawAssetFace(const String &name, int yOffset, uint16_t color) {
  const FaceAsset *asset = findFaceAsset(name);
  if (!asset) return false;
  gfx->drawBitmap(0, yOffset, asset->data, asset->width, asset->height, color);
  return true;
}

void thickLine(int x1, int y1, int x2, int y2, uint16_t color, int width = 4) {
  for (int offset = -width / 2; offset <= width / 2; ++offset) {
    gfx->drawLine(x1, y1 + offset, x2, y2 + offset, color);
  }
}

void drawSmile(int x, int y, int size, uint16_t color) {
  // A filled lower half-circle reads as a warm, open emoticon smile.
  const int radius = size / 2;
  gfx->fillCircle(x, y - 8, radius, color);
  gfx->fillRect(x - radius - 1, y - radius - 9, size + 2, radius + 1, BLACK);
}

void drawBaseEyes(int yOffset = 0, int gazeX = 0) {
  // Approved simulator geometry: solid cyan emoticon dots, without pupils.
  gfx->fillCircle(LEFT_EYE_X + gazeX, EYE_Y + yOffset, EYE_SIZE / 2, cyan);
  gfx->fillCircle(RIGHT_EYE_X + gazeX, EYE_Y + yOffset, EYE_SIZE / 2, cyan);
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
  gfx->drawRoundRect(35, 57 + yOffset, 67, 55, 8, cyan);
  gfx->drawRoundRect(218, 57 + yOffset, 67, 55, 8, cyan);
  thickLine(102, 78 + yOffset, 218, 78 + yOffset, pink, 3);
  thickLine(35, 68 + yOffset, 15, 61 + yOffset, pink, 3);
  thickLine(285, 68 + yOffset, 305, 61 + yOffset, pink, 3);
}

void drawRaceVisor(int yOffset, float progress) {
  // Compact helmet: retain the bot's face and slide a visor into place.
  const int slide = static_cast<int>((1.0f - progress) * -64.0f);
  gfx->drawRoundRect(28, 27 + yOffset, 264, 112, 32, pink);
  gfx->drawRoundRect(30, 29 + yOffset, 260, 108, 30, pink);
  gfx->fillRect(156, 29 + yOffset, 8, 27, pink);
  gfx->fillRoundRect(34, 48 + yOffset + slide, 252, 62, 16, purple);
  gfx->drawRoundRect(34, 48 + yOffset + slide, 252, 62, 16, cyan);
  gfx->drawRoundRect(35, 49 + yOffset + slide, 250, 60, 15, cyan);
  // Excited eyes remain visible behind the visor.
  thickLine(65, 78 + yOffset + slide, 91, 68 + yOffset + slide, cyan, 6);
  thickLine(91, 68 + yOffset + slide, 78, 91 + yOffset + slide, cyan, 6);
  thickLine(255, 78 + yOffset + slide, 229, 68 + yOffset + slide, cyan, 6);
  thickLine(229, 68 + yOffset + slide, 242, 91 + yOffset + slide, cyan, 6);
  // Edge streaks give speed without covering the expression.
  const int streak = (millis() / 55) % 18;
  thickLine(2, 61 + streak, 23, 61 + streak, cyan, 3);
  thickLine(297, 92 - streak, 318, 92 - streak, pink, 3);
}

void drawGaming(int yOffset) {
  gfx->setTextSize(5);
  gfx->setTextColor(cyan);
  gfx->setCursor(30, 65 + yOffset);
  gfx->print("[+..");
  gfx->setTextColor(pink);
  gfx->print("oo]");
}

void drawVerticalEyes(int yOffset) {
  gfx->fillRoundRect(LEFT_EYE_X - 8, EYE_Y - 24 + yOffset, 16, 48, 5, cyan);
  gfx->fillRoundRect(RIGHT_EYE_X - 8, EYE_Y - 24 + yOffset, 16, 48, 5, cyan);
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
  const bool blinkNow = activeState == "idle" && now < blinkUntil;
  const bool winkNow = activeState == "idle" && !blinkNow && now < winkUntil;
  const bool quietMotion = brightness <= 20;
  const bool animated = musicBob || activeState == "music" ||
                        activeState == "loading" || activeState == "reconnect" ||
                        activeState == "browsing_fast" ||
                        blinkNow != lastBlink || winkNow != lastWink;
  if (animated && millis() - lastDrawAt < 90) return;
  int bobStrength = quietMotion ? 1 : 2 + static_cast<int>(volumeLevel * 2.0f);
  int bob = musicBob ? -static_cast<int>((millis() / 125) % 3) * bobStrength : 0;
  int drift = pixelShift ? static_cast<int>((millis() / 25000) % 3) - 1 : 0;
  int yOffset = bob + drift;
  int gazeX = (activeState == "idle" && !quietMotion)
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
    if (!drawAssetFace("gaming", yOffset, cyan)) drawGaming(yOffset);
  } else if (activeState == "browsing_fast") {
    float progress = constrain((now - stateChangedAt) / 420.0f, 0.0f, 1.0f);
    drawRaceVisor(yOffset, progress);
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
  } else if (activeState == "sleep") {
    drawClosedEyes(yOffset);
    thickLine(MOUTH_X - 17, MOUTH_Y + yOffset, MOUTH_X + 17, MOUTH_Y + yOffset, pink, 4);
  } else if (activeState == "music") {
    drawClosedEyes(yOffset, true);
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
  } else if (activeState == "typing") {
    drawVerticalEyes(yOffset);
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
  } else if (activeState == "notification") {
    drawBaseEyes(yOffset);
    gfx->fillRect(RIGHT_EYE_X - 24, EYE_Y - 3 + yOffset, 48, 7, BLACK);
    drawBarEye(RIGHT_EYE_X, yOffset);
    drawOMouth(yOffset);
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
    gfx->fillCircle(RIGHT_EYE_X, EYE_Y + yOffset, EYE_SIZE / 2, cyan);
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
  } else if (activeState == "reconnect") {
    drawCircleEye(LEFT_EYE_X, yOffset);
    gfx->fillCircle(RIGHT_EYE_X, EYE_Y + yOffset, EYE_SIZE / 2, cyan);
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
  } else if (activeState == "cat" || activeState == "helper" ||
             activeState == "showoff" || activeState == "crying" ||
             activeState == "nervous" || activeState == "rage") {
    drawAssetFace(activeState, yOffset,
                  (activeState == "crying" || activeState == "rage") ? pink : cyan);
  } else {
    if (activeState == "idle" && (blinkNow || winkNow)) {
      if (blinkNow) {
        drawBarEye(LEFT_EYE_X, yOffset);
        drawBarEye(RIGHT_EYE_X, yOffset);
      } else {
        gfx->fillCircle(LEFT_EYE_X, EYE_Y + yOffset, EYE_SIZE / 2, cyan);
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
  if (frameCanvas && gfx == frameCanvas) frameCanvas->flush();
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
  purple = gfx->color565(48, 25, 82);
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
