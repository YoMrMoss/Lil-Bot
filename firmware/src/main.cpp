#include <Arduino.h>
#include <ArduinoJson.h>
#include <Arduino_GFX_Library.h>
#include <Wire.h>

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
Arduino_GFX *gfx = new Arduino_ST7789(
    bus, 5, 0, true, 170, 320, 35, 0, 35, 0);

String activeState = "startup";
String serialLine;
uint32_t sequence = 0;
uint32_t lastFrameAt = 0;
uint32_t lastHelloAt = 0;
uint32_t lastDrawAt = 0;
uint32_t touchStartedAt = 0;
uint32_t lastTapAt = 0;
float volumeLevel = 0.5f;
bool volumeMuted = false;
bool musicBob = false;
bool pixelShift = true;
bool linked = false;
bool touchDown = false;
uint8_t brightness = 80;
uint16_t cyan;
uint16_t pink;
uint16_t purple;

void thickLine(int x1, int y1, int x2, int y2, uint16_t color, int width = 4) {
  for (int offset = -width / 2; offset <= width / 2; ++offset) {
    gfx->drawLine(x1, y1 + offset, x2, y2 + offset, color);
  }
}

void drawSmile(int x, int y, int size, uint16_t color) {
  gfx->drawArc(x, y - 8, size / 2, size / 2 - 4, 22, 158, color);
}

void drawBaseEyes(int yOffset = 0) {
  // Approved C2 geometry: large cyan light areas with pupils formed by absence.
  gfx->fillCircle(LEFT_EYE_X, EYE_Y + yOffset, EYE_SIZE / 2, cyan);
  gfx->fillCircle(RIGHT_EYE_X, EYE_Y + yOffset, EYE_SIZE / 2, cyan);
  gfx->fillCircle(LEFT_EYE_X, EYE_Y + yOffset, 12, BLACK);
  gfx->fillCircle(RIGHT_EYE_X, EYE_Y + yOffset, 12, BLACK);
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

void drawRaceVisor(int yOffset) {
  gfx->fillRoundRect(18, 48 + yOffset, 284, 70, 20, purple);
  gfx->drawRoundRect(18, 48 + yOffset, 284, 70, 20, cyan);
  thickLine(43, 54 + yOffset, 277, 54 + yOffset, pink, 5);
  thickLine(53, 87 + yOffset, 92, 70 + yOffset, cyan, 6);
  thickLine(92, 70 + yOffset, 72, 101 + yOffset, cyan, 6);
  thickLine(267, 87 + yOffset, 228, 70 + yOffset, cyan, 6);
  thickLine(228, 70 + yOffset, 248, 101 + yOffset, cyan, 6);
}

void drawGaming(int yOffset) {
  gfx->setTextSize(5);
  gfx->setTextColor(cyan);
  gfx->setCursor(30, 65 + yOffset);
  gfx->print("[+..");
  gfx->setTextColor(pink);
  gfx->print("oo]");
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
  if (millis() - lastDrawAt < 65) return;
  lastDrawAt = millis();
  int bob = musicBob ? -static_cast<int>((millis() / 125) % 3) * 2 : 0;
  int drift = pixelShift ? static_cast<int>((millis() / 25000) % 3) - 1 : 0;
  int yOffset = bob + drift;
  gfx->fillScreen(BLACK);

  if (activeState == "gaming") {
    drawGaming(yOffset);
  } else if (activeState == "browsing_fast") {
    drawRaceVisor(yOffset);
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
  } else if (activeState == "sleep") {
    drawClosedEyes(yOffset);
    thickLine(MOUTH_X - 17, MOUTH_Y + yOffset, MOUTH_X + 17, MOUTH_Y + yOffset, pink, 4);
  } else if (activeState == "music") {
    drawClosedEyes(yOffset, true);
    drawSmile(MOUTH_X, MOUTH_Y + yOffset, MOUTH_SIZE, pink);
  } else {
    drawBaseEyes(yOffset);
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
  if (!linked) gfx->fillCircle(308, 12, 3, purple);
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

void pollSerial() {
  while (Serial.available()) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\n') {
      serialLine.trim();
      if (serialLine.length()) acceptFrame(serialLine);
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
  gfx->begin();
  gfx->setRotation(1);
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
