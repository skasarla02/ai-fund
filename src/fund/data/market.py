"""Unified, cached access to market data across asset classes.

`get_bars` is the single entry point the rest of the system uses. It dispatches
to the right provider by asset class and caches full history to disk (pickle, to
preserve dtypes and tz) so repeated backtests don't re-hit the network.
"""
from __future__ import annotations

import pandas as pd

from fund.config import DATA_CACHE
from fund.data.assets import Asset
from fund.data.crypto import fetch_crypto_bars
from fund.data.equities import fetch_equity_bars


def _cache_path(asset: Asset):
    return DATA_CACHE / f"{asset.asset_class}_{asset.provider_id}.pkl"


def get_bars(
    asset: Asset,
    start: str | None = None,
    end: str | None = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """Return OHLCV bars for ``asset``, optionally sliced to [start, end].

    Full history is cached on first fetch; pass ``refresh=True`` to re-download.
    """
    cache = _cache_path(asset)
    if cache.exists() and not refresh:
        df = pd.read_pickle(cache)
    else:
        if asset.asset_class == "equity":
            df = fetch_equity_bars(asset.provider_id, period="max")
        elif asset.asset_class == "crypto":
            df = fetch_crypto_bars(asset.provider_id, days=365)  # free tier caps at 365
        else:  # pragma: no cover - guarded by the Asset type
            raise ValueError(f"Unknown asset class: {asset.asset_class}")
        if not df.empty:
            df.to_pickle(cache)

    if start is not None:
        df = df[df.index >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        df = df[df.index <= pd.Timestamp(end, tz="UTC")]
    return df


def get_close_panel(
    assets: list[Asset],
    start: str | None = None,
    end: str | None = None,
    field: str = "close",
    refresh: bool = False,
) -> pd.DataFrame:
    """Build a wide panel (index=dates, columns=symbols) for one OHLCV field.

    Columns are aligned on the union of all dates; gaps are left as NaN so the
    caller can decide how to handle non-overlapping calendars.
    """
    series = {}
    for asset in assets:
        bars = get_bars(asset, start=start, end=end, refresh=refresh)
        if not bars.empty:
            series[asset.symbol] = bars[field]
    if not series:
        return pd.DataFrame()
    panel = pd.DataFrame(series).sort_index()
    return panel
