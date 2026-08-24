@echo off
set REPO=C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha
set LOG=C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\tools\logs\alert_watcher.log
cd /d "%REPO%"
echo. >> "%LOG%"
echo ===== %DATE% %TIME% -- alert_watcher starting ===== >> "%LOG%"
"C:\Program Files\nodejs\node.EXE" "C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\tools\alert_watcher.js" --once >> "%LOG%" 2>&1
if errorlevel 1 (
    echo ***** FAILED ***** >> "%LOG%"
) else (
    echo ----- ok ----- >> "%LOG%"
)
