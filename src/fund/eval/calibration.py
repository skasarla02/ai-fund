"""Calibration and attribution — did the desk's confidence mean anything?

Calibration asks: when the desk says "0.7", does it happen ~70% of the time?
We score every logged conviction against the realized forward outcome with a
Brier score and a reliability table. This is the eval that separates "it made
money" (luck-dominated over short samples) from "its stated probabilities were
actually informative" (a real, defensible claim).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from fund.decision.memo import MEMO_DIR


@dataclass
class CalibrationReport:
    brier: float
    n: int
    base_rate: float          # how often the outcome actually happened
    bins: pd.DataFrame        # predicted vs. empirical per confidence bucket

    def summary(self) -> str:
        return (f"Brier score : {self.brier:.4f}  (lower is better; "
                f"0.25 = uninformative coin flip)\n"
                f"Samples     : {self.n}\n"
                f"Base rate   : {self.base_rate:.1%} of longs beat cash over the horizon")


def load_memos(memo_dir: Path = MEMO_DIR) -> list[dict]:
    if not memo_dir.exists():
        return []
    memos = [json.loads(p.read_text()) for p in sorted(memo_dir.glob("*.json"))]
    return memos


def score_calibration(
    memos: list[dict],
    forward_return: Callable[[str, str, int], float | None],
    horizon_days: int = 21,
    n_bins: int = 5,
) -> CalibrationReport | None:
    """Score every ``long`` conviction against its realized forward outcome.

    ``forward_return(symbol, as_of, horizon_days)`` returns the asset's return
    over the horizon starting at the decision date, or None if unavailable
    (e.g. the horizon runs past the data). Outcome = 1 if that return > 0.
    """
    preds: list[float] = []
    outcomes: list[float] = []
    for memo in memos:
        for view in memo.get("assets", []):
            if view.get("stance") != "long":
                continue
            fwd = forward_return(view["symbol"], memo["as_of"], horizon_days)
            if fwd is None:
                continue
            preds.append(float(view["conviction"]))
            outcomes.append(1.0 if fwd > 0 else 0.0)

    if not preds:
        return None

    p = np.array(preds)
    o = np.array(outcomes)
    brier = float(np.mean((p - o) ** 2))

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = idx == b
        if mask.any():
            rows.append({
                "bucket": f"{edges[b]:.1f}-{edges[b + 1]:.1f}",
                "n": int(mask.sum()),
                "avg_predicted": float(p[mask].mean()),
                "empirical": float(o[mask].mean()),
            })
    return CalibrationReport(brier, len(p), float(o.mean()), pd.DataFrame(rows))


def calibration_trend(
    memos: list[dict],
    forward_return: Callable[[str, str, int], float | None],
    horizon_days: int = 21,
    freq: str = "MS",
) -> pd.DataFrame:
    """Brier score binned by calendar period (default: monthly).

    Reuses the same real predictions/outcomes as ``score_calibration``, just
    grouped by the decision's timestamp instead of pooled into one number —
    real evidence that calibration is stable (or improving) over time, not a
    single lucky snapshot. Empty periods are dropped, not interpolated.
    """
    rows = []
    for memo in memos:
        for view in memo.get("assets", []):
            if view.get("stance") != "long":
                continue
            fwd = forward_return(view["symbol"], memo["as_of"], horizon_days)
            if fwd is None:
                continue
            rows.append({
                "as_of": pd.Timestamp(memo["as_of"]),
                "pred": float(view["conviction"]),
                "outcome": 1.0 if fwd > 0 else 0.0,
            })
    if not rows:
        return pd.DataFrame(columns=["period", "brier", "n"])

    df = pd.DataFrame(rows)
    df["period"] = df["as_of"].dt.tz_localize(None).dt.to_period(freq[0]).dt.to_timestamp()
    out = (
        df.groupby("period")
        .apply(lambda g: pd.Series({
            "brier": float(((g["pred"] - g["outcome"]) ** 2).mean()),
            "n": len(g),
        }), include_groups=False)
        .reset_index()
        .sort_values("period")
    )
    return out


def make_panel_forward_return(close_panel: pd.DataFrame) -> Callable[[str, str, int], float | None]:
    """Build a ``forward_return`` from a backtest close panel (index=dates)."""
    idx = close_panel.index

    def forward_return(symbol: str, as_of: str, horizon_days: int) -> float | None:
        if symbol not in close_panel.columns:
            return None
        ts = pd.Timestamp(as_of)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        pos = idx.searchsorted(ts)
        if pos >= len(idx) or pos + horizon_days >= len(idx):
            return None
        start = close_panel[symbol].iloc[pos]
        end = close_panel[symbol].iloc[pos + horizon_days]
        if pd.isna(start) or pd.isna(end) or start <= 0:
            return None
        return float(end / start - 1.0)

    return forward_return


def attribution(weights: pd.DataFrame, close_panel: pd.DataFrame) -> pd.Series:
    """Per-asset contribution to return: sum of weight_t * next-period return.

    A quick read on which names actually drove the book's P&L.
    """
    aligned = close_panel.reindex(columns=weights.columns)
    fwd_ret = aligned.pct_change(fill_method=None).shift(-1)
    contrib = (weights * fwd_ret.reindex(weights.index)).sum().sort_values(ascending=False)
    return contrib.dropna()
