"""Tests for the score 'why' line (population fallback + per-user reasons)."""
from data.samples.generate_samples import generate
from server.pipeline.predictor import population_reasons
from server.pipeline.presentation import build_overlay


def test_population_reasons_always_returns_text():
    """Even an unknown profile gets at least one explanation line."""
    reasons = population_reasons(["interest:does-not-exist-xyz"])
    assert isinstance(reasons, list) and reasons
    assert all("text" in r and r["text"] for r in reasons)


def test_overlay_for_cold_start_user_has_a_why():
    """A user with too little history still gets a 'why' (population fallback)."""
    history = generate(n=3, user_id="cold")          # < MIN_DATES -> no per-user reasons
    overlay = build_overlay(history, ["interest:travel", "hobby:cooking"])
    assert overlay["reasons"]                          # never empty
    assert all("text" in r for r in overlay["reasons"])


def test_overlay_for_rich_user_uses_personal_reasons(history):
    """A user with enough history gets personal, per-user reasons."""
    overlay = build_overlay(history, ["interest:travel"])
    assert overlay["reasons"]
    # personal reasons carry an rho/q signature; population ones may not.
    assert any("feature" in r for r in overlay["reasons"])
