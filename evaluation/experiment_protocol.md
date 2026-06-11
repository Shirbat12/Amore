# A-MORE — Experiment Protocol (project book §4.2)

## Participants
- **N = 50** active dating-app users, ages **23–30**, seeking a relationship.
- Duration: **4 weeks**.

## Stage A — Recruitment & baseline (before installing the extension)
Each participant fills a short intake questionnaire to extract their personal
**baseline**:
1. How many **first dates** in the last month?
2. How many of those became **second dates**? (→ baseline conversion ratio)
3. General dating **burnout** on a 1–10 scale.

## Stage B — Trial period & real-time feedback
Participants install the extension and date as usual. After each date the system
sends a smartphone notification asking them to fill the **Vibe questionnaire**
(triggered after a detected phone-number exchange + a short delay).

The questionnaire combines:
- continuous **VAS sliders** (interest/flow, attraction/chemistry, reality match, comfort);
- two **word-bank clouds** (conversation topics, atmosphere), ≤ 3 tags each;
- one **binary** "second date?" question (yes / no / maybe);
- one **free-text** sentence (→ NLP tag extraction).

## Analysis plan
Because the per-user model needs a minimum history, prediction accuracy is
evaluated **only on the sub-sample that passes `MIN_DATES`**. The other KPIs
(response rate, usability, conversion ratio) are collected on the full sample.

## Success criteria (§4.1)
| KPI | Target |
|-----|--------|
| Conversion ratio uplift | **> +20%** vs personal baseline |
| Prediction accuracy (LOO Spearman) | **ρ ≥ 0.4** for users past `MIN_DATES` |
| Usability (SUS) | **> 68**, aiming for 80+ |
| Vibe response rate | **≥ 60%** of reported dates |

## Ablation & failure analysis
- Re-run prediction with the NLP tags removed (`no_nlp_tags`) to measure the
  contribution of module 2.3.1.
- A `shuffled_control` that breaks the profile↔outcome link confirms the signal
  is real, not an artifact.
- Inspect the records with the largest predicted-vs-actual error for failure
  analysis.
