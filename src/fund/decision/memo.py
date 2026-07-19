"""Immutable decision memos — the audit trail.

Every decision writes one timestamped JSON file capturing exactly what was
decided and on what basis: the market view, each asset's thesis/bear-case/
conviction, the resulting weights, the numeric snapshot the model saw, the
model id, and a hash of the exact prompt. Memos are write-once; the eval layer
reads them back to score calibration and attribute performance.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from fund.config import RESULTS_DIR
from fund.decision.schemas import DeskDecision

MEMO_DIR = RESULTS_DIR / "memos"


def write_memo(
    decision: DeskDecision,
    weights: dict[str, float],
    snapshots: dict[str, dict],
    *,
    model: str,
    mock: bool,
    prompt: str,
    cost_usd: float,
    as_of: str | None = None,
    memo_dir: Path = MEMO_DIR,
) -> dict:
    """Persist one decision memo and return it as a dict."""
    memo_dir.mkdir(parents=True, exist_ok=True)
    stamp = as_of or datetime.now(timezone.utc).isoformat()

    memo = {
        "as_of": stamp,
        "model": model,
        "mock": mock,
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "cost_usd": round(cost_usd, 6),
        "market_view": decision.market_view,
        "assets": [v.model_dump() for v in decision.assets],
        "target_weights": weights,
        "signal_snapshot": snapshots,
    }

    fname = stamp.replace(":", "").replace("+00:00", "Z") + ".json"
    (memo_dir / fname).write_text(json.dumps(memo, indent=2, default=str))
    return memo
