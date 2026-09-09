#include <Arduino.h>
#include <TFT_eSPI.h>

namespace {
constexpr uint8_t kBoardPower = 15;
constexpr uint8_t kBacklight = 38;
constexpr uint16_t kCyan = 0x07FF;
constexpr uint16_t kPink = 0xF81F;
TFT_eSPI tft;
}

void setup() {
  // Minimal hardware diagnostic: no USB serial, touch, preferences, watchdog,
  // networking, animation, or companion communication.
  pinMode(kBoardPower, OUTPUT);
  digitalWrite(kBoardPower, HIGH);
  pinMode(kBacklight, OUTPUT);
  digitalWrite(kBacklight, HIGH);
  delay(250);

  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.fillCircle(78, 75, 27, kCyan);
  tft.fillCircle(242, 75, 27, kCyan);
  tft.fillCircle(78, 75, 11, TFT_BLACK);
  tft.fillCircle(242, 75, 11, TFT_BLACK);
  tft.drawArc(160, 112, 28, 23, 25, 155, kPink, TFT_BLACK);
  tft.fillCircle(308, 12, 4, kPink);
}

void loop() {
  delay(1000);
}
