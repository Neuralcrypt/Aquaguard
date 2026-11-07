
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Configure these values locally. Never commit real credentials.
const char* WIFI_SSID = "CHANGE_ME";
const char* WIFI_PASSWORD = "CHANGE_ME";
const char* API_URL = "http://192.168.1.10:8000/api/readings";

const char* ROOM_ID = "ROOM-101";
const char* SENSOR_ID = "SENSOR-101";

constexpr int FLOW_PIN = 27;
constexpr float PULSES_PER_LITRE = 450.0f;
constexpr unsigned long SAMPLE_INTERVAL_MS = 5000;

volatile uint32_t pulseCount = 0;
unsigned long lastSampleMs = 0;
uint32_t sequenceNumber = 0;

void IRAM_ATTR onFlowPulse() {
    pulseCount++;
}

void connectWiFi() {
    if (WiFi.status() == WL_CONNECTED) return;

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    const unsigned long start = millis();

    while (WiFi.status() != WL_CONNECTED &&
           millis() - start < 15000) {
        delay(300);
        Serial.print('.');
    }

    Serial.println(
        WiFi.status() == WL_CONNECTED
            ? "\nWi-Fi connected"
            : "\nWi-Fi not connected; will retry"
    );
}

void setup() {
    Serial.begin(115200);

    pinMode(FLOW_PIN, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(FLOW_PIN),
                    onFlowPulse, RISING);

    connectWiFi();
    lastSampleMs = millis();
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        connectWiFi();
    }

    const unsigned long now = millis();

    if (now - lastSampleMs < SAMPLE_INTERVAL_MS) {
        delay(20);
        return;
    }

    const unsigned long elapsedMs = now - lastSampleMs;

    noInterrupts();
    uint32_t pulses = pulseCount;
    pulseCount = 0;
    interrupts();

    const float litres = pulses / PULSES_PER_LITRE;
    const float minutes = elapsedMs / 60000.0f;
    const float flowLpm = minutes > 0 ? litres / minutes : 0;

    sequenceNumber++;

    Serial.printf(
        "pulses=%lu interval_litres=%.3f flow_lpm=%.3f\n",
        (unsigned long)pulses, litres, flowLpm
    );

    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;

        http.begin(API_URL);
        http.addHeader("Content-Type", "application/json");

        StaticJsonDocument<384> doc;

        doc["room_id"] = ROOM_ID;
        doc["sensor_id"] = SENSOR_ID;
        doc["device_sequence"] = String("esp32-") + String(sequenceNumber);
        doc["flow_rate_lpm"] = flowLpm;
        doc["interval_volume_litres"] = litres;

        String body;
        serializeJson(doc, body);

        const int status = http.POST(body);

        Serial.printf("API response: %d\n", status);

        http.end();
    }

    lastSampleMs = now;
}
