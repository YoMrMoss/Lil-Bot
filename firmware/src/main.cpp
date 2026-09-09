#include <Arduino.h>
#include <Arduino_GFX_Library.h>

namespace {
constexpr uint8_t kBoardPower = 15;
constexpr uint8_t kBacklight = 38;

// This matches LILYGO's official T-Display-S3 Arduino_GFX example, including
// the Q peripheral driver and the panel's required 35-pixel column offsets.
Arduino_DataBus *bus = new Arduino_ESP32PAR8Q(
    7, 6, 8, 9,
    39, 40, 41, 42, 45, 46, 47, 48);
Arduino_GFX *gfx = new Arduino_ST7789(
    bus, 5, 0, true, 170, 320, 35, 0, 35, 0);
}

void setup() {
  pinMode(kBoardPower, OUTPUT);
  digitalWrite(kBoardPower, HIGH);
  pinMode(kBacklight, OUTPUT);
  digitalWrite(kBacklight, HIGH);
  delay(250);

  gfx->begin();
  gfx->setRotation(1);
  const uint16_t cyan = gfx->color565(25, 247, 255);
  const uint16_t pink = gfx->color565(255, 45, 170);
  gfx->fillScreen(BLACK);
  gfx->fillCircle(78, 75, 27, cyan);
  gfx->fillCircle(242, 75, 27, cyan);
  gfx->fillCircle(78, 75, 11, BLACK);
  gfx->fillCircle(242, 75, 11, BLACK);
  gfx->drawArc(160, 112, 28, 23, 25, 155, pink);
  gfx->fillCircle(308, 12, 4, pink);
}

void loop() {
  delay(1000);
}
