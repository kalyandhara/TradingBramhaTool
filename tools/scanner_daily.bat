@echo off
set PYTHON=C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe
set REPO=%~dp0..
set LOG=%~dp0scanner_daily.log
cd /d "%REPO%"
echo. >> "%LOG%"
echo ===== %DATE% %TIME% — daily scanner starting ===== >> "%LOG%"
set PYTHONIOENCODING=utf-8
"%PYTHON%" "%~dp0job_audit.py" run daily_scanner -- "%PYTHON%" "%~dp0scanner_daily_runner.py" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo ***** FAILED ***** >> "%LOG%"
) else (
    echo ----- ok ----- >> "%LOG%"
)
