@echo off
setlocal
cd /d "%~dp0"

echo Starting TEST collector (source build — captures save under collector\captures\)
echo UDP Data Out port: 9876
echo Web UI:            http://127.0.0.1:8765
echo Timing API:        http://127.0.0.1:8787  (run start-test-server.bat first)
echo.
echo Tip: open http://127.0.0.1:8765/?lab=1 for path-capture / research tools.
echo Tip: run mint-invite-test.bat if you need a fresh local invite.
echo.

start "" "http://127.0.0.1:8765"
python -m collector --port 9876 --web-port 8765 --api-url http://127.0.0.1:8787
if errorlevel 1 (
  echo.
  echo Collector failed — is Python installed and are you in the project folder?
  pause
)
