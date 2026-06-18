# A-MORE — Front-end API reference

All four endpoints live on one backend. Default base URL (local dev):

```
http://localhost:8000
```

## Where the base URL is configured

There are two runtime contexts, each with its own default (both point at the URL
above):

| Context | Where the URL/user is set | How to override |
|---|---|---|
| Dashboard + Questionnaire (web) | `assets/config.js` (`window.AMORE_CONFIG`) | URL query string: `?api=...&user=...` |
| Chrome extension | `extension/background/service_worker.js` (`DEFAULTS`) | the extension popup (API base + user fields) |

The web pages share one config file; load `assets/config.js` **before** any
script that calls the API. The extension can't read that file (different runtime),
so it keeps its own default.

## Which interface calls what

| Interface | Endpoint | Method |
|---|---|---|
| Extension — overlay (`overlay.js` → `service_worker.js`) | `/score` | POST |
| Extension — swipe logger (`selection_logger.js` → `service_worker.js`) | `/selection` | POST |
| Questionnaire (`vibe_form.js`) | `/feedback` | POST |
| Dashboard (`dashboard/src/api.js`) | `/insights/{user_id}` | GET |

---

## POST /score

Real-time match score for a scraped profile (overlay).

**Request**
```json
{
  "user_id": "demo_user",
  "profile": ["age:27-30", "interest:travel", "orientation:straight"]
}
```

**Response**
```json
{
  "score": 82.8,
  "confidence": "high",
  "reasons": [
    { "feature": "interest:travel", "rho": 0.65, "q": 0.02, "text": "..." }
  ]
}
```
`confidence` is `"high"` / `"medium"` / `"low"`. `reasons` may be empty before
enough data is accrued.

## POST /feedback

Ingest one post-date Vibe questionnaire.

**Request** (all fields except `user_id` are optional / defaulted)
```json
{
  "user_id": "demo_user",
  "profile": ["interest:travel", "hobby:cooking"],
  "vas_scores": { "interest_flow": 80, "attraction": 75, "reality_match": 60, "comfort": 70 },
  "topic_tags": ["טיולים וחו\"ל"],
  "vibe_tags": ["מצחיק ומשעשע"],
  "second_date": true,
  "free_text": "היה ממש כיף, הוא היה מצחיק ומקשיב"
}
```
`second_date`: `true` (yes) / `false` (no) / `null` (maybe or unanswered). The
backend treats `vas_scores.attraction` as the primary outcome (falls back to the
mean of all sliders if absent).

**Response**
```json
{ "id": "…", "vas": 75.0, "extracted_tags": ["מצחיק", "מקשיב"], "sentiment": 1.0 }
```

## POST /selection

Log one Like/Pass swipe (feeds the Decision-Alignment KPI).

**Request**
```json
{ "user_id": "demo_user", "action": "like", "profile": ["interest:travel"] }
```
`action` must be exactly `"like"` or `"pass"`.

**Response**
```json
{ "status": "logged", "action": "like", "n_tokens": 1 }
```
The extension sends this fire-and-forget and ignores the body.

## GET /insights/{user_id}

Everything the dashboard renders.

**Response**
```json
{
  "n_dates": 31,
  "heatmap": [ { "feature": "interest:travel", "rho": 0.65, "q": 0.02 } ],
  "funnel": { "first_dates": 30, "second_dates": 12, "maybe": 5 },
  "scatter": [ { "predicted": 80, "actual": 78 } ],
  "boxplots": { "מצחיק ומשעשע": [80, 75, 90] },
  "insights": [
    { "text": "'travel' עושה לך טוב — הדייטים האלה נוטים להצליח",
      "direction": "up", "strength": "strong", "feature": "travel" }
  ],
  "decision_alignment": {
    "rate": 66.7,
    "n_selected": 3,
    "positive_features": ["hobby:cooking", "interest:travel"]
  }
}
```
`decision_alignment.rate` is `null` when there isn't enough signal yet (no likes
logged, or no significant positive features) — render an empty state, not `0%`.

---

## Quick local check

With the backend running (`uvicorn server.app:app --reload`), every endpoint is
browsable and testable at `http://localhost:8000/docs` (FastAPI's auto docs).
