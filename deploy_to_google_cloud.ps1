$ErrorActionPreference = "Stop"

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
$authOutput = & $gcloudBin auth list 2>&1 | Out-String

if ($authOutput -match "No credentialed accounts" -or -not ($authOutput -match "ACTIVE")) {
    Write-Host ""
    Write-Host "No active Google Cloud account detected." -ForegroundColor Yellow
    Write-Host "Opening your browser to log in with jvasquez8@gmail.com..." -ForegroundColor Green
    Write-Host ""
    & $gcloudBin auth login --brief
} else {
    Write-Host "Authentication confirmed!" -ForegroundColor Green
}

Write-Host ""
Write-Host "[2/3] Configuring Cloud Run Region (us-central1)..." -ForegroundColor Yellow
& $gcloudBin config set run/region us-central1

$currentProject = & $gcloudBin config get-value project 2>&1 | Out-String
$currentProject = $currentProject.Trim()

if (-not $currentProject -or $currentProject -match "\(unset\)") {
    Write-Host ""
    Write-Host "Select your Google Cloud Project:" -ForegroundColor Yellow
    & $gcloudBin projects list
    Write-Host ""
    $proj = Read-Host "Enter your Google Cloud Project ID (e.g. my-project-123456)"
    if ($proj) {
        & $gcloudBin config set project $proj.Trim()
    }
}

Write-Host ""
Write-Host "[3/3] Deploying Vicho's Watch Finder to Google Cloud Run..." -ForegroundColor Yellow
$appDir = "C:\Users\home\.gemini\antigravity\scratch\site-search-app"
Set-Location $appDir

& $gcloudBin run deploy watch-finder `
  --source . `
  --region us-central1 `
  --allow-unauthenticated `
  --set-env-vars ALLOWED_EMAILS=jvasquez8@gmail.com

Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
