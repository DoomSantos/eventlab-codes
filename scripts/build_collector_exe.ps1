# Build friend-ready collector (run from repo root)
# Usage: powershell -File scripts/build_collector_exe.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
  python -m pip install pyinstaller
}

Write-Host "Building DSR-Lap-Collector (onedir)..."
pyinstaller --noconfirm --clean "collector/collector.spec"

$Out = Join-Path $Root "dist\DSR-Lap-Collector"
Write-Host "Done: $Out"
Write-Host "Zip that folder and send it with an invite code."
