"""A user whose dates live in the DB should get 'AI insights' (revealed
preference patterns), same as the questionnaire path provides."""
from data.samples.generate_samples import generate
from server.pipeline.presentation import build_dashboard


def test_db_dashboard_includes_revealed_preferences():
    history = generate(n=10, user_id="u")           # 10 DB-style dates
    dash = build_dashboard(history)

    rev = dash["experiment_analysis"]["revealed_preferences"]
    patterns = rev["positive_patterns"] + rev["negative_patterns"]
    assert patterns                                  # AI-insight patterns exist
    assert all(p["appearances"] >= 2 for p in patterns)
    assert all("feature" in p and "confidence" in p for p in patterns)


def test_small_history_has_no_misleading_patterns():
    history = generate(n=1, user_id="u")            # almost nothing to learn from
    rev = build_dashboard(history)["experiment_analysis"]["revealed_preferences"]
    # nothing appears >= 2 times, so no patterns are surfaced
    assert rev["positive_patterns"] == [] and rev["negative_patterns"] == []


def test_insights_from_form_tags_without_any_profile():
    """Dates with no profile but with the form's topic/vibe tags still yield insights."""
    from server.models import DateRecord
    history = [
        DateRecord(
            user_id="y", vas=40 + i * 5, profile=[],
            topic_tags=["טיולים"] if i % 2 else ["קריירה"],
            vibe_tags=["מצחיק ומשעשע"] if i % 2 else ["כבד/מעיק"],
        )
        for i in range(8)
    ]
    rev = build_dashboard(history)["experiment_analysis"]["revealed_preferences"]
    patterns = rev["positive_patterns"] + rev["negative_patterns"]
    assert any(p["appearances"] >= 2 for p in patterns)   # no more "not enough data"
