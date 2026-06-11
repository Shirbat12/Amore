# A-MORE

**Analytics for Meaningful Online Romantic Encounters** — a decision-support
layer over dating apps. Instead of optimizing the *quantity* of matches, A-MORE
closes the loop between the dry digital profile and the real experience of the
date: after each date the user fills a short VAS "Vibe" questionnaire, an LLM
encodes the free text into a closed list of personality tags, and a per-user
statistical engine learns which profile features actually predict a good date —
then paints a real-time match score on new profiles.

> Course capstone (BGU, SISE). This repo is the engineering implementation of the
> architecture in the project book; module numbers in comments (`§2.3.x`) map to
> that document.

## Architecture (3 tiers)

```
Profile (DOM)  ->  Match-score overlay  ->  Real date  ->  Vibe questionnaire
      ^                                                            |
      |                                                            v
Dashboard insights  <-  Per-user model update  <-  NLP tag extraction
```

- **Client** — Chrome extension (`extension/`), Vibe questionnaire
  (`questionnaire/`), insights dashboard (`dashboard/`).
- **Server** — FastAPI app (`server/`) with the 4-module pipeline.
- **Storage** — SQLite relational store + JSON document store (`.data/`, created
  on first run).

### The pipeline (`server/pipeline/`)
| Module | File | Role |
|---|---|---|
| §2.3.1 | `quantify_experience.py` | free text → closed tags + sentiment → `DateRecord` |
| §2.3.2 | `revealed_preferences.py` | cross features → revealed-preference tables |
| §2.3.3 | `predictor.py` | Spearman (+FDR) explanation **and** Ridge prediction (cold-start prior) |
| §2.3.4 | `presentation.py` | overlay + dashboard payloads |

## Quick start

```bash
# 1. install (from the repo root)
python -m venv .venv
.venv\Scripts\activate            # Windows;  source .venv/bin/activate on mac/linux
pip install -r requirements.txt

# 2. seed synthetic data (optional, lets you see charts immediately)
python -m data.samples.generate_samples

# 3. run the API
uvicorn server.app:app --reload   # http://localhost:8000  (docs at /docs)

# 4. run the tests
pytest -q
```

The backend runs **without** a Gemini key — it falls back to a deterministic
offline tagger. To use the real model, copy `.env.example` to `.env` and set
`GEMINI_API_KEY`.

### Front-end
- **Dashboard:** serve the repo over any static server and open
  `dashboard/index.html?api=http://localhost:8000&user=demo_user`.
- **Questionnaire:** open `questionnaire/vibe_form.html?user=demo_user`.
- **Extension:** `chrome://extensions` → *Load unpacked* → select `extension/`.
  Targets the OkCupid web client (`okcupid.com`); the overlay needs the live DOM
  selectors filled in (`extension/content/dom_scraper.js`).

## Team / ownership
- **Shir** — data-science & learning core (`pipeline/revealed_preferences.py`,
  `pipeline/predictor.py`, `evaluation/`, `data/`).
- **Liel** — backend, NLP & data layer (`server/app.py`, `api/`, `nlp/`,
  `models/`, `db/`, `pipeline/quantify_experience.py`).
- **Michal** — front-end (`extension/`, `questionnaire/`, `dashboard/`,
  `assets/`, `pipeline/presentation.py`).

## Repo layout
```
server/        FastAPI app + pipeline + NLP + models + db
extension/     Chrome MV3 extension (scraper, overlay, popup)
questionnaire/ post-date Vibe form
dashboard/     decision-support dashboard (Chart.js)
assets/        shared front-end design tokens (theme.css)
evaluation/    KPIs + ablation + experiment protocol
data/          tag taxonomy + synthetic sample generator
tests/         pytest suite
```
