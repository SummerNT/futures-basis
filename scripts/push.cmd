@echo off
chcp 65001 >nul
setlocal

REM One-command commit & push for futures-basis.
REM
REM Why this exists: data/ and docs/ are owned by GitHub Actions. If you run
REM `git add -A`, your locally generated copies get staged too and collide
REM with the CI commits. This script only ever stages code and docs sources.

cd /d D:\WorkBuddy_spaces\Finance\futures-basis

echo [1/3] 同步远端...
git pull --rebase --autostash origin main
if errorlevel 1 goto :fail

echo [2/3] 暂存代码改动...
REM Never data/ or docs/index.html -- those belong to CI.
git add src .github scripts run.py README.md docs/manual.md

git diff --cached --quiet
if not errorlevel 1 goto :nocommit

set "MSG="
set /p MSG=提交说明（直接回车用默认）: 
if "%MSG%"=="" set MSG=chore: update

git commit -m "%MSG%"
if errorlevel 1 goto :fail
goto :push

:nocommit
echo   没有代码改动，跳过提交

:push
echo [3/3] 推送到 GitHub...
git push origin main
if errorlevel 1 goto :fail

echo.
echo 完成。CI 会自动重新生成页面，约 1 分钟后生效。
echo 线上地址 https://summernt.github.io/futures-basis/
exit /b 0

:fail
echo.
echo 出错了。把上面的输出发给 WorkBuddy。
exit /b 1
