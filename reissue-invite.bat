@echo off
setlocal
cd /d "%~dp0"

if not exist "server\.admin_token" (
  echo Missing server\.admin_token — ask Lead to restore admin setup.
  pause
  exit /b 1
)

echo Replacement invite for a player who already has a display name.
echo Use this when they got a new PC or reset the collector.
echo Type their name EXACTLY as it appears on Live Timing / Leaderboards.
echo.
set /p NAME=Display name: 
if "%NAME%"=="" (
  echo No name entered.
  pause
  exit /b 1
)

echo.
echo Creating a replacement invite on Railway for %NAME%...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$admin = (Get-Content -Raw 'server\.admin_token').Trim();" ^
  "$name = $env:NAME.Trim();" ^
  "$body = @{ display_name = $name } | ConvertTo-Json -Compress;" ^
  "try {" ^
  "  $r = Invoke-RestMethod -Method Post -Uri 'https://dsr-eventlab-timing-production.up.railway.app/v1/admin/invites' -Headers @{ Authorization = ('Bearer ' + $admin) } -ContentType 'application/json' -Body $body;" ^
  "  if (-not $r.reclaim) { throw 'Live API is not updated yet for replacement invites. Redeploy Railway first.' }" ^
  "  Write-Host ''; Write-Host ('INVITE CODE: ' + $r.invite_code);" ^
  "  Write-Host ('DISPLAY NAME: ' + $r.display_name);" ^
  "  Write-Host '';" ^
  "  Add-Content -Path 'server\.invites.txt' -Value ('reissue=' + $r.invite_code + ' name=' + $r.display_name + ' @ ' + (Get-Date -Format o))" ^
  "} catch {" ^
  "  Write-Host ''; Write-Host $_.Exception.Message;" ^
  "  if ($_.ErrorDetails) { Write-Host $_.ErrorDetails.Message }" ^
  "  exit 1" ^
  "}"

if errorlevel 1 (
  echo.
  echo Could not mint a replacement. Check the name with list-players.bat
  echo and that Railway is running.
  pause
  exit /b 1
)

echo.
echo Send that INVITE CODE to the player.
echo They claim it with the SAME display name. Old times stay on the board.
echo It was also appended to server\.invites.txt
echo.
pause
