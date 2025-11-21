<#
    setup_concur_env.ps1

    One-time environment setup script:
    - Creates a Python virtual environment in .venv
    - Upgrades pip
    - Installs required packages:
        azure-storage-file-share
        python-gnupg
        paramiko
#>

# Stop on first error
$ErrorActionPreference = "Stop"

Write-Host "=== Concur PO Environment Setup ===" -ForegroundColor Cyan

# 1) Ensure we're in the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
Write-Host "Working directory: $scriptDir"

# 2) Detect Python
Write-Host "`nStep 1: Checking for Python..." -ForegroundColor Yellow

$python = "python"
try {
    $version = & $python --version 2>$null
} catch {
    Write-Host "Could not run 'python'. If you have Python installed but under a different name (e.g. python3)," -ForegroundColor Red
    Write-Host "edit this script and change the `$python variable." -ForegroundColor Red
    throw
}

Write-Host "Found $version"

# 3) Create virtual environment (.venv)
Write-Host "`nStep 2: Creating virtual environment '.venv' (if not exists)..." -ForegroundColor Yellow

if (Test-Path ".venv") {
    Write-Host ".venv already exists, skipping creation."
} else {
    & $python -m venv .venv
    Write-Host "Virtual environment created in .venv"
}

# 4) Upgrade pip inside venv
Write-Host "`nStep 3: Upgrading pip inside .venv..." -ForegroundColor Yellow

$venvPython = ".\.venv\Scripts\python.exe"
$venvPip    = ".\.venv\Scripts\pip.exe"

& $venvPython -m pip install --upgrade pip
Write-Host "pip upgraded."

# 5) Install required packages
Write-Host "`nStep 4: Installing required packages inside .venv..." -ForegroundColor Yellow

$packages = @(
    "azure-storage-file-share",
    "python-gnupg",
    "paramiko"
)

foreach ($pkg in $packages) {
    Write-Host "Installing $pkg..."
    & $venvPip install $pkg
}

Write-Host "`n=== Setup complete! ===" -ForegroundColor Green
Write-Host "Virtual environment: .venv"
Write-Host "You can now run your script with:"
Write-Host "    .\.venv\Scripts\python.exe `"PO File Build.py`""
