"""Gemini 2.5 Flash client with a deterministic offline fallback (section 2.3.1).

If GEMINI_API_KEY is set and google-genai is installed, real calls are made.
Otherwise a keyword-based mock tagger runs so the whole pipeline works end-to-end
with zero setup. Both paths return raw dicts shaped like TagOutput; validation
happens in quantify_experience().
"""
from __future__ import annotations

import json
import re
from typing import Optional

from server import config
from server.nlp.closed_tags import CLOSED_TAGS, TAG_KEYWORDS, TAG_VALENCE
from server.nlp.prompts import FEW_SHOT_HE, build_prompt

# Try to load the real SDK lazily; absence is fine.
try:  # pragma: no cover - depends on environment
    from google import genai  # type: ignore

    _HAS_GENAI = True
except Exception:  # noqa: BLE001
    _HAS_GENAI = False


class GeminiClient:
    def __init__(self) -> None:
        self.live = bool(config.GEMINI_API_KEY and _HAS_GENAI)
        self._client = None
        if self.live:  # pragma: no cover - needs network + key
            self._client = genai.Client(api_key=config.GEMINI_API_KEY)

    # -- public API -------------------------------------------------------
    def extract_tags(self, free_text: str) -> Optional[dict]:
        """Return a dict {"tags": [...], "sentiment": x} or None on failure."""
        if not free_text or not free_text.strip():
            return {"tags": [], "sentiment": 0.0}
        if self.live:  # pragma: no cover - real call
            return self._extract_live(free_text)
        return self._extract_mock(free_text)

    # -- real model -------------------------------------------------------
    def _extract_live(self, free_text: str) -> Optional[dict]:  # pragma: no cover
        prompt = build_prompt(CLOSED_TAGS, FEW_SHOT_HE, free_text)
        resp = self._client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        try:
            return json.loads(resp.text)
        except (json.JSONDecodeError, AttributeError):
            return None

    # -- offline fallback -------------------------------------------------
    def _extract_mock(self, free_text: str) -> dict:
        text = free_text.lower()
        tags = [
            tag
            for tag, keywords in TAG_KEYWORDS.items()
            if any(kw.lower() in text for kw in keywords)
        ]
        # Naive sentiment: balance of positive vs negative detected tags,
        # nudged by simple polarity words.
        score = sum(TAG_VALENCE[t] for t in tags)
        if re.search(r"לא|בלי|כלל לא", text) and not tags:
            score -= 1
        sentiment = max(-1.0, min(1.0, score / 3.0))
        return {"tags": tags, "sentiment": round(sentiment, 3)}


# Module-level singleton used by the pipeline.
gemini = GeminiClient()
