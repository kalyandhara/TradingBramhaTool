@echo off
title Breakout Scanner
color 0A
echo.
echo  ============================================
echo   BREAKOUT SCANNER - Starting up...
echo  ============================================
echo.

:: ── Kill anything already on 3001 or 5173 ──────────────────────
echo  [1/4] Clearing ports 3001 and 5173...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":3001 " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":5173 " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: ── Start backend ───────────────────────────────────────────────
echo  [2/4] Starting backend  (port 3001)...
start "Breakout Scanner - API" cmd /k "cd /d %~dp0 && node server.js"
timeout /t 2 /nobreak >nul

:: ── Start frontend ──────────────────────────────────────────────
echo  [3/4] Starting frontend (port 5173)...
start "Breakout Scanner - UI" cmd /k "cd /d %~dp0breakout-scanner && npm run dev"
timeout /t 4 /nobreak >nul

:: ── Open browser ────────────────────────────────────────────────
echo  [4/4] Opening browser...
start "" "http://localhost:5173"

echo.
echo  ============================================
echo   Ready at http://localhost:5173
echo   Close the two terminal windows to stop.
echo  ============================================
echo.
pause
