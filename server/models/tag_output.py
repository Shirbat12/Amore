"""Schema the language model output is validated against (section 2.3.1).

The model is forced to emit JSON shaped like TagOutput. Anything that does not
parse or that contains tags outside the closed list is rejected, which triggers
a retry in quantify_experience().
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, field_validator

from server.nlp.closed_tags import CLOSED_TAGS

_ALLOWED = set(CLOSED_TAGS)


class TagOutput(BaseModel):
    """Structured result of encoding one free-text date description."""

    tags: List[str] = Field(default_factory=list)
    sentiment: float = Field(0.0, ge=-1.0, le=1.0)

    @field_validator("tags")
    @classmethod
    def _only_closed_tags(cls, tags: List[str]) -> List[str]:
        # Drop anything outside the closed vocabulary; keep order, de-duplicate.
        seen, clean = set(), []
        for t in tags:
            t = t.strip()
            if t in _ALLOWED and t not in seen:
                seen.add(t)
                clean.append(t)
        return clean
