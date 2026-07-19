"""Technical indicators, computed in code.

Design rule for the whole project: **numbers are computed here, never by the
LLM.** The decision engine (Phase 2) reasons over the snapshot these functions
produce; it never calculates a price, return, or indicator itself. That single
boundary is what keeps the system from hallucinating financial data.

Every function takes a close-price Series and returns a Series aligned to it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from fund.config import CALENDAR_DAYS_PER_YEAR


def returns(close: pd.Series) -> pd.Series:
    return close.pct_change(fill_method=None)


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window).mean()


def ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()


def momentum(close: pd.Series, lookback: int) -> pd.Series:
    """Total return over ``lookback`` periods."""
    return close / close.shift(lookback) - 1.0


def volatility(
    close: pd.Series, window: int = 30, periods_per_year: int = CALENDAR_DAYS_PER_YEAR
) -> pd.Series:
    """Annualized rolling volatility of simple returns."""
    return returns(close).rolling(window).std() * np.sqrt(periods_per_year)


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (macd_line, signal_line, histogram)."""
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def bollinger(
    close: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (middle_band, upper_band, lower_band)."""
    mid = sma(close, window)
    sd = close.rolling(window).std()
    return mid, mid + num_std * sd, mid - num_std * sd


def signal_snapshot(
    close: pd.Series, periods_per_year: int = CALENDAR_DAYS_PER_YEAR
) -> dict[str, float]:
    """Compute the latest value of a standard indicator set for one asset.

    This dict is the exact payload the Phase 2 decision engine will receive per
    asset — a compact, numeric summary of current state. Values may be NaN early
    in a series before enough history exists; callers should handle that.
    """
    if close.dropna().empty:
        return {}
    macd_line, signal_line, hist = macd(close)
    last = -1
    snap = {
        "price": float(close.iloc[last]),
        "ret_1d": _last(returns(close)),
        "mom_21d": _last(momentum(close, 21)),
        "mom_63d": _last(momentum(close, 63)),
        "mom_126d": _last(momentum(close, 126)),
        "sma_50": _last(sma(close, 50)),
        "sma_200": _last(sma(close, 200)),
        "vol_30d_ann": _last(volatility(close, 30, periods_per_year)),
        "rsi_14": _last(rsi(close)),
        "macd_hist": _last(hist),
    }
    # A couple of derived, human-legible flags.
    if not np.isnan(snap["sma_50"]) and not np.isnan(snap["sma_200"]):
        snap["above_200dma"] = float(snap["price"] > snap["sma_200"])
        snap["golden_cross"] = float(snap["sma_50"] > snap["sma_200"])
    return snap


def _last(series: pd.Series) -> float:
    """Last value of a series as a float, or NaN if unavailable."""
    if series is None or len(series) == 0:
        return float("nan")
    return float(series.iloc[-1])
