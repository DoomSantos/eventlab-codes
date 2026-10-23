@echo off
setlocal
cd /d "%~dp0"

if not exist "server\.admin_token" (
  echo Missing server\.admin_token — ask Lead to restore admin setup.
  pause
  exit /b 1
)

echo Players already claimed on the live board:
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$admin = (Get-Content -Raw 'server\.admin_token').Trim();" ^
  "try {" ^
  "  $r = Invoke-RestMethod -Method Get -Uri 'https://dsr-eventlab-timing-production.up.railway.app/v1/admin/players' -Headers @{ Authorization = ('Bearer ' + $admin) };" ^
  "  if (-not $r.players -or $r.players.Count -eq 0) { Write-Host 'No players yet.'; exit 0 }" ^
  "  $r.players | Format-Table display_name, lap_count, created_at -AutoSize" ^
  "} catch {" ^
  "  Write-Host $_.Exception.Message;" ^
  "  if ($_.ErrorDetails) { Write-Host $_.ErrorDetails.Message }" ^
  "  exit 1" ^
  "}"

echo.
echo Copy the display_name exactly when you run reissue-invite.bat
echo.
pause
