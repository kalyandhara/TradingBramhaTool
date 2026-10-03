@echo off
setlocal
title Trading Bramha Dashboard launcher
set "REPO=%~dp0"
set "PORT=8050"
set "PYTHON=C:\Users\Owner\AppData\Local\Programs\Python\Python314\python.exe"
set "PYTHONIOENCODING=utf-8"

echo ==================================================
echo   Trading Bramha Dashboard
echo   http://localhost:%PORT%
echo ==================================================
echo.

if not exist "%PYTHON%" (
    echo [!] Python not found at:
    echo     %PYTHON%
    echo     Falling back to the 'py -3' launcher.
    set "PYTHON=py -3"
)

echo [1/3] Stopping any running dashboard (clean restart) ...
REM kill only PYTHON processes running this dashboard (name-restricted so we
REM never touch shells/editors that merely reference the path).
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*dash_trading_dashboard*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
REM fallback: free whatever is still LISTENING on the port
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT% " ^| findstr LISTENING') do (
    taskkill /F /PID %%p >nul 2>&1
)

echo [2/3] Launching dashboard in its own window ...
cd /d "%REPO%"
start "Trading Bramha Dashboard :%PORT%" %PYTHON% "%REPO%tools\dash_trading_dashboard.py"

echo [3/3] Waiting for the server to come up, then opening the browser ...
timeout /t 12 /nobreak >nul
start "" "http://localhost:%PORT%"

echo.
echo Dashboard is running in the "Trading Bramha Dashboard :%PORT%" window.
echo   - Re-run this file any time to RESTART it.
echo   - Close that window (or run stop.bat) to STOP it.
echo   - If the browser shows an error, wait a few seconds and refresh.
echo.
endlocal
