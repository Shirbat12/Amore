"""Ablation experiments (project book section 4).

Quantifies how much each pipeline component contributes by disabling it and
re-measuring prediction accuracy. Run:  python -m evaluation.ablation
"""
from __future__ import annotations

import copy
from typing import List

from evaluation.kpis import prediction_accuracy
from server.models import DateRecord


def _strip_tags(history: List[DateRecord]) -> List[DateRecord]:
    """Variant with NLP tags removed (tests the contribution of module 2.3.1)."""
    out = []
    for d in history:
        c = copy.deepcopy(d)
        c.tags = []
        c.sentiment = 0.0
        out.append(c)
    return out


def _shuffle_profiles(history: List[DateRecord]) -> List[DateRecord]:
    """Control: break the profile<->outcome link to confirm signal is real."""
    profiles = [d.profile for d in history]
    rotated = profiles[1:] + profiles[:1]
    out = []
    for d, prof in zip(history, rotated):
        c = copy.deepcopy(d)
        c.profile = prof
        out.append(c)
    return out


def run_ablation(history: List[DateRecord]) -> dict:
    full_rho, full_mae = prediction_accuracy(history)
    notags_rho, notags_mae = prediction_accuracy(_strip_tags(history))
    ctrl_rho, ctrl_mae = prediction_accuracy(_shuffle_profiles(history))
    return {
        "full_model": {"rho": full_rho, "mae": full_mae},
        "no_nlp_tags": {"rho": notags_rho, "mae": notags_mae},
        "shuffled_control": {"rho": ctrl_rho, "mae": ctrl_mae},
    }


if __name__ == "__main__":  # pragma: no cover
    import json
    from pathlib import Path

    from server.models import DateRecord as DR

    samples = Path(__file__).resolve().parent.parent / "data" / "samples" / "sample_dates.json"
    data = [DR(**r) for r in json.loads(samples.read_text(encoding="utf-8"))]
    print(json.dumps(run_ablation(data), indent=2, ensure_ascii=False))
