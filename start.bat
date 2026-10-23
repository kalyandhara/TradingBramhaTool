@echo off
title OmniRoute
REM Starts OmniRoute in the foreground.
REM Press Ctrl+C or close this window to stop it.

where omniroute >nul 2>&1
if errorlevel 1 (
  echo [ERROR] omniroute not found on PATH. Install with: npm i -g omniroute
  pause
  exit /b 1
)

echo Starting OmniRoute... (close this window or press Ctrl+C to stop)
call omniroute
echo.
echo OmniRoute stopped.
pause
