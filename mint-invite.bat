@echo off
setlocal
cd /d "%~dp0"

if not exist "server\.admin_token" (
  echo Missing server\.admin_token — ask Lead to restore admin setup.
  pause
  exit /b 1
)

echo Creating a new invite on Railway...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$admin = (Get-Content -Raw 'server\.admin_token').Trim();" ^
  "$r = Invoke-RestMethod -Method Post -Uri 'https://dsr-eventlab-timing-production.up.railway.app/v1/admin/invites' -Headers @{ Authorization = ('Bearer ' + $admin) } -ContentType 'application/json' -Body '{}';" ^
  "Write-Host ''; Write-Host 'INVITE CODE:' $r.invite_code; Write-Host '';" ^
  "Add-Content -Path 'server\.invites.txt' -Value ('minted=' + $r.invite_code + ' @ ' + (Get-Date -Format o))"

echo.
echo Copy the INVITE CODE above and send it to your friend.
echo It was also appended to server\.invites.txt
echo.
pause
