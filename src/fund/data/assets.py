"""The Asset model: a single tradable instrument, equity or crypto."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AssetClass = Literal["equity", "crypto"]


@dataclass(frozen=True)
class Asset:
    """A tradable instrument.

    Attributes:
        symbol: Display / trading symbol, e.g. "AAPL" or "BTC".
        asset_class: "equity" or "crypto".
        data_id: Provider-specific identifier. For crypto this is the CoinGecko
            coin id (e.g. "bitcoin"); for equities it defaults to the symbol.
    """

    symbol: str
    asset_class: AssetClass
    data_id: str | None = None

    @property
    def provider_id(self) -> str:
        """The identifier the data provider expects."""
        return self.data_id or self.symbol

    def __str__(self) -> str:
        return self.symbol
