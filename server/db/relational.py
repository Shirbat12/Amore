"""Relational store (SQLite) - the structured, consistent data (section 2.1).

Holds users, their baseline metrics, and the structured per-date fields. Rich
list fields are stored as JSON text for convenience; the canonical rich copy
lives in the document store.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

from server import config
from server.models import DateRecord, User


_INITIALIZED = False


def _connect() -> sqlite3.Connection:
    _ensure_init()
    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_init() -> None:
    """Create the schema once per process if it isn't there yet."""
    global _INITIALIZED
    if _INITIALIZED:
        return
    schema = (config.REPO_ROOT / "server" / "db" / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(config.SQLITE_PATH)
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()
    _INITIALIZED = True


def init_db() -> None:
    """Public, explicit initialization (called on app startup)."""
    _ensure_init()


# --- users ---------------------------------------------------------------
def upsert_user(user: User) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT INTO users (user_id, baseline_first_dates,
                   baseline_second_dates, baseline_burnout)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   baseline_first_dates = excluded.baseline_first_dates,
                   baseline_second_dates = excluded.baseline_second_dates,
                   baseline_burnout = excluded.baseline_burnout""",
            (user.user_id, user.baseline_first_dates,
             user.baseline_second_dates, user.baseline_burnout),
        )


def get_user(user_id: str) -> Optional[User]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    if row is None:
        return None
    return User(
        user_id=row["user_id"],
        baseline_first_dates=row["baseline_first_dates"],
        baseline_second_dates=row["baseline_second_dates"],
        baseline_burnout=row["baseline_burnout"],
    )


# --- dates ---------------------------------------------------------------
def _second_date_to_int(value) -> Optional[int]:
    if value is None:
        return None
    return 1 if value else 0


def save_date(record: DateRecord) -> None:
    # Ensure the user row exists so the foreign key holds.
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (record.user_id,)
        )
        conn.execute(
            """INSERT OR REPLACE INTO dates (id, user_id, vas, sentiment,
                   second_date, created_at, vas_scores, profile, tags,
                   topic_tags, vibe_tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.id, record.user_id, record.vas, record.sentiment,
                _second_date_to_int(record.second_date), record.created_at,
                json.dumps(record.vas_scores, ensure_ascii=False),
                json.dumps(record.profile, ensure_ascii=False),
                json.dumps(record.tags, ensure_ascii=False),
                json.dumps(record.topic_tags, ensure_ascii=False),
                json.dumps(record.vibe_tags, ensure_ascii=False),
            ),
        )


def _row_to_record(row: sqlite3.Row) -> DateRecord:
    sd = row["second_date"]
    return DateRecord(
        id=row["id"],
        user_id=row["user_id"],
        vas=row["vas"],
        sentiment=row["sentiment"],
        second_date=(None if sd is None else bool(sd)),
        created_at=row["created_at"],
        vas_scores=json.loads(row["vas_scores"] or "{}"),
        profile=json.loads(row["profile"] or "[]"),
        tags=json.loads(row["tags"] or "[]"),
        topic_tags=json.loads(row["topic_tags"] or "[]"),
        vibe_tags=json.loads(row["vibe_tags"] or "[]"),
    )


def get_history(user_id: str) -> List[DateRecord]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM dates WHERE user_id = ? ORDER BY created_at", (user_id,)
        ).fetchall()
    return [_row_to_record(r) for r in rows]


# --- selections (Decision-Alignment KPI) ---------------------------------
def save_selection(user_id: str, action: str, profile: List[str]) -> None:
    """Persist one Like/Pass event with the profile tokens seen at click time."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
        )
        conn.execute(
            """INSERT INTO selections (user_id, action, profile, created_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, action, json.dumps(profile, ensure_ascii=False),
             datetime.now(timezone.utc).isoformat()),
        )


def get_selections(user_id: str, action: Optional[str] = None) -> List[Dict]:
    """Return the user's selection events, optionally filtered to one action."""
    query = "SELECT action, profile, created_at FROM selections WHERE user_id = ?"
    params: list = [user_id]
    if action is not None:
        query += " AND action = ?"
        params.append(action)
    query += " ORDER BY created_at"
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        {"action": r["action"],
         "profile": json.loads(r["profile"] or "[]"),
         "created_at": r["created_at"]}
        for r in rows
    ]
