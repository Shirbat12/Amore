"""Import the questionnaire .xlsx responses into the SQLite DB (single source of truth).

Why this exists
---------------
Pilot dates were collected via Google Forms and live only in
`data/questionnaire/*.xlsx`. The scoring path (`/score`) and `/insights` read the
DB (`relational.get_history`), so until those rows are in the DB they are
invisible to scoring. This module bridges that gap.

It is **idempotent**: each date gets a deterministic id derived from
(user_id, form timestamp), and `save_date` does INSERT OR REPLACE — so you can
re-run it every time you add new responses and it will update, never duplicate.

Workflow (run after exporting new form responses over the .xlsx):
    python -m server.db.import_questionnaire
"""
from __future__ import annotations

import hashlib
from typing import List, Tuple

from server.db import relational
from server.models import DateRecord
from server.pipeline.questionnaire_loader import (
    dataframe_to_date_records,
    load_date_experience_dataframe,
)


def _stable_id(user_id: str, timestamp: object) -> str:
    """Deterministic id from the response's user + form timestamp (unique per row)."""
    key = f"{user_id}|{timestamp}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:32]


def _content_id(record: DateRecord) -> str:
    """Fallback deterministic id from the record's own content."""
    key = "|".join([
        record.user_id,
        ",".join(sorted(record.profile)),
        f"{record.vas:.2f}",
        record.raw_text or "",
        ",".join(sorted(record.tags)),
    ])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:32]


def prepare_records() -> List[DateRecord]:
    """Parse the .xlsx into DateRecords with deterministic ids (no DB write)."""
    df = load_date_experience_dataframe()
    records = dataframe_to_date_records(df)

    aligned = len(records) == len(df) and "timestamp" in df.columns
    timestamps = list(df["timestamp"]) if aligned else [None] * len(records)

    seen, prepared = set(), []
    for record, ts in zip(records, timestamps):
        if aligned and ts is not None and str(ts).strip():
            record.id = _stable_id(record.user_id, ts)
        else:
            record.id = _content_id(record)
        if record.id in seen:                 # guard against exact duplicate rows
            continue
        seen.add(record.id)
        prepared.append(record)
    return prepared


def import_questionnaire(verbose: bool = True) -> Tuple[int, int]:
    """Upsert all questionnaire dates into the DB. Returns (written, parsed)."""
    relational.init_db()
    records = prepare_records()
    for record in records:
        relational.save_date(record)         # INSERT OR REPLACE by deterministic id

    users = {r.user_id for r in records}
    if verbose:
        print(f"Imported {len(records)} dates across {len(users)} users into the DB.")
        print("(idempotent — re-running updates the same rows, never duplicates)")
    return len(records), len(records)


if __name__ == "__main__":
    import_questionnaire()
