"""Thin Claude client for the decision engine.

Wraps `client.messages.create` with structured outputs and adaptive thinking,
tracks token cost, and supports a **mock mode** so the entire pipeline (engine →
risk gate → memo → backtest → eval) runs end-to-end with no API key. Mock mode
activates automatically when `ANTHROPIC_API_KEY` is unset, or explicitly via
`FUND_LLM_MOCK=1`.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Callable

from dotenv import load_dotenv

load_dotenv()  # pull ANTHROPIC_API_KEY etc. from a local .env if present

DEFAULT_MODEL = os.getenv("FUND_MODEL", "claude-opus-4-8")

# Opus 4.8 list price, USD per 1M tokens (for rough cost accounting only).
_PRICE_IN_PER_M = 5.0
_PRICE_OUT_PER_M = 25.0


@dataclass
class LLMClient:
    model: str = DEFAULT_MODEL
    mock: bool | None = None
    max_tokens: int = 8000
    total_cost_usd: float = field(default=0.0, init=False)
    calls: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.mock is None:
            self.mock = os.getenv("FUND_LLM_MOCK") == "1" or not os.getenv("ANTHROPIC_API_KEY")
        self._client = None
        if not self.mock:
            from anthropic import Anthropic  # imported lazily so mock mode needs nothing

            self._client = Anthropic()

    def decide(
        self,
        system: str,
        user: str,
        schema: dict,
        mock_fn: Callable[[], dict],
    ) -> dict:
        """Return a schema-conforming dict, from Claude or from ``mock_fn``."""
        self.calls += 1
        if self.mock:
            return mock_fn()

        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        self._track_cost(response.usage)
        return json.loads(_extract_text(response))

    def _track_cost(self, usage) -> None:
        cost = (
            getattr(usage, "input_tokens", 0) / 1e6 * _PRICE_IN_PER_M
            + getattr(usage, "output_tokens", 0) / 1e6 * _PRICE_OUT_PER_M
        )
        self.total_cost_usd += cost


def _extract_text(response) -> str:
    """Concatenate text blocks, skipping thinking blocks (empty by default)."""
    parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    return "".join(parts)
