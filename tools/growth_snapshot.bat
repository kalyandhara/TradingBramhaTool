@echo off
set REPO=C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha
set LOG=C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\tools\logs\growth_snapshot.log
cd /d "%REPO%"
echo. >> "%LOG%"
echo ===== %DATE% %TIME% -- growth_snapshot starting ===== >> "%LOG%"
"C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha\tools\growth_screen.py" --refresh >> "%LOG%" 2>&1
if errorlevel 1 (
    echo ***** FAILED at %DATE% %TIME% ***** >> "%LOG%"
) else (
    echo ----- ok at %DATE% %TIME% ----- >> "%LOG%"
)
