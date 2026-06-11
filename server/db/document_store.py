"""JSON document store (section 2.1) - the semi-structured half of the data.

Archives each date's rich payload (raw free text + full NLP output + the entire
record) as one JSON file per record. This is the flexible, schema-light store
that complements the relational tables; it is handy for auditing the model and
for re-running the pipeline offline.
"""
from __future__ import annotations

import json
from typing import List, Optional

from server import config
from server.models import DateRecord


def _ensure_dir() -> None:
    config.DOCSTORE_DIR.mkdir(parents=True, exist_ok=True)


def save_document(record: DateRecord) -> None:
    _ensure_dir()
    path = config.DOCSTORE_DIR / f"{record.id}.json"
    path.write_text(
        json.dumps(record.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_document(record_id: str) -> Optional[DateRecord]:
    path = config.DOCSTORE_DIR / f"{record_id}.json"
    if not path.exists():
        return None
    return DateRecord(**json.loads(path.read_text(encoding="utf-8")))


def all_documents() -> List[DateRecord]:
    _ensure_dir()
    out = []
    for path in sorted(config.DOCSTORE_DIR.glob("*.json")):
        out.append(DateRecord(**json.loads(path.read_text(encoding="utf-8"))))
    return out
