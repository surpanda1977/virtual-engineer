# Virtual Engineer — From Idea to Working Product

### A step-by-step account for the leadership team

---

## Executive overview

In a matter of days, we built **Virtual Engineer** — an AI-powered incident-diagnosis copilot that helps L2/L3 engineers diagnose complex incidents in seconds instead of hours. It correlates incidents, changes, and problems across the ITSM estate and uses Claude to generate evidence-backed root-cause analysis, change-impact assessment, similar-incident guidance, and portfolio hotspots.

The entire solution — code, data layer, branded interface, and documentation — was designed and built conversationally using **Claude Code**, on a standard locked-down corporate laptop, with no special infrastructure.

---

## How we got here, step by step

**Step 1 — Set up a working environment on a locked-down machine.**
Software installs are blocked by policy, so we used a portable, no-install toolchain (an embeddable Python runtime). *Outcome: a fully working development setup with zero admin rights or exceptions.*

**Step 2 — Stood up source control.**
We started on a local Git server (Gitea) to version every change, then migrated the project to a **public GitHub repository** so it can be shared. *Outcome: every step is tracked, reviewable, and shareable.*

**Step 3 — Built the first working app.**
A small, fast web application (FastAPI) — the first "Virtual Engineer" — that runs entirely offline with zero configuration. *Outcome: a running product on day one, proving the approach.*

**Step 4 — Added document analysis.**
The ability to read PDFs, Word, Excel, PowerPoint, CSVs, and images and surface issues, requests, and trends. *Outcome: turned unstructured files into structured insight.*

**Step 5 — Connected real AI (Claude).**
We wired in the Claude API (model `claude-opus-4-8`), including the ability to read images, with an automatic fallback so the app never breaks if AI is unavailable. *Outcome: genuine, context-aware analysis — not canned responses.*

**Step 6 — Focused it on incident diagnosis (the core mission).**
We loaded real ServiceNow ITSM data — tens of thousands of incidents, changes, problems, and tasks — into a fast, searchable local database, correlated by the affected system (configuration item). *Outcome: a single, queryable view across data that normally lives in separate screens.*

**Step 7 — Built four expert capabilities.**
On top of that data: **Root Cause** (evidence-backed RCA), **Change Impact** (catches change-induced incidents), **Similar Incidents** (retrieves how past issues were resolved), and **Hotspots & Trends** (a leadership portfolio view). Each pairs precise, deterministic correlation with Claude's reasoning. *Outcome: senior-engineer judgement, available to everyone, in seconds.*

**Step 8 — Made it modular and reusable.**
We added pluggable data sources (a ready-to-activate live ServiceNow connector) and a **bring-your-own-data** mode: any team can upload their own incident/change/problem/task files and get the same analysis on data that stays **private to their session**. *Outcome: useful to any team, not just ours.*

**Step 9 — Made it look professional and on-brand.**
We redesigned the interface to the official **Deloitte** brand and consolidated everything onto one clean workspace, with grouped navigation, colour-coded charts, and tidy result cards that each end with a clear **Conclusion**. *Outcome: an executive-ready, polished product.*

**Step 10 — Made it safe to share, and easy to demo.**
We added a **synthetic demo dataset** so anyone can clone the public repo and run the full app immediately — while the real internal data and credentials are kept private and never published. We added a one-command "demo mode" for safe recordings and a deployment-ready configuration. *Outcome: shareable with confidence, with no data-governance risk.*

**Step 11 — Prepared leadership materials.**
A project summary, a recording-ready demo script with speaking notes, and a one-minute talk track — plus this document. *Outcome: ready to present and socialise.*

---

## At a glance

| # | Step | What it delivered |
|---|------|-------------------|
| 1 | Environment setup | Working dev setup, no admin rights |
| 2 | Source control | Tracked, shareable, public GitHub repo |
| 3 | First app | Running product on day one |
| 4 | Document analysis | Insight from unstructured files |
| 5 | Real Claude AI | Genuine, context-aware analysis |
| 6 | ITSM data layer | One correlated view across the estate |
| 7 | Four capabilities | RCA · change impact · similar · hotspots |
| 8 | Modular + uploads | Reusable by any team, private per session |
| 9 | Deloitte redesign | Executive-ready, on-brand UI |
| 10 | Safe to share | Demo data public; real data kept private |
| 11 | Leadership materials | Summary, demo script, talk track |

---

## The value it produces

- **Speed** — incident root cause goes from hours of manual cross-referencing to seconds, with the evidence cited.
- **Scale** — captures and reuses senior-engineer judgement, so every engineer operates at a higher level.
- **Prevention** — flags change-induced incidents before they spread.
- **Reusability** — bring-your-own-data for any team today; one configuration change away from live ServiceNow and monitoring tools.
- **Speed to build** — delivered in days, not months, using Claude Code.

---

## What's next
- Connect **live** to ServiceNow and monitoring tools (metrics, logs, topology).
- **Downloadable** RCA and design reports.
- Optional **secure hosting** for broader, durable access.

> *Together makes progress* — people and AI, diagnosing faster.

---

*Repository:* `https://github.com/surpanda1977/virtual-engineer` · *Built with Claude Code.*
