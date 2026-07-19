"""Crypto price data via the CoinGecko public API (free, keyless).

The free ``market_chart`` endpoint returns daily close prices and volumes (not
full OHLC). We therefore model each crypto bar as open==high==low==close, which
means the backtester fills crypto orders at the daily close. This is documented
and intentional for Phase 1; a paid OHLC feed can drop in later behind the same
interface.
"""
from __future__ import annotations

import time

import pandas as pd
import requests

_BASE = "https://api.coingecko.com/api/v3"
_HEADERS = {"accept": "application/json", "user-agent": "ai-fund/0.1"}
OHLCV = ["open", "high", "low", "close", "volume"]

# CoinGecko's free public tier allows only a handful of calls per minute from a
# shared IP pool. Proactively space requests so we rarely trip the limit at all;
# reactive backoff (below) handles the occasional miss. Cached after first fetch.
_MIN_INTERVAL_S = 13.0
_last_request_ts = 0.0


def _throttle() -> None:
    global _last_request_ts
    wait = _MIN_INTERVAL_S - (time.monotonic() - _last_request_ts)
    if wait > 0:
        time.sleep(wait)
    _last_request_ts = time.monotonic()


def fetch_crypto_bars(
    coin_id: str,
    days: int | str = 365,
    vs_currency: str = "usd",
    max_retries: int = 3,
) -> pd.DataFrame:
    """Fetch daily close/volume bars for a CoinGecko coin id (e.g. "bitcoin").

    Returns the canonical OHLCV schema (UTC DatetimeIndex). The free tier caps
    historical daily data at ~365 days, which is the default.
    """
    url = f"{_BASE}/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": days}  # omit interval -> daily for >90d

    last_err: Exception | None = None
    for attempt in range(max_retries):
        backoff = min(15 * (attempt + 1), 60)  # free tier resets per minute
        try:
            _throttle()
            resp = requests.get(url, params=params, headers=_HEADERS, timeout=30)
            if resp.status_code == 429:  # HTTP-level rate limit
                last_err = RuntimeError("HTTP 429 rate limit")
                time.sleep(backoff)
                continue
            resp.raise_for_status()
            payload = resp.json()
            # Free tier can return HTTP 200 with a rate-limit error in the body.
            status = payload.get("status") if isinstance(payload, dict) else None
            if status and status.get("error_code"):
                last_err = RuntimeError(status.get("error_message", "rate limited"))
                time.sleep(backoff)
                continue
            return _to_frame(payload)
        except requests.RequestException as exc:  # pragma: no cover - network
            last_err = exc
            time.sleep(backoff)
    raise RuntimeError(f"CoinGecko fetch failed for {coin_id}: {last_err}")


def _to_frame(payload: dict) -> pd.DataFrame:
    prices = payload.get("prices", [])
    volumes = {ts: v for ts, v in payload.get("total_volumes", [])}
    if not prices:
        return pd.DataFrame(columns=OHLCV)

    rows = []
    for ts_ms, price in prices:
        rows.append(
            {
                "timestamp": pd.to_datetime(ts_ms, unit="ms", utc=True).normalize(),
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volumes.get(ts_ms, float("nan")),
            }
        )
    df = pd.DataFrame(rows).set_index("timestamp")
    # market_chart can return the current partial day twice; keep last per day.
    df = df[~df.index.duplicated(keep="last")]
    return df.sort_index()
