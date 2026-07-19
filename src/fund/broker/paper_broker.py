"""A deterministic paper broker: cash, positions, fills, costs.

The broker has no concept of time — the backtest engine (or, later, the live
runner) drives it bar by bar. It models commission and slippage so reported
returns are net of realistic trading frictions rather than idealized.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Fill:
    timestamp: pd.Timestamp
    symbol: str
    qty: float  # signed: >0 buy, <0 sell
    price: float  # price actually paid/received, after slippage
    commission: float


@dataclass
class PaperBroker:
    """A cash + positions account that fills market orders at a reference price.

    Args:
        starting_cash: Opening account value.
        commission_bps: Commission per trade, in basis points of notional.
        slippage_bps: Adverse price move applied to every fill, in basis points
            (buys pay up, sells receive less).
    """

    starting_cash: float = 100_000.0
    commission_bps: float = 1.0
    slippage_bps: float = 5.0

    cash: float = field(init=False)
    positions: dict[str, float] = field(init=False, default_factory=dict)
    blotter: list[Fill] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self.cash = self.starting_cash

    # --- Order execution ----------------------------------------------------
    def market_order(
        self, timestamp: pd.Timestamp, symbol: str, qty: float, ref_price: float
    ) -> Fill | None:
        """Fill a signed market order for ``qty`` shares/units at ``ref_price``.

        Returns the resulting Fill, or None if the order was a no-op.
        """
        if qty == 0 or ref_price <= 0 or pd.isna(ref_price):
            return None
        side = 1.0 if qty > 0 else -1.0
        fill_price = ref_price * (1 + side * self.slippage_bps / 1e4)
        commission = abs(qty) * fill_price * self.commission_bps / 1e4

        # Buying spends cash (qty>0 -> cash down); selling adds cash.
        self.cash -= qty * fill_price
        self.cash -= commission
        self.positions[symbol] = self.positions.get(symbol, 0.0) + qty
        if abs(self.positions[symbol]) < 1e-9:
            self.positions.pop(symbol, None)

        fill = Fill(timestamp, symbol, qty, fill_price, commission)
        self.blotter.append(fill)
        return fill

    # --- Valuation ----------------------------------------------------------
    def equity(self, prices: dict[str, float]) -> float:
        """Total account value = cash + marked-to-market positions."""
        holdings = 0.0
        for symbol, qty in self.positions.items():
            px = prices.get(symbol)
            if px is not None and not pd.isna(px):
                holdings += qty * px
        return self.cash + holdings

    # --- Rebalancing --------------------------------------------------------
    def rebalance_to_weights(
        self,
        timestamp: pd.Timestamp,
        target_weights: dict[str, float],
        prices: dict[str, float],
    ) -> list[Fill]:
        """Trade the account to a set of target portfolio weights.

        Weights are fractions of current total equity. Symbols currently held
        but absent from ``target_weights`` are liquidated. Only symbols with a
        valid price are traded; others are left untouched this bar.
        """
        equity = self.equity(prices)
        fills: list[Fill] = []

        targets = dict(target_weights)
        for held in list(self.positions):
            targets.setdefault(held, 0.0)  # close anything not in the target set

        for symbol, weight in targets.items():
            px = prices.get(symbol)
            if px is None or pd.isna(px) or px <= 0:
                continue
            target_qty = (weight * equity) / px
            delta = target_qty - self.positions.get(symbol, 0.0)
            fill = self.market_order(timestamp, symbol, delta, px)
            if fill is not None:
                fills.append(fill)
        return fills
