@echo off
REM Launches Virtual Engineer in DEMO MODE — serves the synthetic sample_data/
REM only (never your real data/). Use this for recordings, screenshots, and demos.
cd /d "%~dp0"
set VE_USE_SAMPLE=1
echo Starting Virtual Engineer in DEMO MODE on http://127.0.0.1:8000  (Ctrl+C to stop)
"C:\Users\surpanda\tools\python312\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
