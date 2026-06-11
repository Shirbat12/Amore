"""Module 2.3.1 - quantify the post-date experience.

Turns one subjective Vibe form into a structured DateRecord by encoding the free
text into closed-list tags + sentiment via the language model, with a retry loop
and graceful degradation (keep the date, drop the tags) on persistent failure.
"""
from __future__ import annotations

from server import config
from server.models import DateRecord, TagOutput, VibeForm
from server.nlp.gemini_client import gemini


def _try_validate(raw: dict | None) -> TagOutput | None:
    if raw is None:
        return None
    try:
        return TagOutput(**raw)
    except Exception:  # noqa: BLE001 - any schema/type error -> retry
        return None


def quantify_experience(form: VibeForm) -> DateRecord:
    """VibeForm -> DateRecord (the pseudo-code of section 2.3.1, made real)."""
    parsed: TagOutput | None = None
    for _ in range(config.MAX_RETRIES):          # Gemini sometimes breaks schema
        raw = gemini.extract_tags(form.free_text)
        parsed = _try_validate(raw)
        if parsed is not None:
            break
    if parsed is None:
        parsed = TagOutput(tags=[], sentiment=0.0)  # keep the date, drop the tags

    return DateRecord(
        user_id=form.user_id,
        vas=form.primary_vas(),
        vas_scores=form.vas_scores,
        profile=form.profile,
        tags=parsed.tags,
        topic_tags=form.topic_tags,
        vibe_tags=form.vibe_tags,
        sentiment=parsed.sentiment,
        second_date=form.second_date,
        raw_text=form.free_text,
    )
