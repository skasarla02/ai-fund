"""Coverage engine tests — pure logic, no network."""
import math

from fund.coverage.engine import _clean, _mock_rating
from fund.coverage.schemas import CompanyRating


def _snapshot(mom_63d=0.1, above_200=1.0, margin=0.2, growth=0.1, pe=20.0):
    return {
        "signals": {"mom_63d": mom_63d, "above_200dma": above_200},
        "fundamentals": {"profitMargins": margin, "revenueGrowth": growth, "trailingPE": pe},
    }


def test_clean_replaces_nan_with_none():
    out = _clean({"a": float("nan"), "b": 1.0, "c": "x"})
    assert out == {"a": None, "b": 1.0, "c": "x"}


def test_mock_rating_conforms_to_schema():
    raw = _mock_rating(_snapshot())
    rating = CompanyRating.model_validate(raw)  # raises if it doesn't conform
    assert 0.0 <= rating.conviction <= 1.0
    assert rating.rating in ("bullish", "neutral", "bearish")


def test_mock_rating_strong_fundamentals_beat_weak_ones():
    strong = _mock_rating(_snapshot(mom_63d=0.15, above_200=1.0, margin=0.4, growth=0.3, pe=15))
    weak = _mock_rating(_snapshot(mom_63d=0.15, above_200=1.0, margin=0.02, growth=-0.1, pe=80))
    assert strong["conviction"] > weak["conviction"]


def test_mock_rating_handles_missing_fundamentals():
    snap = {"signals": {"mom_63d": 0.05, "above_200dma": 1.0},
            "fundamentals": {"profitMargins": None, "revenueGrowth": None, "trailingPE": None}}
    raw = _mock_rating(snap)  # must not raise on None fields
    CompanyRating.model_validate(raw)
    assert "n/a" in raw["bear_case"] or "unavailable" in raw["thesis"]


def test_mock_rating_deterministic():
    snap = _snapshot()
    assert _mock_rating(snap) == _mock_rating(snap)
