"""The coverage engine: one rating per S&P 500 company.

For each company: pull the price signal snapshot (existing indicator engine) and
the fundamentals snapshot, hand both to Claude for a structured rating, and store
the result — one JSON file per ticker, overwritten on refresh, so the UI always
serves the latest rating and a company's history can be reconstructed from git.

Model: claude-sonnet-5, not Opus — see PRD.md §6. This is bounded, structured
reasoning over data we hand the model, not frontier-hard problem solving, and
Sonnet 5 is near-Opus quality on it at roughly half the cost. A full 500-company
refresh is ~$9 at Sonnet 5 intro pricing.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fund.config import RESULTS_DIR, TRADING_DAYS_PER_YEAR
from fund.coverage.fundamentals import get_fundamentals
from fund.coverage.schemas import CompanyRating
from fund.coverage.universe import Company, fetch_sp500
from fund.data.assets import Asset
from fund.data.market import get_bars
from fund.decision.llm import LLMClient
from fund.decision.schemas import strict_json_schema
from fund.signals.indicators import signal_snapshot

COVERAGE_DIR = RESULTS_DIR / "coverage"
COVERAGE_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """\
You are an equity research analyst. You are given one company's pre-computed
price/technical signals and fundamental data — never invent or recompute a
number; reason only over what you're given.

Produce a rating (bullish, neutral, or bearish), a conviction — an honest
probability in [0,1] that the rating direction is correct over roughly the next
quarter — a one-sentence key signal (the single most notable thing about this
company right now), a bull thesis, and a steelmanned bear case that is genuinely
the strongest argument against the thesis, not a throwaway caveat.

Be specific to this company's actual numbers. Generic reasoning that would apply
to any company in the sector is a failure — ground every claim in the given
data. Calibration matters: if you say 0.7, that direction should be right about
70% of the time across many companies.\
"""


@dataclass
class CoverageResult:
    ticker: str
    company: Company
    rating: CompanyRating
    price: float | None
    as_of: str


def build_snapshot(company: Company) -> dict | None:
    """Price signals + fundamentals for one company, or None if data is unusable."""
    asset = Asset(company.ticker, "equity")
    bars = get_bars(asset)
    if bars.empty or len(bars) < 260:  # need a full year for the 200dma etc.
        return None
    signals = _clean(signal_snapshot(bars["close"], TRADING_DAYS_PER_YEAR))
    fundamentals = _clean(get_fundamentals(company.ticker))
    return {"signals": signals, "fundamentals": fundamentals}


def rate_company(
    company: Company, client: LLMClient, snapshot: dict | None = None
) -> CoverageResult | None:
    snapshot = snapshot if snapshot is not None else build_snapshot(company)
    if snapshot is None:
        return None

    user = _build_prompt(company, snapshot)
    schema = strict_json_schema(CompanyRating)
    raw = client.decide(
        SYSTEM_PROMPT, user, schema, mock_fn=lambda: _mock_rating(snapshot)
    )
    rating = CompanyRating.model_validate(raw)

    return CoverageResult(
        ticker=company.ticker,
        company=company,
        rating=rating,
        price=snapshot["signals"].get("price"),
        as_of=datetime.now(timezone.utc).isoformat(),
    )


def write_result(result: CoverageResult, out_dir: Path = COVERAGE_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "ticker": result.ticker,
        "name": result.company.name,
        "sector": result.company.sector,
        "sub_industry": result.company.sub_industry,
        "price": result.price,
        "as_of": result.as_of,
        **result.rating.model_dump(),
    }
    (out_dir / f"{result.ticker}.json").write_text(json.dumps(payload, indent=2))


def run_coverage(
    tickers: list[str] | None = None,
    client: LLMClient | None = None,
    pace_seconds: float = 0.0,
    on_result: Callable[[CoverageResult], None] | None = None,
) -> list[CoverageResult]:
    """Rate every requested ticker (default: the full S&P 500) and persist each."""
    client = client or LLMClient(model=COVERAGE_MODEL)
    companies = fetch_sp500()
    if tickers:
        wanted = set(tickers)
        companies = [c for c in companies if c.ticker in wanted]

    results = []
    for company in companies:
        try:
            result = rate_company(company, client)
        except Exception as exc:  # pragma: no cover - network; don't let one bad ticker kill the run
            print(f"  [skip] {company.ticker}: {exc}")
            continue
        if result is None:
            continue
        write_result(result)
        results.append(result)
        if on_result:
            on_result(result)
        if pace_seconds:
            time.sleep(pace_seconds)
    return results


def _build_prompt(company: Company, snapshot: dict) -> str:
    return "\n".join([
        f"Company: {company.name} ({company.ticker})",
        f"Sector / sub-industry: {company.sector} / {company.sub_industry}",
        "",
        "Price/technical signals (JSON):",
        json.dumps(snapshot["signals"], indent=2),
        "",
        "Fundamentals (JSON, fields may be null if unavailable):",
        json.dumps(snapshot["fundamentals"], indent=2),
        "",
        "Return one CompanyRating for this company.",
    ])


def _clean(d: dict) -> dict:
    """Coerce NaN -> None so every snapshot is valid JSON."""
    return {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in d.items()}


def _mock_rating(snapshot: dict) -> dict:
    """Deterministic stand-in for Claude, using the same fundamentals-aware logic
    a real rating should apply — lets the whole coverage pipeline run for free."""
    sig, fnd = snapshot["signals"], snapshot["fundamentals"]
    mom = float(sig.get("mom_63d") or 0.0)
    above_200 = bool(sig.get("above_200dma", 0.0))
    margin = fnd.get("profitMargins")
    growth = fnd.get("revenueGrowth")
    pe = fnd.get("trailingPE")

    score = 0.5 + 0.5 * mom
    if margin is not None:
        score += 0.1 if margin > 0.15 else -0.1
    if growth is not None:
        score += 0.1 if growth > 0.1 else (-0.05 if growth < 0 else 0)
    if pe is not None and pe > 50:
        score -= 0.08
    conviction = max(0.05, min(0.95, score))

    rating = "bullish" if conviction > 0.58 and above_200 else (
        "bearish" if conviction < 0.42 else "neutral")

    return {
        "rating": rating,
        "conviction": round(conviction, 3),
        "key_signal": f"63d momentum {mom:+.1%}, margin "
                      f"{f'{margin:.1%}' if margin is not None else 'n/a'}.",
        "thesis": f"[mock] Trades {'above' if above_200 else 'below'} its 200-day "
                  f"average with {mom:+.1%} momentum; profit margin "
                  f"{f'{margin:.1%}' if margin is not None else 'unavailable'}.",
        "bear_case": f"[mock] Valuation at {f'{pe:.1f}x' if pe is not None else 'n/a'} "
                     f"trailing earnings leaves little room for a growth miss.",
    }
