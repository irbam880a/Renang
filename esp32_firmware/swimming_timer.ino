/*
 * Swimming Competition Timer – ESP32 Firmware
 * =============================================
 * Communicates with the Python GUI over USB-Serial (115200 baud).
 *
 * Protocol (newline-terminated):
 *   PC -> ESP32 :  START          – start all timers
 *                  RESET          – reset all timers
 *                  STOP:<N>       – stop lane N from PC side
 *                  PING           – connection test
 *
 *   ESP32 -> PC :  STARTED        – timer is running
 *                  RESET_OK       – reset acknowledged
 *                  LANE:<N>:TIME:<ms> – lane N finished at <ms> milliseconds
 *                  PONG           – response to PING
 *
 * Hardware:
 *   - 1 × Start button on START_BTN_PIN (active LOW, internal pull-up)
 *   - Up to 16 × Lane sensor/button on LANE_PINS[0..15] (active LOW)
 *   - Optional: status LED on LED_PIN
 *
 * Tested on ESP32 DevKit V1 / ESP32-WROOM-32.
 */

#include <Arduino.h>

// ── Pin definitions ──────────────────────────────────────────────────────────
#define START_BTN_PIN   0          // BOOT button on most DevKit boards
#define LED_PIN         2          // Built-in LED
#define MAX_LANES       16

// Lane sensor pins – adjust to your wiring (must be valid GPIO input pins)
const int LANE_PINS[MAX_LANES] = {
  4, 5, 13, 14, 15, 16, 17, 18,
  19, 21, 22, 23, 25, 26, 27, 32
};

// ── Runtime state ────────────────────────────────────────────────────────────
static bool  running           = false;
static unsigned long startMs   = 0;
static bool  laneStopped[MAX_LANES];
static bool  prevLaneState[MAX_LANES];
static bool  prevStartState    = HIGH;

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  pinMode(START_BTN_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);

  for (int i = 0; i < MAX_LANES; i++) {
    pinMode(LANE_PINS[i], INPUT_PULLUP);
    laneStopped[i]   = false;
    prevLaneState[i] = HIGH;
  }

  digitalWrite(LED_PIN, LOW);
  Serial.println("READY");
}

// ── Start race ────────────────────────────────────────────────────────────────
void startRace() {
  running = true;
  startMs = millis();
  for (int i = 0; i < MAX_LANES; i++) {
    laneStopped[i] = false;
  }
  digitalWrite(LED_PIN, HIGH);
  Serial.println("STARTED");
}

// ── Reset all ─────────────────────────────────────────────────────────────────
void resetAll() {
  running = false;
  startMs = 0;
  for (int i = 0; i < MAX_LANES; i++) {
    laneStopped[i] = false;
  }
  digitalWrite(LED_PIN, LOW);
  Serial.println("RESET_OK");
}

// ── Stop a specific lane ──────────────────────────────────────────────────────
void stopLane(int lane) {               // lane is 1-based
  int idx = lane - 1;
  if (idx < 0 || idx >= MAX_LANES) return;
  if (!running || laneStopped[idx]) return;
  laneStopped[idx] = true;
  unsigned long elapsed = millis() - startMs;
  Serial.print("LANE:");
  Serial.print(lane);
  Serial.print(":TIME:");
  Serial.println(elapsed);
}

// ── Handle serial commands from PC ────────────────────────────────────────────
void handleSerial() {
  static String buf = "";
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      buf.trim();
      if (buf.length() > 0) {
        if (buf == "START") {
          startRace();
        } else if (buf == "RESET") {
          resetAll();
        } else if (buf == "PING") {
          Serial.println("PONG");
        } else if (buf.startsWith("STOP:")) {
          int lane = buf.substring(5).toInt();
          stopLane(lane);
        }
        buf = "";
      }
    } else {
      buf += c;
    }
  }
}

// ── Main loop ─────────────────────────────────────────────────────────────────
void loop() {
  handleSerial();

  // Physical start button (falling edge)
  bool startState = digitalRead(START_BTN_PIN);
  if (prevStartState == HIGH && startState == LOW) {
    if (!running) {
      startRace();
    }
  }
  prevStartState = startState;

  if (!running) return;

  // Check lane sensors (falling edge = swimmer touched pad)
  for (int i = 0; i < MAX_LANES; i++) {
    if (laneStopped[i]) continue;
    bool state = digitalRead(LANE_PINS[i]);
    if (prevLaneState[i] == HIGH && state == LOW) {
      stopLane(i + 1);   // convert to 1-based
    }
    prevLaneState[i] = state;
  }

  // Blink LED while running
  unsigned long elapsed = millis() - startMs;
  digitalWrite(LED_PIN, (elapsed / 250) % 2 == 0 ? HIGH : LOW);

  delay(1);  // small yield to prevent watchdog issues
}
