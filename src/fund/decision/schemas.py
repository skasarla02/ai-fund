"""Structured-output schemas for the LLM decision engine.

The model returns a `DeskDecision` — a market view plus, per candidate asset, a
bull thesis, a steelmanned bear case, a stance, and a **conviction** in [0, 1].
Conviction is the number the eval layer later scores for calibration (Brier),
so it must be an honest probability, not a vibe.

Crucially, the model does NOT choose position sizes. It expresses conviction;
`fund.decision.risk` turns convictions into weights under hard limits. Judgment
from the model, math and risk control from code.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AssetView(BaseModel):
    symbol: str
    stance: Literal["long", "avoid"]
    conviction: float = Field(description="Probability in [0,1] that a long "
                              "outperforms cash over the ~21-day horizon.")
    thesis: str = Field(description="The bull case, grounded in the provided signals.")
    bear_case: str = Field(description="The strongest argument against the long.")


class DeskDecision(BaseModel):
    market_view: str = Field(description="One-paragraph read of the current regime.")
    assets: list[AssetView]


def strict_json_schema(model: type[BaseModel]) -> dict:
    """Return a JSON schema for ``model`` that satisfies structured-output rules.

    Structured outputs require every object to set ``additionalProperties: false``
    and list all properties as ``required``. Pydantic doesn't emit those, so we
    add them recursively (including nested ``$defs``).
    """
    schema = model.model_json_schema()
    _strictify(schema)
    for definition in schema.get("$defs", {}).values():
        _strictify(definition)
    return schema


def _strictify(node: object) -> None:
    if not isinstance(node, dict):
        return
    if node.get("type") == "object" and "properties" in node:
        node["additionalProperties"] = False
        node["required"] = list(node["properties"].keys())
        for value in node["properties"].values():
            _strictify(value)
    if "items" in node:
        _strictify(node["items"])
    for combinator in ("anyOf", "allOf", "oneOf"):
        for sub in node.get(combinator, []):
            _strictify(sub)
