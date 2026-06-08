"""
The "brain" of the Virtual Engineer.

Right now this is a self-contained MOCK: it classifies the user's request and
returns a helpful, templated answer. No network, no API key, fully offline.

>>> THIS IS THE SINGLE SWAP-IN POINT FOR A REAL LLM <<<
When you are ready to use the real Claude API, you only need to change the body
of `generate_reply()`. The rest of the application (web server, UI, tests) does
not need to change at all. See `generate_reply_with_claude()` at the bottom of
this file for a ready-to-use example.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from typing import Literal

Intent = Literal["review", "explain", "debug", "generate", "greeting", "general"]


@dataclass
class Reply:
    """A structured answer from the Virtual Engineer."""

    intent: Intent
    text: str
    suggestions: list[str] = field(default_factory=list)


# --- Intent detection -------------------------------------------------------

_KEYWORDS: dict[Intent, tuple[str, ...]] = {
    "review": ("review", "improve", "refactor", "clean up", "code smell", "best practice"),
    "debug": ("error", "exception", "traceback", "bug", "not working", "fails", "crash", "stack trace"),
    "explain": ("explain", "what is", "what's", "how does", "difference between", "why does"),
    "generate": ("write", "generate", "create", "scaffold", "boilerplate", "example of", "give me a"),
    "greeting": ("hello", "hi ", "hey", "good morning", "good afternoon"),
}


def classify(message: str) -> Intent:
    """Best-effort intent classification using simple keyword matching."""
    text = f" {message.lower().strip()} "
    for intent, keywords in _KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return intent
    return "general"


# --- Mock response generation ----------------------------------------------

def _has_code(message: str) -> bool:
    """Heuristic: does the message appear to contain a code snippet?"""
    return bool(re.search(r"[{};=()]|def |class |import |function |=>", message))


def _mock_reply(message: str) -> Reply:
    intent = classify(message)
    msg = message.strip()

    if intent == "greeting":
        return Reply(
            intent=intent,
            text=(
                "Hi! I'm your Virtual Engineer. I can review code, explain concepts, "
                "help debug errors, and scaffold boilerplate. What are you working on?"
            ),
            suggestions=[
                "Review this function for me",
                "Explain dependency injection",
                "Help me debug a KeyError",
            ],
        )

    if intent == "review":
        body = textwrap.dedent(
            """\
            Here's how I'd approach a review of this:

            1. **Naming** — make sure names describe intent, not implementation.
            2. **Single responsibility** — each function should do one thing; split if it grew.
            3. **Error handling** — fail fast on bad input, and don't swallow exceptions silently.
            4. **Tests** — add a test for the happy path and at least one edge case.
            5. **Readability** — prefer early returns over deep nesting.
            """
        )
        if not _has_code(msg):
            body += "\nPaste the actual code snippet and I'll give specific, line-level feedback."
        return Reply(intent=intent, text=body, suggestions=["Show me the refactored version", "What edge cases am I missing?"])

    if intent == "debug":
        return Reply(
            intent=intent,
            text=textwrap.dedent(
                """\
                Let's debug this methodically:

                1. **Read the bottom of the traceback first** — the last line names the actual error.
                2. **Reproduce it reliably** — find the smallest input that triggers it.
                3. **Check assumptions** — print/log the variable types and values right before the failing line.
                4. **Isolate** — comment out half the code to bisect where it breaks.

                Paste the full error message (and the line it points to) and I'll pinpoint the cause.
                """
            ),
            suggestions=["Here's my traceback", "How do I add logging?"],
        )

    if intent == "generate":
        return Reply(
            intent=intent,
            text=textwrap.dedent(
                """\
                Happy to scaffold that. Here's a clean starting point you can adapt:

                ```python
                def main() -> None:
                    \"\"\"Entry point.\"\"\"
                    # TODO: describe what you want and I'll fill in the body
                    ...


                if __name__ == "__main__":
                    main()
                ```

                Tell me the language and the exact behaviour you want, and I'll flesh it out.
                """
            ),
            suggestions=["Make it a FastAPI endpoint", "Add unit tests for it"],
        )

    if intent == "explain":
        return Reply(
            intent=intent,
            text=textwrap.dedent(
                f"""\
                Good question. Here's the short version:

                You asked: *"{msg}"*

                The key idea is to separate **what** something does from **how** it's
                implemented, so you can reason about each part independently. If you tell
                me the specific technology or term, I'll give you a concrete example with code.
                """
            ),
            suggestions=["Give me a concrete example", "When should I NOT use it?"],
        )

    # general / fallback
    return Reply(
        intent="general",
        text=textwrap.dedent(
            f"""\
            I read your message: *"{msg}"*

            I'm running in **offline mock mode** right now, so my answers are templated.
            Once you connect the real Claude API (see `app/engineer.py`), I'll give full,
            context-aware engineering help. In the meantime, try asking me to *review*,
            *explain*, *debug*, or *generate* something.
            """
        ),
        suggestions=["Review my code", "Explain a concept", "Help me debug"],
    )


# --- Public entry point -----------------------------------------------------

def generate_reply(message: str, history: list[dict] | None = None) -> Reply:
    """
    Produce the Virtual Engineer's reply to a user message.

    `history` is a list of {"role": "user"|"assistant", "content": str} dicts.

    Uses the real Claude API when an ANTHROPIC_API_KEY is configured (see
    app/config.py); otherwise falls back to the offline mock. If a Claude call
    fails (bad key, no network), we degrade gracefully to the mock so the app
    never hard-fails.
    """
    from app import config

    if config.use_real_llm():
        try:
            return generate_reply_with_claude(message, history)
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            fallback = _mock_reply(message)
            fallback.text = (
                f"⚠️ Couldn't reach Claude ({type(exc).__name__}); showing an offline "
                f"answer instead.\n\n{fallback.text}"
            )
            return fallback
    return _mock_reply(message)


# --- Real Claude API --------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are the Virtual Engineer, a senior software engineer acting as a helpful "
    "pair-programming assistant. Be concise, correct, and practical. Prefer concrete "
    "code examples in fenced code blocks. When reviewing or debugging, give specific, "
    "actionable feedback."
)


def generate_reply_with_claude(message: str, history: list[dict] | None = None) -> Reply:
    """Call the real Claude API. Credentials resolve from ANTHROPIC_API_KEY."""
    from anthropic import Anthropic  # imported lazily so the mock needs no SDK

    from app import config

    client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    messages = [{"role": m["role"], "content": m["content"]} for m in (history or [])]
    messages.append({"role": "user", "content": message})

    response = client.messages.create(
        model=config.CHAT_MODEL,
        max_tokens=config.CHAT_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=messages,
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return Reply(intent=classify(message), text=text or "(no response)")
