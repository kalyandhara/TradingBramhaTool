@echo off
title Screener.in Session - reuse your default browser profile
cd /d "%~dp0"

echo Reuses your DEFAULT browser's screener.in session (SSO, no re-login, no admin).
echo Your browser must be CLOSED so its profile is not locked.
echo.
echo   1) Make sure you are logged into screener.in in your browser.
echo   2) CLOSE the browser completely - check the system tray / background.
echo.
pause

py -3 "%~dp0tools\screener_login.py" --use-profile

echo.
echo If it said the browser is still running, close it fully (tray too) and re-run.
echo Force a specific browser:  py -3 tools\screener_login.py --use-profile --browser edge
echo One-time login window fallback:  py -3 tools\screener_login.py
echo.
pause
