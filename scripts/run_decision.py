#!/usr/bin/env python3
"""Run the LLM decision engine and print a memo.

Runs in MOCK mode automatically when ANTHROPIC_API_KEY is unset (no key, no
network — proves the pipeline). Set the key in a local .env to run it for real.

    python scripts/run_decision.py                  # one decision on equities
    python scripts/run_decision.py --universe crypto
    python scripts/run_decision.py --backtest       # mock backtest + calibration
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fund.config import (  # noqa: E402
    CALENDAR_DAYS_PER_YEAR, CRYPTO_UNIVERSE, EQUITY_UNIVERSE, TRADING_DAYS_PER_YEAR,
)
from fund.decision.engine import DecisionEngine  # noqa: E402
from fund.decision.strategy import make_llm_strategy  # noqa: E402
from fund.data.market import get_bars  # noqa: E402
from fund.signals.indicators import signal_snapshot  # noqa: E402


def one_decision(universe, periods_per_year):
    engine = DecisionEngine()
    mode = "MOCK (no API key)" if engine.client.mock else f"LIVE ({engine.client.model})"
    print(f"\n{'=' * 62}\nDECISION ENGINE — {mode}\n{'=' * 62}")

    snapshots = {}
    for asset in universe:
        bars = get_bars(asset)
        if not bars.empty:
            snapshots[asset.symbol] = signal_snapshot(bars["close"], periods_per_year)

    decision = engine.decide(snapshots, {"timestamp": "latest"})

    print(f"\nMarket view:\n  {decision.desk.market_view}\n")
    print(f"{'symbol':<8}{'stance':<8}{'conv.':<7}thesis")
    print("-" * 62)
    for v in decision.desk.assets:
        print(f"{v.symbol:<8}{v.stance:<8}{v.conviction:<7.2f}{v.thesis[:60]}")

    print("\nTarget weights (after code-side risk gate):")
    if decision.weights:
        for sym, w in sorted(decision.weights.items(), key=lambda kv: -kv[1]):
            print(f"  {sym:<8}{w:>7.1%}")
        print(f"  {'cash':<8}{1 - sum(decision.weights.values()):>7.1%}")
    else:
        print("  100% cash — no position cleared the conviction floor.")

    if not engine.client.mock:
        print(f"\nLLM cost this run: ${engine.client.total_cost_usd:.4f}")
    print(f"\nMemo written to results/memos/ (as_of={decision.memo['as_of']})")


def mock_backtest_calibration(universe, start, periods_per_year):
    """Exercise the full loop: LLM strategy -> memos -> calibration score."""
    from fund.backtest.engine import run_backtest
    from fund.eval.calibration import load_memos, make_panel_forward_return, score_calibration

    print(f"\n{'=' * 62}\nMOCK BACKTEST + CALIBRATION\n{'=' * 62}")
    engine = DecisionEngine()  # mock if no key
    strat = make_llm_strategy(engine, periods_per_year=periods_per_year)
    result = run_backtest(
        universe, strat, start=start, warmup=200,
        rebalance_every=21, periods_per_year=periods_per_year,
    )
    print(result.summary())

    report = score_calibration(
        load_memos(),
        make_panel_forward_return(result.close_panel),
        horizon_days=21,
    )
    if report:
        print("\n" + report.summary())
        print("\nReliability table (predicted vs. actual):")
        print(report.bins.to_string(index=False))
    else:
        print("\nNot enough resolved outcomes to score calibration yet.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", choices=["equities", "crypto"], default="equities")
    parser.add_argument("--backtest", action="store_true")
    args = parser.parse_args()

    if args.universe == "crypto":
        universe, ppy, start = CRYPTO_UNIVERSE, CALENDAR_DAYS_PER_YEAR, None
    else:
        universe, ppy, start = EQUITY_UNIVERSE, TRADING_DAYS_PER_YEAR, "2019-01-01"

    if args.backtest:
        mock_backtest_calibration(universe, start, ppy)
    else:
        one_decision(universe, ppy)


if __name__ == "__main__":
    main()
