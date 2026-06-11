"""Success metrics defined under the SMART principle (project book section 4.1).

Each function is pure: it takes data and returns a number, so it can be run on
pilot exports or on synthetic data in tests.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
from scipy.stats import spearmanr

from server import config
from server.models import DateRecord
from server.pipeline.predictor import fit_predictor


# 1. Pairing effectiveness - conversion ratio (second / first dates) ----------
def conversion_ratio(history: List[DateRecord]) -> float:
    first = len(history)
    if first == 0:
        return 0.0
    seconds = sum(1 for d in history if d.second_date is True)
    return 100.0 * seconds / first


def conversion_uplift(baseline_ratio: float, current_ratio: float) -> float:
    """Relative uplift vs the user's personal baseline (target: +20%)."""
    if baseline_ratio <= 0:
        return float("inf") if current_ratio > 0 else 0.0
    return (current_ratio - baseline_ratio) / baseline_ratio


# 2. Decision alignment -------------------------------------------------------
def decision_alignment(
    selected_profiles: List[List[str]], positive_features: set
) -> float:
    """Share of chosen profiles that carry the user's known positive features."""
    if not selected_profiles:
        return 0.0
    hits = sum(
        1 for p in selected_profiles if positive_features.intersection(p)
    )
    return 100.0 * hits / len(selected_profiles)


# 3. Usability - SUS ----------------------------------------------------------
def sus_score(responses: List[int]) -> float:
    """Standard SUS scoring for one 10-item response (each 1-5) -> 0-100."""
    if len(responses) != 10:
        raise ValueError("SUS needs exactly 10 item responses")
    odd = sum(responses[i] - 1 for i in range(0, 10, 2))      # positive items
    even = sum(5 - responses[i] for i in range(1, 10, 2))     # negative items
    return (odd + even) * 2.5


def mean_sus(all_responses: List[List[int]]) -> float:
    if not all_responses:
        return 0.0
    return float(np.mean([sus_score(r) for r in all_responses]))


# 4. Vibe response rate -------------------------------------------------------
def vibe_response_rate(completed: int, reported_dates: int) -> float:
    if reported_dates == 0:
        return 0.0
    return completed / reported_dates


# 5. Prediction accuracy - leave-one-out (the system core) -------------------
def prediction_accuracy(history: List[DateRecord]) -> Tuple[Optional[float], Optional[float]]:
    """Return (spearman_rho, MAE) of LOO predicted vs reported VAS.

    Returns (None, None) if there isn't enough history to evaluate a per-user
    model (below MIN_DATES + 1 the held-out fit is itself a cold-start prior).
    """
    if len(history) <= config.MIN_DATES:
        return None, None
    preds, actuals = [], []
    for i, held in enumerate(history):
        rest = history[:i] + history[i + 1:]
        predictor = fit_predictor(rest)
        pred = max(0.0, min(100.0, predictor.predict_one(held.profile)))
        preds.append(pred)
        actuals.append(held.vas)
    if len(set(preds)) < 2 or len(set(actuals)) < 2:
        return None, float(np.mean(np.abs(np.array(preds) - np.array(actuals))))
    rho = float(spearmanr(preds, actuals).statistic)
    mae = float(np.mean(np.abs(np.array(preds) - np.array(actuals))))
    return rho, mae


def meets_targets(history: List[DateRecord]) -> dict:
    """Convenience summary against the section 4.1 success criteria."""
    rho, mae = prediction_accuracy(history)
    return {
        "conversion_ratio": conversion_ratio(history),
        "prediction_rho": rho,
        "prediction_mae": mae,
        "prediction_target_met": (rho is not None and rho >= config.TARGET_PREDICTION_RHO),
    }
