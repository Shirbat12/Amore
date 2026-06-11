"""Generate synthetic DateRecords with a built-in latent preference.

Creates a user who genuinely enjoys 'interest:travel' and dislikes
'interest:finance', so the correlation engine and predictor have a real signal
to recover. Deterministic (seeded) so tests are stable.

Run:  python -m data.samples.generate_samples
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List

from server.models import DateRecord

OUT = Path(__file__).resolve().parent / "sample_dates.json"

PROFILE_POOL = [
    "interest:travel", "interest:finance", "interest:music", "interest:sports",
    "hobby:cooking", "hobby:gaming", "age:23-26", "age:27-30",
]
# Latent truth: these features push the date's VAS up or down.
FEATURE_EFFECT = {
    "interest:travel": +22, "interest:music": +10, "hobby:cooking": +8,
    "interest:finance": -20, "hobby:gaming": -6,
}
# Traits that tend to co-occur with certain features (drives revealed prefs).
FEATURE_TRAITS = {
    "interest:travel": ["מצחיק", "זורם בשיחה", "תוסס"],
    "interest:finance": ["משעמם", "מרוכז בעצמו"],
    "interest:music": ["אנרגטי", "מצחיק"],
    "hobby:cooking": ["חמים", "אכפתי"],
}


def _make_record(rng: random.Random, user_id: str) -> DateRecord:
    k = rng.randint(2, 3)
    profile = rng.sample(PROFILE_POOL, k)
    base = 55 + sum(FEATURE_EFFECT.get(f, 0) for f in profile)
    vas = max(0.0, min(100.0, base + rng.gauss(0, 7)))

    tags = []
    for f in profile:
        for t in FEATURE_TRAITS.get(f, []):
            if rng.random() < 0.7:
                tags.append(t)
    tags = list(dict.fromkeys(tags))             # de-dup, keep order
    sentiment = max(-1.0, min(1.0, (vas - 50) / 50))

    return DateRecord(
        user_id=user_id,
        vas=round(vas, 1),
        vas_scores={"attraction": round(vas, 1)},
        profile=profile,
        tags=tags,
        sentiment=round(sentiment, 2),
        second_date=(vas >= 65),
        raw_text="(synthetic)",
    )


def generate(n: int = 30, user_id: str = "demo_user", seed: int = 42) -> List[DateRecord]:
    rng = random.Random(seed)
    return [_make_record(rng, user_id) for _ in range(n)]


if __name__ == "__main__":
    records = generate()
    OUT.write_text(
        json.dumps([r.model_dump() for r in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} records to {OUT}")
