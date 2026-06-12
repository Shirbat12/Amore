"""Module 2.3.4 - presentation layer.

Translates the statistical output into JSON-serializable payloads for the two
client surfaces: the real-time overlay (one profile) and the dashboard (four
aggregate visualizations + natural-language insights). Grounded in the idea that
visuals reduce decision load (Larkin & Simon, 1987).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from server import config
from server.models import DateRecord
from server.pipeline.predictor import fit_predictor, learn_correlations, score_profile


def build_overlay(history: List[DateRecord], profile_tokens: List[str]) -> Dict:
    """Payload the extension paints on top of a profile (fast decision)."""
    result = score_profile(history, profile_tokens)
    return {
        "score": result["score"],
        "confidence": result["confidence"],
        "reasons": result["reasons"],
    }


def _heatmap(corr: Dict[str, tuple]) -> List[Dict]:
    """Correlation heatmap data: rho (color) and q-value (opacity) per feature."""
    return [
        {"feature": name, "rho": round(rho, 3), "q": round(q, 3)}
        for name, (rho, q) in sorted(corr.items(), key=lambda kv: kv[1][0])
    ]


def _funnel(history: List[DateRecord]) -> Dict[str, int]:
    """First dates -> reported second-date intent."""
    first = len(history)
    seconds = sum(1 for d in history if d.second_date is True)
    maybes = sum(1 for d in history if d.second_date is None)
    return {"first_dates": first, "second_dates": seconds, "maybe": maybes}


def _scatter_predicted_vs_actual(history: List[DateRecord]) -> List[Dict]:
    """Leave-one-out predicted VAS vs the actually reported VAS."""
    points = []
    if len(history) <= config.MIN_DATES:
        return points
    for i, held in enumerate(history):
        rest = history[:i] + history[i + 1:]
        predictor = fit_predictor(rest)
        pred = max(0.0, min(100.0, predictor.predict_one(held.profile)))
        points.append({"predicted": round(pred, 1), "actual": round(held.vas, 1)})
    return points


def _boxplots_by_tag(history: List[DateRecord]) -> Dict[str, List[float]]:
    """Distribution of VAS scores grouped by extracted character tag."""
    by_tag: Dict[str, List[float]] = defaultdict(list)
    for d in history:
        for t in d.tags:
            by_tag[t].append(d.vas)
    return {tag: vals for tag, vals in by_tag.items() if len(vals) >= 2}


def _insights(corr: Dict[str, tuple]) -> List[Dict]:
    """Plain-language, rank-ordered takeaways from the strongest significant links.

    Returns structured items the dashboard styles by direction and strength,
    instead of raw correlation text. An empty list means "not enough signal yet",
    and the client shows its own friendly empty state.
    """
    out: List[Dict] = []
    ranked = sorted(corr.items(), key=lambda kv: abs(kv[1][0]), reverse=True)
    for name, (rho, q) in ranked:
        if q > config.SIGNIFICANT_Q:
            continue
        if name == "sentiment":          # circular (derived from the date) -> skip
            continue
        # Show just the human value, dropping the "profile:"/"interest:" prefixes.
        label = name.split(":")[-1]
        if rho > 0:
            text = f"'{label}' עושה לך טוב — הדייטים האלה נוטים להצליח"
            direction = "up"
        else:
            text = f"'{label}' פחות מתאים לך — הדייטים האלה נוטים לזרום פחות"
            direction = "down"
        out.append({
            "text": text,
            "direction": direction,
            "strength": "strong" if abs(rho) >= 0.5 else "medium",
            "feature": label,
        })
        if len(out) >= 5:
            break
    return out


def build_dashboard(history: List[DateRecord]) -> Dict:
    """Full dashboard payload returned by /insights."""
    corr = learn_correlations(history) if len(history) >= 2 else {}
    return {
        "n_dates": len(history),
        "heatmap": _heatmap(corr),
        "funnel": _funnel(history),
        "scatter": _scatter_predicted_vs_actual(history),
        "boxplots": _boxplots_by_tag(history),
        "insights": _insights(corr),
    }
