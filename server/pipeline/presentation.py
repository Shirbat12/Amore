"""Module 2.3.4 - presentation layer.

Translates statistical output into JSON-serializable payloads for the two client
surfaces:
  - Overlay: real-time score painted on top of one profile.
  - Dashboard: aggregate visualizations, experiment analysis and insights.

The module intentionally returns plain dictionaries so the backend can send them
as JSON without additional transformation.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

import pandas as pd

from server import config
from server.models import DateRecord
from server.pipeline.predictor import (
    fit_predictor,
    learn_correlations,
    population_reasons,
    score_profile,
)


def _safe_round(value, digits: int = 2):
    """Round numeric values safely for JSON output."""
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _token_label(token: str) -> str:
    """Normalize profile tokens such as 'interest:טיולים' into 'טיולים'."""
    return str(token).split(":")[-1].strip()


# ============================================================
# Overlay / Chrome extension
# ============================================================


def build_overlay(history: List[DateRecord], profile_tokens: List[str]) -> Dict:
    """Payload the extension paints on top of a profile using the predictor.

    If the user has too little personal history for per-user reasons (the common
    case in the pilot), fall back to population-level tendencies so the overlay
    always shows a 'why' line under the score.
    """
    result = score_profile(history, profile_tokens)
    reasons = result["reasons"] or population_reasons(profile_tokens)
    return {
        "score": result["score"],
        "confidence": result["confidence"],
        "reasons": reasons,
    }


def build_revealed_preference_overlay(
    profile_tokens: List[str],
    experiment_analysis: Dict,
) -> Dict:
    """
    Explainable add-on score based on revealed-preference dashboard patterns.

    This does not call Gemini. It only consumes an existing experiment_analysis
    payload and compares profile tokens to positive/negative learned patterns.
    """
    revealed = experiment_analysis.get("revealed_preferences", {})
    positive_patterns = revealed.get("positive_patterns", [])
    negative_patterns = revealed.get("negative_patterns", [])

    profile_labels = {_token_label(token) for token in profile_tokens}

    score = 50.0
    reasons: List[str] = []
    warnings: List[str] = []
    matched_count = 0

    for pattern in positive_patterns:
        feature = str(pattern.get("feature", "")).strip()
        if feature not in profile_labels:
            continue

        matched_count += 1
        strength = float(pattern.get("preference_strength") or 0)
        confidence = pattern.get("confidence", {}).get("confidence_level", "low")
        weight = {"low": 4, "medium": 7, "high": 10}.get(confidence, 4)
        score += weight + max(strength, 0) * 10
        reasons.append(
            f"'{feature}' הופיע בדפוסים חיוביים קודמים "
            f"({pattern.get('feature_type_label', 'מאפיין')})."
        )

    for pattern in negative_patterns:
        feature = str(pattern.get("feature", "")).strip()
        if feature not in profile_labels:
            continue

        matched_count += 1
        strength = float(pattern.get("preference_strength") or 0)
        confidence = pattern.get("confidence", {}).get("confidence_level", "low")
        weight = {"low": 4, "medium": 7, "high": 10}.get(confidence, 4)
        score -= weight + abs(min(strength, 0)) * 10
        warnings.append(
            f"'{feature}' הופיע בדפוסים שפחות נטו להצליח בעבר "
            f"({pattern.get('feature_type_label', 'מאפיין')})."
        )

    score = max(0, min(100, round(score)))

    if matched_count >= 4:
        confidence = "high"
    elif matched_count >= 2:
        confidence = "medium"
    else:
        confidence = "low"
        warnings.append("אין עדיין מספיק דפוסים אישיים עבור כל מאפייני הפרופיל.")

    return {
        "score": score,
        "confidence": confidence,
        "reasons": reasons[:5],
        "warnings": warnings[:5],
        "matched_patterns": matched_count,
    }


# ============================================================
# Dashboard helpers
# ============================================================


def _heatmap(corr: Dict[str, tuple]) -> List[Dict]:
    """Correlation heatmap: rho and q-value per feature."""
    rows = []
    for name, values in corr.items():
        try:
            rho, q_value = values
        except (TypeError, ValueError):
            continue

        rows.append({
            "feature": name,
            "rho": _safe_round(rho, 3),
            "q": _safe_round(q_value, 3),
        })

    return sorted(rows, key=lambda row: row["rho"] if row["rho"] is not None else 0)


def _funnel(history: List[DateRecord]) -> Dict[str, int]:
    """First dates -> reported second-date intent."""
    first_dates = len(history)
    second_dates = sum(1 for date_record in history if date_record.second_date is True)
    maybes = sum(1 for date_record in history if date_record.second_date is None)
    return {
        "first_dates": first_dates,
        "second_dates": second_dates,
        "maybe": maybes,
    }


def _scatter_predicted_vs_actual(history: List[DateRecord]) -> List[Dict]:
    """Leave-one-out predicted VAS vs. actually reported VAS."""
    if len(history) <= config.MIN_DATES:
        return []

    points = []
    for index, held_out in enumerate(history):
        rest = history[:index] + history[index + 1:]
        try:
            predictor = fit_predictor(rest)
            predicted = predictor.predict_one(held_out.profile)
        except Exception:
            continue

        predicted = max(0.0, min(100.0, predicted))
        points.append({
            "predicted": _safe_round(predicted, 1),
            "actual": _safe_round(held_out.vas, 1),
        })

    return points


def _boxplots_by_tag(history: List[DateRecord]) -> Dict[str, List[float]]:
    """Distribution of VAS scores grouped by extracted character tag."""
    by_tag: Dict[str, List[float]] = defaultdict(list)

    for date_record in history:
        for tag in date_record.tags:
            by_tag[tag].append(float(date_record.vas))

    return {
        tag: values
        for tag, values in by_tag.items()
        if len(values) >= 2
    }


def _insights(corr: Dict[str, tuple], max_items: int = 5) -> List[Dict]:
    """
    Plain-language, rank-ordered takeaways from the strongest correlations.

    Significant links are marked as significant=True. With small datasets, q may
    be high, so we still return useful low-confidence candidates instead of an
    empty list.
    """
    ranked = sorted(corr.items(), key=lambda item: abs(item[1][0]), reverse=True)
    out: List[Dict] = []

    for name, (rho, q_value) in ranked:
        if name == "sentiment":
            continue

        label = _token_label(name)
        direction = "up" if rho > 0 else "down"
        significant = q_value <= config.SIGNIFICANT_Q
        strength = "strong" if abs(rho) >= 0.5 else "medium" if abs(rho) >= 0.3 else "weak"

        if rho > 0:
            text = f"'{label}' נוטה להופיע בדייטים עם ציון גבוה יותר"
        else:
            text = f"'{label}' נוטה להופיע בדייטים עם ציון נמוך יותר"

        out.append({
            "text": text,
            "direction": direction,
            "strength": strength,
            "feature": label,
            "rho": _safe_round(rho, 3),
            "q": _safe_round(q_value, 3),
            "significant": bool(significant),
            "confidence_note": (
                "מובהק סטטיסטית"
                if significant
                else "כיוון ראשוני בלבד - המדגם קטן"
            ),
        })

        if len(out) >= max_items:
            break

    return out


# ============================================================
# Public entry points
# ============================================================


def _confidence_label(q_value: float) -> Dict[str, str]:
    if q_value <= config.SIGNIFICANT_Q:
        return {"confidence_level": "high", "confidence_label": "ביטחון גבוה"}
    if q_value <= 0.3:
        return {"confidence_level": "medium", "confidence_label": "ביטחון בינוני"}
    return {"confidence_level": "low", "confidence_label": "כיוון ראשוני"}


def _revealed_preferences_from_history(history: List[DateRecord]) -> Dict:
    """Build the revealed-preference patterns the dashboard renders as 'AI insights'.

    The questionnaire pipeline produces this from the .xlsx, but users whose dates
    live in the DB never went through it - so without this they'd see no AI
    insights. Here we derive the same shape from the DB history using the per-user
    correlations: profile features that consistently co-occur with better (or
    worse) dates become positive / negative patterns.
    """
    corr = learn_correlations(history)

    # Count how often each feature appeared, per source (profile / topic / vibe).
    app_profile: Dict[str, int] = defaultdict(int)
    app_topic: Dict[str, int] = defaultdict(int)
    app_dynamic: Dict[str, int] = defaultdict(int)
    for record in history:
        for token in set(record.profile):
            app_profile[token] += 1
        for tag in set(record.topic_tags):
            app_topic[tag] += 1
        for tag in set(record.vibe_tags):
            app_dynamic[tag] += 1

    # name-prefix -> (appearances map, feature-type label)
    sources = {
        "profile:": (app_profile, "מאפיין פרופיל"),
        "topic:": (app_topic, "נושא שיחה"),
        "dynamic:": (app_dynamic, "דינמיקה בדייט"),
    }

    positive, negative = [], []
    for name, (rho, q_value) in corr.items():
        match = next(((p, s) for p, s in sources.items() if name.startswith(p)), None)
        if match is None:                   # e.g. 'trait:' / 'sentiment' -> skip
            continue
        prefix, (app_map, type_label) = match
        key = name.split(prefix, 1)[1]
        count = app_map.get(key, 0)
        if count < 2:                       # frontend ignores < 2 anyway
            continue
        pattern = {
            "feature": _token_label(key),
            "feature_type_label": type_label,
            "appearances": count,
            "preference_strength": _safe_round(rho, 3),
            "confidence": _confidence_label(q_value),
        }
        (positive if rho > 0 else negative).append(pattern)

    positive.sort(key=lambda p: p["preference_strength"], reverse=True)
    negative.sort(key=lambda p: p["preference_strength"])
    return {"positive_patterns": positive, "negative_patterns": negative}


def build_dashboard(history: List[DateRecord]) -> Dict:
    """Full standard dashboard payload returned by /insights."""
    corr = learn_correlations(history) if len(history) >= 2 else {}

    return {
        "n_dates": len(history),
        "heatmap": _heatmap(corr),
        "funnel": _funnel(history),
        "scatter": _scatter_predicted_vs_actual(history),
        "boxplots": _boxplots_by_tag(history),
        "insights": [] if len(history) < 5 else _insights(corr),
        # Give DB-history users the same "AI insights" the questionnaire path has.
        "experiment_analysis": {
            "revealed_preferences": _revealed_preferences_from_history(history)
        },
    }


def build_questionnaire_dashboard(user_id: str | None = None) -> Dict:
    """
    Dashboard based on the real questionnaire data.
    If user_id is provided, filters questionnaire responses to that user.
    """
    from server.pipeline.questionnaire_loader import load_questionnaire_history
    from server.pipeline.experiment_analysis import analyze_questionnaire_experiment

    history, baseline_df, date_df = load_questionnaire_history()

    if user_id is not None and "user_id" in date_df.columns:
        user_date_df = date_df[date_df["user_id"] == user_id].copy()

        if "user_id" in baseline_df.columns:
            user_baseline_df = baseline_df[baseline_df["user_id"] == user_id].copy()
        else:
            user_baseline_df = baseline_df.copy()

        if len(user_date_df) > 0:
            date_df = user_date_df
            baseline_df = user_baseline_df
            history = [d for d in history if d.user_id == user_id]

    dashboard = build_dashboard(history)

    dashboard["data_source"] = "questionnaire_responses"
    dashboard["user"] = {
        "user_id": user_id or "all_questionnaire_responses",
        "display_name": user_id or "Questionnaire Demo User",
    }

    dashboard["experiment_analysis"] = analyze_questionnaire_experiment(
        baseline_df=baseline_df,
        date_df=date_df,
    )

    return dashboard
