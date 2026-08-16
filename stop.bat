@echo off
setlocal
set "PORT=8050"
echo Stopping Trading Bramha - SBC Dashboard ...
powershell -NoProfile -Command ^
  "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*dash_trading_dashboard*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT% " ^| findstr LISTENING') do (
    taskkill /F /PID %%p >nul 2>&1
)
echo Done - port %PORT% freed.
endlocal
