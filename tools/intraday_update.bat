@echo off
:: ---------------------------------------------------------------------------
:: intraday_update.bat — daily top-up for the intraday bar store.
::
:: Registered as the Windows scheduled task "TradingBramha-IntradayUpdate".
:: See wiki/analyses/Intraday-Store.md for WHY this must run on a schedule:
:: Yahoo serves intraday history as a ROLLING WINDOW (15m/5m ~60 days), so a day
:: this does not run is a day of fine-grained data that can never be recovered.
:: Daily bars keep; 15m bars do not.
::
:: Two things this wrapper exists to get right:
::   1. THE INTERPRETER. A bare `python` on this machine resolves to
::      hermes-agent\venv, which has no pandas and would fail every run. The
::      full path below is the same interpreter .claude/launch.json uses for the
::      dashboard. See wiki/analyses/Python-Environments.md.
::   2. A LOG. A scheduled task that silently stops working is the exact
::      failure mode this repo keeps being bitten by (frozen Yahoo feeds). Every
::      run appends a timestamped block, so `coverage` disagreeing with the log
::      is diagnosable rather than mysterious.
:: ---------------------------------------------------------------------------

set PYTHON=C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe
set REPO=%~dp0..
set LOG=%~dp0intraday_update.log

cd /d "%REPO%"

echo. >> "%LOG%"
echo ===== %DATE% %TIME% (local) — intraday update starting ===== >> "%LOG%"
"%PYTHON%" "%~dp0intraday_store.py" update >> "%LOG%" 2>&1
if errorlevel 1 (
    echo ***** FAILED with errorlevel %errorlevel% ***** >> "%LOG%"
) else (
    echo ----- ok ----- >> "%LOG%"
)
