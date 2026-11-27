@echo off
set REPO=C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha
set LOG=C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\tools\logs\dma_watch.log
set PYTHONIOENCODING=utf-8
cd /d "%REPO%"
echo. >> "%LOG%"
echo ===== %DATE% %TIME% -- dma_watch starting ===== >> "%LOG%"
"C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\tools\job_audit.py" run dma_watch -- "C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe" -X utf8 "C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\tools\dma_watch.py" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo ***** FAILED at %DATE% %TIME% ***** >> "%LOG%"
) else (
    echo ----- ok at %DATE% %TIME% ----- >> "%LOG%"
)
