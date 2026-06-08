# ⚙️ Virtual Engineer

An AI **pair-programming assistant** in your browser. Ask it to review code,
explain concepts, debug errors, or scaffold boilerplate. Built with FastAPI.

It ships in **offline mock mode** — it works with zero configuration, no API
key, and no internet. When you're ready, there's a single, clearly-marked place
to swap in the real Claude API.

![mode: mock](https://img.shields.io/badge/mode-mock-86e01e) ![python](https://img.shields.io/badge/python-3.12-blue)

---

## Quick start

```powershell
# from the project folder
.\run.ps1
```

Open **http://127.0.0.1:8000** and start chatting.

> This machine uses an embeddable Python at
> `C:\Users\surpanda\tools\python312\python.exe`. The `run.ps1` script already
> points at it, so you don't need `python` on your PATH.

### Run the tests
```powershell
C:\Users\surpanda\tools\python312\python.exe -m unittest discover -s tests -t .
```

---

## How it works

```
Browser (chat UI)  ──POST /api/chat──►  FastAPI (app/main.py)
                                            │
                                            ▼
                                   app/engineer.py
                                   generate_reply()      ◄── swap point for a real LLM
```

- **`app/main.py`** — web server and routes.
- **`app/engineer.py`** — the assistant's "brain". Classifies your message
  (review / explain / debug / generate) and returns a helpful reply.
- **`app/templates/` + `app/static/`** — the single-page chat interface.

---

## Going from mock → real Claude

1. In `requirements.txt`, uncomment the `anthropic` line and reinstall:
   ```powershell
   C:\Users\surpanda\tools\python312\python.exe -m pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and set your `ANTHROPIC_API_KEY`.
3. In `app/engineer.py`, change the body of `generate_reply()` to:
   ```python
   return generate_reply_with_claude(message, history)
   ```

That's the only change. The UI, server, and tests stay the same.

---

## Project + source control

Source lives in a **local Gitea** server (no cloud, fully on your machine):

- Web UI: http://localhost:3000
- Repo: http://localhost:3000/surpanda/virtual-engineer

See [CLAUDE.md](CLAUDE.md) for the full environment and workflow notes.
