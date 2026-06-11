"""POST /score - real-time match score for a scraped profile (section 2.3.3/2.3.4).

The extension sends the user id and the dry profile tokens it scraped; we load
that user's accrued history, fit the per-user predictor, and return the overlay
payload (score + confidence + top reasons).
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from server.db import relational
from server.pipeline.presentation import build_overlay

router = APIRouter(tags=["score"])


class ScoreRequest(BaseModel):
    user_id: str
    profile: List[str]


@router.post("/score")
def score(req: ScoreRequest) -> dict:
    history = relational.get_history(req.user_id)
    return build_overlay(history, req.profile)
