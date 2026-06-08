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

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app import __version__
from app.engineer import generate_reply

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
        request, "index.html", {"version": __version__}
    )


@app.get("/api/health")
def health() -> dict:
    """Simple liveness/version probe."""
    return {"status": "ok", "version": __version__, "mode": "mock"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """Core endpoint: take a user message, return the engineer's reply."""
    history = [m.model_dump() for m in req.history]
    reply = generate_reply(req.message, history)
    return ChatResponse(intent=reply.intent, reply=reply.text, suggestions=reply.suggestions)
