"""Per-company fundamentals, fetched via yfinance and cached to disk.

This is what makes coverage memos company-specific instead of interchangeable —
a growth/valuation/quality snapshot alongside the price signals. All numbers
come straight from the provider; nothing here is computed or estimated.
"""
from __future__ import annotations

import json
import time

import yfinance as yf

from fund.config import DATA_CACHE

FUND_CACHE = DATA_CACHE / "fundamentals"

# The yfinance .info fields we pull. Any of these can be missing/None for a
# given company (e.g. non-dividend payers, unprofitable names) — callers must
# handle nulls rather than assume completeness.
FIELDS = [
    "sector", "industry", "marketCap", "beta",
    "trailingPE", "forwardPE", "priceToBook",
    "profitMargins", "grossMargins", "operatingMargins",
    "revenueGrowth", "earningsGrowth", "returnOnEquity",
    "debtToEquity", "freeCashflow", "totalRevenue",
    "dividendYield", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
    "recommendationKey",
]


def get_fundamentals(ticker: str, refresh: bool = False, max_retries: int = 4) -> dict:
    """Return a fundamentals snapshot for ``ticker``, cached to disk.

    yfinance's info endpoint throttles under rapid successive requests (a full
    S&P 500 sweep hits this reliably); retry with backoff rather than fail the
    whole run over one flaky company.
    """
    path = FUND_CACHE / f"{ticker}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text())

    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            info = yf.Ticker(ticker).info
            snap = {k: info.get(k) for k in FIELDS}
            FUND_CACHE.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(snap, indent=2, default=str))
            return snap
        except Exception as exc:  # pragma: no cover - network
            last_err = exc
            time.sleep(min(3 * (attempt + 1), 15))
    raise RuntimeError(f"Fundamentals fetch failed for {ticker}: {last_err}")
