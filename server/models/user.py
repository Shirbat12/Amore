"""The user entity and their baseline metrics (section 4.2, stage A)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    user_id: str
    # Baseline measured before installing the extension, used by the
    # conversion-ratio KPI as the personal reference point.
    baseline_first_dates: int = 0
    baseline_second_dates: int = 0
    baseline_burnout: Optional[int] = Field(None, ge=1, le=10)
