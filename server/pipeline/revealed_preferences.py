"""Module 2.3.2 - revealed-preferences analysis.

This module has two responsibilities:

1. Model-facing logic
   Builds (trait_dist, vas_mean) from DateRecord history so the predictor can
   reason about new profiles that contain only dry profile data.

2. Dashboard-facing questionnaire analysis
   Connects closed questionnaire answers, profile attributes, date dynamics and
   optional NLP tags from free text into one explainable preference dashboard.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from server.models import DateRecord


# ============================================================
# Model-facing logic
# ============================================================


def _to_distribution(counter: Counter) -> Dict[str, float]:
    """Convert counts into a probability distribution."""
    total = sum(counter.values())
    if total == 0:
        return {}
    return {k: v / total for k, v in counter.items()}


def learn_revealed_preferences(
    history: List[DateRecord],
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, float]]:
    """Return (trait_dist, vas_mean) keyed by dry profile feature."""
    trait_counts: Dict[str, Counter] = defaultdict(Counter)
    vas_by_feature: Dict[str, list] = defaultdict(list)

    for date_record in history:
        for profile_feature in date_record.profile:
            vas_by_feature[profile_feature].append(date_record.vas)
            for tag in date_record.tags:
                trait_counts[profile_feature][tag] += 1

    trait_dist = {feature: _to_distribution(counts) for feature, counts in trait_counts.items()}
    vas_mean = {feature: mean(values) for feature, values in vas_by_feature.items() if values}

    return trait_dist, vas_mean


# ============================================================
# Dashboard-facing questionnaire analysis
# ============================================================

EXPERIENCE_COLUMNS = [
    "conversation_flow",
    "profile_reality_match",
    "comfort_safety",
    "spark",
]

SUCCESS_SCORE_THRESHOLD = 7.0

_FEATURE_TYPE_LABELS: Dict[str, str] = {
    "conversation_topic": "נושא שיחה",
    "date_dynamic": "דינמיקה בדייט",
    "profile_interest": "תחום עניין בפרופיל",
    "profile_visual_vibe": "וייב ויזואלי בפרופיל",
    "dating_app": "אפליקציה",
    "profile_career": "תחום עיסוק בפרופיל",
    "nlp_free_text_trait": "תגית מטקסט חופשי",
}

_FEATURE_TYPE_SOURCE: Dict[str, str] = {
    "conversation_topic": "date_questionnaire",
    "date_dynamic": "date_questionnaire",
    "profile_interest": "profile_questionnaire",
    "profile_visual_vibe": "profile_questionnaire",
    "dating_app": "profile_questionnaire",
    "profile_career": "profile_questionnaire",
    "nlp_free_text_trait": "free_text_nlp",
}


def _safe_round(value, digits: int = 2):
    """Round numeric values safely for JSON output."""
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _safe_bool(value) -> bool:
    """Convert common questionnaire values into bool."""
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y", "כן", "בטח", "רוצה", "מעוניינת", "מעוניין"}


def _split_tags(value) -> List[str]:
    """
    Split Google Forms multi-select answers into clean tags.

    Handles comma-separated strings, semicolon-separated strings, and lists.
    """
    if value is None or pd.isna(value):
        return []

    if isinstance(value, list):
        raw_values: Iterable = value
    else:
        text = str(value).replace(";", ",").replace("\n", ",")
        raw_values = text.split(",")

    cleaned = []
    seen = set()
    for item in raw_values:
        tag = str(item).strip()
        if tag and tag not in seen:
            cleaned.append(tag)
            seen.add(tag)
    return cleaned


def _ensure_experience_columns(date_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived columns required by the revealed-preferences dashboard.

    The function is idempotent: it can safely run on a dataframe that already
    has these columns, and it will keep the existing values unless missing.
    """
    df = date_df.copy()

    for column in EXPERIENCE_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    missing_score_columns = [column for column in EXPERIENCE_COLUMNS if column not in df.columns]
    if missing_score_columns:
        raise KeyError(
            "Missing required date-experience columns: "
            + ", ".join(missing_score_columns)
        )

    if "experience_score" not in df.columns:
        df["experience_score"] = df[EXPERIENCE_COLUMNS].mean(axis=1)
    else:
        df["experience_score"] = pd.to_numeric(df["experience_score"], errors="coerce")

    if "profile_reality_gap" not in df.columns:
        df["profile_reality_gap"] = 10 - df["profile_reality_match"]
    else:
        df["profile_reality_gap"] = pd.to_numeric(df["profile_reality_gap"], errors="coerce")

    if "second_date_bool" in df.columns:
        df["second_date_bool"] = df["second_date_bool"].apply(_safe_bool)
    else:
        df["second_date_bool"] = False

    df["is_successful_date"] = (
        (df["experience_score"] >= SUCCESS_SCORE_THRESHOLD)
        | df["second_date_bool"]
    )

    return df


# --- feature-row collectors -------------------------------------------------


def _base_feature_row(row, feature: str, feature_type: str) -> Dict:
    """Create one normalized feature row for later aggregation."""
    return {
        "feature": feature,
        "feature_type": feature_type,
        "feature_type_label": _feature_type_label(feature_type),
        "feature_source": _FEATURE_TYPE_SOURCE.get(feature_type, "unknown"),
        "experience_score": row["experience_score"],
        "profile_reality_match": row["profile_reality_match"],
        "profile_reality_gap": row["profile_reality_gap"],
        "second_date_bool": row["second_date_bool"],
        "is_successful_date": row["is_successful_date"],
    }


def _collect_string_feature_rows(
    df: pd.DataFrame,
    column_name: str,
    feature_type: str,
    multi_value: bool = False,
) -> pd.DataFrame:
    """Collect feature rows from single-value or comma-separated string columns."""
    if column_name not in df.columns:
        return pd.DataFrame()

    rows = []
    for _, row in df.iterrows():
        raw_value = row.get(column_name)
        values = _split_tags(raw_value) if multi_value else _split_tags(raw_value)[:1]

        for value in values:
            rows.append(_base_feature_row(row, value, feature_type))

    return pd.DataFrame(rows)


def _collect_list_feature_rows(
    df: pd.DataFrame,
    column_name: str,
    feature_type: str,
) -> pd.DataFrame:
    """Collect feature rows from columns that already contain Python lists."""
    if column_name not in df.columns:
        return pd.DataFrame()

    rows = []
    for _, row in df.iterrows():
        if bool(row.get("nlp_parse_error", False)):
            continue

        for value in _split_tags(row.get(column_name)):
            rows.append(_base_feature_row(row, value, feature_type))

    return pd.DataFrame(rows)


def _build_feature_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build one unified feature table from all questionnaire/NLP feature columns."""
    tables = [
        _collect_string_feature_rows(df, "conversation_topics", "conversation_topic", multi_value=True),
        _collect_string_feature_rows(df, "date_dynamic_tags", "date_dynamic", multi_value=True),
        _collect_string_feature_rows(df, "profile_interests", "profile_interest", multi_value=True),
        _collect_string_feature_rows(df, "profile_visual_vibe", "profile_visual_vibe", multi_value=False),
        _collect_string_feature_rows(df, "dating_app", "dating_app", multi_value=False),
        _collect_string_feature_rows(df, "profile_career", "profile_career", multi_value=False),
        _collect_list_feature_rows(df, "nlp_tags", "nlp_free_text_trait"),
    ]

    non_empty_tables = [table for table in tables if not table.empty]
    if not non_empty_tables:
        return pd.DataFrame()

    return pd.concat(non_empty_tables, ignore_index=True)


# --- labelling & insight helpers --------------------------------------------


def _feature_type_label(feature_type: str) -> str:
    return _FEATURE_TYPE_LABELS.get(feature_type, feature_type)


def _confidence_from_appearances(appearances: int) -> Dict[str, str]:
    """Convert support count into a simple confidence label for the dashboard."""
    if appearances <= 2:
        return {
            "confidence_level": "low",
            "confidence_label": "מבוסס על מעט מקרים",
        }
    if appearances <= 5:
        return {
            "confidence_level": "medium",
            "confidence_label": "מבוסס על מספר בינוני של מקרים",
        }
    return {
        "confidence_level": "high",
        "confidence_label": "מבוסס על מספר גבוה יחסית של מקרים",
    }


def _positive_insight(row) -> str:
    label = _feature_type_label(row["feature_type"])
    avg_score = _safe_round(row["avg_experience_score"])
    success_rate = _safe_round(row["success_rate"] * 100)
    return (
        f"{label} מסוג '{row['feature']}' חזר בדייטים מוצלחים. "
        f"ציון החוויה הממוצע היה {avg_score}, "
        f"ושיעור ההצלחה היה {success_rate}%."
    )


def _negative_insight(row) -> str:
    label = _feature_type_label(row["feature_type"])
    avg_score = _safe_round(row["avg_experience_score"])
    success_rate = _safe_round(row["success_rate"] * 100)
    return (
        f"{label} מסוג '{row['feature']}' חזר בדייטים שפחות נטו להצליח. "
        f"ציון החוויה הממוצע היה {avg_score}, "
        f"ושיעור ההצלחה היה {success_rate}%."
    )


def _pattern_row_to_dict(row) -> Dict:
    confidence = _confidence_from_appearances(int(row["appearances"]))
    return {
        "feature": row["feature"],
        "feature_type": row["feature_type"],
        "feature_type_label": _feature_type_label(row["feature_type"]),
        "feature_source": _FEATURE_TYPE_SOURCE.get(row["feature_type"], "unknown"),
        "appearances": int(row["appearances"]),
        "support_pct": _safe_round(row["support_pct"]),
        "successful_appearances": int(row["successful_appearances"]),
        "avg_experience_score": _safe_round(row["avg_experience_score"]),
        "avg_profile_reality_match": _safe_round(row["avg_profile_reality_match"]),
        "avg_profile_reality_gap": _safe_round(row["avg_profile_reality_gap"]),
        "second_date_rate": _safe_round(row["second_date_rate"]),
        "success_rate": _safe_round(row["success_rate"]),
        "success_lift": _safe_round(row["success_lift"]),
        "experience_lift": _safe_round(row["experience_lift"]),
        "preference_strength": _safe_round(row["preference_strength"]),
        "confidence": confidence,
    }


def _rank_patterns(grouped: pd.DataFrame, baseline_success_rate: float, overall_experience: float):
    """Split and rank positive/negative patterns with overlap prevention."""
    positive_candidates = grouped[
        (grouped["success_rate"] >= baseline_success_rate)
        | (grouped["avg_experience_score"] >= overall_experience)
    ].copy()

    negative_candidates = grouped[
        (grouped["success_rate"] <= baseline_success_rate)
        | (grouped["avg_experience_score"] <= overall_experience)
    ].copy()

    positive = positive_candidates.sort_values(
        ["preference_strength", "success_rate", "avg_experience_score", "appearances"],
        ascending=[False, False, False, False],
    ).head(8)

    positive_keys = set(zip(positive["feature_type"], positive["feature"]))

    negative_candidates = negative_candidates[
        ~negative_candidates.apply(
            lambda row: (row["feature_type"], row["feature"]) in positive_keys,
            axis=1,
        )
    ]

    negative = negative_candidates.sort_values(
        ["preference_strength", "success_rate", "avg_experience_score", "appearances"],
        ascending=[True, True, True, False],
    ).head(5)

    return positive, negative


# --- public entry point ------------------------------------------------------


def build_revealed_preferences_dashboard(
    date_df: pd.DataFrame,
    min_count: int = 2,
) -> Dict:
    """
    Build dashboard-ready revealed-preferences insights from questionnaire data.

    The analysis combines profile attributes, date-level closed answers, and
    optional NLP tags extracted from the free-text response.
    """
    empty_response = {
        "ready": False,
        "positive_patterns": [],
        "negative_patterns": [],
        "definition": {
            "successful_date": "experience_score >= 7 OR second_date_bool == True",
            "min_count": min_count,
            "success_score_threshold": SUCCESS_SCORE_THRESHOLD,
        },
    }

    if date_df.empty:
        return {**empty_response, "message": "No date-experience data available"}

    df = _ensure_experience_columns(date_df)
    feature_table = _build_feature_table(df)

    if feature_table.empty:
        return {**empty_response, "message": "Not enough feature data yet"}

    total_dates = max(len(df), 1)
    baseline_success_rate = float(df["is_successful_date"].mean())
    overall_experience = float(df["experience_score"].mean())

    grouped = (
        feature_table
        .groupby(["feature_type", "feature"], dropna=True)
        .agg(
            appearances=("feature", "count"),
            successful_appearances=("is_successful_date", "sum"),
            avg_experience_score=("experience_score", "mean"),
            avg_profile_reality_match=("profile_reality_match", "mean"),
            avg_profile_reality_gap=("profile_reality_gap", "mean"),
            second_date_rate=("second_date_bool", "mean"),
            success_rate=("is_successful_date", "mean"),
        )
        .reset_index()
    )

    grouped = grouped[grouped["appearances"] >= min_count].copy()

    if grouped.empty:
        return {**empty_response, "message": "Not enough repeated patterns yet"}

    grouped["support_pct"] = grouped["appearances"] / total_dates * 100
    grouped["success_lift"] = grouped["success_rate"] - baseline_success_rate
    grouped["experience_lift"] = grouped["avg_experience_score"] - overall_experience

    # A simple explainable strength score for ranking. It intentionally keeps
    # support in the formula so one-off patterns do not dominate the dashboard.
    grouped["preference_strength"] = (
        grouped["success_lift"] * 0.6
        + (grouped["experience_lift"] / 10) * 0.4
    ) * grouped["appearances"].clip(upper=8) / 8

    positive, negative = _rank_patterns(grouped, baseline_success_rate, overall_experience)

    positive_patterns = [
        {**_pattern_row_to_dict(row), "insight": _positive_insight(row)}
        for _, row in positive.iterrows()
    ]
    negative_patterns = [
        {**_pattern_row_to_dict(row), "insight": _negative_insight(row)}
        for _, row in negative.iterrows()
    ]

    return {
        "ready": True,
        "baseline": {
            "n_dates": int(len(df)),
            "baseline_success_rate": _safe_round(baseline_success_rate),
            "overall_experience_score": _safe_round(overall_experience),
        },
        "positive_patterns": positive_patterns,
        "negative_patterns": negative_patterns,
        "definition": {
            "successful_date": "experience_score >= 7 OR second_date_bool == True",
            "min_count": min_count,
            "success_score_threshold": SUCCESS_SCORE_THRESHOLD,
        },
    }
