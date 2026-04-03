/**
 * Swimming Timer - ESP32 Firmware
 * ================================
 * - 16 lane finish sensors (active-LOW with internal pull-up)
 * - 2 start buttons  (START_A and START_B for two heats/groups)
 * - 1 reset button   (resets all lanes and clears the server state)
 * - WiFi + HTTP to post events to the backend server
 *
 * Wiring (all buttons/sensors: one side → pin, other side → GND):
 *   Lane  1 → GPIO 4     Lane  9 → GPIO 25
 *   Lane  2 → GPIO 5     Lane 10 → GPIO 26
 *   Lane  3 → GPIO 13    Lane 11 → GPIO 27
 *   Lane  4 → GPIO 14    Lane 12 → GPIO 32
 *   Lane  5 → GPIO 15    Lane 13 → GPIO 33 (input-only, no pull-up – add 10 kΩ ext.)
 *   Lane  6 → GPIO 16    Lane 14 → GPIO 34 (input-only, no pull-up – add 10 kΩ ext.)
 *   Lane  7 → GPIO 17    Lane 15 → GPIO 35 (input-only, no pull-up – add 10 kΩ ext.)
 *   Lane  8 → GPIO 18    Lane 16 → GPIO 36 (input-only, no pull-up – add 10 kΩ ext.)
 *
 *   Start Button A → GPIO 19
 *   Start Button B → GPIO 21
 *   Reset Button   → GPIO 22
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ── WiFi credentials ─────────────────────────────────────────────────────────
// IMPORTANT: Replace with your actual WiFi credentials before flashing.
// Do NOT commit real credentials to source control.
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ── Backend server address ────────────────────────────────────────────────────
// Change to the IP / hostname where the Node.js server is running.
const char* SERVER_BASE = "http://192.168.1.100:3000";

// ── Hardware configuration ────────────────────────────────────────────────────
const int NUM_LANES = 16;

// Lane finish sensor pins (GPIO numbers, index 0 = lane 1 … index 15 = lane 16)
const int LANE_PINS[NUM_LANES] = {
     4,  5, 13, 14, 15, 16, 17, 18,  // lanes  1 – 8
    25, 26, 27, 32, 33, 34, 35, 36   // lanes  9 – 16
};

// GPIO 33-36 on ESP32 are input-only (no internal pull-up).
// For these pins, connect a 10 kΩ resistor from the pin to 3V3.
const int LANE_HAS_PULLUP[NUM_LANES] = {
    1, 1, 1, 1, 1, 1, 1, 1,  // lanes  1 –  8  (have pull-up)
    1, 1, 1, 1, 0, 0, 0, 0   // lanes  9 – 16  (33-36 = external pull-up)
};

const int BTN_START_A = 19;  // Start button for heat/group A
const int BTN_START_B = 21;  // Start button for heat/group B
const int BTN_RESET   = 22;  // Reset all lanes

// Debounce time in milliseconds
const unsigned long DEBOUNCE_MS = 50;

// ── Runtime state ─────────────────────────────────────────────────────────────
bool     laneFinished[NUM_LANES];
unsigned long laneFinishTime[NUM_LANES];  // millis() when lane finished
unsigned long startTime = 0;             // millis() when START was pressed
bool     raceRunning = false;
int      activeHeat  = 0;               // 1 = heat A, 2 = heat B

// Debounce tracking
unsigned long lastDebounce[NUM_LANES + 3];  // +3 for startA, startB, reset
int          lastRaw[NUM_LANES + 3];

// ── Helpers ───────────────────────────────────────────────────────────────────

bool isLowPressed(int pin, int idx) {
    int raw = digitalRead(pin);
    if (raw != lastRaw[idx]) {
        lastDebounce[idx] = millis();
        lastRaw[idx] = raw;
    }
    return (millis() - lastDebounce[idx] > DEBOUNCE_MS) && (raw == LOW);
}

void connectWiFi() {
    Serial.printf("Connecting to WiFi: %s\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\nConnected! IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\nWiFi connection failed – continuing offline.");
    }
}

// POST a JSON payload to the given path; returns HTTP status code.
int httpPost(const char* path, const char* body) {
    if (WiFi.status() != WL_CONNECTED) return -1;

    HTTPClient http;
    String url = String(SERVER_BASE) + path;
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(body);
    http.end();
    return code;
}

void sendStart(int heat) {
    // Build JSON: { "heat": 1, "startTime": <epoch ms via millis placeholder> }
    StaticJsonDocument<128> doc;
    doc["heat"] = heat;
    doc["startMillis"] = startTime;
    char body[128];
    serializeJson(doc, body);
    int code = httpPost("/api/start", body);
    Serial.printf("POST /api/start heat=%d → HTTP %d\n", heat, code);
}

void sendFinish(int lane, unsigned long elapsed) {
    StaticJsonDocument<128> doc;
    doc["lane"]       = lane + 1;  // 1-based
    doc["heat"]       = activeHeat;
    doc["elapsedMs"]  = elapsed;
    char body[128];
    serializeJson(doc, body);
    int code = httpPost("/api/finish", body);
    Serial.printf("POST /api/finish lane=%d elapsed=%lums → HTTP %d\n",
                  lane + 1, elapsed, code);
}

void sendReset() {
    int code = httpPost("/api/reset", "{}");
    Serial.printf("POST /api/reset → HTTP %d\n", code);
}

void startRace(int heat) {
    raceRunning = true;
    activeHeat  = heat;
    startTime   = millis();
    for (int i = 0; i < NUM_LANES; i++) {
        laneFinished[i]    = false;
        laneFinishTime[i]  = 0;
    }
    Serial.printf("=== RACE STARTED (heat %d) ===\n", heat);
    sendStart(heat);
}

void resetAll() {
    raceRunning = false;
    activeHeat  = 0;
    startTime   = 0;
    for (int i = 0; i < NUM_LANES; i++) {
        laneFinished[i]   = false;
        laneFinishTime[i] = 0;
    }
    Serial.println("=== RACE RESET ===");
    sendReset();
}

// ── Arduino lifecycle ─────────────────────────────────────────────────────────

void setup() {
    Serial.begin(115200);
    delay(200);

    // Lane finish sensors
    for (int i = 0; i < NUM_LANES; i++) {
        if (LANE_HAS_PULLUP[i]) {
            pinMode(LANE_PINS[i], INPUT_PULLUP);
        } else {
            pinMode(LANE_PINS[i], INPUT);  // external pull-up required
        }
        laneFinished[i]   = false;
        laneFinishTime[i] = 0;
        lastRaw[i]        = HIGH;
        lastDebounce[i]   = 0;
    }

    // Control buttons (internal pull-up)
    pinMode(BTN_START_A, INPUT_PULLUP);
    pinMode(BTN_START_B, INPUT_PULLUP);
    pinMode(BTN_RESET,   INPUT_PULLUP);
    lastRaw[NUM_LANES]     = HIGH;
    lastRaw[NUM_LANES + 1] = HIGH;
    lastRaw[NUM_LANES + 2] = HIGH;
    lastDebounce[NUM_LANES]     = 0;
    lastDebounce[NUM_LANES + 1] = 0;
    lastDebounce[NUM_LANES + 2] = 0;

    connectWiFi();
    Serial.println("Swimming Timer ready.");
}

// Edge-detection state (to trigger once per press)
bool prevStartA = false;
bool prevStartB = false;
bool prevReset  = false;
bool prevLane[NUM_LANES];

void loop() {
    // ── Start Button A ────────────────────────────────────────────────────────
    bool curStartA = isLowPressed(BTN_START_A, NUM_LANES);
    if (curStartA && !prevStartA && !raceRunning) {
        startRace(1);
    }
    prevStartA = curStartA;

    // ── Start Button B ────────────────────────────────────────────────────────
    bool curStartB = isLowPressed(BTN_START_B, NUM_LANES + 1);
    if (curStartB && !prevStartB && !raceRunning) {
        startRace(2);
    }
    prevStartB = curStartB;

    // ── Reset Button ──────────────────────────────────────────────────────────
    bool curReset = isLowPressed(BTN_RESET, NUM_LANES + 2);
    if (curReset && !prevReset) {
        resetAll();
    }
    prevReset = curReset;

    // ── Lane finish sensors ───────────────────────────────────────────────────
    if (raceRunning) {
        for (int i = 0; i < NUM_LANES; i++) {
            if (laneFinished[i]) continue;  // already recorded

            bool curLane = isLowPressed(LANE_PINS[i], i);
            if (curLane && !prevLane[i]) {
                unsigned long elapsed = millis() - startTime;
                laneFinished[i]   = true;
                laneFinishTime[i] = elapsed;
                Serial.printf("Lane %2d finished: %lu ms\n", i + 1, elapsed);
                sendFinish(i, elapsed);
            }
            prevLane[i] = curLane;
        }
    } else {
        // Keep prevLane in sync even when race is not running
        for (int i = 0; i < NUM_LANES; i++) {
            prevLane[i] = isLowPressed(LANE_PINS[i], i);
        }
    }

    delay(5);  // small yield to avoid WDT issues
}
