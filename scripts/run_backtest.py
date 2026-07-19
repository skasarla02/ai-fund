#!/usr/bin/env python3
"""Run baseline backtests on live (free) data and save results.

Usage:
    python scripts/run_backtest.py                # both equities + crypto
    python scripts/run_backtest.py --only equities
    python scripts/run_backtest.py --only crypto

Results (metrics JSON + equity/weights CSVs) are written to ./results/ for the
dashboard to consume later.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make `src` importable when run as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from fund.backtest.engine import run_backtest  # noqa: E402
from fund.backtest.metrics import compute_metrics  # noqa: E402
from fund.backtest.strategies import cross_sectional_momentum  # noqa: E402
from fund.config import (  # noqa: E402
    CALENDAR_DAYS_PER_YEAR,
    CRYPTO_BENCHMARK,
    CRYPTO_UNIVERSE,
    EQUITY_BENCHMARK,
    EQUITY_UNIVERSE,
    RESULTS_DIR,
    TRADING_DAYS_PER_YEAR,
)
from fund.data.market import get_bars  # noqa: E402


def benchmark_curve(asset, dates, starting_cash):
    """Buy-and-hold equity curve for a single benchmark asset, aligned to dates."""
    bars = get_bars(asset)
    close = bars["close"].reindex(dates).ffill()
    close = close.dropna()
    if close.empty:
        return None
    return starting_cash * close / close.iloc[0]


def run_one(name, universe, benchmark_asset, start, warmup, periods_per_year, starting_cash):
    print(f"\n{'=' * 60}\n{name.upper()} — cross-sectional momentum\n{'=' * 60}")
    result = run_backtest(
        universe,
        cross_sectional_momentum,
        start=start,
        warmup=warmup,
        periods_per_year=periods_per_year,
        starting_cash=starting_cash,
    )

    bench = benchmark_curve(benchmark_asset, result.equity_curve.index, starting_cash)
    metrics = compute_metrics(
        result.equity_curve, periods_per_year=periods_per_year, benchmark=bench
    )

    period = f"{result.equity_curve.index[0].date()} -> {result.equity_curve.index[-1].date()}"
    print(f"period: {period}  ({metrics['n_days']} days)")
    print(f"final equity: ${result.equity_curve.iloc[-1]:,.0f}")
    _print_metrics(metrics, benchmark_asset.symbol)

    # Persist for the dashboard.
    (RESULTS_DIR / f"{name}_metrics.json").write_text(json.dumps(metrics, indent=2))
    result.equity_curve.rename("strategy").to_frame().assign(
        benchmark=bench
    ).to_csv(RESULTS_DIR / f"{name}_equity.csv")
    result.weights.to_csv(RESULTS_DIR / f"{name}_weights.csv")
    result.blotter.to_csv(RESULTS_DIR / f"{name}_blotter.csv", index=False)
    return metrics


def _print_metrics(m, bench_symbol):
    show = [
        ("Total return", "total_return", "pct"),
        (f"vs {bench_symbol} (buy&hold)", "benchmark_total_return", "pct"),
        ("Excess return", "excess_return", "pct"),
        ("CAGR", "cagr", "pct"),
        ("Ann. volatility", "ann_volatility", "pct"),
        ("Sharpe", "sharpe", "num"),
        ("Sortino", "sortino", "num"),
        ("Max drawdown", "max_drawdown", "pct"),
        ("Calmar", "calmar", "num"),
        ("Beta vs bench", "beta", "num"),
    ]
    for label, key, kind in show:
        if key not in m:
            continue
        val = m[key]
        formatted = f"{val:+.1%}" if kind == "pct" else f"{val:,.2f}"
        print(f"  {label:>22}: {formatted}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["equities", "crypto"], default=None)
    parser.add_argument("--equity-start", default="2019-01-01")
    parser.add_argument("--cash", type=float, default=100_000)
    args = parser.parse_args()

    if args.only in (None, "equities"):
        run_one(
            "equities", EQUITY_UNIVERSE, EQUITY_BENCHMARK,
            start=args.equity_start, warmup=200,
            periods_per_year=TRADING_DAYS_PER_YEAR, starting_cash=args.cash,
        )
    if args.only in (None, "crypto"):
        run_one(
            "crypto", CRYPTO_UNIVERSE, CRYPTO_BENCHMARK,
            start=None, warmup=120,
            periods_per_year=CALENDAR_DAYS_PER_YEAR, starting_cash=args.cash,
        )
    print(f"\nResults written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
