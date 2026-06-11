"""Tests for module 2.3.1 - the NLP/quantify step (offline mock tagger)."""
from server.models import VibeForm
from server.nlp.closed_tags import CLOSED_TAGS
from server.pipeline.quantify_experience import quantify_experience


def test_extracts_closed_tags_from_hebrew_text():
    form = VibeForm(
        user_id="u1",
        profile=["interest:travel"],
        vas_scores={"attraction": 80},
        free_text="היה ממש כיף, הוא היה מצחיק ודברן",
    )
    rec = quantify_experience(form)
    assert "מצחיק" in rec.tags
    assert "דברן" in rec.tags
    assert all(t in CLOSED_TAGS for t in rec.tags)
    assert rec.vas == 80


def test_negative_text_yields_negative_sentiment():
    form = VibeForm(
        user_id="u1",
        free_text="די משעמם, הוא דיבר רק על עצמו",
        vas_scores={"attraction": 20},
    )
    rec = quantify_experience(form)
    assert rec.sentiment < 0
    assert "משעמם" in rec.tags


def test_empty_text_degrades_gracefully():
    form = VibeForm(user_id="u1", free_text="", vas_scores={"attraction": 50})
    rec = quantify_experience(form)
    assert rec.tags == []
    assert rec.vas == 50


def test_primary_vas_falls_back_to_mean():
    form = VibeForm(user_id="u1", vas_scores={"comfort": 40, "reality_match": 60})
    assert form.primary_vas() == 50
