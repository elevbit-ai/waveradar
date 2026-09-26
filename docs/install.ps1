# WaveRadar one-line installer (Windows)
#   irm https://elevbit-ai.github.io/waveradar/install.ps1 | iex
#
# Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>

$ErrorActionPreference = "Stop"
Write-Host ""
Write-Host "  WaveRadar — Wi-Fi sensing motion radar" -ForegroundColor Green
Write-Host "  (c) 2026 Joaquim Pedro de Morais Filho" -ForegroundColor DarkGreen
Write-Host ""

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Python 3.9+ is required. Install it from https://python.org and re-run." -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/2] Installing waveradar from GitHub..." -ForegroundColor Cyan
python -m pip install --upgrade --quiet "waveradar[esp32] @ git+https://github.com/elevbit-ai/waveradar.git"

Write-Host "[2/2] Starting the radar (your router's Wi-Fi signal)..." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Run it again anytime with:  waveradar" -ForegroundColor Green
Write-Host "  No hardware demo:           waveradar --source sim" -ForegroundColor Green
Write-Host "  ESP32 CSI mode:             waveradar --source esp32" -ForegroundColor Green
Write-Host ""
python -m waveradar
