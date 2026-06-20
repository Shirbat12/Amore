"""POST /feedback - ingest one post-date Vibe questionnaire (section 2.3.1).

Runs the quantify-experience module on the submission, then persists the
resulting record to both stores.
"""
from __future__ import annotations

from fastapi import APIRouter

from server.db import document_store, relational
from server.models import VibeForm
from server.pipeline.questionnaire_loader import resolve_user_id
from server.pipeline.quantify_experience import quantify_experience

router = APIRouter(tags=["feedback"])


@router.post("/feedback")
def submit_feedback(form: VibeForm) -> dict:
    # Store live feedback under the same canonical id as the imported data.
    form.user_id = resolve_user_id(form.user_id)
    record = quantify_experience(form)
    relational.save_date(record)
    document_store.save_document(record)
    return {
        "id": record.id,
        "vas": record.vas,
        "extracted_tags": record.tags,
        "sentiment": record.sentiment,
    }
