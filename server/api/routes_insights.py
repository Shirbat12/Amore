"""GET /insights - aggregated data for the decision-support dashboard (2.3.4)."""
from __future__ import annotations

from fastapi import APIRouter

from evaluation.kpis import decision_alignment_report
from server.db import relational
from server.pipeline.presentation import build_dashboard, build_questionnaire_dashboard

router = APIRouter(tags=["insights"])


@router.get("/insights/{user_id}")
def insights(user_id: str) -> dict:
    history = relational.get_history(user_id)

    if history:
        selections = relational.get_selections(user_id)
        payload = build_dashboard(history)
        payload["data_source"] = "sqlite_user_history"
        payload["user_id"] = user_id
        payload["decision_alignment"] = decision_alignment_report(history, selections)
        return payload

    payload = build_questionnaire_dashboard(user_id=user_id)
    payload["data_source"] = "questionnaire_responses"
    payload["user_id"] = user_id
    payload["is_demo_fallback"] = True
    return payload

    # Development/demo path: build the dashboard from the real questionnaire
    # pipeline instead of synthetic sample_dates.json / generate_samples.py.
    return build_questionnaire_dashboard(user_id=user_id)
