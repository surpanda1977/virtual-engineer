@echo off
REM Launches the Virtual Engineer web app (no PowerShell execution policy needed).
REM Double-click this file, or run it from any terminal:  run.cmd
cd /d "%~dp0"
echo Starting Virtual Engineer on http://127.0.0.1:8000  (press Ctrl+C to stop)
"C:\Users\surpanda\tools\python312\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
