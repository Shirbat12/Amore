"""GET /insights - aggregated data for the decision-support dashboard (2.3.4)."""
from __future__ import annotations

from fastapi import APIRouter

from server.db import relational
from server.pipeline.presentation import build_dashboard

router = APIRouter(tags=["insights"])


@router.get("/insights/{user_id}")
def insights(user_id: str) -> dict:
    history = relational.get_history(user_id)
    return build_dashboard(history)
