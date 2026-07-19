import pandas as pd

from fund.broker.paper_broker import PaperBroker

TS = pd.Timestamp("2024-01-01", tz="UTC")


def test_buy_no_costs_preserves_equity():
    b = PaperBroker(starting_cash=100_000, commission_bps=0, slippage_bps=0)
    b.market_order(TS, "AAPL", 100, ref_price=10.0)
    assert b.cash == 99_000
    assert b.positions["AAPL"] == 100
    assert b.equity({"AAPL": 10.0}) == 100_000


def test_slippage_costs_are_deducted():
    b = PaperBroker(starting_cash=100_000, commission_bps=0, slippage_bps=5)
    b.market_order(TS, "AAPL", 100, ref_price=10.0)
    # Buy fills 5bps above ref: 10 * 1.0005 = 10.005
    assert b.cash == 100_000 - 100 * 10.005
    # Marked at true price 10, we are down exactly the slippage paid.
    assert round(b.equity({"AAPL": 10.0}), 6) == round(100_000 - 100 * 0.005, 6)


def test_commission_is_deducted():
    b = PaperBroker(starting_cash=100_000, commission_bps=10, slippage_bps=0)
    b.market_order(TS, "AAPL", 100, ref_price=10.0)
    commission = 100 * 10.0 * 10 / 1e4  # 1.0
    assert round(b.cash, 6) == round(100_000 - 1000 - commission, 6)


def test_sell_closes_position():
    b = PaperBroker(starting_cash=100_000, commission_bps=0, slippage_bps=0)
    b.market_order(TS, "AAPL", 100, 10.0)
    b.market_order(TS, "AAPL", -100, 12.0)
    assert "AAPL" not in b.positions
    assert b.cash == 100_000 + 100 * 2  # bought at 10, sold at 12


def test_rebalance_to_weights_roundtrip():
    b = PaperBroker(starting_cash=100_000, commission_bps=0, slippage_bps=0)
    b.rebalance_to_weights(TS, {"AAPL": 0.5}, {"AAPL": 10.0})
    assert round(b.positions["AAPL"], 6) == 5000  # 50% of 100k / $10
    assert round(b.equity({"AAPL": 10.0}), 6) == 100_000
    # Rebalancing to nothing liquidates.
    b.rebalance_to_weights(TS, {}, {"AAPL": 10.0})
    assert "AAPL" not in b.positions
    assert round(b.cash, 6) == 100_000


def test_ignores_invalid_price():
    b = PaperBroker(starting_cash=100_000)
    assert b.market_order(TS, "AAPL", 100, ref_price=float("nan")) is None
    assert b.market_order(TS, "AAPL", 0, ref_price=10.0) is None
    assert b.positions == {}
