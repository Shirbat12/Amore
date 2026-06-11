"""GET /insights - aggregated data for the decision-support dashboard (2.3.4)."""
from __future__ import annotations

from fastapi import APIRouter

from evaluation.kpis import decision_alignment_report
from server.db import relational
from server.pipeline.presentation import build_dashboard

router = APIRouter(tags=["insights"])


@router.get("/insights/{user_id}")
def insights(user_id: str) -> dict:
    history = relational.get_history(user_id)
    selections = relational.get_selections(user_id)
    payload = build_dashboard(history)
    # Attach the Decision-Alignment KPI (section 4.1) computed from logged swipes.
    payload["decision_alignment"] = decision_alignment_report(history, selections)
    return payload
