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
from fund.data.market import get_close_panel  # noqa: E402
from fund.eval.calibration import (  # noqa: E402
    load_memos, make_panel_forward_return, score_calibration,
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
