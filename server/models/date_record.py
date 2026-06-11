"""The central data structures that flow through the whole pipeline.

VibeForm  -> what the questionnaire submits (section 4.2)
DateRecord -> the quantified record produced by module 2.3.1 and consumed by
              every downstream module.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VibeForm(BaseModel):
    """Raw post-date questionnaire payload sent by the client to /feedback."""

    user_id: str
    # Dry profile tokens scraped from the app, e.g. "interest:travel", "age:25-30".
    profile: List[str] = Field(default_factory=list)
    # Continuous VAS sliders, each 0-100 (section 4.2).
    vas_scores: Dict[str, float] = Field(default_factory=dict)
    # Word-bank selections (context, not character traits).
    topic_tags: List[str] = Field(default_factory=list)
    vibe_tags: List[str] = Field(default_factory=list)
    # "yes" -> True, "no" -> False, "maybe" -> None.
    second_date: Optional[bool] = None
    free_text: str = ""

    def primary_vas(self) -> float:
        """The main outcome variable: romantic chemistry/attraction.

        Falls back to the mean of all sliders if 'attraction' wasn't sent.
        """
        if "attraction" in self.vas_scores:
            return float(self.vas_scores["attraction"])
        if self.vas_scores:
            return float(sum(self.vas_scores.values()) / len(self.vas_scores))
        return 50.0


class DateRecord(BaseModel):
    """One quantified date - the unit the learning core operates on."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    user_id: str
    vas: float                                   # primary outcome, 0-100
    vas_scores: Dict[str, float] = Field(default_factory=dict)
    profile: List[str] = Field(default_factory=list)     # dry feature tokens
    tags: List[str] = Field(default_factory=list)        # NLP character traits
    topic_tags: List[str] = Field(default_factory=list)
    vibe_tags: List[str] = Field(default_factory=list)
    sentiment: float = 0.0                       # [-1, 1]
    second_date: Optional[bool] = None
    raw_text: str = ""
    created_at: str = Field(default_factory=_now_iso)
