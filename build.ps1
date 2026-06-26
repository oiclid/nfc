# build.ps1
# Builds NFC-Cooperative as a Windows executable.
# Run from the nfc\ directory in PowerShell:
#
#   .\build.ps1              — plain EXE folder  (fastest, for testing)
#   .\build.ps1 -Installer   — EXE folder + Inno Setup installer (.exe)
#   .\build.ps1 -Clean       — delete dist\ and build\ before building
#
# Prerequisites:
#   pip install pyinstaller pillow
#   Inno Setup 6 (only needed for -Installer): https://jrsoftware.org/isinfo.php

param(
    [switch]$Installer,
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root    = $PSScriptRoot
$Dist    = Join-Path $Root "dist\NFC-Cooperative"
$OutExe  = Join-Path $Root "dist\installer\NFC-Cooperative-Setup-v2.0.0.exe"

# ── 0. Clean ─────────────────────────────────────────────────────────────────
if ($Clean) {
    Write-Host "[0] Cleaning dist\ and build\..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "$Root\dist"  -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$Root\build" -ErrorAction SilentlyContinue
}

# ── 1. Generate placeholder icons if assets\app.ico doesn't exist ────────────
$AssetsDir = Join-Path $Root "assets"
$IcoPath   = Join-Path $AssetsDir "app.ico"
if (-not (Test-Path $IcoPath)) {
    Write-Host "[1] Generating placeholder icons (no assets\app.ico found)..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $AssetsDir | Out-Null
    python (Join-Path $Root "msix\generate_icons.py") --out $AssetsDir
} else {
    Write-Host "[1] Icons OK ($IcoPath)" -ForegroundColor DarkGray
}

# ── 2. PyInstaller ────────────────────────────────────────────────────────────
Write-Host "`n[2] Running PyInstaller..." -ForegroundColor Yellow
Push-Location $Root
python -m PyInstaller NFC-Cooperative.spec --noconfirm
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed." }
Pop-Location
Write-Host "    EXE folder: $Dist" -ForegroundColor Green

# ── 3. Verify key files exist in the bundle ───────────────────────────────────
Write-Host "`n[3] Verifying bundle..." -ForegroundColor Yellow
$checks = @(
    "NFC-Cooperative.exe",
    "_internal\data\database.sld",
    "_internal\migrations\migrate.py",
    "_internal\migrations\0002_purge_members.py",
    "_internal\migrations\0004_cooperative_fund.py"
)
$ok = $true
foreach ($rel in $checks) {
    $full = Join-Path $Dist $rel
    # PyInstaller 6+ puts data in _internal; older versions put it at root
    $alt  = Join-Path $Dist ($rel -replace '^_internal\\','')
    if ((Test-Path $full) -or (Test-Path $alt)) {
        Write-Host "    OK  $rel" -ForegroundColor DarkGreen
    } else {
        Write-Host "    MISSING  $rel" -ForegroundColor Red
        $ok = $false
    }
}
if (-not $ok) {
    Write-Warning "Some expected files are missing from the bundle. Check the spec file."
}

# ── 4. Optional: Inno Setup installer ────────────────────────────────────────
if ($Installer) {
    Write-Host "`n[4] Building Inno Setup installer..." -ForegroundColor Yellow
    $iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (-not (Test-Path $iscc)) {
        Write-Warning "Inno Setup not found at $iscc — skipping installer."
        Write-Warning "Download from https://jrsoftware.org/isinfo.php"
    } else {
        & $iscc (Join-Path $Root "installer.iss")
        if ($LASTEXITCODE -ne 0) { Write-Error "Inno Setup failed." }
        Write-Host "    Installer: $OutExe" -ForegroundColor Green
    }
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Build complete." -ForegroundColor Cyan
Write-Host "  Run directly : $Dist\NFC-Cooperative.exe"
if ($Installer -and (Test-Path $OutExe)) {
    Write-Host "  Installer    : $OutExe"
}
