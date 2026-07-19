"""The backtest engine.

Design goal: **no lookahead bias.** At each bar the strategy sees history only
up to and including that bar's close, and its decision is executed at the *next*
bar's open. Equity is marked at every bar's close. This decide-at-close /
fill-at-next-open convention is the same one the live runner will use, so a
strategy that backtests well behaves identically in forward paper trading.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from fund.broker.paper_broker import PaperBroker
from fund.config import CALENDAR_DAYS_PER_YEAR
from fund.data.assets import Asset
from fund.data.market import get_bars

Strategy = Callable[[dict[str, pd.DataFrame], dict], dict[str, float]]


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    weights: pd.DataFrame  # target weights over time (index=date, cols=symbol)
    blotter: pd.DataFrame
    close_panel: pd.DataFrame
    metrics: dict

    def summary(self) -> str:
        lines = [f"{k:>22}: {v:,.4f}" if isinstance(v, float) else f"{k:>22}: {v}"
                 for k, v in self.metrics.items()]
        return "\n".join(lines)


def run_backtest(
    assets: list[Asset],
    strategy: Strategy,
    start: str | None = None,
    end: str | None = None,
    starting_cash: float = 100_000.0,
    commission_bps: float = 1.0,
    slippage_bps: float = 5.0,
    warmup: int = 200,
    rebalance_every: int = 5,
    periods_per_year: int = CALENDAR_DAYS_PER_YEAR,
    refresh: bool = False,
) -> BacktestResult:
    """Run ``strategy`` over ``assets`` between ``start`` and ``end``.

    Args:
        warmup: Bars to skip before the first decision (lets indicators warm up).
        rebalance_every: Decide/rebalance every N bars (1 = every bar).
    """
    close_panel, open_panel, history_by_symbol = _load_panels(assets, start, end, refresh)
    if close_panel.empty:
        raise ValueError("No price data loaded for the requested assets/date range.")

    dates = close_panel.index
    broker = PaperBroker(starting_cash, commission_bps, slippage_bps)

    equity_records: dict[pd.Timestamp, float] = {}
    weight_records: dict[pd.Timestamp, dict[str, float]] = {}
    pending_weights: dict[str, float] | None = None

    for i, ts in enumerate(dates):
        # 1) Execute the previous decision at THIS bar's open (no lookahead).
        if pending_weights is not None:
            open_prices = open_panel.loc[ts].dropna().to_dict()
            broker.rebalance_to_weights(ts, pending_weights, open_prices)
            pending_weights = None

        # 2) Mark the account at this bar's close.
        close_prices = close_panel.loc[ts].dropna().to_dict()
        equity_records[ts] = broker.equity(close_prices)

        # 3) Decide for the next bar, using data only through ts.
        if i >= warmup and i % rebalance_every == 0 and i < len(dates) - 1:
            history = {
                sym: bars.loc[:ts] for sym, bars in history_by_symbol.items()
            }
            weights = strategy(history, {"timestamp": ts, "equity": equity_records[ts]})
            weights = _sanitize_weights(weights)
            if weights is not None:
                pending_weights = weights
                weight_records[ts] = weights

    equity_curve = pd.Series(equity_records, name="equity").sort_index()
    weights_df = pd.DataFrame.from_dict(weight_records, orient="index").sort_index()
    blotter_df = _blotter_frame(broker)

    from fund.backtest.metrics import compute_metrics  # local import avoids cycle

    metrics = compute_metrics(equity_curve, periods_per_year=periods_per_year)
    return BacktestResult(equity_curve, weights_df, blotter_df, close_panel, metrics)


# --- Internals ---------------------------------------------------------------
def _load_panels(assets, start, end, refresh):
    """Return (close_panel, open_panel, history_by_symbol) aligned on a union index."""
    closes, opens, history = {}, {}, {}
    for asset in assets:
        bars = get_bars(asset, start=start, end=end, refresh=refresh)
        if bars.empty:
            continue
        closes[asset.symbol] = bars["close"]
        opens[asset.symbol] = bars["open"]
        history[asset.symbol] = bars

    if not closes:
        return pd.DataFrame(), pd.DataFrame(), {}

    close_panel = pd.DataFrame(closes).sort_index()
    open_panel = pd.DataFrame(opens).sort_index().reindex(close_panel.index)
    # Forward-fill only for marking equity across non-overlapping calendars
    # (e.g. equities on weekends); tradability is governed by open prices, which
    # we leave un-filled so we never fill an order on a day an asset didn't trade.
    close_panel = close_panel.ffill()
    return close_panel, open_panel, history


def _sanitize_weights(weights: dict[str, float] | None) -> dict[str, float] | None:
    """Drop non-positive/NaN weights and scale down if they sum to > 1."""
    if not weights:
        return {} if weights == {} else None
    clean = {s: float(w) for s, w in weights.items() if w and w > 0 and pd.notna(w)}
    total = sum(clean.values())
    if total > 1.0:
        clean = {s: w / total for s, w in clean.items()}
    return clean


def _blotter_frame(broker: PaperBroker) -> pd.DataFrame:
    if not broker.blotter:
        return pd.DataFrame(columns=["timestamp", "symbol", "qty", "price", "commission"])
    return pd.DataFrame(
        [
            {
                "timestamp": f.timestamp,
                "symbol": f.symbol,
                "qty": f.qty,
                "price": f.price,
                "commission": f.commission,
            }
            for f in broker.blotter
        ]
    )
