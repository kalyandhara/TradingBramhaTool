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
::   2. A LOG + JOB_AUDIT. Run history is recorded in trading_bramha.db so the
::      Scheduler Hub can show it. A day that silently fails is a day of
::      fine-grained data that can never be recovered; job_audit makes failures
::      visible. (F-13 audit finding 2026-11-23.)
:: ---------------------------------------------------------------------------

set PYTHON=C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe
set REPO=C:\Users\Owner\OneDrive\Documents\Trading\Trading_Bramha\Trading_Bramha
set LOG=%REPO%\tools\logs\intraday_update.log
set PYTHONIOENCODING=utf-8
cd /d "%REPO%"

echo. >> "%LOG%"
echo ===== %DATE% %TIME% -- intraday_update starting ===== >> "%LOG%"
"%PYTHON%" "%REPO%\tools\job_audit.py" run intraday_update -- "%PYTHON%" "%REPO%\tools\intraday_store.py" update >> "%LOG%" 2>&1
if errorlevel 1 (
    echo ***** FAILED at %DATE% %TIME% ***** >> "%LOG%"
) else (
    echo ----- ok at %DATE% %TIME% ----- >> "%LOG%"
)
