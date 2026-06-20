"""The server resolves emails/usernames to the canonical anonymized id, so the
imported questionnaire history is actually retrievable by score/insights."""
from server.db import relational
from server.db.import_questionnaire import import_questionnaire
from server.pipeline.questionnaire_loader import (
    _anonymous_user_id,
    load_date_experience_dataframe,
    resolve_user_id,
)


def test_resolve_is_idempotent():
    resolved = resolve_user_id("Yael.c40@gmail.com")
    assert resolve_user_id(resolved) == resolved        # resolving twice is safe


def test_resolve_matches_loader_anonymization():
    email = "Some.User@Example.com"
    assert resolve_user_id(email) == _anonymous_user_id(email)


def test_history_is_retrievable_by_username_after_import():
    """End-to-end: import, then look the user up by their human identifier."""
    import_questionnaire(verbose=False)
    username = str(load_date_experience_dataframe()["username"].iloc[0])
    history = relational.get_history(resolve_user_id(username))
    assert len(history) >= 1                              # found, not cold-start
