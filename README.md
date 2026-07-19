# ai-fund

An autonomous, continuously-running **research desk** that makes paper-trading
decisions across equities and crypto, and — the part that actually matters —
**measures whether those decisions were any good.**

This is not a "my AI made me money" project. It's a decision-making system built
to be *audited*: every allocation is logged with the data and reasoning behind
it, and performance is reported risk-adjusted and benchmark-relative, not as a
single return number that got lucky.

> ⚠️ Paper trading only. Nothing here is investment advice or a live trading
> system. Returns are simulated.

---

## Why it's built the way it is

**Numbers are computed in code; the model only reasons.** Every price, return,
and indicator comes from [`signals/indicators.py`](src/fund/signals/indicators.py).
The Phase 2 LLM decision engine receives a compact numeric *snapshot* and reasons
over it — it never calculates a figure itself. That single boundary is what stops
the system from hallucinating financial data, the #1 failure mode of LLM-in-the-loop
finance projects.

**No lookahead bias.** The [backtest engine](src/fund/backtest/engine.py) shows a
strategy only the data up to and including each decision bar, and fills its orders
at the *next* bar's open. The same decide-at-close / fill-at-next-open convention
is what the live runner will use, so backtest and live behavior match. There's a
[dedicated test](tests/test_backtest_engine.py) asserting the strategy never sees
a future bar.

**Realistic frictions.** The [paper broker](src/fund/broker/paper_broker.py) models
commission and slippage, so reported returns are net of trading costs.

**A strategy is just a function** `(_price history_) -> (_target weights_)`. The
baseline is cross-sectional momentum; the Phase 2 LLM engine implements the exact
same interface and drops into the same backtester unchanged.

---

## Results (baseline momentum strategy)

Cross-sectional momentum over a small liquid universe, net of costs. Run it
yourself with `python scripts/run_backtest.py`.

| | Equities (2019–2026) | Crypto (trailing 1y) |
|---|---|---|
| Total return | **+861%** | −33% |
| Benchmark (buy & hold) | +232% (SPY) | −45% (BTC) |
| Excess return | +630% | +12% |
| Sharpe | 1.26 | −2.17 |
| Max drawdown | −31% | −34% |
| Beta vs benchmark | 0.94 | 0.13 |

**The honest read** — and the point of building the eval layer: the equities
number looks spectacular, but a 0.94 beta says most of it is simply *being long
megacap tech during a historic bull run.* The strategy added real excess return,
but it is not market-neutral alpha, and any recruiter-facing claim should say so.
The crypto sleeve *lost money* in absolute terms while still beating a −45% BTC
benchmark. Reporting both — the win and the loss, risk-adjusted — is the entire
credibility thesis of this project.

---

## Architecture

```
src/fund/
  data/        # equities (yfinance) + crypto (CoinGecko), unified & cached
  signals/     # technical indicators — all math lives here, never the LLM
  broker/      # deterministic paper broker: cash, positions, costs
  backtest/    # lookahead-safe engine, metrics, baseline strategies
```

Roadmap:

- **Phase 1 — done.** Data, signals, paper broker, lookahead-safe backtester,
  baseline strategy, metrics, tests.
- **Phase 2 — the decision engine.** Multi-stage LLM research desk (thesis →
  steelman the bear case → risk gate → allocate), plus the eval layer:
  calibration (Brier score), attribution, immutable decision memos.
- **Phase 3 — live + dashboard.** Forward-running paper fund on a scheduler
  (free via GitHub Actions) and a hosted dashboard showing the track record.

---

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python scripts/run_backtest.py            # equities + crypto
python scripts/run_backtest.py --only equities
pytest                                    # 18 tests, no network required
```

Phase 1 needs no API keys — market data is free and keyless. Phase 2 will read
`ANTHROPIC_API_KEY` from a local `.env` (see `.env.example`).
