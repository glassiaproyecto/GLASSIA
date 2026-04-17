#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>

// ================== CONFIG WIFI ==================
const char* ssid = "SISTELCEL_CACERES_GALLEGOS";
const char* password = "capi2007";

//CAMBIA ESTA IP (tu computadora con Flask)
//const char* serverURL = "http://192.168.1.9:5000/data_oled";
const char* serverURL = "http://192.168.0.127:5000/data_oled";
// ================== OLED ==================
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// ================== I2C ==================
#define SDA_PIN 14
#define SCL_PIN 15

// ================== CAMERA ==================
#include "board_config.h"

void startCameraServer();

void setup() {
  Serial.begin(115200);

  // ===== OLED =====
  Wire.begin(SDA_PIN, SCL_PIN);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("Error OLED");
    return;
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);

  display.setCursor(0, 0);
  display.println("Iniciando...");
  display.display();


  // ===== CAMERA CONFIG =====
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_QVGA;
  config.pixel_format = PIXFORMAT_JPEG;

  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  if (psramFound()) {
    config.fb_count = 2;
  }

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Error camara");
    return;
  }

  // ===== WIFI =====
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);

  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("Conectando WiFi...");
  Serial.println("Conectando WiFi...");
  display.display();

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("WiFi OK");
  Serial.println("WiFi OK");
  display.println(WiFi.localIP());
  Serial.println(WiFi.localIP());
  display.display();

  startCameraServer();
}

// ================== LOOP ==================
void loop() {

  if (WiFi.status() == WL_CONNECTED) {

    HTTPClient http;
    http.begin(serverURL);

    int httpCode = http.GET();

    if (httpCode == 200) {
      String payload = http.getString();

      DynamicJsonDocument doc(512);
      deserializeJson(doc, payload);

      String nombre = doc["nombre"] | "N/A";
      int confianza = doc["confianza"] | 0;
      String funcion = doc["funcion"] | "";

      // ===== MOSTRAR EN OLED =====
      display.clearDisplay();

      display.setCursor(0, 0);
      display.println(nombre);   // Línea 1

      display.print("Conf:");
      display.print(confianza);
      display.println("%");      // Línea 2

      display.println("");       // Espacio

      // Reducimos texto (máx 2 líneas)
      display.println(funcion.substring(0, 20));
      display.println(funcion.substring(20, 40));

      display.display();

    } else {
      display.clearDisplay();
      display.setCursor(0, 0);
      display.println("Error servidor");
      display.display();
    }

    http.end();
  }

  delay(2500); // 🔥 importante (no saturar)
}