@echo off
setlocal
title Trading Bramha - test suite
cd /d "%~dp0"

REM ── B-83 ────────────────────────────────────────────────────────────────────
REM
REM The suite passed under exactly ONE of the three Pythons on this machine and
REM nothing invoked it. The other two are not hypothetical:
REM
REM   Programs\Python314        runs the dashboard (.claude/launch.json)  + pytest
REM   Python\pythoncore-3.14-64 runs the SCHEDULED JOBS (the .bat files)  - no pytest
REM   hermes-agent\venv         what a bare `python` resolves to          - no pandas
REM
REM So `python -m pytest` in a shell is a coin toss, and the one it most often
REM lands on cannot import pandas. This file removes the choice.
REM
REM Usage:
REM   run_tests.bat                     the whole suite
REM   run_tests.bat tools\test_pcr*.py  anything after the name goes to pytest
REM   run_tests.bat --batch             ALSO report on the scheduled-job interpreter
REM
REM --batch exists because the code that runs unattended every evening is never
REM exercised under the interpreter that runs it, and that interpreter carries a
REM different yfinance (1.6.0 vs 1.4.1 - see analyses/Python-Environments). It is
REM a REPORT, never a gate: a dev dependency missing on a second interpreter must
REM not fail a run that is otherwise green.

set "PY_TEST=C:\Users\Owner\AppData\Local\Programs\Python\Python314\python.exe"
set "PY_BATCH=C:\Users\Owner\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set "PYTHONIOENCODING=utf-8"

REM Strip --batch out of the arguments; everything else is pytest's.
REM
REM A shift loop with `call set`, NOT a `for` over %* with delayed expansion: the
REM latter is the idiom everyone reaches for and it silently passed the literal
REM text "!ARGS!" through to pytest here. Verified by running it.
set "WANT_BATCH="
set "ARGS="
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--batch" (
    set "WANT_BATCH=1"
) else (
    call set "ARGS=%%ARGS%% %~1"
)
shift
goto parse_args
:args_done

if not exist "%PY_TEST%" (
    echo [!] Test interpreter not found:
    echo     %PY_TEST%
    echo     This is the one .claude\launch.json uses to run the dashboard.
    echo     If Python moved, update this file AND launch.json together.
    exit /b 9
)

"%PY_TEST%" -c "import pytest" 2>nul
if errorlevel 1 (
    echo [!] pytest is not installed in the test interpreter.
    echo     Install it with:
    echo         "%PY_TEST%" -m pip install -r tools\requirements_dev.txt
    exit /b 9
)

echo === suite: %PY_TEST%
"%PY_TEST%" -m pytest%ARGS%
set "RC=%ERRORLEVEL%"

if defined WANT_BATCH call :batch_report

echo.
if "%RC%"=="0" (echo PASS) else (echo FAIL ^(exit %RC%^))
exit /b %RC%


:batch_report
echo.
echo === also under the scheduled-job interpreter: %PY_BATCH%
if not exist "%PY_BATCH%" (
    echo     [skip] not found on this machine.
    goto :eof
)
"%PY_BATCH%" -c "import pytest" 2>nul
if errorlevel 1 (
    echo     [gap] no pytest here, so the interpreter that runs the nightly jobs
    echo           is never tested. Install with:
    echo               "%PY_BATCH%" -m pip install -r tools\requirements_dev.txt
    goto :eof
)
"%PY_BATCH%" -m pytest%ARGS%
goto :eof
