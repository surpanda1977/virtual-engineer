# Launches the Virtual Engineer web app.
# Usage:  .\run.ps1
# Then open http://127.0.0.1:8000 in your browser.

$ErrorActionPreference = "Stop"
$python = "C:\Users\surpanda\tools\python312\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Embedded Python not found at $python. See README.md for setup."
    exit 1
}

Write-Host "Starting Virtual Engineer on http://127.0.0.1:8000  (Ctrl+C to stop)" -ForegroundColor Green
& $python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
