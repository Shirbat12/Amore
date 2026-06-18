"""Experiment analysis for real A-MORE questionnaire data.

This module analyzes the real Google Forms experiment data:
- baseline questionnaire
- post-date experience questionnaire

It produces JSON-serializable insights for the dashboard.
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from server.pipeline.free_text_analysis import (
    analyze_free_text_dataframe,
    summarize_free_text_analysis,
)
from server.pipeline.revealed_preferences import build_revealed_preferences_dashboard


def _safe_round(value, digits: int = 2):
    """Round safely for JSON output."""
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _add_experiment_metrics(date_df: pd.DataFrame) -> pd.DataFrame:
    """Adds derived A-MORE metrics to the date experience dataframe."""
    df = date_df.copy()

    df["experience_score"] = df[
        [
            "conversation_flow",
            "profile_reality_match",
            "comfort_safety",
            "spark",
        ]
    ].mean(axis=1)

    df["profile_reality_gap"] = 10 - df["profile_reality_match"]

    df["is_successful_date"] = (
        (df["experience_score"] >= 7)
        | (df["second_date_bool"] == True)  # noqa: E712
    )

    return df


def analyze_second_date_drivers(date_df: pd.DataFrame) -> Dict:
    """Compares dates that led to second-date intent vs. dates that did not."""
    yes_df = date_df[date_df["second_date_bool"] == True]   # noqa: E712
    no_df = date_df[date_df["second_date_bool"] == False]   # noqa: E712

    compared_columns = [
        "conversation_flow",
        "profile_reality_match",
        "comfort_safety",
        "spark",
        "experience_score",
        "profile_reality_gap",
    ]

    comparison = {}

    for col in compared_columns:
        yes_avg = yes_df[col].mean()
        no_avg = no_df[col].mean()

        comparison[col] = {
            "second_date_yes_avg": _safe_round(yes_avg),
            "second_date_no_avg": _safe_round(no_avg),
            "difference": _safe_round(yes_avg - no_avg),
        }

    return {
        "yes_count": int(len(yes_df)),
        "no_count": int(len(no_df)),
        "comparison": comparison,
    }


def analyze_profile_reality_gap(date_df: pd.DataFrame) -> Dict:
    """Analyzes profile-reality gap."""

    def gap_level(score):
        if pd.isna(score):
            return "unknown"
        if score <= 2:
            return "low_gap"
        if score <= 5:
            return "medium_gap"
        return "high_gap"

    df = date_df.copy()
    df["gap_level"] = df["profile_reality_gap"].apply(gap_level)

    gap_summary = (
        df.groupby("gap_level")
        .agg(
            count=("gap_level", "count"),
            avg_experience=("experience_score", "mean"),
            second_date_rate=("second_date_bool", "mean"),
        )
        .reset_index()
    )

    return {
        "avg_profile_reality_gap": _safe_round(df["profile_reality_gap"].mean()),
        "gap_distribution": df["gap_level"].value_counts().to_dict(),
        "gap_summary": [
            {
                "gap_level": row["gap_level"],
                "count": int(row["count"]),
                "avg_experience": _safe_round(row["avg_experience"]),
                "second_date_rate": _safe_round(row["second_date_rate"]),
            }
            for _, row in gap_summary.iterrows()
        ],
    }


def analyze_segments(date_df: pd.DataFrame, min_count: int = 2) -> Dict:
    """Analyzes average experience by profile/context segments."""

    def group_mean(group_col: str):
        grouped = (
            date_df.groupby(group_col)
            .agg(
                count=(group_col, "count"),
                avg_experience_score=("experience_score", "mean"),
                second_date_rate=("second_date_bool", "mean"),
            )
            .reset_index()
        )

        grouped = grouped[grouped["count"] >= min_count]
        grouped = grouped.sort_values(
            ["avg_experience_score", "count"],
            ascending=[False, False],
        )

        return [
            {
                "name": str(row[group_col]),
                "count": int(row["count"]),
                "avg_experience_score": _safe_round(row["avg_experience_score"]),
                "second_date_rate": _safe_round(row["second_date_rate"]),
            }
            for _, row in grouped.iterrows()
        ]

    return {
        "by_dating_app": group_mean("dating_app"),
        "by_profile_career": group_mean("profile_career"),
        "by_visual_vibe": group_mean("profile_visual_vibe"),
    }


def analyze_free_text_closed_alignment(date_df: pd.DataFrame) -> Dict:
    """
    Connects Gemini free-text NLP outputs with the closed questionnaire answers.

    This checks whether the qualitative free-text analysis supports
    the numeric/closed-form responses.
    """
    required_columns = {
        "nlp_sentiment",
        "nlp_warmth",
        "nlp_agency",
        "nlp_tags",
        "experience_score",
        "conversation_flow",
        "comfort_safety",
        "spark",
        "profile_reality_match",
        "profile_reality_gap",
        "second_date_bool",
    }

    if not required_columns.issubset(date_df.columns):
        return {
            "ready": False,
            "message": "NLP/closed-question alignment could not be calculated",
            "correlations": {},
            "tag_alignment": {},
            "alignment_insights": [],
        }

    df = date_df.copy()

    correlations = {
        "nlp_sentiment_vs_experience_score": _safe_round(
            df["nlp_sentiment"].corr(df["experience_score"], method="spearman")
        ),
        "nlp_warmth_vs_comfort_safety": _safe_round(
            df["nlp_warmth"].corr(df["comfort_safety"], method="spearman")
        ),
        "nlp_agency_vs_conversation_flow": _safe_round(
            df["nlp_agency"].corr(df["conversation_flow"], method="spearman")
        ),
        "nlp_sentiment_vs_spark": _safe_round(
            df["nlp_sentiment"].corr(df["spark"], method="spearman")
        ),
        "nlp_sentiment_vs_second_date": _safe_round(
            df["nlp_sentiment"].corr(
                df["second_date_bool"].astype(float),
                method="spearman",
            )
        ),
    }

    def rows_with_tag(tag: str) -> pd.DataFrame:
        return df[
            df["nlp_tags"].apply(
                lambda tags: isinstance(tags, list) and tag in tags
            )
        ]

    tag_alignment = {}

    important_tags = [
        "מקשיב",
        "מתעניין",
        "מצחיק",
        "מרוכז בעצמו",
        "לא מקשיב",
        "חוסר משיכה",
        "פער בין פרופיל למציאות",
    ]

    for tag in important_tags:
        tag_df = rows_with_tag(tag)

        if tag_df.empty:
            continue

        tag_alignment[tag] = {
            "count": int(len(tag_df)),
            "avg_experience_score": _safe_round(tag_df["experience_score"].mean()),
            "avg_conversation_flow": _safe_round(tag_df["conversation_flow"].mean()),
            "avg_comfort_safety": _safe_round(tag_df["comfort_safety"].mean()),
            "avg_spark": _safe_round(tag_df["spark"].mean()),
            "avg_profile_reality_match": _safe_round(
                tag_df["profile_reality_match"].mean()
            ),
            "avg_profile_reality_gap": _safe_round(
                tag_df["profile_reality_gap"].mean()
            ),
            "second_date_rate": _safe_round(tag_df["second_date_bool"].mean()),
        }

    insights = []

    warmth_corr = correlations["nlp_warmth_vs_comfort_safety"]
    if warmth_corr is not None:
        insights.append(
            f"קיים קשר של {warmth_corr} בין חום/הקשבה בטקסט החופשי לבין תחושת נוחות וביטחון."
        )

    agency_corr = correlations["nlp_agency_vs_conversation_flow"]
    if agency_corr is not None:
        insights.append(
            f"קיים קשר של {agency_corr} בין אנרגיה/פעלתנות בטקסט החופשי לבין זרימת השיחה."
        )

    sentiment_corr = correlations["nlp_sentiment_vs_experience_score"]
    if sentiment_corr is not None:
        insights.append(
            f"קיים קשר של {sentiment_corr} בין סנטימנט הטקסט החופשי לבין ציון החוויה הכללי."
        )

    if "חוסר משיכה" in tag_alignment:
        avg_spark = tag_alignment["חוסר משיכה"]["avg_spark"]
        insights.append(
            f"כאשר הופיעה בטקסט תגית 'חוסר משיכה', ציון הניצוץ הממוצע היה {avg_spark}."
        )

    if "פער בין פרופיל למציאות" in tag_alignment:
        avg_gap = tag_alignment["פער בין פרופיל למציאות"]["avg_profile_reality_gap"]
        insights.append(
            f"כאשר הטקסט ציין פער בין הפרופיל למציאות, מדד הפער הממוצע היה {avg_gap}."
        )

    return {
        "ready": True,
        "correlations": correlations,
        "tag_alignment": tag_alignment,
        "alignment_insights": insights,
    }


def build_natural_language_insights(
    baseline_df: pd.DataFrame,
    date_df: pd.DataFrame,
    second_date_analysis: Dict,
) -> List[str]:
    """Converts the numeric analysis into short dashboard-ready text insights."""
    insights = []

    avg_burnout = baseline_df["burnout_level"].mean()
    second_date_rate = date_df["second_date_bool"].mean()

    insights.append(
        f"רמת השחיקה הממוצעת מהאפליקציות היא {_safe_round(avg_burnout)} מתוך 10."
    )

    insights.append(
        f"שיעור הרצון לדייט שני במדגם הוא {_safe_round(second_date_rate * 100)}%."
    )

    comparison = second_date_analysis["comparison"]

    spark_diff = comparison["spark"]["difference"]
    match_diff = comparison["profile_reality_match"]["difference"]
    gap_diff = comparison["profile_reality_gap"]["difference"]

    if spark_diff is not None:
        insights.append(
            f"בדייטים שהובילו לרצון לדייט שני, מדד הניצוץ/משיכה היה גבוה יותר "
            f"ב-{spark_diff} נקודות בממוצע."
        )

    if match_diff is not None:
        insights.append(
            f"בדייטים שהובילו לרצון לדייט שני, ההתאמה בין הפרופיל למציאות הייתה גבוהה יותר "
            f"ב-{match_diff} נקודות בממוצע."
        )

    if gap_diff is not None and gap_diff < 0:
        insights.append(
            "פער נמוך יותר בין הפרופיל למציאות הופיע יותר בדייטים שהובילו לרצון להמשך."
        )

    return insights


def analyze_questionnaire_experiment(
    baseline_df: pd.DataFrame,
    date_df: pd.DataFrame,
) -> Dict:
    """
    Main function for analyzing the real questionnaire experiment.

    Returns a JSON-ready dictionary for the backend/dashboard.
    """
    df = _add_experiment_metrics(date_df)

    df = analyze_free_text_dataframe(
        df,
        text_col="free_text",
        vas_col="experience_score",
    )

    free_text_analysis = summarize_free_text_analysis(df)
    free_text_closed_alignment = analyze_free_text_closed_alignment(df)

    second_date_analysis = analyze_second_date_drivers(df)
    gap_analysis = analyze_profile_reality_gap(df)
    segment_analysis = analyze_segments(df)

    revealed_preferences = build_revealed_preferences_dashboard(df)
    word_cloud = build_word_cloud_from_preferences(revealed_preferences)
    natural_language_insights = build_natural_language_insights(
        baseline_df=baseline_df,
        date_df=df,
        second_date_analysis=second_date_analysis,
    )

    return {
        "overview": {
            "baseline_responses": int(len(baseline_df)),
            "date_experience_responses": int(len(df)),
            "avg_burnout": _safe_round(baseline_df["burnout_level"].mean()),
            "avg_experience_score": _safe_round(df["experience_score"].mean()),
            "avg_profile_reality_match": _safe_round(
                df["profile_reality_match"].mean()
            ),
            "avg_profile_reality_gap": _safe_round(
                df["profile_reality_gap"].mean()
            ),
            "second_date_rate": _safe_round(df["second_date_bool"].mean()),
        },
        "second_date_drivers": second_date_analysis,
        "profile_reality_gap_analysis": gap_analysis,
        "segment_analysis": segment_analysis,
        "revealed_preferences": revealed_preferences,
        "free_text_analysis": free_text_analysis,
        "free_text_closed_alignment": free_text_closed_alignment,
        "natural_language_insights": natural_language_insights,
        "word_cloud": word_cloud,
    }

    def build_word_cloud_from_preferences(revealed_preferences: Dict) -> Dict:
    """
    Builds a dashboard-ready word cloud from positive revealed preferences.
    """
    positive_patterns = revealed_preferences.get("positive_patterns", [])

    items = []

    for pattern in positive_patterns:
        appearances = int(pattern.get("appearances", 0))

        if appearances < 2:
            continue

        items.append({
            "text": pattern.get("feature"),
            "weight": appearances,
            "score": pattern.get("preference_strength"),
            "sentiment": "positive",
            "source": pattern.get("feature_type"),
            "confidence": pattern.get("confidence", {}).get("confidence_label"),
        })

    items = sorted(
        items,
        key=lambda item: (item["weight"], item["score"] or 0),
        reverse=True,
    )[:12]

    return {
        "title": "ענן תחומי עניין בולטים",
        "subtitle": "מילים שחזרו בדייטים החיוביים שלך",
        "items": items,
    }