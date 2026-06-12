"""
Diagnostic engine — the AIOps brain on top of the ITSM data layer.

Four capabilities, each pairing deterministic correlation (from datasources.py)
with Claude reasoning when an API key is configured, and a heuristic narrative
otherwise:

  rca(identifier)        -> root-cause analysis for an incident # or CI
  change_impact(...)     -> change-induced incident detection
  similar(text, ...)     -> retrieve & synthesise similar past incidents
  hotspots(...)          -> portfolio hotspots + trends, with an exec summary

Like the rest of the app, Claude calls degrade gracefully to heuristics.
"""

from __future__ import annotations

from app import config, datasources as ds


# --- Claude helper ----------------------------------------------------------

def _claude(system: str, user_text: str, max_tokens: int = 1600, thinking: bool = True) -> str | None:
    """Call Claude with a system + single user message. Returns text or None."""
    if not config.use_real_llm():
        return None
    try:
        from anthropic import Anthropic

        client = Anthropic()
        kwargs = {
            "model": config.ANALYSIS_MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user_text}],
        }
        if thinking:
            kwargs["thinking"] = {"type": "adaptive"}
        resp = client.messages.create(**kwargs)
        return "".join(b.text for b in resp.content if b.type == "text").strip() or None
    except Exception:  # noqa: BLE001 - degrade to heuristic
        return None


def _fmt(rows: list[dict], fields: list[str], limit: int = 10) -> str:
    out = []
    for r in rows[:limit]:
        out.append(" | ".join(f"{f}={r.get(f, '')}" for f in fields if r.get(f)))
    return "\n".join(out) if out else "(none)"


# --- 1. Root-cause analysis -------------------------------------------------

_RCA_SYSTEM = (
    "You are the Virtual Engineer's principal incident analyst (SRE/ITSM expert). "
    "Given an incident (or configuration item) and correlated ITSM evidence — related "
    "incidents, problems, and recent changes on the same CI, plus similar past incidents "
    "and how they were resolved — produce a focused root-cause analysis:\n"
    "1) **Most likely root cause** — a clear hypothesis with your reasoning.\n"
    "2) **Evidence & correlation** — cite specific ticket numbers (INC/PRB/CHG).\n"
    "3) **Change correlation** — could a recent change be responsible? State it plainly, "
    "noting correlation is not proof.\n"
    "4) **Recommended actions** — concrete next steps / likely fix, drawing on how similar "
    "incidents were resolved.\n"
    "5) **Confidence** — high/medium/low and why.\n"
    "6) **Conclusion** — one or two sentences: the bottom line and the single most important next action.\n"
    "Be specific and concise. Use **bold** labels, NOT markdown headings (no '#')."
)


def rca(identifier: str, db_path: str | None = None) -> dict:
    identifier = (identifier or "").strip()
    incident = None
    if identifier.upper().startswith("INC"):
        incident = ds.get_incident(identifier, db_path=db_path)
        if not incident:
            return {"ok": False, "error": f"Incident {identifier} not found."}
        ci = (incident.get("cmdb_ci") or "").strip()
    else:
        ci = identifier  # treat as a CI name

    if not ci:
        return {"ok": False, "error": "No configuration item associated — can't correlate."}

    corr = ds.correlate_ci(ci, limit=25, db_path=db_path)
    similar = ds.similar_incidents(
        incident["short_description"] if incident else ci, k=6, db_path=db_path)

    # Build the evidence bundle for the model (compact, cited).
    parts = []
    if incident:
        parts.append(
            "TARGET INCIDENT: " + " | ".join(
                f"{k}={incident.get(k, '')}" for k in
                ("number", "priority", "category", "short_description", "assignment_group",
                 "opened_iso", "incident_state", "close_code", "close_notes") if incident.get(k)))
    parts.append(f"\nAFFECTED CI: {ci} — total incidents on this CI: {corr['incident_count']}, "
                 f"changes on this CI: {corr['change_count']}")
    parts.append("\nRECENT INCIDENTS ON THIS CI:\n" + _fmt(
        corr["incidents"], ["number", "opened_iso", "priority", "short_description", "close_code"], 12))
    parts.append("\nPROBLEMS ON THIS CI:\n" + _fmt(
        corr["problems"], ["number", "short_description", "state", "resolution_code", "related_incidents"], 8))
    parts.append("\nCHANGES ON THIS CI (most recent first):\n" + _fmt(
        corr["changes"], ["number", "type", "approval", "created_iso", "start_iso"], 10))
    parts.append("\nSIMILAR PAST INCIDENTS & RESOLUTIONS:\n" + _fmt(
        similar, ["number", "short_description", "close_code", "close_notes"], 6))
    evidence = "\n".join(parts)

    narrative = _claude(_RCA_SYSTEM, "Analyse this incident:\n\n" + evidence)
    source = "claude"
    if not narrative:
        narrative = _heuristic_rca(incident, ci, corr, similar)
        source = "heuristic"

    return {
        "ok": True,
        "identifier": identifier,
        "incident": incident,
        "cmdb_ci": ci,
        "correlation": corr,
        "similar": similar,
        "rca": narrative,
        "source": source,
    }


def _heuristic_rca(incident, ci, corr, similar) -> str:
    lines = []
    if incident:
        lines.append(f"**Incident {incident.get('number')}** — {incident.get('short_description','')} "
                     f"(priority {incident.get('priority','?')}, category {incident.get('category','?')}).")
    lines.append(f"**Affected CI:** {ci} has **{corr['incident_count']}** incidents and "
                 f"**{corr['change_count']}** changes on record.")
    if corr["changes"]:
        c = corr["changes"][0]
        lines.append(f"**Recent change to watch:** {c.get('number')} ({c.get('type')}, "
                     f"{c.get('created_iso')}) — review whether it correlates with this incident.")
    if corr["problems"]:
        p = corr["problems"][0]
        lines.append(f"**Known problem on this CI:** {p.get('number')} — {p.get('short_description','')} "
                     f"(state {p.get('state','?')}).")
    if similar:
        codes = [s.get("close_code") for s in similar if s.get("close_code")]
        if codes:
            lines.append(f"**How similar incidents were resolved:** {', '.join(dict.fromkeys(codes))}.")
    lines.append("\n_(Offline heuristic. Configure ANTHROPIC_API_KEY for a full Claude root-cause analysis.)_")
    return "\n".join(lines)


# --- 2. Change impact -------------------------------------------------------

_CHANGE_SYSTEM = (
    "You are a change-management risk analyst. You are given changes that were followed by "
    "incidents on the same configuration item within a short window. Identify which changes "
    "look genuinely risky (likely change-induced incidents) versus coincidental — high-volume "
    "CIs naturally see many incidents, so a high count alone is not proof. Be specific, cite "
    "CHG/CI names, and recommend what to review. End with a **Conclusion** line: the single most "
    "important takeaway. Use **bold** labels, no markdown headings."
)


def change_impact(window_hours: int = 72, top: int = 15, db_path: str | None = None) -> dict:
    correlations = ds.change_incident_correlation(window_hours=window_hours, top=top, db_path=db_path)
    summary = None
    if correlations:
        evidence = f"Window: {window_hours}h after each change.\n" + _fmt(
            correlations, ["change", "type", "ci", "change_time", "incidents_after"], top)
        summary = _claude(_CHANGE_SYSTEM, "Assess change-induced incident risk:\n\n" + evidence)
    if not summary:
        summary = _heuristic_change_summary(correlations, window_hours)
        source = "heuristic"
    else:
        source = "claude"
    return {"ok": True, "window_hours": window_hours, "correlations": correlations,
            "summary": summary, "source": source}


def _heuristic_change_summary(correlations, window_hours) -> str:
    if not correlations:
        return "No changes were followed by incidents on the same CI in the window."
    top = correlations[0]
    return (f"**{len(correlations)} changes** were followed by incidents on the same CI within "
            f"{window_hours}h. Highest: **{top['change']}** on **{top['ci']}** "
            f"→ {top['incidents_after']} incidents after. Note: high-volume CIs see many incidents "
            f"regardless, so treat counts as a signal to investigate, not proof of causation.\n\n"
            "_(Offline heuristic. Configure ANTHROPIC_API_KEY for a risk assessment.)_")


# --- 3. Similar-incident retrieval ------------------------------------------

_SIMILAR_SYSTEM = (
    "You are a support knowledge assistant. Given a new incident description and the most "
    "similar past incidents (with their resolution/close codes and notes), recommend the most "
    "likely resolution path as a short, ordered set of steps. Cite the INC numbers you drew from. "
    "End with a **Conclusion** line: the single recommended next step. Use **bold** labels, no markdown headings."
)


def similar(text: str, k: int = 8, db_path: str | None = None) -> dict:
    matches = ds.similar_incidents(text, k=k, db_path=db_path)
    guidance = None
    if matches:
        evidence = f"NEW INCIDENT: {text}\n\nSIMILAR PAST INCIDENTS:\n" + _fmt(
            matches, ["number", "short_description", "close_code", "close_notes"], k)
        guidance = _claude(_SIMILAR_SYSTEM, evidence)
    source = "claude" if guidance else "heuristic"
    if not guidance:
        if matches:
            codes = list(dict.fromkeys(m.get("close_code") for m in matches if m.get("close_code")))
            guidance = (f"Found **{len(matches)}** similar past incidents. Common resolutions: "
                        f"{', '.join(codes) or 'n/a'}.\n\n_(Configure ANTHROPIC_API_KEY for step-by-step guidance.)_")
        else:
            guidance = "No similar past incidents found."
    return {"ok": True, "query": text, "matches": matches, "guidance": guidance, "source": source}


# --- 4. Hotspots & trends ---------------------------------------------------

_HOTSPOT_SYSTEM = (
    "You are an IT operations analyst writing a brief executive summary of an incident "
    "portfolio. Given top configuration items, assignment groups, categories, monthly volumes, "
    "and SLA/reopen/major-incident stats, highlight the most important risks and where to focus "
    "improvement effort. End with a **Conclusion** line: the top priority to act on. "
    "Be concise. Use **bold** labels, no markdown headings."
)


def hotspots(top: int = 10, db_path: str | None = None) -> dict:
    data = ds.hotspots(top=top, db_path=db_path)
    evidence = (
        "TOP CIs BY INCIDENTS:\n" + _fmt(data.get("top_cis", []), ["ci", "incidents"], top) +
        "\n\nTOP ASSIGNMENT GROUPS:\n" + _fmt(data.get("top_groups", []), ["team", "incidents"], top) +
        "\n\nTOP CATEGORIES:\n" + _fmt(data.get("top_categories", []), ["category", "incidents"], top) +
        f"\n\nMONTHLY VOLUME: {[(m['month'], m['incidents']) for m in data.get('by_month', [])]}" +
        f"\n\nSLA: {data.get('sla')} | reopened: {data.get('reopened')} | "
        f"major incidents: {data.get('major_incidents')}"
    )
    summary = _claude(_HOTSPOT_SYSTEM, "Summarise this incident portfolio:\n\n" + evidence,
                      max_tokens=1200)
    data["summary"] = summary or ("Portfolio loaded. Configure ANTHROPIC_API_KEY for an "
                                  "AI executive summary.")
    data["source"] = "claude" if summary else "heuristic"
    return data
