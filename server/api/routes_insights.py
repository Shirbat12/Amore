"""GET /insights - aggregated data for the decision-support dashboard (2.3.4)."""
from __future__ import annotations

from fastapi import APIRouter

from server.db import relational
from server.pipeline.presentation import build_dashboard, build_questionnaire_dashboard
from server.pipeline.questionnaire_loader import resolve_user_id

router = APIRouter(tags=["insights"])


@router.get("/insights/{user_id}")
def insights(user_id: str) -> dict:
    # Map the incoming email/username to the canonical anonymized id the DB uses.
    uid = resolve_user_id(user_id)
    history = relational.get_history(uid)

    if history:
        payload = build_dashboard(history)
        payload["data_source"] = "sqlite_user_history"
        payload["user_id"] = user_id
        return payload

    payload = build_questionnaire_dashboard(user_id=uid)
    payload["data_source"] = "questionnaire_responses"
    payload["user_id"] = user_id
    payload["is_demo_fallback"] = True
    return payload
