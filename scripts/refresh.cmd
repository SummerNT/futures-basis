@echo off
chcp 65001 >nul
setlocal

REM Daily data refresh for futures-basis.
REM Intended to be run by Windows Task Scheduler on weekdays after market close.

cd /d D:\WorkBuddy_spaces\Finance\futures-basis
if not exist logs mkdir logs

set PY=C:\Users\myg10\.workbuddy\binaries\python\versions\3.13.12\python.exe
set LOG=logs\refresh.log

echo. >> "%LOG%"
echo ===== %date% %time% ===== >> "%LOG%"

REM 1) Sync with remote first, so CI commits do not cause a push conflict.
git pull --rebase --autostash origin main >> "%LOG%" 2>&1

REM 2) Fetch quotes, compute, render.
"%PY%" run.py --days 5 >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [ERROR] run.py failed >> "%LOG%"
    exit /b 1
)

REM 3) Commit only the generated data and page.
git add data docs
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "data: refresh %date%" >> "%LOG%" 2>&1
    git push origin main >> "%LOG%" 2>&1
    if errorlevel 1 (
        echo [ERROR] push failed, will retry next run >> "%LOG%"
        exit /b 1
    )
    echo [OK] pushed >> "%LOG%"
) else (
    echo [OK] no change, nothing to push >> "%LOG%"
)

endlocal
