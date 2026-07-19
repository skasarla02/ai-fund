"""The S&P 500 constituent list, fetched from Wikipedia and cached locally.

Wikipedia's table is community-maintained and reflects index changes with a lag
of at most a few days — good enough for a research-coverage universe, not a
production index-tracking product.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import pandas as pd
import requests

from fund.config import DATA_CACHE

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
CACHE_PATH = DATA_CACHE / "sp500_constituents.csv"
_HEADERS = {"user-agent": "Mozilla/5.0 (ai-fund coverage engine)"}


@dataclass(frozen=True)
class Company:
    ticker: str
    name: str
    sector: str
    sub_industry: str


def fetch_sp500(refresh: bool = False) -> list[Company]:
    """Return the current S&P 500 constituent list, cached to disk."""
    if CACHE_PATH.exists() and not refresh:
        df = pd.read_csv(CACHE_PATH)
    else:
        resp = requests.get(WIKI_URL, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        df = pd.read_html(io.StringIO(resp.text))[0]
        df = df.rename(columns={
            "Symbol": "ticker", "Security": "name",
            "GICS Sector": "sector", "GICS Sub-Industry": "sub_industry",
        })[["ticker", "name", "sector", "sub_industry"]]
        # yfinance uses '-' where Wikipedia uses '.' for share classes (e.g. BRK.B -> BRK-B).
        df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)
        CACHE_PATH.parent.mkdir(exist_ok=True)
        df.to_csv(CACHE_PATH, index=False)

    return [Company(**row) for row in df.to_dict(orient="records")]
