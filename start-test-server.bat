@echo off
setlocal
cd /d "%~dp0"

echo Starting local timing API on http://127.0.0.1:8787
echo Keep this window open while testing.
echo.

python -m server --port 8787
if errorlevel 1 (
  echo.
  echo Server failed — is Python installed and are you in the project folder?
  pause
)
