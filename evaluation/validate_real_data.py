"""Validate that the A-MORE scoring engine actually works, on the REAL pilot data.

The goal of this script is to answer one question for the project book and the
final presentation: *does the algorithm's score track real date outcomes, more
than chance?* — not just "does it emit a number".

Why it is built the way it is
-----------------------------
The pilot collected ~21 dates spread over ~17 people (mostly 1 date each). That
is far too little to validate a *per-user* model, so we validate the **engine at
the population level**, with a deliberately **low-dimensional** predictor so the
small sample is not fatal:

  * Model A - "revealed-preference prototype": predict a date's outcome from the
    average outcome of past dates that shared its features. This is exactly what
    module 2.3.2 (`learn_revealed_preferences`) computes, so it tests the core
    idea directly.
  * Mean baseline: always predict the training average. The bar to beat.
  * Permutation control: shuffle the outcomes and re-run; the signal must
    collapse. Comparing the real result to this null gives a real p-value even
    at N=21.
  * Model B - the deployed RidgeCV predictor, reported for honesty (it is
    high-dimensional, so on this tiny sample it tends toward the mean).

Everything is leave-one-out (LOO): for each date we learn from the other 20 and
predict the held-out one. Metrics: Spearman rho (rank agreement) and MAE on the
0-100 scale.

Run:  python -m evaluation.validate_real_data
Outputs a printed report and PNG plots under evaluation/reports/.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy.stats import spearmanr

import matplotlib
matplotlib.use("Agg")  # no display needed; we save PNGs
import matplotlib.pyplot as plt

from server import config
from server.models import DateRecord
from server.pipeline.predictor import fit_predictor, learn_correlations
from server.pipeline.revealed_preferences import learn_revealed_preferences
from server.pipeline.questionnaire_loader import load_questionnaire_history

REPORTS_DIR = Path(__file__).resolve().parent / "reports"
N_PERMUTATIONS = 300
RNG = np.random.default_rng(42)  # fixed seed -> reproducible report


# ---------------------------------------------------------------------------
# The predictors we compare (all leave-one-out)
# ---------------------------------------------------------------------------
def _prototype_predict(profile_tokens: List[str], vas_mean: Dict[str, float],
                       global_mean: float) -> float:
    """Model A: average the learned per-feature outcome over the profile's tokens."""
    vals = [vas_mean[t] for t in profile_tokens if t in vas_mean]
    return float(np.mean(vals)) if vals else global_mean


def loo_prototype(records: List[DateRecord]) -> Tuple[np.ndarray, np.ndarray]:
    preds, actuals = [], []
    for i, held in enumerate(records):
        train = records[:i] + records[i + 1:]
        _, vas_mean = learn_revealed_preferences(train)
        global_mean = float(np.mean([r.vas for r in train]))
        preds.append(_prototype_predict(held.profile, vas_mean, global_mean))
        actuals.append(held.vas)
    return np.array(preds), np.array(actuals)


def loo_mean_baseline(records: List[DateRecord]) -> Tuple[np.ndarray, np.ndarray]:
    preds, actuals = [], []
    for i, held in enumerate(records):
        train = records[:i] + records[i + 1:]
        preds.append(float(np.mean([r.vas for r in train])))
        actuals.append(held.vas)
    return np.array(preds), np.array(actuals)


def loo_ridge(records: List[DateRecord]) -> Tuple[np.ndarray, np.ndarray]:
    preds, actuals = [], []
    for i, held in enumerate(records):
        train = records[:i] + records[i + 1:]
        predictor = fit_predictor(train)
        pred = max(0.0, min(100.0, predictor.predict_one(held.profile)))
        preds.append(pred)
        actuals.append(held.vas)
    return np.array(preds), np.array(actuals)


# ---------------------------------------------------------------------------
# Metrics + significance
# ---------------------------------------------------------------------------
def _metrics(preds: np.ndarray, actuals: np.ndarray) -> Dict[str, float]:
    mae = float(np.mean(np.abs(preds - actuals)))
    if len(np.unique(preds)) < 2:               # constant predictions -> rho undefined
        return {"rho": float("nan"), "p": float("nan"), "mae": mae}
    res = spearmanr(preds, actuals)
    return {"rho": float(res.statistic), "p": float(res.pvalue), "mae": mae}


def permutation_pvalue(records: List[DateRecord], observed_rho: float) -> float:
    """Empirical p-value: how often does shuffled data reach the observed rho?"""
    vas = np.array([r.vas for r in records])
    hits = 0
    for _ in range(N_PERMUTATIONS):
        shuffled = vas[RNG.permutation(len(vas))]
        perm_records = [r.model_copy(update={"vas": float(v)})
                        for r, v in zip(records, shuffled)]
        preds, actuals = loo_prototype(perm_records)
        m = _metrics(preds, actuals)
        if not np.isnan(m["rho"]) and m["rho"] >= observed_rho:
            hits += 1
    return (hits + 1) / (N_PERMUTATIONS + 1)


def significant_features(records: List[DateRecord], top: int = 12) -> List[Tuple[str, float, float]]:
    """FDR-corrected Spearman of each feature/tag against the outcome."""
    corr = learn_correlations(records)
    ranked = sorted(corr.items(), key=lambda kv: abs(kv[1][0]), reverse=True)
    return [(name, rho, q) for name, (rho, q) in ranked[:top]]


def lift_table(preds: np.ndarray, actuals: np.ndarray) -> List[Tuple[str, int, float]]:
    """Bucket predictions into terciles and show the mean actual outcome per bucket."""
    order = np.argsort(preds)
    buckets = np.array_split(order, 3)
    labels = ["low", "mid", "high"]
    out = []
    for lab, idx in zip(labels, buckets):
        if len(idx):
            out.append((lab, len(idx), float(np.mean(actuals[idx]))))
    return out


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def save_plots(proto: Tuple[np.ndarray, np.ndarray], lift: List[Tuple[str, int, float]]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    preds, actuals = proto

    plt.figure(figsize=(5, 5))
    plt.scatter(preds, actuals, c="#c16e7f")
    lims = [0, 100]
    plt.plot(lims, lims, "--", color="#888", linewidth=1)
    plt.xlabel("Predicted score"); plt.ylabel("Actual outcome (VAS)")
    plt.title("Predicted vs actual (leave-one-out)")
    plt.xlim(lims); plt.ylim(lims)
    plt.tight_layout(); plt.savefig(REPORTS_DIR / "predicted_vs_actual.png", dpi=120)
    plt.close()

    if lift:
        plt.figure(figsize=(5, 4))
        plt.bar([l[0] for l in lift], [l[2] for l in lift], color="#c16e7f")
        plt.ylabel("Mean actual outcome (VAS)"); plt.ylim(0, 100)
        plt.title("Lift: outcome rises with predicted score")
        plt.tight_layout(); plt.savefig(REPORTS_DIR / "lift.png", dpi=120)
        plt.close()


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def main() -> None:
    records, baseline_df, date_df = load_questionnaire_history()
    n = len(records)
    users = {r.user_id for r in records}

    print("=" * 64)
    print("A-MORE — REAL-DATA VALIDATION REPORT")
    print("=" * 64)
    print(f"Dates: {n}  |  Users: {len(users)}  |  "
          f"VAS range: {min(r.vas for r in records):.0f}–{max(r.vas for r in records):.0f}")
    print("Per-user model NOT validated here (too few dates/user); this validates")
    print("the population engine — do features carry real outcome signal?\n")

    proto = loo_prototype(records)
    mean_bl = loo_mean_baseline(records)
    ridge = loo_ridge(records)

    m_proto, m_mean, m_ridge = _metrics(*proto), _metrics(*mean_bl), _metrics(*ridge)

    print("LEAVE-ONE-OUT ACCURACY (predicted vs actual)")
    print("-" * 64)
    print(f"{'model':<34}{'rho':>8}{'p':>9}{'MAE':>9}")
    print(f"{'Model A: revealed-pref prototype':<34}"
          f"{m_proto['rho']:>8.3f}{m_proto['p']:>9.3f}{m_proto['mae']:>9.1f}")
    print(f"{'Mean baseline (beat this)':<34}"
          f"{'--':>8}{'--':>9}{m_mean['mae']:>9.1f}")
    print(f"{'Model B: deployed RidgeCV':<34}"
          f"{m_ridge['rho']:>8.3f}{m_ridge['p']:>9.3f}{m_ridge['mae']:>9.1f}")

    print("\nPERMUTATION TEST (is Model A's signal real?)")
    print("-" * 64)
    if not np.isnan(m_proto["rho"]):
        p_perm = permutation_pvalue(records, m_proto["rho"])
        verdict = "REAL signal (p<0.05)" if p_perm < 0.05 else "not significant at this N"
        print(f"observed rho = {m_proto['rho']:.3f}  |  permutation p = {p_perm:.3f}  ->  {verdict}")
    else:
        print("Model A produced constant predictions — cannot run permutation test.")

    print("\nMODEL A BEATS MEAN BASELINE?")
    print("-" * 64)
    diff = m_mean["mae"] - m_proto["mae"]
    print(f"MAE improvement over mean baseline: {diff:+.1f} points "
          f"({'better' if diff > 0 else 'not better'})")

    print("\nFEATURES MOST CORRELATED WITH A GOOD DATE (FDR q-value)")
    print("-" * 64)
    for name, rho, q in significant_features(records):
        star = " *" if q <= config.SIGNIFICANT_Q else ""
        print(f"  rho={rho:+.2f}  q={q:.3f}{star}   {name}")
    print(f"  (* = significant at q<={config.SIGNIFICANT_Q})")

    print("\nLIFT (mean actual outcome by predicted tercile)")
    print("-" * 64)
    for lab, count, mean_actual in lift_table(*proto):
        print(f"  {lab:<5} (n={count}):  mean actual VAS = {mean_actual:.1f}")

    save_plots(proto, lift_table(*proto))
    print(f"\nPlots saved to: {REPORTS_DIR}")
    print("=" * 64)


if __name__ == "__main__":
    main()
