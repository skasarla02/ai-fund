# ai-fund

**AI equity research that shows its receipts.** Every S&P 500 company gets a
bull case, a steelmanned bear case, and a confidence score — graded publicly
against what actually happened. See [PRD.md](PRD.md) for the product thesis
(the problem, who it's for, and why this beats "another AI stock opinion").

This repo is also, underneath that, an autonomous, continuously-running
**research desk** that makes paper-trading decisions across equities and
crypto, and — the part that actually matters — **measures whether those
decisions were any good.**

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
  decision/    # LLM research desk: schemas, Claude client, risk gate, memos
  eval/        # calibration (Brier) + attribution — did the confidence mean anything
  coverage/    # S&P 500 coverage engine — see PRD.md, this is the product's core
```

Roadmap:

- **Phase 1 — done.** Data, signals, paper broker, lookahead-safe backtester,
  baseline strategy, metrics, tests.
- **Phase 2 — done.** LLM research desk + eval layer (below).
- **Phase 3 — live + dashboard.** Forward-running paper fund on a scheduler
  (free via GitHub Actions) and a hosted dashboard showing the track record.

---

## The decision engine (Phase 2)

The research desk runs on `claude-opus-4-8` with adaptive thinking. For each
asset it receives the **code-computed** signal snapshot and returns structured
output — a market view plus, per asset, a bull thesis, a steelmanned bear case,
a stance, and a **conviction** in [0, 1]. The model expresses judgment; it never
sizes a position and never computes a number.

[`fund/decision/risk.py`](src/fund/decision/risk.py) — **in code, not the model**
— turns convictions into weights under hard limits (max position, max gross, a
conviction floor). Every decision writes an immutable
[memo](src/fund/decision/memo.py): market view, per-asset reasoning, weights, the
exact numeric snapshot, model id, and a prompt hash. Fully auditable and replayable.

The same `decide(...) -> weights` shape plugs into the Phase 1 backtester, so the
LLM desk runs on the identical lookahead-safe harness.

**The eval layer is the point.** [`fund/eval/calibration.py`](src/fund/eval/calibration.py)
scores every logged conviction against its realized forward outcome — a Brier
score and a reliability table (predicted vs. actual per confidence bucket). This
is what turns "it made money" into "its stated probabilities were actually
informative," and it flags overconfidence directly.

Runs in **mock mode with no API key** (deterministic stand-in for the model) so
the whole pipeline is verifiable for free; drop `ANTHROPIC_API_KEY` into a local
`.env` to run the real desk.

```bash
python scripts/run_decision.py               # one decision + memo
python scripts/run_decision.py --backtest    # backtest the desk + calibration report
```

---

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python scripts/run_backtest.py            # equities + crypto
python scripts/run_backtest.py --only equities
python scripts/run_decision.py            # one portfolio decision + memo
python scripts/run_coverage.py --limit 5  # rate a handful of S&P 500 companies
python scripts/run_coverage.py            # rate the full S&P 500 (real run: ~$9 on Sonnet 5)
python -m uvicorn api.main:app --reload   # serve everything as JSON on :8000
pytest                                    # unit tests, no network required
```

Phase 1 needs no API keys — market data is free and keyless. Phases 2–3c read
`ANTHROPIC_API_KEY` from a local `.env` (see `.env.example`); without a key,
`run_decision.py` and `run_coverage.py` both run in **mock mode** (deterministic
stand-in, no network calls to Claude) so the full pipeline is verifiable for free.
