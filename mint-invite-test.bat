@echo off
setlocal
cd /d "%~dp0"

echo Creating a new invite on the LOCAL test server DB...
echo (API should be running via start-test-server.bat, or at least use the same project folder.)
echo.

for /f "usebackq delims=" %%I in (`python -m server --create-invite`) do set "INVITE=%%I"

if not defined INVITE (
  echo Failed to mint invite — is Python working in this folder?
  pause
  exit /b 1
)

echo.
echo INVITE CODE: %INVITE%
echo.
echo Paste that into the test collector Claim box with your display name.
echo.

>> "server\.invites-test.txt" echo minted=%INVITE% local @ %DATE% %TIME%
echo Also saved to server\.invites-test.txt
echo.
pause
