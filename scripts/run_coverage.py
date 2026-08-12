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
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fund.coverage.engine import COVERAGE_DIR, COVERAGE_MODEL, run_coverage  # noqa: E402
from fund.coverage.universe import fetch_universe  # noqa: E402
from fund.decision.llm import LLMClient  # noqa: E402

# Rough per-company cost at Sonnet 5 intro pricing ($2/$10 per MTok):
# ~5k input (signals+fundamentals+prompt) + ~700 output tokens.
EST_COST_PER_COMPANY = 5000 / 1e6 * 2.0 + 700 / 1e6 * 10.0


def _rated_at(ticker: str, out_dir: Path = COVERAGE_DIR) -> datetime | None:
    """When the stored rating for ``ticker`` was written, or None if unreadable."""
    path = out_dir / f"{ticker}.json"
    try:
        stamp = json.loads(path.read_text()).get("as_of")
        return datetime.fromisoformat(stamp) if stamp else None
    except (OSError, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Rate only the first N companies (universe order).")
    parser.add_argument("--tickers", nargs="+", default=None, help="Rate only these specific tickers.")
    parser.add_argument("--tier", choices=["S&P 500", "S&P 400", "S&P 600"], default=None, help="Restrict to a single index tier.")
    parser.add_argument("--pace", type=float, default=0.0, help="Seconds to sleep between companies (rate-limit friendliness).")
    parser.add_argument("--refresh", action="store_true", help="Re-rate companies that already have a stored rating (default: skip them).")
    parser.add_argument("--max-new", type=int, default=None, help="Hard cap on how many companies this run may rate (cost bound for scheduled runs).")
    parser.add_argument("--stale-days", type=float, default=None, help="Also re-rate companies whose stored rating is older than this many days, oldest first.")
    parser.add_argument("--out-dir", type=Path, default=COVERAGE_DIR, help="Where to write ratings (default: results/coverage). Point elsewhere to test without touching live data.")
    args = parser.parse_args()

    client = LLMClient(model=COVERAGE_MODEL)
    mode = "MOCK (no API key)" if client.mock else f"LIVE ({client.model})"

    universe = fetch_universe([args.tier] if args.tier else None)
    tickers = args.tickers
    if tickers is None and args.limit:
        tickers = [c.ticker for c in universe[: args.limit]]

    scope = [c for c in universe if c.ticker in set(tickers)] if tickers else universe
    already = {p.stem for p in args.out_dir.glob("*.json")} if args.out_dir.exists() else set()
    remaining = scope if args.refresh else [c for c in scope if c.ticker not in already]
    skipped = len(scope) - len(remaining)

    # Scheduled runs top up a fully-rated universe by rotating through the
    # oldest ratings: unrated companies first (they're the real gaps), then
    # anything whose rating has gone stale, oldest first.
    stale = []
    if args.stale_days is not None and not args.refresh:
        unrated = {c.ticker for c in remaining}
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.stale_days)
        aged = [(t, ts) for t, ts in ((c.ticker, _rated_at(c.ticker, args.out_dir)) for c in scope)
                if t not in unrated and ts is not None and ts < cutoff]
        aged.sort(key=lambda pair: pair[1])
        by_ticker = {c.ticker: c for c in scope}
        stale = [by_ticker[t] for t, _ in aged]
        remaining = remaining + stale
        skipped -= len(stale)

    capped = 0
    if args.max_new is not None and len(remaining) > args.max_new:
        capped = len(remaining) - args.max_new
        remaining = remaining[: args.max_new]
    n = len(remaining)

    print(f"\n{'=' * 62}\nCOVERAGE ENGINE — {mode}\n{'=' * 62}")
    print(f"Scope: {len(scope)} companies" + (f" (of {len(universe)} in universe)" if tickers else ""))
    if skipped and not args.refresh:
        print(f"Already rated: {skipped} (skipping — pass --refresh to re-rate)")
    if stale:
        print(f"Stale re-rates queued: {len(stale)} (rating older than {args.stale_days:g}d, oldest first)")
    if capped:
        print(f"Capped by --max-new {args.max_new}: {capped} deferred to a later run")
    print(f"To rate this run: {n}")
    if n == 0:
        print("Nothing to do — everything in scope is already rated and current.")
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
        # ``remaining`` is already exactly what should be rated — the skip and
        # staleness filtering happened above. Letting the engine skip again
        # would drop the stale re-rates, which have files by definition.
        skip_existing=False,
        out_dir=args.out_dir,
    )

    elapsed = time.time() - t0
    print(f"\n{len(results)}/{n} companies rated in {elapsed:.1f}s.")
    if not client.mock:
        print(f"Actual LLM cost: ${client.total_cost_usd:.4f}")
    if results:
        bullish = sum(1 for r in results if r.rating.rating == "bullish")
        bearish = sum(1 for r in results if r.rating.rating == "bearish")
        print(f"Bullish: {bullish}  Neutral: {len(results) - bullish - bearish}  Bearish: {bearish}")
    total_done = len(list(args.out_dir.glob("*.json"))) if args.out_dir.exists() else 0
    print(f"Results written to {args.out_dir}/  ({total_done}/{len(universe)} of the full universe rated so far)")

    # Rating nothing at all when work was queued means the run failed — no data
    # reached the engine. Exit non-zero so a scheduled run reports red instead
    # of quietly succeeding at doing nothing, night after night.
    if not results:
        print(f"\nFAILED: 0 of {n} companies rated. No usable market data was fetched.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
