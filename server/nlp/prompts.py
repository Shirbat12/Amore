"""Prompt construction for the tag-extraction model (section 2.3.1).

The prompt pins the model to the closed tag list and a strict JSON schema, with
a couple of Hebrew few-shot examples so it learns the expected mapping.
"""
from __future__ import annotations

import json
from typing import List

FEW_SHOT_HE = [
    {
        "text": "היה ממש כיף, הוא היה מצחיק ודברן וזרמנו כל הערב",
        "out": {"tags": ["מצחיק", "דברן", "זורם בשיחה"], "sentiment": 0.8},
    },
    {
        "text": "די משעמם, הוא דיבר רק על עצמו ולא ממש הקשיב לי",
        "out": {"tags": ["משעמם", "מרוכז בעצמו"], "sentiment": -0.6},
    },
]


def build_prompt(closed_tags: List[str], few_shot: List[dict], free_text: str) -> str:
    """Return the full instruction string sent to the model."""
    tag_line = ", ".join(closed_tags)
    examples = "\n".join(
        f'טקסט: "{ex["text"]}"\nפלט: {json.dumps(ex["out"], ensure_ascii=False)}'
        for ex in few_shot
    )
    return (
        "אתה ממפה תיאור חופשי של דייט לתגיות אופי מתוך רשימה סגורה בלבד.\n"
        f"הרשימה הסגורה: [{tag_line}].\n"
        "החזר אך ורק JSON תקין בפורמט: "
        '{"tags": [..], "sentiment": <מספר בין -1 ל-1>}.\n'
        "בחר רק תגיות מהרשימה. אל תמציא תגיות חדשות.\n\n"
        f"{examples}\n\n"
        f'טקסט: "{free_text}"\nפלט:'
    )
