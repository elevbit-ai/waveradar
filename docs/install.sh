#!/usr/bin/env bash
# WaveRadar one-line installer (Linux / macOS)
#   curl -fsSL https://elevbit-ai.github.io/waveradar/install.sh | bash
#
# Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
set -euo pipefail

echo
echo "  WaveRadar — Wi-Fi sensing motion radar"
echo "  (c) 2026 Joaquim Pedro de Morais Filho"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.9+ is required (sudo apt install python3 python3-pip)." >&2
  exit 1
fi

echo "[1/2] Installing waveradar from GitHub..."
python3 -m pip install --upgrade --quiet \
  "waveradar[esp32] @ git+https://github.com/elevbit-ai/waveradar.git"

echo "[2/2] Starting the radar (your router's Wi-Fi signal)..."
echo
echo "  Run it again anytime with:  waveradar"
echo "  No hardware demo:           waveradar --source sim"
echo "  ESP32 CSI mode:             waveradar --source esp32"
echo
python3 -m waveradar
