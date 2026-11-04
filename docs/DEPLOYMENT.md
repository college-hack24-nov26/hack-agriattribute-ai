# Deploying AgriAttribute AI

**Status (4 Nov 2026):** the current version runs locally (`streamlit run app.py`). The two older Streamlit Cloud
links from Hack Core 2026 redirect to a Streamlit login page and serve the old code, so there is **no public demo
of this version yet**.

**Deployment check (4 Nov 2026):** a clean install of `requirements.txt` in a fresh Python 3.13 environment resolved
Streamlit 1.66.1, scikit-learn 1.9.1 and SHAP 0.54.1, and all 13 tabs opened with no errors **with no API keys set**
(every service fell back gracefully). CI also runs the tests on Python 3.12.

## What the app needs

| Item | Value |
|---|---|
| Entry file | `app.py` |
| Python | 3.12 (tested in CI); 3.13 also installs cleanly |
| Packages | `requirements.txt` (runtime only; ~1 GB less than before: no torch/transformers) |
| Memory | about 1 GB (Random Forest + SHAP + Plotly) |
| Writable disk | yes, for `scratch/` (local fallback store) and `data/i18n/` (new translations); both may reset on redeploy |
| Cold start | about 30–60 s for the first visitor after a restart (model and libraries load once) |

### Secrets (all optional; the app degrades gracefully without each)

| Name | Used for | Without it |
|---|---|---|
| `GEMINI_API_KEY` | assistant, photo check, translating new text | offline rule-based answers; cached translations still work |
| `OPENWEATHER_API_KEY` | live weather and forecast | cached / regional weather |
| `OPENWEATHER_MAPS_KEY` | weather map overlays | base map only |
| `SUPABASE_URL`, `SUPABASE_SECRET_KEY` (or `SUPABASE_PUB_KEY`) | shared database | saves to local files on the server |
| `GEMINI_MODELS` | model fallback order | default list |

Never commit these. `.env` is git-ignored; on a host they go into the host's secret store.

## Option A — Streamlit Community Cloud (recommended, free, permanent link)

1. Sign in at <https://share.streamlit.io> with the GitHub account that can read the repository.
2. **New app** → repository, branch `main`, main file `app.py`, *Advanced settings* → Python **3.12**.
3. Paste the secrets in TOML form (values from your own `.env`):
   ```toml
   GEMINI_API_KEY = "..."
   OPENWEATHER_API_KEY = "..."
   OPENWEATHER_MAPS_KEY = "..."
   SUPABASE_URL = "..."
   SUPABASE_SECRET_KEY = "..."
   ```
   Root-level secrets are exposed as environment variables, which is how the app reads them.
4. Pick a subdomain (for example `agriattribute-ha097`) and **Deploy**. First build takes a few minutes.
5. Set sharing to **public** if judges must open it without signing in.

**If the organisation repository is not listed:** Streamlit Cloud needs access to the `college-hack24-nov26`
organisation, which only an organisation owner can grant. Ask a coordinator, or deploy from a private copy in your
own GitHub account (keep it private so the code is not shared with other teams).

## Option B — public link from the laptop in 5 minutes (backup for the demo)

A Cloudflare quick tunnel gives a temporary `https://….trycloudflare.com` link to the app running on the laptop.
No account is needed; the link works only while the laptop and the app are running.

```bash
streamlit run app.py --server.port 8511
cloudflared tunnel --url http://localhost:8511
```

`cloudflared` is a single executable from Cloudflare (<https://github.com/cloudflare/cloudflared/releases>).
Anyone with the link uses your API quota, so stop the tunnel after judging.

## Option C — Docker (any container host)

```bash
docker build -t agriattribute .
docker run -p 8501:8501 --env-file .env agriattribute
```

## Checks after deploying

1. The home screen loads and shows a live temperature (OpenWeather key works).
2. Today → *Where these numbers come from* shows Supabase as LIVE (database works).
3. Switch the language to Marathi: the navbar changes within a second.
4. AI Chat answers a question (Gemini works; if quota is exhausted it falls back to another model).
5. Yield tab → the model card shows "SIMULATED TRAINING DATA · NOT FIELD-VALIDATED".
