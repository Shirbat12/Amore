"""Module 2.3.2 - cross features to infer 'revealed preferences'.

Builds, from the accrued history, two association views:
  - trait_dist: for each dry profile feature, the probability distribution over
    character traits that showed up on dates with that feature.
  - vas_mean:   for each dry profile feature, the mean date outcome (VAS).

These let the system reason about a brand-new profile that has only dry data:
its expected traits and expected outcome are read off these tables.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean
from typing import Dict, List, Tuple

from server.models import DateRecord


def _to_distribution(counter: Counter) -> Dict[str, float]:
    total = sum(counter.values())
    if total == 0:
        return {}
    return {k: v / total for k, v in counter.items()}


def learn_revealed_preferences(
    history: List[DateRecord],
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, float]]:
    """Return (trait_dist, vas_mean) keyed by dry profile feature."""
    trait_counts: Dict[str, Counter] = defaultdict(Counter)   # feature -> {trait: n}
    vas_by_feature: Dict[str, list] = defaultdict(list)       # feature -> [vas, ...]

    for d in history:
        for f in d.profile:
            vas_by_feature[f].append(d.vas)
            for t in d.tags:
                trait_counts[f][t] += 1

    trait_dist = {f: _to_distribution(c) for f, c in trait_counts.items()}
    vas_mean = {f: mean(v) for f, v in vas_by_feature.items() if v}
    return trait_dist, vas_mean
