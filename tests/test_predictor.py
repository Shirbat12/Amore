"""Tests for module 2.3.3 - correlation + regularized prediction."""
from server import config
from server.models import DateRecord
from server.pipeline.predictor import (
    PriorPredictor,
    fit_predictor,
    learn_correlations,
    score_profile,
)


def test_cold_start_returns_prior():
    short = [
        DateRecord(user_id="u", vas=50, profile=["interest:travel"])
        for _ in range(config.MIN_DATES - 1)
    ]
    predictor = fit_predictor(short)
    assert isinstance(predictor, PriorPredictor)


def test_correlations_recover_latent_signal(history):
    corr = learn_correlations(history)
    travel = corr.get("profile:interest:travel")
    finance = corr.get("profile:interest:finance")
    assert travel is not None and finance is not None
    assert travel[0] > 0          # travel positively correlates with VAS
    assert finance[0] < 0         # finance negatively correlates


def test_score_in_range_and_ranks_profiles(history):
    good = score_profile(history, ["interest:travel", "hobby:cooking"])
    bad = score_profile(history, ["interest:finance", "hobby:gaming"])
    assert 0 <= good["score"] <= 100
    assert 0 <= bad["score"] <= 100
    assert good["score"] > bad["score"]
    assert good["confidence"] == "high"           # 30 dates >= 2*MIN_DATES
