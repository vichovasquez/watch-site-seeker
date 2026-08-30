@echo off
setlocal
echo ===================================================
echo   VICHO'S WATCH FINDER - GOOGLE CLOUD DEPLOYMENT
echo ===================================================
echo.

set CLOUDSDK_PYTHON=C:\Users\home\AppData\Local\Programs\Python\Python312\python.exe
set GCLOUD_BIN=C:\Users\home\.gemini\antigravity\scratch\google-cloud-sdk-install\google-cloud-sdk\bin\gcloud.cmd

echo [1/3] Checking Google Cloud Authentication...
"%GCLOUD_BIN%" auth list 2>&1 | findstr /C:"No credentialed accounts" >nul
if %errorlevel% equ 0 (
    echo.
    echo No active Google Cloud account found.
    echo Opening browser for Google login (jvasquez8@gmail.com)...
    echo.
    "%GCLOUD_BIN%" auth login --brief
)

echo.
echo [2/3] Setting project and configuring Cloud Run...
"%GCLOUD_BIN%" config set run/region us-central1

echo.
echo [3/3] Deploying Vicho's Watch Finder to Google Cloud Run...
cd /d "C:\Users\home\.gemini\antigravity\scratch\site-search-app"
"%GCLOUD_BIN%" run deploy watch-finder ^
  --source . ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --set-env-vars ALLOWED_EMAILS=jvasquez8@gmail.com

echo.
echo ===================================================
echo Deployment finished!
echo ===================================================
pause
