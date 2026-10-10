# WaveRadar for Windows - build
# Criado por Joaquim Pedro de Morais Filho - j360074@hotmail.com
#
# Compila o WaveRadar.exe e (se o Windows SDK estiver instalado) empacota o MSIX.
#   powershell -ExecutionPolicy Bypass -File build.ps1
param([switch]$Assinar)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$csc = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"

Write-Host "Compilando WaveRadar.exe..." -ForegroundColor Cyan
& $csc /nologo /target:winexe /out:"$here\WaveRadar.exe" `
    /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.dll "$here\WaveRadar.cs"
if (!(Test-Path "$here\WaveRadar.exe")) { throw "Falha ao compilar." }
Write-Host "OK: $here\WaveRadar.exe" -ForegroundColor Green

# MSIX (opcional) - precisa do makeappx (Windows 10/11 SDK)
$ma = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\makeappx.exe" -ErrorAction SilentlyContinue |
      Sort-Object FullName -Descending | Select-Object -First 1
if (-not $ma) { Write-Host "makeappx nao encontrado - pulei o MSIX (instale o Windows SDK)." -ForegroundColor Yellow; return }

$stage = "$here\_pkg"
New-Item -ItemType Directory -Path "$stage\Assets" -Force | Out-Null
Copy-Item "$here\WaveRadar.exe" "$stage\" -Force
Copy-Item "$here\msix\AppxManifest.xml" "$stage\" -Force
Copy-Item "$here\msix\Assets\*.png" "$stage\Assets\" -Force
$msix = "$here\WaveRadar-1.0.0.0.msix"
& $ma.FullName pack /d $stage /p $msix /o
Write-Host "MSIX: $msix" -ForegroundColor Green
Write-Host "Para a Store: troque Identity Name/Publisher no AppxManifest.xml pelos valores do Partner Center e gere de novo." -ForegroundColor Cyan
