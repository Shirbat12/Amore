"""Tests for the evaluation KPIs (project book section 4.1)."""
import pytest

from evaluation.kpis import (
    conversion_ratio,
    decision_alignment,
    decision_alignment_report,
    positive_features_from_history,
    prediction_accuracy,
    sus_score,
    vibe_response_rate,
)
from server.models import DateRecord


# --- Decision-Alignment (the new KPI) -----------------------------------
def test_positive_features_recovers_liked_not_disliked(history):
    positives = positive_features_from_history(history)
    assert "interest:travel" in positives        # seeded positive
    assert "interest:finance" not in positives    # seeded negative


def test_decision_alignment_pure_formula():
    selected = [["interest:travel"], ["interest:finance"], ["other"]]
    rate = decision_alignment(selected, {"interest:travel"})
    assert rate == pytest.approx(100 / 3)         # 1 of 3 liked profiles aligns


def test_decision_alignment_report_over_selections(history):
    selections = [
        {"action": "like", "profile": ["interest:travel", "age:23-26"]},
        {"action": "like", "profile": ["interest:finance"]},
        {"action": "pass", "profile": ["interest:travel"]},   # ignored (not a like)
    ]
    report = decision_alignment_report(history, selections)
    assert report["n_selected"] == 2              # only the two likes count
    assert report["rate"] == pytest.approx(50.0)  # 1 of 2 likes carries a positive
    assert "interest:travel" in report["positive_features"]


def test_decision_alignment_report_handles_no_data(history):
    report = decision_alignment_report(history, [])
    assert report["rate"] is None                 # nothing liked yet
    assert report["n_selected"] == 0


# --- SUS -----------------------------------------------------------------
def test_sus_scoring_endpoints():
    assert sus_score([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == 100.0   # best
    assert sus_score([3] * 10) == 50.0                          # neutral


def test_sus_requires_ten_items():
    with pytest.raises(ValueError):
        sus_score([5, 1, 5])


# --- Conversion ratio & response rate -----------------------------------
def test_conversion_ratio_counts_second_dates():
    recs = [
        DateRecord(user_id="u", vas=80, second_date=True),
        DateRecord(user_id="u", vas=40, second_date=False),
        DateRecord(user_id="u", vas=70, second_date=True),
    ]
    assert conversion_ratio(recs) == pytest.approx(200 / 3)     # 2 of 3
    assert conversion_ratio([]) == 0.0


def test_vibe_response_rate():
    assert vibe_response_rate(6, 10) == pytest.approx(0.6)
    assert vibe_response_rate(0, 0) == 0.0


# --- Prediction accuracy -------------------------------------------------
def test_prediction_accuracy_recovers_signal(history):
    rho, mae = prediction_accuracy(history)
    assert rho is not None and rho > 0.4          # section 4.1 target
    assert 0 <= mae <= 100
