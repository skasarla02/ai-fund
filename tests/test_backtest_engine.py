"""Backtest engine tests on synthetic data (no network).

The most important property to prove is **no lookahead**: the strategy must
never receive a bar dated after its decision timestamp.
"""
import numpy as np
import pandas as pd
import pytest

from fund.backtest import engine as engine_mod
from fund.backtest.engine import run_backtest
from fund.backtest.strategies import cross_sectional_momentum
from fund.data.assets import Asset


def _synthetic(trend: float, n: int = 300, start_price: float = 100.0):
    idx = pd.date_range("2023-01-01", periods=n, freq="D", tz="UTC")
    close = start_price * np.cumprod(1 + np.full(n, trend))
    return pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "volume": 1.0},
        index=idx,
    )


@pytest.fixture
def patched_data(monkeypatch):
    data = {"UP": _synthetic(0.002), "FLAT": _synthetic(0.0)}
    monkeypatch.setattr(engine_mod, "get_bars", lambda asset, **kw: data[asset.symbol])
    return data


def test_backtest_runs_and_marks_equity(patched_data):
    assets = [Asset("UP", "equity"), Asset("FLAT", "equity")]
    result = run_backtest(assets, cross_sectional_momentum, warmup=100, starting_cash=100_000)
    assert len(result.equity_curve) == 300
    assert np.isfinite(result.equity_curve.iloc[-1])
    assert "sharpe" in result.metrics


def test_momentum_picks_the_uptrend_and_profits(patched_data):
    assets = [Asset("UP", "equity"), Asset("FLAT", "equity")]
    result = run_backtest(assets, cross_sectional_momentum, warmup=100, starting_cash=100_000)
    # A persistent uptrend should leave us ahead of where we started.
    assert result.equity_curve.iloc[-1] > 100_000
    assert not result.blotter.empty


def test_no_lookahead(patched_data):
    """Strategy must only ever see history up to its decision timestamp."""
    seen = []

    def spy_strategy(history, context):
        ts = context["timestamp"]
        for bars in history.values():
            if not bars.empty:
                assert bars.index.max() <= ts, "strategy saw a future bar!"
        seen.append(ts)
        return cross_sectional_momentum(history, context)

    assets = [Asset("UP", "equity"), Asset("FLAT", "equity")]
    run_backtest(assets, spy_strategy, warmup=100, starting_cash=100_000)
    assert len(seen) > 0
    # We never decide on the final bar (nothing to fill it against).
    assert max(seen) < _synthetic(0.0).index.max()
