# Deploying Virtual Engineer (durable hosted demo)

This deploys a **public, always-available** copy of the app that serves the
**synthetic demo data** in `sample_data/` — never the real internal ITSM data.

## What is (and isn't) deployed
- ✅ The app + the **synthetic demo dataset** (`sample_data/`, committed, 100% fake).
- ❌ **No real data** — `data/` is git-ignored and not in the repo, so the host can't see it. On the host the app automatically falls back to `sample_data/`.
- ❌ **No secrets in the repo** — the Anthropic API key is set as a host **environment variable**, never committed.
- Without a key, the app still runs in **offline heuristic mode** (good enough to show the flow); with a key, you get full Claude analysis.

---

## Recommended: Render (free, deploys from GitHub)

1. Go to **https://render.com** and sign up / log in (you can use "Sign in with GitHub").
2. Click **New +** → **Blueprint**.
3. Connect your GitHub and pick **`surpanda1977/virtual-engineer`**. Render reads `render.yaml` automatically.
4. When prompted for the `ANTHROPIC_API_KEY` env var, paste your key (kept secret).
   *Or leave it blank to run in offline heuristic mode.*
5. Click **Apply** / **Create**. First build takes ~2–3 minutes.
6. You get a public URL like `https://virtual-engineer.onrender.com` — share that with leadership.

**Manual alternative** (if you skip the blueprint): New + → **Web Service** → connect the repo →
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Add env var `ANTHROPIC_API_KEY` (secret).

### Railway / Heroku-style hosts
The repo also includes a `Procfile` and `runtime.txt`, so Railway (railway.app) works the same way: New Project → Deploy from GitHub repo → add the `ANTHROPIC_API_KEY` variable.

---

## Good to know
- **Cold starts:** Render's free tier sleeps after ~15 min idle; the first hit then takes ~30–60s to wake. Fine for a demo; upgrade the plan to keep it warm.
- **Updating:** push to `main` on GitHub → the host auto-redeploys.
- **Data builds at startup** from `sample_data/` into an ephemeral SQLite DB — nothing to manage.

## ⚠️ Before you make it public with a key
A public URL that uses **your** API key means anyone who finds it can run Claude calls **on your account**. Recommended:
- Set a **spend limit** on the Anthropic key (console.anthropic.com).
- Add a lightweight **password gate** so only people you share the password with can use it. *(Not built yet — ask and I'll add a simple `DEMO_PASSWORD` env-var gate in ~10 minutes.)*
- Or deploy **without** a key (offline heuristic mode) for a fully no-risk public demo.
