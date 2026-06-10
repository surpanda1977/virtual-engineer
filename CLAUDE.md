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
- `app/main.py` — FastAPI app, routes (`/`, `/diagnostics`, `/api/health`, `/api/chat`, `/api/analyze`, `/api/itsm/*`).
- `app/engineer.py` — the chat "brain". `generate_reply()` is the swap point for a real LLM.
- `app/ingest.py` — extracts text/tables/metadata from PDF, Word, Excel, PowerPoint, CSV, text, images.
- `app/analysis.py` — heuristic issue/request + trend engine. `analyze_documents()` is the swap point
  for a real LLM (`analyze_with_claude()` is the ready example, incl. image/vision).
- `app/datasources.py` — ITSM data layer: loads the 4 ServiceNow CSVs (INC/PRB/CR/TSK) into a local
  SQLite DB (`data/itsm.db`, lazy-built, indexed on cmdb_ci/group/dates, FTS5 on incidents) + query helpers.
- `app/diagnostics.py` — AIOps engine: `rca()`, `change_impact()`, `similar()`, `hotspots()`. Each pairs
  deterministic correlation with Claude reasoning (heuristic fallback when no key).
- `app/templates/`, `app/static/` — chat UI (`index.html`) + diagnostics UI (`diagnostics.html`/`.js`).
- `tests/` — unittest suite. Test modules force offline mode via `setUpModule` (patch `config.use_real_llm`)
  so tests stay deterministic even with a real key in `.env`.

## Incident Diagnostics (AIOps copilot) — /diagnostics
- Data: 4 ServiceNow CSV exports live in git-ignored `data/` (Incidents ~59k, Tasks ~70k, Changes ~4k,
  Problems ~92). Shared correlation key is `cmdb_ci`; also `assignment_group` + timestamps.
- `data/` and `*.db` are git-ignored — **never commit the ITSM data** (the GitHub repo is public).
- The DB rebuilds automatically when a CSV is newer than `data/itsm.db`.
- Four capabilities: root-cause analysis, change-impact correlation, similar-incident retrieval, hotspots/trends.
- Note: this is ITSM *ticket* data — no live metrics/logs/traces/topology graph. Those would plug in as
  future data sources in `datasources.py`.

## Document analysis feature
- Attach files in the UI (📎) → POST multipart to `/api/analyze` → renders an insights report
  (issues/requests by category, top themes, month-by-month trend chart).
- Offline/heuristic today. Images: only metadata is read offline; real vision needs the Claude API.
- To get real insights: flip `analyze_documents()` to `analyze_with_claude()` (mirrors the engineer swap).

## Real Claude API vs offline mock (automatic)
- `app/config.py` is the single source of truth: if `ANTHROPIC_API_KEY` (starts with
  `sk-ant-`) is set, the app uses the real Claude API (`claude-opus-4-8`); otherwise the
  offline mock. Both chat (`engineer.py`) and analysis (`analysis.py`) follow this and
  **fall back to mock/heuristic if a Claude call fails**, so the app never hard-fails.
- Analysis: the heuristic always computes the category counts + trend chart; Claude adds a
  real executive summary and reads images directly (vision).
- To enable: `pip install -r requirements.txt`, copy `.env.example` to `.env`, set
  `ANTHROPIC_API_KEY`. The mode badge in the UI shows "🟢 Claude API" vs "offline mock".

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
