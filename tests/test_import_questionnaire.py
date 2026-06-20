"""Tests for the questionnaire -> DB importer (deterministic, idempotent ids)."""
from server.db.import_questionnaire import prepare_records


def test_ids_are_deterministic():
    """Re-parsing produces identical ids — the basis of idempotent imports."""
    ids1 = [r.id for r in prepare_records()]
    ids2 = [r.id for r in prepare_records()]
    assert ids1 == ids2


def test_ids_are_unique():
    """No two prepared dates collide, so nothing is silently dropped."""
    ids = [r.id for r in prepare_records()]
    assert len(set(ids)) == len(ids)


def test_records_have_outcome_and_features():
    """Imported records carry what the predictor needs."""
    records = prepare_records()
    assert records
    sample = records[0]
    assert sample.profile and 0 <= sample.vas <= 100
