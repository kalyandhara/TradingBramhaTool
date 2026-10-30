@echo off
REM scanner_batch.bat - Batch screener execution wrapper
REM Executes scanner_batch_runner.py with logging

REM Configuration
set "PYTHON=C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set "REPO=C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha"
set "LOG=%REPO%\tools\scanner_batch.log"

REM Navigate to tools directory
cd /d "%REPO%\tools"

REM Run batch screener with default parameters
echo [%DATE% %TIME%] Starting batch screener...
"%PYTHON%" scanner_batch_runner.py --universe bhavcopy --top-n 500 --regime MIXED >> "%LOG%" 2>&1

REM Check exit code
if errorlevel 1 (
    echo [%DATE% %TIME%] ***** FAILED ***** >> "%LOG%"
    exit /b 1
) else (
    echo [%DATE% %TIME%] ----- ok ----- >> "%LOG%"
    exit /b 0
)
