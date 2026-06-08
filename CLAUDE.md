# Virtual Engineer — project notes for Claude Code

## What this is
A small FastAPI web app: an AI "Virtual Engineer" chat assistant. It currently
runs in **offline mock mode** (no API key, no network). There is a single,
clearly-marked swap point to plug in the real Claude API.

## Environment (important — non-standard Python)
This machine is locked down (winget/MSI installs are blocked by Group Policy).
Python is the **embeddable build**, not a normal install:

- Python executable: `C:\Users\surpanda\tools\python312\python.exe`
- There is **no** `python` on PATH and **no** `py` launcher. Always call the full path.
- pip works via `& "C:\Users\surpanda\tools\python312\python.exe" -m pip ...`

## Run the app
```powershell
.\run.ps1
# or:
C:\Users\surpanda\tools\python312\python.exe -m uvicorn app.main:app --reload
```
Then open http://127.0.0.1:8000

## Run the tests
```powershell
C:\Users\surpanda\tools\python312\python.exe -m unittest discover -s tests -t .
```

## Layout
- `app/main.py` — FastAPI app, routes (`/`, `/api/health`, `/api/chat`, `/api/analyze`).
- `app/engineer.py` — the chat "brain". `generate_reply()` is the swap point for a real LLM.
- `app/ingest.py` — extracts text/tables/metadata from PDF, Word, Excel, PowerPoint, CSV, text, images.
- `app/analysis.py` — heuristic issue/request + trend engine. `analyze_documents()` is the swap point
  for a real LLM (`analyze_with_claude()` is the ready example, incl. image/vision).
- `app/templates/`, `app/static/` — the chat UI (chat + attach-files document analysis).
- `tests/` — unittest suite (`test_engineer.py`, `test_analysis.py`).

## Document analysis feature
- Attach files in the UI (📎) → POST multipart to `/api/analyze` → renders an insights report
  (issues/requests by category, top themes, month-by-month trend chart).
- Offline/heuristic today. Images: only metadata is read offline; real vision needs the Claude API.
- To get real insights: flip `analyze_documents()` to `analyze_with_claude()` (mirrors the engineer swap).

## Switching to the real Claude API
1. Uncomment `anthropic` in `requirements.txt`, then `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`.
3. In `app/engineer.py`, change `generate_reply()` to call `generate_reply_with_claude()`.

## Git / Gitea
- Local Gitea server: http://localhost:3000  (user: `surpanda`)
- Remote `origin`: http://localhost:3000/surpanda/virtual-engineer.git
- Start Gitea if it's not running:
  ```powershell
  $env:GITEA_WORK_DIR="C:\Users\surpanda\tools\gitea"
  C:\Users\surpanda\tools\gitea\gitea.exe web -c C:\Users\surpanda\tools\gitea\custom\conf\app.ini
  ```

## Conventions
- Keep `engineer.py` as the only place that knows how replies are produced.
- Add a test in `tests/test_engineer.py` for any new intent or behaviour.
