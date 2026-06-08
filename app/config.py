"""
Central configuration. Reads from environment variables and a local .env file.

The single source of truth for "are we using the real Claude API or the offline
mock?" is whether a valid-looking ANTHROPIC_API_KEY is present.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    # Load .env from the project root (one level up from app/). Never committed.
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:  # pragma: no cover - dotenv is optional
    pass

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

# Model + tuning knobs (overridable via env).
CHAT_MODEL = os.environ.get("VE_MODEL", "claude-opus-4-8")
ANALYSIS_MODEL = os.environ.get("VE_ANALYSIS_MODEL", "claude-opus-4-8")
CHAT_MAX_TOKENS = int(os.environ.get("VE_CHAT_MAX_TOKENS", "4096"))
ANALYSIS_MAX_TOKENS = int(os.environ.get("VE_ANALYSIS_MAX_TOKENS", "8000"))


def use_real_llm() -> bool:
    """True only when a real Anthropic key is configured.

    We require the official `sk-ant-` prefix so a leftover placeholder in .env
    doesn't flip us into a broken 'real' mode.
    """
    return ANTHROPIC_API_KEY.startswith("sk-ant-")


def mode() -> str:
    return "claude" if use_real_llm() else "mock"
