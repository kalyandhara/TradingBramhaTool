@echo off
title Trading Bramha — Start
cd /d "%~dp0"

set PYTHON=C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe
set CHART_PORT=5001
set DASH_PORT=8501

:: ── Kill any existing instance on our ports ─────────────────────────────────
echo Stopping existing chart server (port %CHART_PORT%)...
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":%CHART_PORT% "') do (
    taskkill /PID %%p /F >nul 2>&1
)

echo Stopping existing dashboard (port %DASH_PORT%)...
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":%DASH_PORT% "') do (
    taskkill /PID %%p /F >nul 2>&1
)

timeout /t 2 /nobreak >nul

:: ── Launch chart server ──────────────────────────────────────────────────────
echo Starting chart server on port %CHART_PORT%...
start "Chart Server" /B "%PYTHON%" "%~dp0tools\chart_server.py"

:: ── Launch Streamlit dashboard ──────────────────────────────────────────────
echo Starting Streamlit dashboard on port %DASH_PORT%...
start "Trading Bramha Dashboard" /B "%PYTHON%" -m streamlit run ^
    "%~dp0tools\dashboard_app.py" ^
    --server.headless true ^
    --server.port %DASH_PORT%

:: ── Wait for services to come up, then open both in browser ────────────────
timeout /t 4 /nobreak >nul
echo Opening http://localhost:%CHART_PORT% (chart) ...
start "" "http://localhost:%CHART_PORT%"
echo Opening http://localhost:%DASH_PORT% (dashboard) ...
start "" "http://localhost:%DASH_PORT%"

echo.
echo  Chart server  : http://localhost:%CHART_PORT%
echo  Dashboard     : http://localhost:%DASH_PORT%
echo.
echo  Close this window to keep services running in the background.
echo  Re-run start.bat any time to restart both.
echo.
pause
