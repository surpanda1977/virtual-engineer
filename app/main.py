"""
Virtual Engineer - FastAPI web application.

Run locally with:
    .\run.ps1
or directly:
    C:\\Users\\surpanda\\tools\\python312\\python.exe -m uvicorn app.main:app --reload

Then open http://127.0.0.1:8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app import __version__, config
from app.analysis import analyze_documents
from app.engineer import generate_reply
from app.ingest import extract

# Reject individual uploads larger than this (bytes) to stay safe.
MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Virtual Engineer", version=__version__)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    intent: str
    reply: str
    suggestions: list[str] = []


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Serve the chat UI."""
    return templates.TemplateResponse(
        request, "index.html", {"version": __version__, "mode": config.mode()}
    )


@app.get("/api/health")
def health() -> dict:
    """Simple liveness/version probe."""
    return {"status": "ok", "version": __version__, "mode": config.mode()}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """Core endpoint: take a user message, return the engineer's reply."""
    history = [m.model_dump() for m in req.history]
    reply = generate_reply(req.message, history)
    return ChatResponse(intent=reply.intent, reply=reply.text, suggestions=reply.suggestions)


@app.post("/api/analyze")
async def analyze(files: list[UploadFile]) -> dict:
    """
    Ingest one or more uploaded files and return structured insights:
    detected issues & requests, categories, top themes, and time-trends.
    """
    docs = []
    skipped = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_FILE_BYTES:
            skipped.append({"filename": f.filename, "reason": "file too large"})
            continue
        docs.append(extract(f.filename or "unnamed", data))

    if not docs:
        return {"ok": False, "skipped": skipped, "error": "No readable files were uploaded."}

    result = analyze_documents(docs)
    payload = result.to_dict()
    payload["ok"] = True
    payload["skipped"] = skipped
    return payload
