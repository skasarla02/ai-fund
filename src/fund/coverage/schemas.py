"""Structured output for a single-company coverage rating.

Distinct from `fund.decision.schemas.AssetView`: that one feeds the portfolio's
21-day trading decisions. This one is a standalone equity-research rating,
graded on its own longer horizon (~1 quarter), meant to be read on its own by
someone looking up one company — not consumed by the risk gate.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Rating = Literal["bullish", "neutral", "bearish"]


class CompanyRating(BaseModel):
    rating: Rating
    conviction: float = Field(description="Probability in [0,1] that the rating "
                              "direction is correct over the next ~3 months.")
    key_signal: str = Field(description="The single most notable thing about this "
                            "company right now, in one sentence.")
    thesis: str = Field(description="The bull case, grounded in the provided "
                        "fundamentals and price signals.")
    bear_case: str = Field(description="The strongest, most specific argument "
                           "against the thesis — steelmanned, not a throwaway caveat.")
