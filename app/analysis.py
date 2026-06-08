"""
Analysis layer: turn ingested documents into meaningful insights.

Right now this is an OFFLINE, heuristic engine — it detects issues and requests
by keyword/category matching, finds top themes, and builds month-by-month
trends from any dates it can spot. It is deterministic and needs no network.

>>> SWAP-IN POINT FOR A REAL LLM <<<
`analyze_documents()` is the single public entry point. To get genuine,
context-aware insight (and real image understanding), switch it to call
`analyze_with_claude()` — see the bottom of this file. Nothing else changes.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime

from app.ingest import ExtractedDoc

# --- Keyword taxonomy -------------------------------------------------------

ISSUE_CATEGORIES: dict[str, tuple[str, ...]] = {
    "Errors & Failures": ("error", "exception", "fail", "failure", "crash", "traceback",
                          "fatal", "broken", "does not work", "doesn't work", "not working"),
    "Performance": ("slow", "latency", "timeout", "timed out", "lag", "hang", "freeze",
                    "unresponsive", "bottleneck", "performance"),
    "Bugs & Defects": ("bug", "defect", "glitch", "incorrect", "wrong", "unexpected", "misbehav"),
    "Outages & Incidents": ("outage", "downtime", "incident", "unavailable", "is down",
                            "went down", "disruption", "offline"),
    "Data & Quality": ("missing data", "corrupt", "duplicate", "inconsistent", "mismatch",
                       "data quality", "invalid"),
    "Security": ("vulnerability", "breach", "unauthorized", "security", "exploit", "leak"),
    "Usability": ("confusing", "hard to use", "unclear", "complicated", "frustrating",
                  "difficult", "cumbersome"),
}

REQUEST_CATEGORIES: dict[str, tuple[str, ...]] = {
    "Feature Requests": ("feature", "would like", "wish", "enhancement", "ability to",
                        "support for", "new capability", "it would be great"),
    "Changes & Improvements": ("improve", "enhance", "optimi", "upgrade", "modernize",
                              "streamline", "simplify", "refactor"),
    "Help & Support": ("please", "can you", "could you", "need help", "how do i",
                      "assistance", "guidance", "how to"),
    "Access & Permissions": ("access", "permission", "grant", "enable", "allow",
                            "account", "login", "credential"),
    "Integrations": ("integrate", "integration", "connect", "api", "sync", "import", "export"),
}

_STOPWORDS = set("""
a an the and or but if then else for to of in on at by with from into over under
is are was were be been being do does did has have had will would shall should can
could may might must this that these those it its as not no yes you your we our they
their he she his her them us i me my mine our ours so such than too very just also
""".split())

# Date patterns we try to recognise inside a line of text.
_DATE_PATTERNS = [
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), "%Y-%m-%d"),
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), "%m/%d/%Y"),
    (re.compile(r"\b(\d{1,2})-(\d{1,2})-(\d{4})\b"), "%m-%d-%Y"),
    (re.compile(r"\b(\d{4})/(\d{1,2})/(\d{1,2})\b"), "%Y/%m/%d"),
]
_MONTH_NAME = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+(\d{4})\b",
    re.IGNORECASE,
)
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


# --- Data structures --------------------------------------------------------

@dataclass
class Finding:
    kind: str          # "issue" | "request"
    category: str
    snippet: str
    source: str        # filename
    period: str | None  # "YYYY-MM" if a date was found, else None


@dataclass
class TrendPoint:
    period: str
    issues: int
    requests: int


@dataclass
class AnalysisResult:
    total_files: int
    total_words: int
    file_summaries: list[dict] = field(default_factory=list)
    issues: list[Finding] = field(default_factory=list)
    requests: list[Finding] = field(default_factory=list)
    issue_categories: dict[str, int] = field(default_factory=dict)
    request_categories: dict[str, int] = field(default_factory=dict)
    top_terms: list[list] = field(default_factory=list)  # [term, count]
    trends: list[TrendPoint] = field(default_factory=list)
    summary: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# --- Helpers ----------------------------------------------------------------

def _find_period(line: str) -> str | None:
    """Return 'YYYY-MM' for the first date found in the line, else None."""
    for pattern, fmt in _DATE_PATTERNS:
        m = pattern.search(line)
        if m:
            try:
                dt = datetime.strptime(m.group(0), fmt)
                return f"{dt.year:04d}-{dt.month:02d}"
            except ValueError:
                continue
    m = _MONTH_NAME.search(line)
    if m:
        mon = _MONTHS.get(m.group(1).lower()[:3])
        if mon:
            return f"{int(m.group(2)):04d}-{mon:02d}"
    return None


def _units(doc: ExtractedDoc) -> list[str]:
    """Break a document into scannable units (sentences / table rows)."""
    units: list[str] = []
    for raw_line in doc.text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Table rows (joined with '|') stay whole; prose is split into sentences.
        if "|" in line:
            units.append(line)
        else:
            units.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+", line) if s.strip())
    return units


def _categorise(unit_lower: str, taxonomy: dict[str, tuple[str, ...]]) -> str | None:
    for category, keywords in taxonomy.items():
        if any(kw in unit_lower for kw in keywords):
            return category
    return None


def _top_terms(text: str, n: int = 15) -> list[list]:
    words = re.findall(r"[a-zA-Z][a-zA-Z\-']{2,}", text.lower())
    counts = Counter(w for w in words if w not in _STOPWORDS)
    return [[w, c] for w, c in counts.most_common(n)]


# --- Public entry point -----------------------------------------------------

def analyze_documents(docs: list[ExtractedDoc]) -> AnalysisResult:
    """
    Analyse a batch of ingested documents and return structured insights.

    To use the real Claude API instead, replace the body with:
        return analyze_with_claude(docs)
    """
    return _heuristic_analysis(docs)


def _heuristic_analysis(docs: list[ExtractedDoc]) -> AnalysisResult:
    result = AnalysisResult(total_files=len(docs), total_words=0)
    issue_cat = Counter()
    request_cat = Counter()
    trend_issue = defaultdict(int)
    trend_request = defaultdict(int)
    all_text_parts: list[str] = []
    has_image = False
    dated_findings = 0

    for doc in docs:
        result.total_words += doc.word_count
        all_text_parts.append(doc.text)
        if doc.filetype == "image":
            has_image = True
        result.file_summaries.append({
            "filename": doc.filename,
            "filetype": doc.filetype,
            "words": doc.word_count,
            "metadata": doc.metadata,
            "error": doc.error,
        })
        if doc.error:
            continue

        for unit in _units(doc):
            lower = unit.lower()
            period = _find_period(unit)
            snippet = unit if len(unit) <= 240 else unit[:237] + "..."

            issue_c = _categorise(lower, ISSUE_CATEGORIES)
            if issue_c:
                result.issues.append(Finding("issue", issue_c, snippet, doc.filename, period))
                issue_cat[issue_c] += 1
                if period:
                    trend_issue[period] += 1
                    dated_findings += 1

            request_c = _categorise(lower, REQUEST_CATEGORIES)
            if request_c:
                result.requests.append(Finding("request", request_c, snippet, doc.filename, period))
                request_cat[request_c] += 1
                if period:
                    trend_request[period] += 1
                    dated_findings += 1

    result.issue_categories = dict(issue_cat.most_common())
    result.request_categories = dict(request_cat.most_common())
    result.top_terms = _top_terms("\n".join(all_text_parts))

    periods = sorted(set(trend_issue) | set(trend_request))
    result.trends = [TrendPoint(p, trend_issue.get(p, 0), trend_request.get(p, 0)) for p in periods]

    result.summary = _build_summary(result)
    result.notes = _build_notes(result, has_image, dated_findings)
    return result


def _build_summary(r: AnalysisResult) -> str:
    if not r.issues and not r.requests:
        return (f"I read {r.total_files} file(s) ({r.total_words:,} words) but didn't detect "
                "explicit issues or requests. Try files containing tickets, feedback, or notes.")
    top_issue = next(iter(r.issue_categories), None)
    top_request = next(iter(r.request_categories), None)
    parts = [f"Across **{r.total_files} file(s)** ({r.total_words:,} words), I found "
             f"**{len(r.issues)} issue mention(s)** and **{len(r.requests)} request mention(s)**."]
    if top_issue:
        parts.append(f"The most common issue theme is **{top_issue}** "
                     f"({r.issue_categories[top_issue]}).")
    if top_request:
        parts.append(f"The most requested area is **{top_request}** "
                     f"({r.request_categories[top_request]}).")
    if r.trends:
        peak = max(r.trends, key=lambda t: t.issues + t.requests)
        parts.append(f"Activity peaked in **{peak.period}** "
                     f"({peak.issues} issues, {peak.requests} requests).")
    return " ".join(parts)


def _build_notes(r: AnalysisResult, has_image: bool, dated_findings: int) -> list[str]:
    notes: list[str] = []
    if has_image:
        notes.append("🖼️ Images were detected. Offline mode reads only their metadata — "
                     "switch on the Claude vision API for real image understanding.")
    if dated_findings == 0:
        notes.append("📅 No dates were detected, so no time-trend could be built. "
                     "Include a date column or timestamps to see trends over time.")
    notes.append("⚙️ Running in offline heuristic mode. Connect the Claude API "
                "(see app/analysis.py) for deeper, context-aware insights.")
    return notes


# --- Real Claude API example (disabled until you opt in) --------------------

def analyze_with_claude(docs: list[ExtractedDoc]) -> AnalysisResult:
    """
    Drop-in replacement that sends the ingested content to Claude for genuine
    analysis. Images can be passed as image blocks for true vision analysis.

    To enable:
      1. Uncomment `anthropic` in requirements.txt and install it.
      2. Set ANTHROPIC_API_KEY (see .env.example).
      3. In analyze_documents() above, return analyze_with_claude(docs).

    The heuristic result below is computed first so the structured fields
    (categories, trends) stay populated; you can then have Claude enrich the
    `summary` and `notes`, or replace the parsing entirely with the model.
    """
    import os

    from anthropic import Anthropic  # type: ignore  # lazy import on purpose

    base = _heuristic_analysis(docs)
    corpus = "\n\n".join(f"### {d.filename}\n{d.text[:8000]}" for d in docs if not d.error)
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1500,
        system=("You are a senior analyst. Read the provided documents and produce a concise, "
                "executive summary of the key issues and requests, plus notable trends. "
                "Be specific and cite which file each insight came from."),
        messages=[{"role": "user", "content": f"Analyse these documents:\n\n{corpus}"}],
    )
    base.summary = "".join(b.text for b in response.content if b.type == "text")
    return base
