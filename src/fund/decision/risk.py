"""The risk gate: turn model convictions into portfolio weights, in code.

This is deliberately *not* the model's job. The LLM says how confident it is;
this module decides how much to hold, subject to hard limits (max position size,
max gross exposure, a conviction floor). Keeping sizing here means position risk
is governed by auditable rules, not by a paragraph of model prose.
"""
from __future__ import annotations

from fund.decision.schemas import AssetView


def convictions_to_weights(
    views: list[AssetView],
    max_weight: float = 0.34,
    target_gross: float = 1.0,
    min_conviction: float = 0.55,
) -> dict[str, float]:
    """Map per-asset convictions to long-only target weights.

    Only ``long`` stances with conviction >= ``min_conviction`` are held. Each
    name is weighted by its *edge over a coin flip* (conviction - 0.5), then
    capped at ``max_weight`` and scaled so the book never exceeds ``target_gross``.
    Whatever isn't allocated stays in cash.
    """
    candidates = [
        v for v in views
        if v.stance == "long" and _clamp01(v.conviction) >= min_conviction
    ]
    edges = {v.symbol: max(_clamp01(v.conviction) - 0.5, 0.0) for v in candidates}
    total_edge = sum(edges.values())
    if total_edge <= 0:
        return {}

    weights = {s: e / total_edge * target_gross for s, e in edges.items()}
    weights = {s: min(w, max_weight) for s, w in weights.items()}

    gross = sum(weights.values())
    if gross > target_gross:  # scaling down only shrinks, so the cap still holds
        weights = {s: w * target_gross / gross for s, w in weights.items()}
    return {s: round(w, 6) for s, w in weights.items() if w > 0}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))
