#!/usr/bin/env python3
"""Run the coverage engine across S&P 500 + 400 + 600 (~1,500 companies).

Runs in MOCK mode automatically when ANTHROPIC_API_KEY is unset (no key, no
network calls to Claude — proves the pipeline for free). Set the key in a
local .env to run it for real on claude-sonnet-5.

Resumable by default: already-rated companies are skipped, so an interrupted
run (killed process, sleeping laptop, closed terminal) picks back up exactly
where it left off with no flags and no wasted spend re-rating what's already
done. Pass --refresh to deliberately re-rate everyone (e.g. to catch rating
drift and populate the changes feed for real).

    python scripts/run_coverage.py --limit 5              # smoke test, a few names
    python scripts/run_coverage.py --tickers NVDA KO JPM  # specific companies
    python scripts/run_coverage.py --tier "S&P 600"       # just the small-cap tier
    python scripts/run_coverage.py                        # full universe, resuming (real run: ~$27 total)
    python scripts/run_coverage.py --refresh               # re-rate everyone regardless of existing ratings
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fund.coverage.engine import COVERAGE_DIR, COVERAGE_MODEL, run_coverage  # noqa: E402
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
    parser.add_argument("--refresh", action="store_true", help="Re-rate companies that already have a stored rating (default: skip them).")
    args = parser.parse_args()

    client = LLMClient(model=COVERAGE_MODEL)
    mode = "MOCK (no API key)" if client.mock else f"LIVE ({client.model})"

    universe = fetch_universe([args.tier] if args.tier else None)
    tickers = args.tickers
    if tickers is None and args.limit:
        tickers = [c.ticker for c in universe[: args.limit]]

    scope = [c for c in universe if c.ticker in set(tickers)] if tickers else universe
    already = {p.stem for p in COVERAGE_DIR.glob("*.json")} if COVERAGE_DIR.exists() else set()
    remaining = scope if args.refresh else [c for c in scope if c.ticker not in already]
    skipped = len(scope) - len(remaining)
    n = len(remaining)

    print(f"\n{'=' * 62}\nCOVERAGE ENGINE — {mode}\n{'=' * 62}")
    print(f"Scope: {len(scope)} companies" + (f" (of {len(universe)} in universe)" if tickers else ""))
    if skipped and not args.refresh:
        print(f"Already rated: {skipped} (skipping — pass --refresh to re-rate)")
    print(f"To rate this run: {n}")
    if n == 0:
        print("Nothing to do — everything in scope is already rated. Pass --refresh to re-rate.")
        return
    if not client.mock:
        print(f"Estimated cost: ~${n * EST_COST_PER_COMPANY:.2f}")

    t0 = time.time()
    count = {"n": 0}

    def on_result(r):
        count["n"] += 1
        print(f"  [{count['n']:>3}/{n}] {r.ticker:<6} {r.rating.rating:<9} "
              f"conv={r.rating.conviction:.2f}  {r.rating.key_signal[:64]}")

    results = run_coverage(
        tickers=[c.ticker for c in remaining],
        client=client,
        pace_seconds=args.pace,
        on_result=on_result,
        skip_existing=not args.refresh,
    )

    elapsed = time.time() - t0
    print(f"\n{len(results)}/{n} companies rated in {elapsed:.1f}s.")
    if not client.mock:
        print(f"Actual LLM cost: ${client.total_cost_usd:.4f}")
    if results:
        bullish = sum(1 for r in results if r.rating.rating == "bullish")
        bearish = sum(1 for r in results if r.rating.rating == "bearish")
        print(f"Bullish: {bullish}  Neutral: {len(results) - bullish - bearish}  Bearish: {bearish}")
    total_done = len(list(COVERAGE_DIR.glob("*.json"))) if COVERAGE_DIR.exists() else 0
    print(f"Results written to results/coverage/  ({total_done}/{len(universe)} of the full universe rated so far)")


if __name__ == "__main__":
    main()
