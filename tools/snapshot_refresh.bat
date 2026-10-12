@echo off
set REPO=C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha
set LOG=C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\tools\logs\snapshot_refresh.log
cd /d "%REPO%"
echo. >> "%LOG%"
echo ===== %DATE% %TIME% -- snapshot_refresh starting ===== >> "%LOG%"
"C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\tools\snapshot_refresh.py" --all >> "%LOG%" 2>&1
if errorlevel 1 (
    echo ***** FAILED at %DATE% %TIME% ***** >> "%LOG%"
) else (
    echo ----- ok at %DATE% %TIME% ----- >> "%LOG%"
)
