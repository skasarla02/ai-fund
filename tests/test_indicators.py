import numpy as np
import pandas as pd

from fund.signals.indicators import momentum, rsi, signal_snapshot, sma


def _series(values):
    idx = pd.date_range("2024-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=idx, dtype=float)


def test_sma_last_value():
    s = _series([1, 2, 3, 4, 5])
    assert sma(s, 2).iloc[-1] == 4.5


def test_momentum_simple():
    s = _series([10, 11])
    assert round(momentum(s, 1).iloc[-1], 6) == 0.1


def test_rsi_bounded_and_high_for_uptrend():
    s = _series(list(range(1, 40)))  # strictly increasing
    r = rsi(s).iloc[-1]
    assert 0 <= r <= 100
    assert r > 90  # pure uptrend -> RSI near 100


def test_signal_snapshot_has_expected_keys():
    s = _series(list(np.linspace(100, 200, 260)))
    snap = signal_snapshot(s)
    for key in ["price", "mom_63d", "sma_200", "rsi_14", "vol_30d_ann"]:
        assert key in snap
    assert snap["price"] == 200
