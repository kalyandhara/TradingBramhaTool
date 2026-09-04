@echo off
set REPO=C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha
set LOG=C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\tools\logs\opportunity_daily.log
cd /d "%REPO%"
echo. >> "%LOG%"
echo ===== %DATE% %TIME% -- opportunity_daily starting ===== >> "%LOG%"
"C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\tools\opportunity_daily.py" --universe 500 --top 100 >> "%LOG%" 2>&1
if errorlevel 1 (
    echo ***** FAILED ***** >> "%LOG%"
) else (
    echo ----- ok ----- >> "%LOG%"
)
