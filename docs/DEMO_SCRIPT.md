# Virtual Engineer — Demo Recording Script

A recording-ready walkthrough (~6–7 minutes). Each scene has **SHOW** (what to do on screen) and **SAY** (word-for-word narration). Record with Loom, MS Teams, or Camtasia.

## Before you record
1. Start the app: `cd C:\Users\surpanda\1st-Project` → `.\run.cmd`
2. Open **http://127.0.0.1:8000** (full-screen the browser; Ctrl+F5 to ensure latest).
3. Have a second tab open at the GitHub repo: `https://github.com/surpanda1977/virtual-engineer`
4. Confirm the badge top-right reads **🟢 Claude API**.
5. Pick one CI in advance for the live RCA (e.g. **BeeHive Platform**) so it's ready.

---

### Scene 1 — Opening (0:00–0:30)
**SHOW:** The home page — bulldozer logo, "Virtual Engineer" title, description box, the data cards, the four tabs.
**SAY:** "This is **Virtual Engineer** — an AI-powered incident-diagnosis copilot we built to help our L2 and L3 engineers diagnose complex incidents faster. It's analyzing real ServiceNow data: about 59,000 incidents, 70,000 tasks, 4,000 changes, and our problem records — all correlated in one place. Everything you'll see is powered by Claude, and it's built on the Deloitte brand."

### Scene 2 — Root Cause (0:30–2:00)  ⭐ the hero feature
**SHOW:** Root Cause tab. In **Option B**, open the **Configuration Item** dropdown — show it's grouped (Applications, Network, Database, Infrastructure…). Select **BeeHive Platform**.
**SAY:** "Say a platform is misbehaving. I either type the incident number, or pick the configuration item — and notice the CIs are grouped by type. I'll pick BeeHive Platform."
**SHOW:** Wait for the result card to render.
**SAY:** "In seconds, the copilot has correlated every incident, problem, and change on this CI — and Claude has written a full root-cause analysis. It gives the **most likely root cause**, the **evidence** with specific ticket numbers, whether a **recent change** may be responsible, **recommended actions**, and a clear **Conclusion** with the next step."
**SHOW:** Expand the collapsible **evidence** sections (incidents, problems, changes, similar).
**SAY:** "And it's not a black box — every claim is backed by the underlying tickets, right here. That's hours of manual cross-referencing, done instantly."
**SHOW:** Click **✕ Clear**.

### Scene 3 — Change Impact (2:00–2:45)
**SHOW:** Change Impact tab → **Analyze changes**.
**SAY:** "Next — change impact. This finds changes that were followed by a spike of incidents on the same CI, which is our signal for change-induced incidents. Claude reads the pattern and tells us which changes are genuinely risky versus coincidental — because high-volume systems see incidents regardless. This is how we catch a bad change before it spreads."

### Scene 4 — Similar Incidents (2:45–3:30)
**SHOW:** Similar Incidents tab → type *"user cannot connect to VPN after password change"* → **Find & advise**.
**SAY:** "Now knowledge retrieval. An engineer describes a new issue in plain language. The copilot finds the most similar past incidents and — crucially — synthesizes how they were actually resolved into a step-by-step recommendation. New engineers instantly get the team's hard-won experience."

### Scene 5 — Hotspots & Trends (3:30–4:15)
**SHOW:** Hotspots tab → **Load portfolio**. Then change **Break down by** between Category, Assignment Group, Priority.
**SAY:** "For the leadership view — hotspots and trends. Where do incidents concentrate? Which teams and systems carry the load? Claude writes an executive summary — it even flagged a data-quality gap in our SLA field. And I can re-slice the data live by any dimension, with each category color-coded."

### Scene 6 — Bring-your-own data (4:15–5:15)  ⭐ the differentiator
**SHOW:** Click **⬆ Upload my data** (screen clears to the upload box). Choose 4 files (INC/PRB/CR/TSK). Click **Analyze my data**.
**SAY:** "Here's what makes this reusable for any team. I click Upload my data — the screen clears to focus on the upload. I drop in my own Incident, Problem, Change, and Task exports. The copilot **auto-detects** each file's type, builds a dataset that's **completely isolated to my session**, and switches to analyzing *my* data."
**SHOW:** Point at the stat cards now showing the uploaded counts; toggle **Demo data ⇄ My data**.
**SAY:** "Notice the counts switched to my files. One toggle flips between the demo data and my data. Same four capabilities — now on data I just brought, privately."

### Scene 7 — Under the hood / what we wrote (5:15–6:15)
**SHOW:** Switch to the GitHub tab. Scroll the file tree; open `app/diagnostics.py` and `app/datasources.py` briefly; open `app/connectors/`; show `tests/`.
**SAY:** "Briefly under the hood — this is the codebase, public on GitHub. `diagnostics.py` is the AIOps brain that pairs deterministic SQL correlation with Claude's reasoning. `datasources.py` loads the ITSM data into an indexed database with full-text search. The `connectors` folder means we can swap the data source — there's already a ready-to-go **ServiceNow REST connector** — so going live is a config change, not a rebuild. And it's covered by automated tests."
**SHOW:** Show the commit history.
**SAY:** "And the whole thing was built conversationally with **Claude Code** — every feature you saw, in days, not months."

### Scene 8 — Close (6:15–6:45)
**SHOW:** Back to the home page.
**SAY:** "So that's Virtual Engineer: it turns our engineers into AI-augmented experts — faster root cause, change-risk detection, instant access to past resolutions, and a portfolio view for leadership. It's bring-your-own-data, on-brand, and ready to connect live to ServiceNow and our monitoring tools next. Thanks for watching."

---

## Tips
- Speak to the **outcome** ("hours → seconds", "evidence-backed", "private to your session"), not the mechanics.
- If a Claude call is slow on camera, keep narrating the evidence tables while it finishes.
- Total runtime target: **6–7 minutes**. For a 3-minute cut, keep Scenes 1, 2, 6, 8.
