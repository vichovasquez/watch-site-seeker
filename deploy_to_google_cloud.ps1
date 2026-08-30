$ErrorActionPreference = "Continue"

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  VICHO'S WATCH FINDER - GOOGLE CLOUD DEPLOYMENT" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

$env:CLOUDSDK_PYTHON = "C:\Users\home\AppData\Local\Programs\Python\Python312\python.exe"
$gcloudBin = "C:\Users\home\.gemini\antigravity\scratch\google-cloud-sdk-install\google-cloud-sdk\bin\gcloud.cmd"

if (-not (Test-Path $gcloudBin)) {
    Write-Host "Error: gcloud CLI not found at $gcloudBin" -ForegroundColor Red
    exit 1
}

Write-Host "[1/3] Checking Google Cloud Authentication..." -ForegroundColor Yellow
Write-Host "Opening your browser to authenticate with your Google account (jvasquez8@gmail.com)..." -ForegroundColor Green
Write-Host ""

cmd.exe /c "`"$gcloudBin`" auth login --brief"

Write-Host ""
Write-Host "[2/3] Configuring Cloud Run Region (us-central1)..." -ForegroundColor Yellow
cmd.exe /c "`"$gcloudBin`" config set run/region us-central1"

Write-Host ""
Write-Host "Checking active Google Cloud Project..." -ForegroundColor Yellow
$currentProject = cmd.exe /c "`"$gcloudBin`" config get-value project"

if (-not $currentProject -or $currentProject -match "\(unset\)" -or $currentProject -match "None") {
    Write-Host ""
    Write-Host "Available Google Cloud Projects:" -ForegroundColor Cyan
    cmd.exe /c "`"$gcloudBin`" projects list"
    Write-Host ""
    $proj = Read-Host "Enter your Google Cloud Project ID (e.g. my-project-123456)"
    if ($proj) {
        cmd.exe /c "`"$gcloudBin`" config set project $($proj.Trim())"
    }
}

Write-Host ""
Write-Host "[3/3] Deploying Vicho's Watch Finder to Google Cloud Run..." -ForegroundColor Yellow
$appDir = "C:\Users\home\.gemini\antigravity\scratch\site-search-app"
Set-Location $appDir

cmd.exe /c "`"$gcloudBin`" run deploy watch-finder --source . --region us-central1 --allow-unauthenticated --set-env-vars ALLOWED_EMAILS=jvasquez8@gmail.com"

Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT COMPLETED!" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
