/*
 * WaveRadar — ESP32 CSI streamer
 * ------------------------------
 * Connects to your Wi-Fi network, keeps light traffic flowing (pings the
 * gateway) and streams raw Channel State Information over USB serial,
 * one line per received frame:
 *
 *     CSI_DATA,<rssi>,<n_pairs>,[i0,q0,i1,q1,...]
 *
 * Flash with the Arduino IDE (board: any ESP32 dev module) or arduino-cli,
 * open the WaveRadar app with:  python -m waveradar --source esp32
 *
 * Author:  Joaquim Pedro de Morais Filho <j360074@hotmail.com>
 * License: MIT
 */

#include <WiFi.h>
#include <ESP32Ping.h>          // library: "ESP32Ping" (optional, see below)
#include "esp_wifi.h"

// ---- EDIT THESE ------------------------------------------------------------
const char *WIFI_SSID = "YOUR_WIFI_NAME";
const char *WIFI_PASS = "YOUR_WIFI_PASSWORD";
// ----------------------------------------------------------------------------

static const uint32_t BAUD = 921600;
static const uint32_t TRAFFIC_INTERVAL_MS = 50;   // keep ~20 pkt/s flowing

static void csi_rx_cb(void *ctx, wifi_csi_info_t *info) {
  if (!info || !info->buf || info->len == 0) return;

  Serial.printf("CSI_DATA,%d,%d,[", info->rx_ctrl.rssi, info->len / 2);
  const int8_t *b = info->buf;
  for (int i = 0; i < info->len; i++) {
    Serial.print(b[i]);
    if (i < info->len - 1) Serial.print(',');
  }
  Serial.println(']');
}

void setup() {
  Serial.begin(BAUD);
  delay(300);
  Serial.println("# WaveRadar CSI firmware — waveradar by Joaquim Pedro de Morais Filho");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("# connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print('.');
  }
  Serial.printf("\n# connected: %s  rssi=%d dBm\n",
                WiFi.localIP().toString().c_str(), WiFi.RSSI());

  // Enable CSI capture
  wifi_csi_config_t cfg = {};
  cfg.lltf_en          = true;   // legacy long training field
  cfg.htltf_en         = true;   // HT LTF (802.11n)
  cfg.stbc_htltf2_en   = true;
  cfg.ltf_merge_en     = true;
  cfg.channel_filter_en = false;
  cfg.manu_scale       = false;
  ESP_ERROR_CHECK(esp_wifi_set_csi_config(&cfg));
  ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(csi_rx_cb, nullptr));
  ESP_ERROR_CHECK(esp_wifi_set_csi(true));
  Serial.println("# CSI enabled");
}

void loop() {
  // CSI is only produced when frames are received; ping the gateway so the
  // AP answers continuously.  If you don't want the ESP32Ping library,
  // replace this block with any periodic UDP/TCP traffic.
  static uint32_t last = 0;
  if (millis() - last >= TRAFFIC_INTERVAL_MS) {
    last = millis();
    Ping.ping(WiFi.gatewayIP(), 1);
  }
}
