"""Equity price data via yfinance (free, keyless)."""
from __future__ import annotations

import pandas as pd
import yfinance as yf

OHLCV = ["open", "high", "low", "close", "volume"]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a provider frame to the canonical OHLCV schema.

    Returns a DataFrame indexed by a tz-aware (UTC) DatetimeIndex with columns
    exactly ``[open, high, low, close, volume]``, sorted ascending.
    """
    if df.empty:
        return pd.DataFrame(columns=OHLCV)
    df = df.rename(columns={c: c.lower() for c in df.columns})
    df = df[[c for c in OHLCV if c in df.columns]].copy()
    idx = pd.to_datetime(df.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    df.index = idx.normalize()
    df.index.name = "timestamp"
    return df.sort_index()


def fetch_equity_bars(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    period: str = "max",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch adjusted daily OHLCV bars for an equity symbol.

    Prices are split/dividend-adjusted (auto_adjust=True) so returns are
    total returns. If ``start`` is given, ``period`` is ignored.
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(
        start=start,
        end=end,
        period=None if start else period,
        interval=interval,
        auto_adjust=True,
    )
    return _normalize(df)
