"""Central configuration: paths, constants, and the default trading universe."""
from __future__ import annotations

from pathlib import Path

from fund.data.assets import Asset

# --- Paths -------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA_CACHE = ROOT / "data_cache"
RESULTS_DIR = ROOT / "results"
DATA_CACHE.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# --- Calendar constants ------------------------------------------------------
# Equities trade ~252 sessions/year; crypto trades every calendar day.
TRADING_DAYS_PER_YEAR = 252
CALENDAR_DAYS_PER_YEAR = 365

# --- Default universe --------------------------------------------------------
# A deliberately small, liquid universe so backtests are fast and data is clean.
# `data_id` is the provider-specific identifier (CoinGecko id for crypto).
EQUITY_UNIVERSE = [
    Asset("AAPL", "equity"),
    Asset("MSFT", "equity"),
    Asset("NVDA", "equity"),
    Asset("AMZN", "equity"),
    Asset("GOOGL", "equity"),
    Asset("META", "equity"),
    Asset("JPM", "equity"),
    Asset("XOM", "equity"),
    Asset("UNH", "equity"),
    Asset("WMT", "equity"),
]

CRYPTO_UNIVERSE = [
    Asset("BTC", "crypto", data_id="bitcoin"),
    Asset("ETH", "crypto", data_id="ethereum"),
    Asset("SOL", "crypto", data_id="solana"),
    Asset("BNB", "crypto", data_id="binancecoin"),
    Asset("XRP", "crypto", data_id="ripple"),
    Asset("ADA", "crypto", data_id="cardano"),
]

# Benchmarks for relative performance.
EQUITY_BENCHMARK = Asset("SPY", "equity")
CRYPTO_BENCHMARK = Asset("BTC", "crypto", data_id="bitcoin")
