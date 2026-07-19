#!/usr/bin/env python3
"""Run the coverage engine across S&P 500 + 400 + 600 (~1,500 companies).

Runs in MOCK mode automatically when ANTHROPIC_API_KEY is unset (no key, no
network calls to Claude — proves the pipeline for free). Set the key in a
local .env to run it for real on claude-sonnet-5.

    python scripts/run_coverage.py --limit 5              # smoke test, a few names
    python scripts/run_coverage.py --tickers NVDA KO JPM  # specific companies
    python scripts/run_coverage.py --tier "S&P 600"       # just the small-cap tier
    python scripts/run_coverage.py                        # full universe (real run: ~$27)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fund.coverage.engine import COVERAGE_MODEL, run_coverage  # noqa: E402
from fund.coverage.universe import fetch_universe  # noqa: E402
from fund.decision.llm import LLMClient  # noqa: E402

# Rough per-company cost at Sonnet 5 intro pricing ($2/$10 per MTok):
# ~5k input (signals+fundamentals+prompt) + ~700 output tokens.
EST_COST_PER_COMPANY = 5000 / 1e6 * 2.0 + 700 / 1e6 * 10.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Rate only the first N companies (universe order).")
    parser.add_argument("--tickers", nargs="+", default=None, help="Rate only these specific tickers.")
    parser.add_argument("--tier", choices=["S&P 500", "S&P 400", "S&P 600"], default=None, help="Restrict to a single index tier.")
    parser.add_argument("--pace", type=float, default=0.0, help="Seconds to sleep between companies (rate-limit friendliness).")
    args = parser.parse_args()

    client = LLMClient(model=COVERAGE_MODEL)
    mode = "MOCK (no API key)" if client.mock else f"LIVE ({client.model})"

    universe = fetch_universe([args.tier] if args.tier else None)
    tickers = args.tickers
    if tickers is None and args.limit:
        tickers = [c.ticker for c in universe[: args.limit]]
    n = len(tickers) if tickers else len(universe)

    print(f"\n{'=' * 62}\nCOVERAGE ENGINE — {mode}\n{'=' * 62}")
    print(f"Universe: {n} companies" + (f" (of {len(universe)} in scope)" if tickers else ""))
    if not client.mock:
        print(f"Estimated cost: ~${n * EST_COST_PER_COMPANY:.2f}")

    t0 = time.time()
    count = {"n": 0}

    def on_result(r):
        count["n"] += 1
        print(f"  [{count['n']:>3}/{n}] {r.ticker:<6} {r.rating.rating:<9} "
              f"conv={r.rating.conviction:.2f}  {r.rating.key_signal[:64]}")

    results = run_coverage(tickers=tickers, client=client, pace_seconds=args.pace, on_result=on_result)

    elapsed = time.time() - t0
    print(f"\n{len(results)}/{n} companies rated in {elapsed:.1f}s.")
    if not client.mock:
        print(f"Actual LLM cost: ${client.total_cost_usd:.4f}")
    if results:
        bullish = sum(1 for r in results if r.rating.rating == "bullish")
        bearish = sum(1 for r in results if r.rating.rating == "bearish")
        print(f"Bullish: {bullish}  Neutral: {len(results) - bullish - bearish}  Bearish: {bearish}")
    print("Results written to results/coverage/")


if __name__ == "__main__":
    main()
