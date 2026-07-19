"""Performance and risk metrics for an equity curve.

These are the numbers that make the project credible: not just total return, but
risk-adjusted and benchmark-relative measures a reviewer will actually probe.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from fund.config import CALENDAR_DAYS_PER_YEAR


def compute_metrics(
    equity_curve: pd.Series,
    periods_per_year: int = CALENDAR_DAYS_PER_YEAR,
    risk_free_rate: float = 0.0,
    benchmark: pd.Series | None = None,
) -> dict[str, float]:
    """Summary stats for an equity curve (a Series indexed by date).

    Returns total return, CAGR, annualized vol, Sharpe, Sortino, max drawdown,
    Calmar, and — if a benchmark curve is supplied — excess return and beta.
    """
    curve = equity_curve.dropna()
    if len(curve) < 2:
        return {}

    rets = curve.pct_change(fill_method=None).dropna()
    total_return = curve.iloc[-1] / curve.iloc[0] - 1.0
    n_years = len(curve) / periods_per_year
    cagr = (curve.iloc[-1] / curve.iloc[0]) ** (1 / n_years) - 1.0 if n_years > 0 else np.nan

    ann_vol = rets.std() * np.sqrt(periods_per_year)
    rf_per_period = risk_free_rate / periods_per_year
    excess = rets - rf_per_period
    sharpe = (
        excess.mean() / rets.std() * np.sqrt(periods_per_year)
        if rets.std() > 0
        else np.nan
    )
    downside = rets[rets < 0].std()
    sortino = (
        excess.mean() / downside * np.sqrt(periods_per_year)
        if downside and downside > 0
        else np.nan
    )

    max_dd = max_drawdown(curve)
    calmar = cagr / abs(max_dd) if max_dd < 0 else np.nan

    out = {
        "total_return": float(total_return),
        "cagr": float(cagr),
        "ann_volatility": float(ann_vol),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_drawdown": float(max_dd),
        "calmar": float(calmar),
        "n_days": int(len(curve)),
    }

    if benchmark is not None:
        bench = benchmark.reindex(curve.index).dropna()
        common = curve.index.intersection(bench.index)
        if len(common) > 2:
            bench_ret = bench.loc[common].pct_change(fill_method=None).dropna()
            port_ret = curve.loc[common].pct_change(fill_method=None).dropna()
            aligned = pd.concat([port_ret, bench_ret], axis=1, join="inner").dropna()
            bench_total = bench.loc[common].iloc[-1] / bench.loc[common].iloc[0] - 1.0
            out["benchmark_total_return"] = float(bench_total)
            out["excess_return"] = float(total_return - bench_total)
            if len(aligned) > 2 and aligned.iloc[:, 1].var() > 0:
                cov = aligned.cov().iloc[0, 1]
                out["beta"] = float(cov / aligned.iloc[:, 1].var())
    return out


def max_drawdown(equity_curve: pd.Series) -> float:
    """Largest peak-to-trough decline as a negative fraction (e.g. -0.23)."""
    curve = equity_curve.dropna()
    if curve.empty:
        return 0.0
    running_max = curve.cummax()
    drawdown = curve / running_max - 1.0
    return float(drawdown.min())
