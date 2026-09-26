# ESP32 CSI firmware

This firmware turns a **$4 ESP32 dev board** into a true CSI (Channel State
Information) probe for WaveRadar: one amplitude + phase per OFDM subcarrier,
~50–100 measurements per second, streamed over USB serial.

## Flashing (Arduino IDE — easiest)

1. Install the [Arduino IDE](https://www.arduino.cc/en/software) and add the
   ESP32 board package (`Boards Manager → esp32 by Espressif`).
2. Install the **ESP32Ping** library (`Library Manager → ESP32Ping`).
3. Open `waveradar_csi/waveradar_csi.ino`, set `WIFI_SSID` / `WIFI_PASS`
   to your network, select your board + COM port and click **Upload**.
4. Run the app:

   ```
   python -m waveradar --source esp32
   ```

   The serial port is auto-detected; use `--serial COM5` (Windows) or
   `--serial /dev/ttyUSB0` (Linux) to pick one explicitly.

## Line format

```
CSI_DATA,<rssi>,<n_pairs>,[i0,q0,i1,q1,...]
```

Each `(i, q)` pair is one subcarrier: amplitude = √(i²+q²),
phase = atan2(i, q). WaveRadar's parser also accepts the CSV emitted by
Espressif's official [`esp-csi`](https://github.com/espressif/esp-csi)
examples, so you can use that project's firmware instead if you prefer.

## Notes

- CSI is only generated when the ESP32 *receives* frames, so the firmware
  pings the gateway ~20×/s to keep traffic flowing.
- 802.11n (2.4 GHz, HT20) gives ~52 usable subcarriers — plenty for motion
  and micro-Doppler analysis.

—
Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com> · MIT License
