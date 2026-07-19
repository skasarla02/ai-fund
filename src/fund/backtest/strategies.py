"""Strategies: functions that turn price history into target weights.

A strategy is any callable with the signature::

    strategy(history: dict[str, pd.DataFrame], context: dict) -> dict[str, float]

where ``history`` maps symbol -> OHLCV bars strictly up to and including the
current decision bar (the engine guarantees no lookahead), and the return value
maps symbol -> target portfolio weight (fractions summing to <= 1.0; leftover is
held as cash).

The Phase 2 LLM decision engine implements this exact interface, so it drops
into the same backtester with no changes.
"""
from __future__ import annotations

import pandas as pd

from fund.signals.indicators import momentum


def cross_sectional_momentum(
    history: dict[str, pd.DataFrame],
    context: dict,
    lookback: int = 90,
    top_k: int = 3,
) -> dict[str, float]:
    """Equal-weight the ``top_k`` assets with the highest positive momentum.

    A standard, defensible baseline — the point of Phase 1 is a real track
    record to beat, not a clever alpha. If fewer than ``top_k`` assets have
    positive momentum, only those are held and the rest stays in cash.
    """
    scores: dict[str, float] = {}
    for symbol, bars in history.items():
        close = bars["close"].dropna()
        if len(close) <= lookback:
            continue
        mom = momentum(close, lookback).iloc[-1]
        if pd.notna(mom):
            scores[symbol] = float(mom)

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    winners = [(s, m) for s, m in ranked if m > 0][:top_k]
    if not winners:
        return {}
    weight = 1.0 / len(winners)
    return {symbol: weight for symbol, _ in winners}


def buy_and_hold(
    history: dict[str, pd.DataFrame], context: dict
) -> dict[str, float]:
    """Equal-weight every asset that has data — the naive benchmark strategy."""
    symbols = [s for s, bars in history.items() if not bars["close"].dropna().empty]
    if not symbols:
        return {}
    weight = 1.0 / len(symbols)
    return {s: weight for s in symbols}
