"""Module 2.3.3 - predict a match score with an explainable core.

Two layers, exactly as in the project book:
  1. Exploratory / explainable: per-feature Spearman correlation with the VAS
     outcome, FDR-corrected (Benjamini-Hochberg) -> a transparent reason matrix.
  2. Predictive: leave-one-out-tuned Ridge regression on a per-user design
     matrix, with a population prior for cold start (< MIN_DATES).

The design matrix for *prediction* uses only signals available before a date
happens: the dry profile tokens, plus the traits those tokens are expected to
reveal (read from module 2.3.2). That keeps train-time and score-time symmetric.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import RidgeCV
from statsmodels.stats.multitest import multipletests

from server import config
from server.models import DateRecord
from server.nlp.closed_tags import CLOSED_TAGS
from server.pipeline.revealed_preferences import learn_revealed_preferences


# ----------------------------------------------------------------------------
# 1. Explainable correlation layer
# ----------------------------------------------------------------------------
def _explanatory_columns(history: List[DateRecord]) -> Tuple[Dict[str, list], list]:
    """Build retrospective columns: profile tokens, observed tags, sentiment."""
    features = sorted({f for d in history for f in d.profile})
    columns: Dict[str, list] = {}
    for f in features:
        columns[f"profile:{f}"] = [1 if f in d.profile else 0 for d in history]
    for tag in CLOSED_TAGS:
        col = [1 if tag in d.tags else 0 for d in history]
        if any(col):                              # skip tags never seen
            columns[f"trait:{tag}"] = col
    columns["sentiment"] = [d.sentiment for d in history]
    y = [d.vas for d in history]
    return columns, y


def learn_correlations(history: List[DateRecord]) -> Dict[str, Tuple[float, float]]:
    """Return {feature: (spearman_rho, q_value)} - the explainable reason matrix."""
    columns, y = _explanatory_columns(history)
    raw: Dict[str, Tuple[float, float]] = {}
    for name, col in columns.items():
        if len(set(col)) < 2:                     # constant column -> undefined
            continue
        res = spearmanr(col, y)
        rho = float(res.statistic)
        if np.isnan(rho):
            continue
        raw[name] = (rho, float(res.pvalue))

    if not raw:
        return {}
    names = list(raw)
    pvals = [raw[n][1] for n in names]
    _, qvals, _, _ = multipletests(pvals, method=config.FDR_METHOD)
    return {n: (raw[n][0], float(q)) for n, q in zip(names, qvals)}


# ----------------------------------------------------------------------------
# 2. Predictive layer
# ----------------------------------------------------------------------------
class FeatureSpace:
    """Vectorizes a profile into [dry-token presence | expected-trait scores]."""

    def __init__(self, history: List[DateRecord]) -> None:
        self.profile_vocab = sorted({f for d in history for f in d.profile})
        self.trait_vocab = list(CLOSED_TAGS)
        self.trait_dist, _ = learn_revealed_preferences(history)

    def row(self, profile_tokens: List[str]) -> np.ndarray:
        present = [1.0 if f in profile_tokens else 0.0 for f in self.profile_vocab]
        # Expected trait scores = average trait distribution over the profile's tokens.
        expected = np.zeros(len(self.trait_vocab))
        contributing = [f for f in profile_tokens if f in self.trait_dist]
        if contributing:
            for f in contributing:
                dist = self.trait_dist[f]
                for j, trait in enumerate(self.trait_vocab):
                    expected[j] += dist.get(trait, 0.0)
            expected /= len(contributing)
        return np.array(present + expected.tolist(), dtype=float)

    def matrix(self, history: List[DateRecord]) -> Tuple[np.ndarray, np.ndarray]:
        X = np.vstack([self.row(d.profile) for d in history])
        y = np.array([d.vas for d in history], dtype=float)
        return X, y


class PriorPredictor:
    """Cold-start predictor: returns the population/historical prior mean."""

    def __init__(self, prior_mean: float = 50.0) -> None:
        self.prior_mean = float(prior_mean)

    def predict_one(self, profile_tokens: List[str]) -> float:
        return self.prior_mean


class RidgePredictor:
    """Per-user regularized predictor over the FeatureSpace."""

    def __init__(self, space: FeatureSpace, model: RidgeCV) -> None:
        self.space = space
        self.model = model

    def predict_one(self, profile_tokens: List[str]) -> float:
        x = self.space.row(profile_tokens).reshape(1, -1)
        return float(self.model.predict(x)[0])


def fit_predictor(history: List[DateRecord]):
    """Return a predictor object exposing .predict_one(profile_tokens)."""
    if len(history) < config.MIN_DATES:           # cold start
        prior = float(np.mean([d.vas for d in history])) if history else 50.0
        return PriorPredictor(prior)
    space = FeatureSpace(history)
    X, y = space.matrix(history)
    # alpha tuned per-user by leave-one-out CV - data is tiny.
    model = RidgeCV(alphas=config.ALPHA_GRID).fit(X, y)
    return RidgePredictor(space, model)


def confidence_for(n_dates: int) -> str:
    if n_dates < config.CONF_MEDIUM_DATES:
        return "low"
    if n_dates < config.CONF_HIGH_DATES:
        return "medium"
    return "high"


def score_profile(
    history: List[DateRecord], profile_tokens: List[str]
) -> Dict[str, object]:
    """Full scoring entry point used by the API: score + confidence + reasons."""
    predictor = fit_predictor(history)
    raw = predictor.predict_one(profile_tokens)
    score = max(0.0, min(100.0, raw))

    reasons = []
    if len(history) >= config.MIN_DATES:
        corr = learn_correlations(history)
        present = {f"profile:{t}" for t in profile_tokens}
        ranked = sorted(
            (
                (name, rho, q)
                for name, (rho, q) in corr.items()
                if name in present and q <= config.SIGNIFICANT_Q
            ),
            key=lambda r: abs(r[1]),
            reverse=True,
        )
        for name, rho, q in ranked[:3]:
            token = name.split("profile:", 1)[1]
            direction = "raises" if rho > 0 else "lowers"
            reasons.append(
                {"feature": token, "rho": round(rho, 2), "q": round(q, 3),
                 "text": f"'{token}' {direction} your typical vibe (rho={rho:.2f})"}
            )

    return {
        "score": round(score, 1),
        "confidence": confidence_for(len(history)),
        "n_dates": len(history),
        "reasons": reasons,
    }
