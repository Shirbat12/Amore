"""POST /selection - log a Like/Pass the user made in the app (section 4.1).

The extension's selection_logger fires this for every swipe. We persist it so the
Decision-Alignment KPI can later ask: of the profiles the user *liked*, how many
carried the features A-MORE found to be positive for them?
"""
from __future__ import annotations

from typing import List, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from server.db import relational

router = APIRouter(tags=["selection"])


class SelectionRequest(BaseModel):
    user_id: str
    action: Literal["like", "pass"]
    profile: List[str]


@router.post("/selection")
def log_selection(req: SelectionRequest) -> dict:
    relational.save_selection(req.user_id, req.action, req.profile)
    return {"status": "logged", "action": req.action, "n_tokens": len(req.profile)}
