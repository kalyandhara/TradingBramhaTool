@echo off
setlocal
cd /d "%~dp0.."

REM Installs the OPT-IN pre-commit hook (B-83). Nothing installs it for you: a
REM hook changes what `git commit` does, and that is the user's call, not a side
REM effect of a session that happened to touch the test setup.
REM
REM   tools\install_hooks.bat            install
REM   tools\install_hooks.bat --remove   uninstall
REM
REM The hook runs the 566-test suite (~19s) and can always be skipped with
REM   SKIP_TESTS=1 git commit -m "..."

if /i "%~1"=="--remove" goto remove

if not exist ".git\hooks" (
    echo [!] .git\hooks not found - is this a git checkout?
    exit /b 1
)
if exist ".git\hooks\pre-commit" (
    echo [!] .git\hooks\pre-commit already exists. Not overwriting.
    echo     Inspect it, then re-run with --remove first if you want ours.
    exit /b 1
)
copy /y "tools\hooks\pre-commit" ".git\hooks\pre-commit" >nul
if errorlevel 1 (
    echo [!] copy failed.
    exit /b 1
)
echo Installed .git\hooks\pre-commit
echo   The suite now runs before every commit. Skip one with:
echo       SKIP_TESTS=1 git commit -m "..."
exit /b 0

:remove
if exist ".git\hooks\pre-commit" (
    del ".git\hooks\pre-commit"
    echo Removed .git\hooks\pre-commit
) else (
    echo Nothing to remove.
)
exit /b 0
