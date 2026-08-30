@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy_to_google_cloud.ps1"
if %errorlevel% neq 0 (
    echo.
    echo Deployment encountered an issue.
)
pause
