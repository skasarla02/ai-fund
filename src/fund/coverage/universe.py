"""The coverage universe: S&P 500 + 400 + 600, fetched from Wikipedia and cached.

All three are S&P Dow Jones indices with a real quality bar (profitability,
liquidity, minimum float) — unlike Russell 2000, which has no earnings
requirement and includes a long tail of unprofitable, thinly-traded names.
That quality floor is what keeps ratings on the smaller tiers specific instead
of generic ("loses money, avoid" x200).

The tiers double as the product's core differentiator: S&P 500 is the most
analyst-covered stretch of the market in the world; S&P 600 (small-cap) names
routinely have single-digit analyst counts. Same rigorous selection
methodology, descending by size — a defensible ladder from "most covered" to
"least covered," not an arbitrary universe swap.

Wikipedia's tables are community-maintained and reflect index changes with a
lag of at most a few days — good enough for a research-coverage universe, not
a production index-tracking product.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd
import requests

from fund.config import DATA_CACHE

Tier = Literal["S&P 500", "S&P 400", "S&P 600"]

_SOURCES: dict[Tier, str] = {
    "S&P 500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "S&P 400": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
    "S&P 600": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
}
_HEADERS = {"user-agent": "Mozilla/5.0 (ai-fund coverage engine)"}


@dataclass(frozen=True)
class Company:
    ticker: str
    name: str
    sector: str
    sub_industry: str
    tier: Tier


def _cache_path(tier: Tier) -> Path:
    slug = tier.lower().replace(" ", "").replace("&", "")
    return DATA_CACHE / f"{slug}_constituents.csv"


def _fetch_tier(tier: Tier, refresh: bool) -> list[Company]:
    path = _cache_path(tier)
    if path.exists() and not refresh:
        df = pd.read_csv(path)
    else:
        resp = requests.get(_SOURCES[tier], headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        df = pd.read_html(io.StringIO(resp.text))[0]
        df = df.rename(columns={
            "Symbol": "ticker", "Security": "name",
            "GICS Sector": "sector", "GICS Sub-Industry": "sub_industry",
        })[["ticker", "name", "sector", "sub_industry"]]
        # yfinance uses '-' where Wikipedia uses '.' for share classes (e.g. BRK.B -> BRK-B).
        df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)
        path.parent.mkdir(exist_ok=True)
        df.to_csv(path, index=False)

    return [Company(**row, tier=tier) for row in df.to_dict(orient="records")]


def fetch_sp500(refresh: bool = False) -> list[Company]:
    """S&P 500 only — kept as its own entry point for the existing decision
    engine / backtest strategies, which trade the large-cap universe."""
    return _fetch_tier("S&P 500", refresh)


def fetch_universe(tiers: list[Tier] | None = None, refresh: bool = False) -> list[Company]:
    """The full coverage universe across the requested tiers (default: all three).

    De-duplicates by ticker, preferring the larger-cap tier if a company
    somehow appears in more than one list (index reconstitutions can overlap
    briefly).
    """
    tiers = tiers or ["S&P 500", "S&P 400", "S&P 600"]
    seen: dict[str, Company] = {}
    for tier in tiers:  # iterate largest-cap first so it wins de-dup
        for company in _fetch_tier(tier, refresh):
            seen.setdefault(company.ticker, company)
    return list(seen.values())
