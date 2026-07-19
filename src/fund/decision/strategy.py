"""Adapter: expose the LLM decision engine as a backtester strategy.

`make_llm_strategy(engine)` returns a callable with the exact
`(history, context) -> weights` signature the Phase 1 backtester expects, so the
research desk runs through the same lookahead-safe engine as any other strategy.

Note on cost: a live LLM call per rebalance is cheap, but a full multi-year
*daily* backtest would be thousands of calls. Use a coarse `rebalance_every`
(e.g. monthly) and a bounded window when backtesting the live engine — or run it
in mock mode (no key) to exercise the plumbing for free.
"""
from __future__ import annotations

import pandas as pd

from fund.config import CALENDAR_DAYS_PER_YEAR
from fund.decision.engine import DecisionEngine
from fund.signals.indicators import signal_snapshot


def make_llm_strategy(
    engine: DecisionEngine | None = None,
    periods_per_year: int = CALENDAR_DAYS_PER_YEAR,
    min_history: int = 60,
):
    engine = engine or DecisionEngine()

    def strategy(history: dict[str, pd.DataFrame], context: dict) -> dict[str, float]:
        snapshots = {}
        for symbol, bars in history.items():
            close = bars["close"].dropna()
            if len(close) >= min_history:
                snapshots[symbol] = signal_snapshot(close, periods_per_year)
        if not snapshots:
            return {}
        return engine.decide(snapshots, context).weights

    return strategy
