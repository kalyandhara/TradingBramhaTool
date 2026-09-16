@echo off
setlocal
title Trading Bramha - Desk launcher
set "REPO=%~dp0"
set "PORT=8760"
REM The interpreter .claude\launch.json uses. If Python moves, change it in BOTH
REM (and in run_tests.bat, which a test asserts agrees with launch.json).
set "PYTHON=C:\Users\Owner\AppData\Local\Programs\Python\Python314\python.exe"
set "PYTHONIOENCODING=utf-8"

REM ── B-84 ────────────────────────────────────────────────────────────────────
REM
REM This repo ships THREE apps and, until now, a .bat for only one of them:
REM
REM   dashboard_app.py           the DESK      Streamlit  :8760   <- this file
REM   dash_trading_dashboard.py  SBC / astro   Dash       :8050   <- start.bat
REM   sbc_app.py                 SBC (older)   Streamlit  ----    launched by nothing
REM
REM start.bat launches the SBC dashboard and says so in its own title, so it was
REM never mislabelled -- the gap was that the desk, the thing used daily, could
REM only be started from .claude\launch.json, i.e. from inside Claude Code.
REM
REM   start_desk.bat   the desk      (this file)
REM   start.bat        SBC / astro   (unchanged)

echo ==================================================
echo   Trading Bramha - Desk (screening, research, risk)
echo   http://localhost:%PORT%
echo.
echo   For the SBC / astro dashboard, run start.bat instead.
echo ==================================================
echo.

if not exist "%PYTHON%" (
    echo [!] Python not found at:
    echo     %PYTHON%
    echo     Falling back to the 'py -3' launcher.
    set "PYTHON=py -3"
)

echo [1/3] Stopping any running desk (clean restart) ...
REM Name-restricted so we never touch shells or editors that merely reference the
REM path, and matched on dashboard_app so we do not kill the SBC dashboard.
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*dashboard_app*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT% " ^| findstr LISTENING') do (
    taskkill /F /PID %%p >nul 2>&1
)

echo [2/3] Launching the desk in its own window ...
cd /d "%REPO%"
start "Trading Bramha Desk :%PORT%" %PYTHON% -m streamlit run "%REPO%tools\dashboard_app.py" ^
    --server.port %PORT% --server.headless true --browser.gatherUsageStats false

echo [3/3] Waiting for the server to come up, then opening the browser ...
timeout /t 12 /nobreak >nul
start "" "http://localhost:%PORT%"

echo.
echo Desk is running in the "Trading Bramha Desk :%PORT%" window.
echo   - Re-run this file any time to RESTART it.
echo   - Close that window to STOP it.
echo   - The chart tool is a separate server; see .claude\launch.json ("chart").
echo.
endlocal
