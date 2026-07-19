"""FastAPI backend for the ai-fund dashboard.

Serves everything the frontend renders — metrics, equity curves vs benchmark,
allocations, decision memos, and calibration — as clean JSON read from the
`results/` directory the engine writes. No live API calls happen here; when the
live desk runs, it simply writes newer memos and this API serves them unchanged.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fund.config import EQUITY_UNIVERSE, RESULTS_DIR  # noqa: E402
from fund.coverage.engine import COVERAGE_DIR, COVERAGE_MODEL, load_changes  # noqa: E402
from fund.data.market import get_close_panel  # noqa: E402
from fund.eval.calibration import (  # noqa: E402
    calibration_trend, load_memos, make_panel_forward_return, score_calibration,
)

UNIVERSES = ("equities", "crypto")
BENCHMARKS = {"equities": "SPY", "crypto": "BTC"}

app = FastAPI(title="ai-fund API", version="0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev; tighten before any public deploy
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- helpers -----------------------------------------------------------------
def _read_metrics(universe: str) -> dict:
    path = RESULTS_DIR / f"{universe}_metrics.json"
    if not path.exists():
        raise HTTPException(404, f"No metrics for '{universe}'. Run scripts/run_backtest.py.")
    return json.loads(path.read_text())


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> list of dicts with NaN coerced to None (valid JSON)."""
    return json.loads(df.where(pd.notna(df), None).to_json(orient="records", date_format="iso"))


# --- endpoints ---------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/summary")
def summary() -> dict:
    """Headline metrics for every universe, plus whether the desk is live or mock."""
    memos = load_memos()
    mode = "unknown"
    if memos:
        mode = "mock" if memos[-1].get("mock") else "live"
    out = {"mode": mode, "universes": {}}
    for u in UNIVERSES:
        try:
            out["universes"][u] = {"benchmark": BENCHMARKS[u], **_read_metrics(u)}
        except HTTPException:
            continue
    return out


@app.get("/api/metrics/{universe}")
def metrics(universe: str) -> dict:
    return {"benchmark": BENCHMARKS.get(universe), **_read_metrics(universe)}


@app.get("/api/equity/{universe}")
def equity(universe: str) -> list[dict]:
    """Equity curve: [{timestamp, strategy, benchmark}, ...]."""
    path = RESULTS_DIR / f"{universe}_equity.csv"
    if not path.exists():
        raise HTTPException(404, f"No equity curve for '{universe}'.")
    df = pd.read_csv(path)
    return _records(df)


@app.get("/api/decisions")
def decisions(limit: int = 30) -> list[dict]:
    """Recent decision memos, newest first (summarized)."""
    memos = load_memos()
    memos.sort(key=lambda m: m.get("as_of", ""), reverse=True)
    return [
        {
            "as_of": m["as_of"],
            "model": m.get("model"),
            "mock": m.get("mock"),
            "market_view": m.get("market_view"),
            "n_longs": sum(1 for a in m.get("assets", []) if a.get("stance") == "long"),
            "target_weights": m.get("target_weights", {}),
        }
        for m in memos[:limit]
    ]


@app.get("/api/decisions/latest")
def latest_decision() -> dict:
    memos = load_memos()
    if not memos:
        raise HTTPException(404, "No decisions yet. Run scripts/run_decision.py.")
    memos.sort(key=lambda m: m.get("as_of", ""))
    return memos[-1]


def _load_coverage() -> list[dict]:
    if not COVERAGE_DIR.exists():
        return []
    return [json.loads(p.read_text()) for p in sorted(COVERAGE_DIR.glob("*.json"))]


@app.get("/api/coverage/stats")
def coverage_stats() -> dict:
    """Headline coverage numbers for the hero: how many companies, how it splits,
    and by tier — so the UI can show the S&P 500 vs 400/600 breakdown directly."""
    rows = _load_coverage()
    if not rows:
        return {"n": 0, "bullish": 0, "neutral": 0, "bearish": 0, "by_tier": {}, "model": COVERAGE_MODEL}
    bullish = sum(1 for r in rows if r["rating"] == "bullish")
    bearish = sum(1 for r in rows if r["rating"] == "bearish")
    by_tier: dict[str, int] = {}
    for r in rows:
        by_tier[r.get("tier", "unknown")] = by_tier.get(r.get("tier", "unknown"), 0) + 1
    return {
        "n": len(rows),
        "bullish": bullish,
        "neutral": len(rows) - bullish - bearish,
        "bearish": bearish,
        "by_tier": by_tier,
        "model": COVERAGE_MODEL,
        "last_updated": max((r["as_of"] for r in rows), default=None),
    }


@app.get("/api/coverage")
def coverage(
    q: str | None = None,
    sector: str | None = None,
    rating: str | None = None,
    tier: str | None = None,
    hidden_winners: bool = False,
    max_analysts: int | None = None,
) -> list[dict]:
    """Search/filter coverage.

    ``q`` matches ticker or company name (case-insensitive). ``hidden_winners``
    is the product's core differentiator: bullish calls on the least-covered
    names, sorted by analyst count ascending (fewest analysts first) rather
    than conviction — the point is surfacing companies Wall Street has mostly
    stopped watching, not just our highest-confidence calls.
    """
    rows = _load_coverage()
    if q:
        needle = q.lower()
        rows = [r for r in rows if needle in r["ticker"].lower() or needle in r["name"].lower()]
    if sector:
        rows = [r for r in rows if r["sector"].lower() == sector.lower()]
    if rating:
        rows = [r for r in rows if r["rating"].lower() == rating.lower()]
    if tier:
        rows = [r for r in rows if r.get("tier", "").lower() == tier.lower()]
    if max_analysts is not None:
        rows = [r for r in rows if (r.get("metrics", {}).get("analyst_coverage") or 0) <= max_analysts]

    if hidden_winners:
        rows = [r for r in rows if r["rating"] == "bullish" and r.get("metrics", {}).get("analyst_coverage") is not None]
        rows.sort(key=lambda r: (r["metrics"]["analyst_coverage"], -r["conviction"]))
    else:
        rows.sort(key=lambda r: r["conviction"], reverse=True)
    return rows


@app.get("/api/coverage/{ticker}")
def coverage_detail(ticker: str) -> dict:
    path = COVERAGE_DIR / f"{ticker.upper()}.json"
    if not path.exists():
        raise HTTPException(404, f"No coverage for '{ticker}'. Not yet rated or not in the S&P 500.")
    return json.loads(path.read_text())


@app.get("/api/coverage/changes/feed")
def coverage_changes(limit: int = 20) -> list[dict]:
    """Real upgrade/downgrade events — populated only once a company has been
    rated more than once. Empty until the coverage engine has run on a
    recurring schedule (Phase 4)."""
    return load_changes(limit=limit)


@app.get("/api/calibration/trend")
def calibration_trend_endpoint(horizon_days: int = 21, freq: str = "MS") -> list[dict]:
    """Brier score binned by calendar period — real evidence calibration holds
    up over time, computed from the same decision memos as /api/calibration."""
    memos = load_memos()
    if not memos:
        raise HTTPException(404, "No decisions to score yet.")
    panel = get_close_panel(EQUITY_UNIVERSE)
    trend = calibration_trend(memos, make_panel_forward_return(panel), horizon_days=horizon_days, freq=freq)
    return _records(trend)


@app.get("/api/calibration")
def calibration(horizon_days: int = 21) -> dict:
    """Brier score + reliability table across all logged convictions."""
    memos = load_memos()
    if not memos:
        raise HTTPException(404, "No decisions to score yet.")
    panel = get_close_panel(EQUITY_UNIVERSE)
    report = score_calibration(memos, make_panel_forward_return(panel), horizon_days=horizon_days)
    if report is None:
        raise HTTPException(404, "Not enough resolved outcomes to score calibration yet.")
    return {
        "brier": report.brier,
        "n": report.n,
        "base_rate": report.base_rate,
        "bins": _records(report.bins),
    }
