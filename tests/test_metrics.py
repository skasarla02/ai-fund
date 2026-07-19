import numpy as np
import pandas as pd

from fund.backtest.metrics import compute_metrics, max_drawdown


def _curve(values):
    idx = pd.date_range("2024-01-01", periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=idx, dtype=float)


def test_max_drawdown_known_value():
    curve = _curve([100, 120, 90, 150])
    # Peak 120 -> trough 90 is -25%.
    assert round(max_drawdown(curve), 6) == -0.25


def test_monotonic_curve_has_no_drawdown():
    curve = _curve([100, 101, 102, 103])
    assert max_drawdown(curve) == 0.0


def test_total_return():
    curve = _curve([100, 150, 200])
    m = compute_metrics(curve)
    assert round(m["total_return"], 6) == 1.0  # 100 -> 200


def test_benchmark_excess_return():
    port = _curve([100, 110, 120])   # +20%
    bench = _curve([100, 105, 110])  # +10%
    m = compute_metrics(port, benchmark=bench)
    assert round(m["benchmark_total_return"], 6) == 0.10
    assert round(m["excess_return"], 6) == 0.10  # 20% - 10%


def test_sharpe_positive_for_upward_drift():
    rng = np.random.default_rng(0)
    daily = 0.001 + rng.normal(0, 0.005, 500)  # positive drift
    curve = _curve(100 * np.cumprod(1 + daily))
    m = compute_metrics(curve)
    assert m["sharpe"] > 0
