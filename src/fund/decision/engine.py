"""The decision engine — the research desk.

`DecisionEngine.decide` takes a numeric signal snapshot per asset, asks Claude
for a market view plus per-asset thesis / steelmanned bear case / conviction
(structured output), then hands those convictions to the code-side risk gate to
produce weights, and logs an immutable memo. The model reasons; code does the
math and the risk control.

The same `decide(snapshots, context) -> Decision` shape is wrapped by
`fund.decision.strategy` into the backtester's strategy interface, so the LLM
desk backtests on the exact same engine as the lookahead-safe Phase 1 harness.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass

from fund.decision.llm import LLMClient
from fund.decision.memo import write_memo
from fund.decision.risk import convictions_to_weights
from fund.decision.schemas import AssetView, DeskDecision, strict_json_schema

SYSTEM_PROMPT = """\
You are the research desk of a paper-trading fund. You are given a compact,
pre-computed numeric snapshot of each candidate asset (prices, momentum,
volatility, RSI, moving-average relationships). All numbers are computed for
you — never invent or recompute a price or return; reason only over what you're
given.

For each asset, produce: a stance (long or avoid), a bull thesis grounded in the
snapshot, the strongest bear case against a long, and a conviction — an honest
probability in [0,1] that a long outperforms cash over roughly the next 21 days.
Calibration matters: 0.6 should be right ~60% of the time. Do not output
position sizes; a separate risk system handles sizing. Prefer to avoid when the
signals conflict or are weak.\
"""


@dataclass
class Decision:
    weights: dict[str, float]
    desk: DeskDecision
    memo: dict


class DecisionEngine:
    def __init__(
        self,
        client: LLMClient | None = None,
        max_weight: float = 0.34,
        target_gross: float = 1.0,
        min_conviction: float = 0.55,
    ) -> None:
        self.client = client or LLMClient()
        self.max_weight = max_weight
        self.target_gross = target_gross
        self.min_conviction = min_conviction

    def decide(self, snapshots: dict[str, dict], context: dict | None = None) -> Decision:
        context = context or {}
        snapshots = {s: _clean_snap(v) for s, v in snapshots.items()}
        user = _build_prompt(snapshots, context)
        schema = strict_json_schema(DeskDecision)

        raw = self.client.decide(
            SYSTEM_PROMPT, user, schema, mock_fn=lambda: _mock_decision(snapshots)
        )
        desk = DeskDecision.model_validate(raw)

        weights = convictions_to_weights(
            desk.assets,
            max_weight=self.max_weight,
            target_gross=self.target_gross,
            min_conviction=self.min_conviction,
        )
        memo = write_memo(
            desk, weights, snapshots,
            model=self.client.model,
            mock=bool(self.client.mock),
            prompt=SYSTEM_PROMPT + "\n" + user,
            cost_usd=self.client.total_cost_usd,
            as_of=_as_of(context),
        )
        return Decision(weights=weights, desk=desk, memo=memo)


def _build_prompt(snapshots: dict[str, dict], context: dict) -> str:
    as_of = _as_of(context) or "now"
    lines = [
        f"Decision date: {as_of}",
        f"Universe: {', '.join(snapshots)}",
        "",
        "Per-asset signal snapshot (JSON):",
        json.dumps(snapshots, indent=2, default=lambda v: round(v, 4) if isinstance(v, float) else v),
        "",
        "Return a market view and one AssetView per asset above.",
    ]
    return "\n".join(lines)


def _as_of(context: dict) -> str | None:
    ts = context.get("timestamp")
    return str(ts) if ts is not None else None


def _mock_decision(snapshots: dict[str, dict]) -> dict:
    """Deterministic stand-in for Claude: conviction from trend + momentum.

    Lets the whole pipeline run without an API key. Real runs replace this with
    the model's structured output — the schema is identical either way.
    """
    assets = []
    for symbol, snap in snapshots.items():
        mom = float(snap.get("mom_63d") or 0.0)
        above_200 = bool(snap.get("above_200dma", 0.0))
        rsi = float(snap.get("rsi_14") or 50.0)
        conviction = _clamp01(0.5 + 0.8 * mom - (0.15 if rsi > 75 else 0.0))
        long = above_200 and mom > 0
        assets.append(
            AssetView(
                symbol=symbol,
                stance="long" if long else "avoid",
                conviction=round(conviction, 3),
                thesis=f"{symbol}: 63d momentum {mom:+.1%}, "
                       f"{'above' if above_200 else 'below'} the 200d MA, RSI {rsi:.0f}.",
                bear_case=f"Momentum can reverse; RSI {rsi:.0f} "
                          f"{'is stretched' if rsi > 70 else 'is neutral'}.",
            ).model_dump()
        )
    return {"market_view": "[mock desk] trend-following read of the snapshot.",
            "assets": assets}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _clean_snap(snap: dict) -> dict:
    """Drop NaNs (unset indicators) so prompts and memos stay valid JSON."""
    return {
        k: (None if isinstance(v, float) and math.isnan(v) else v)
        for k, v in snap.items()
    }
