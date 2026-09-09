#include <Arduino.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <TFT_eSPI.h>
#include <Wire.h>

#include "face_assets.h"

namespace {
constexpr uint8_t kBoardPower = 15;
constexpr uint8_t kBacklight = 38;
constexpr uint8_t kTouchSda = 17;
constexpr uint8_t kTouchScl = 18;
constexpr uint8_t kTouchReset = 21;
constexpr uint8_t kTouchAddress = 0x15;
constexpr uint16_t kWidth = 320;
constexpr uint16_t kHeight = 170;
constexpr uint32_t kLinkTimeoutMs = 2500;
constexpr uint16_t kCyan = 0x07FF;
constexpr uint16_t kPink = 0xF81F;

TFT_eSPI tft;
Preferences settings;
String state = "startup";
uint32_t sequence = 0;
uint32_t lastFrameAt = 0;
uint32_t lastHelloAt = 0;
uint8_t brightness = 100;
bool musicBob = false;
bool pixelShift = true;
bool connected = false;
bool touchDown = false;
uint32_t touchStartedAt = 0;
uint32_t lastTapAt = 0;
String inputLine;

const FaceAsset *findFace(const String &name) {
  for (size_t i = 0; i < FACE_ASSET_COUNT; ++i) {
    if (name.equals(FACE_ASSETS[i].name)) return &FACE_ASSETS[i];
  }
  if (name == "music") return findFace("showoff");
  if (name == "gaming") return findFace("gaming");
  if (name == "rage") return findFace("rage");
  if (name == "crying") return findFace("crying");
  if (name == "nervous") return findFace("nervous");
  if (name == "helper" || name == "notification") return findFace("helper");
  return nullptr;
}

void setBrightness(uint8_t percent) {
  brightness = constrain(percent, 10, 100);
  // Keep first hardware validation simple and deterministic. PWM dimming is
  // enabled only after the specific board revision is confirmed.
  digitalWrite(kBacklight, brightness > 0 ? HIGH : LOW);
}

void renderFallback(const String &name, int dx, int dy) {
  uint16_t color = name == "error" ? kPink : kCyan;
  const int eyeY = 72 + dy;
  if (name == "sleep") {
    tft.drawFastHLine(62 + dx, eyeY, 54, color);
    tft.drawFastHLine(204 + dx, eyeY, 54, color);
  } else if (name == "typing" || name == "browsing") {
    tft.drawRoundRect(52 + dx, eyeY - 22, 62, 45, 8, color);
    tft.drawRoundRect(206 + dx, eyeY - 22, 62, 45, 8, color);
  } else {
    tft.fillCircle(84 + dx, eyeY, 24, color);
    tft.fillCircle(236 + dx, eyeY, 24, color);
  }
  tft.drawArc(160 + dx, 114 + dy, 24, 20, 20, 160, color, TFT_BLACK);
}

void renderAsset(const FaceAsset &face, int dx, int dy, uint16_t color) {
  const uint8_t *bits = face.data;
  for (uint16_t y = 0; y < face.height; ++y) {
    int run = -1;
    for (uint16_t x = 0; x <= face.width; ++x) {
      bool lit = false;
      if (x < face.width) {
        const uint32_t bit = static_cast<uint32_t>(y) * face.width + x;
        lit = pgm_read_byte(bits + (bit >> 3)) & (0x80 >> (bit & 7));
      }
      if (lit && run < 0) run = x;
      if (!lit && run >= 0) {
        tft.drawFastHLine(run + dx, y + dy, x - run, color);
        run = -1;
      }
    }
  }
}

void render() {
  static uint32_t lastRender = 0;
  if (millis() - lastRender < 33) return;
  lastRender = millis();
  int dy = musicBob ? static_cast<int>((millis() / 130) % 3) - 1 : 0;
  int dx = pixelShift ? static_cast<int>((millis() / 30000) % 3) - 1 : 0;
  tft.fillScreen(TFT_BLACK);
  tft.startWrite();
  const FaceAsset *face = findFace(state);
  if (face) renderAsset(*face, dx, dy, state == "rage" || state == "crying" ? kPink : kCyan);
  else renderFallback(state, dx, dy);
  if (!connected) {
    tft.fillCircle(307, 12, 4, kPink);
  }
  tft.endWrite();
}

bool readTouch(bool &pressed) {
  Wire.beginTransmission(kTouchAddress);
  Wire.write(0x02);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(kTouchAddress, static_cast<uint8_t>(1)) != 1) return false;
  pressed = (Wire.read() & 0x0F) > 0;
  return true;
}

void emitTouch(const char *gesture) {
  Serial.print("TOUCH:");
  Serial.println(gesture);
}

void pollTouch() {
  static uint32_t lastPoll = 0;
  if (millis() - lastPoll < 20) return;
  lastPoll = millis();
  bool pressed = false;
  if (!readTouch(pressed)) return;
  if (pressed && !touchDown) {
    touchDown = true;
    touchStartedAt = millis();
  } else if (!pressed && touchDown) {
    touchDown = false;
    uint32_t held = millis() - touchStartedAt;
    if (held >= 650) emitTouch("hold");
    else if (millis() - lastTapAt <= 320) {
      lastTapAt = 0;
      emitTouch("double");
    } else {
      lastTapAt = millis();
      emitTouch("tap");
    }
  }
}

void acceptFrame(const String &line) {
  StaticJsonDocument<768> doc;
  if (deserializeJson(doc, line)) return;
  if ((doc["protocol_version"] | 0) != 1) return;
  uint32_t incoming = doc["sequence"] | 0;
  if (incoming >= sequence) {
    sequence = incoming;
    state = String(static_cast<const char *>(doc["state"] | "idle"));
  }
  musicBob = doc["modifiers"]["music_bob"] | false;
  pixelShift = doc["modifiers"]["pixel_shift"] | true;
  setBrightness(doc["modifiers"]["brightness"] | brightness);
  lastFrameAt = millis();
  connected = true;
  Serial.print("ACK:");
  Serial.println(sequence);
}

void pollSerial() {
  while (Serial.available()) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n') {
      inputLine.trim();
      if (inputLine.length()) acceptFrame(inputLine);
      inputLine = "";
    } else if (c != '\r' && inputLine.length() < 1024) {
      inputLine += c;
    }
  }
  if (millis() - lastHelloAt >= 1000) {
    lastHelloAt = millis();
    Serial.println("HELLO:LILBOT/1");
  }
}
}  // namespace

void setup() {
  pinMode(kBoardPower, OUTPUT);
  digitalWrite(kBoardPower, HIGH);
  pinMode(kBacklight, OUTPUT);
  digitalWrite(kBacklight, HIGH);
  Serial.begin(115200);
  delay(350);
  Serial.println("BOOT:POWER_OK");
  tft.begin();
  Serial.println("BOOT:TFT_OK");
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  Wire.begin(kTouchSda, kTouchScl);
  Serial.println("BOOT:I2C_OK");
  pinMode(kTouchReset, OUTPUT);
  digitalWrite(kTouchReset, LOW);
  delay(5);
  digitalWrite(kTouchReset, HIGH);
  settings.begin("lilbot", false);
  setBrightness(settings.getUChar("brightness", 100));
  Serial.println("READY:LILBOT/1");
}

void loop() {
  pollSerial();
  pollTouch();
  if (connected && millis() - lastFrameAt > kLinkTimeoutMs) {
    connected = false;
    state = "reconnect";
  }
  render();
  delay(2);
}
