# Virtual Engineer — Project Summary

*What we built, and how we built it.*

![Virtual Engineer — home screen (demo data)](app-preview.svg)

*The unified workspace: centered hero, live data overview, and the four diagnostic capabilities — on the Deloitte brand. (Shown with synthetic demo data.)*

---

## In one line
**Virtual Engineer** is an AI-powered incident-diagnosis copilot that turns L2/L3 engineers into AI-augmented experts — correlating incidents, changes, and problems across the ITSM estate and using Claude to generate root-cause analysis, change-impact assessment, similar-incident guidance, and portfolio hotspots, in seconds.

---

## What it does (capabilities)

| Capability | What the engineer gets |
|---|---|
| 🔍 **Root Cause** | Enter an incident # or pick a configuration item → the copilot correlates every incident, problem, and change on that CI, then Claude writes a root-cause analysis with **cited evidence** and a clear **Conclusion** + next action. |
| 🔧 **Change Impact** | Detects changes that were followed by incidents on the same CI within a time window — a signal for change-induced incidents — with a risk read. |
| 📚 **Similar Incidents** | Describe a new issue → full-text search over historical incidents → Claude synthesises a recommended **resolution path** from how similar tickets were actually solved. |
| 📊 **Hotspots & Trends** | Portfolio view: top problem CIs, assignment groups, categories, SLA/reopen/major stats, monthly volume, and an AI executive summary — with interactive break-down-by menus. |
| ⬆ **Bring-your-own data** | Upload your own Incident/Problem/Change/Task files (CSV/Excel); types are auto-detected and analysed in a **private, per-session** dataset, isolated from the demo data. |

Every result is presented in a clean, Deloitte-branded card: a titled, grouped narrative that ends with a **Conclusion**, the supporting evidence in collapsible tables, and a **Clear** button.

---

## The data
ServiceNow ITSM exports — the shared correlation key is `cmdb_ci` (the affected configuration item), plus `assignment_group` and timestamps:

- **~59,000** Incidents · **~70,000** Tasks · **~4,000** Changes · **92** Problems

Loaded into a local, indexed **SQLite** database (with FTS5 full-text search) that rebuilds automatically. *This is ITSM ticket history — live metrics/logs/traces/topology would plug in next as additional data sources.*

---

## How it works (architecture)

```
                         Browser (Deloitte-themed UI, one page)
                                      │  /api/itsm/*
                                      ▼
   FastAPI (app/main.py)  ──►  diagnostics.py  ──►  Claude API (claude-opus-4-8)
                                      │                    (reasoning, vision)
                                      ▼
                              datasources.py  (SQLite: correlation, FTS, trends)
                                      ▲
                              connectors/  ── Mock (CSV) · ServiceNow (REST) · per-session upload
```

- **Deterministic + AI by design.** The engine does the precise correlation in SQL; Claude does the cross-domain *reasoning*. If there's no API key or a call fails, it **degrades gracefully** to a heuristic — the app never hard-fails.
- **Pluggable data sources** behind one `ITSMConnector` interface: the local demo CSVs today, a ready **ServiceNow REST** connector (activate with credentials), and isolated per-session uploads — swappable via config.
- **Schema-aware queries** so user-uploaded files with different columns still work.

### Code map
| File | Responsibility |
|---|---|
| `app/main.py` | FastAPI app + routes (`/`, `/api/itsm/*`, upload) |
| `app/diagnostics.py` | The AIOps brain: `rca` · `change_impact` · `similar` · `hotspots` (correlation + Claude) |
| `app/datasources.py` | ITSM data layer: CSV→SQLite, indexes, FTS, correlation queries, per-session DBs |
| `app/connectors/` | `MockConnector` (CSV) · `ServiceNowConnector` (REST) behind a common interface |
| `app/engineer.py` / `app/analysis.py` / `app/ingest.py` | Chat brain + document analysis + multi-format file ingestion |
| `app/config.py` | Single source of truth: real Claude vs offline mock (auto-detect `ANTHROPIC_API_KEY`) |
| `app/templates/` · `app/static/` | Unified UI + Deloitte theme |
| `tests/` | 26 deterministic unit tests (forced offline) |

---

## How we built it

- **Built with Claude Code** — the entire app was designed, written, debugged, and shipped conversationally with Claude, in days rather than months.
- **Iterative loop:** change → run → verify in a live browser preview → commit → push, on every increment.
- **Locked-down environment:** winget/MSI installs are blocked, so we used a **portable, embeddable Python** and the **Gitea single binary** — no admin rights needed.
- **Source control:** started on a local **Gitea** server, then migrated to a public **GitHub** repo (`surpanda1977/virtual-engineer`).
- **Real Claude API** (`claude-opus-4-8`), with vision for images, wired in with an automatic offline fallback.
- **Brand:** redesigned to the official **Deloitte** light theme (green accent, Open Sans, white cards, branded charts) per the brand guidelines.
- **Safety:** internal ITSM data and secrets are git-ignored and never published; uploaded data is isolated per session.

---

## Why it matters
Today, diagnosing a major incident means an engineer manually stitching together incidents, changes, and problems across multiple screens — slow, and dependent on tribal knowledge. Virtual Engineer compresses that to seconds, scales senior-engineer judgement across the team, flags change-induced incidents before they spread, and turns historical tickets into reusable knowledge. It's **bring-your-own-data**, on-brand, and ready to connect live to ServiceNow and monitoring tools next.

> *Together makes progress* — people + AI, diagnosing faster.
