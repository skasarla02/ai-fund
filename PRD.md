# AI Fund — Product Requirements Document

**Status:** Living document. Updated every time scope, priorities, or the narrative change.
**Last updated:** 2026-07-19 (S&P 500 coverage pivot)

---

## 1. The problem

A serious DIY investor today isn't short on opinions about a stock. They're drowning in
them — Reddit, YouTube, Twitter, their own AI chatbot — an infinite stream of confident
takes. What they don't have is any way to tell **which opinions to trust**.

Every source has the same three failures:
- **No accountability.** Nobody tracks whether their calls were right. A prediction with
  no scorecard is just content.
- **One-sided by default.** Bull cases are easy to find. Bear cases require actively
  seeking out someone arguing against the thing they already want to believe.
- **Incomplete coverage.** Retail attention follows whatever's trending. The 400 solid,
  unglamorous companies nobody's tweeting about get zero coverage.

LLMs just made it cheap to generate a plausible-sounding take on any company. That
made the problem *worse*, not better — it's now trivially easy to produce infinite
confident, unaccountable opinions. Nobody is using the same technology to fix the
actual gap: **accountability**.

## 2. Who this is for

The **serious DIY investor** — manages their own portfolio, takes it seriously, reads
beyond headlines, but isn't a professional analyst and can't personally cover 500
companies or read 500 10-Ks.

Not the target: complete beginners needing investing 101, or professional quants who
want raw signal exports. Different products.

## 3. The value proposition

> **AI equity research that shows its receipts.**
> The analyst that keeps score.

Not "AI gives you a stock opinion" — that's a commodity, already everywhere. The wedge
is doing the three things nobody else does, together:

| Pillar | What it means | Why it's the differentiator |
|---|---|---|
| **Keeps score** | Every conviction is logged, timestamped, and graded against what actually happened. Public Brier/calibration score. | Turns "trust me" into "check me." No other retail-facing AI research product publishes its own accuracy. |
| **Always argues both sides** | Every call ships with a bull thesis *and* a steelmanned bear case — structurally, not optionally. | Directly counters confirmation bias, the thing that actually loses people money. |
| **Covers everything** | All S&P 500 names rated, not just whatever's trending. | You can look up the boring company nobody's talking about, not just NVDA for the 400th time. |

## 4. Why now

Two things became true at the same moment: LLMs made per-company qualitative
reasoning at scale cheap for the first time, *and* that same capability flooded the
world with unaccountable AI-generated takes. Accountability became newly valuable
exactly when it became newly buildable.

## 5. Non-goals / constraints

- **Not investment advice.** Paper trading only. Every surface says so.
- **Not going to beat Bloomberg/FactSet on data completeness.** Not the game — the
  game is accountability and two-sidedness, not data breadth.
- **Not a beginner-education product.** Assumes the reader already knows what a P/E
  ratio is.
- **Not real-money execution**, now or in v1. If that ever changes it's a deliberate,
  separately-scoped decision — not a default.

## 6. Scope — v1.1 (Hidden Winners expansion)

- **Universe:** S&P 500 + 400 (mid-cap) + 600 (small-cap) — ~1,500 companies.
  **Why S&P, not Russell 2000 or "all US stocks":** S&P indices require positive
  earnings (most recent quarter + trailing four quarters) plus minimum market
  cap, liquidity, and float. Russell 2000 has no such bar — it's just "rank by
  market cap, take the next 2,000" — and is full of unprofitable, thinly-traded
  names that would degrade ratings into generic "loses money, avoid" noise
  across hundreds of companies, the exact specificity failure flagged in §9.
  S&P 500/400/600 share one rigorous methodology at three sizes, giving a
  defensible "most-covered → least-covered" ladder instead of an arbitrary
  universe swap, while keeping recognizable names (S&P 500) as the searchable
  hook that makes the product instantly testable by a stranger.
- **Why this expansion matters:** rating the S&P 500 alone was a weak claim —
  it's the *most* analyst-covered stretch of the market in the world. The
  actual differentiator is **analyst coverage gap**, made literal via
  yfinance's `numberOfAnalystOpinions` field: NVDA has 58 analysts covering
  it; small-cap names in S&P 600 routinely have single digits (Artisan
  Partners: 4). That number is now a first-class stat on every card, and
  a dedicated **Hidden Winners** view (`/api/coverage?hidden_winners=true`)
  surfaces bullish calls sorted by *fewest analysts first* — not highest
  conviction — because the point is surfacing what Wall Street stopped
  watching, not just our best guesses.
- **Reasoning inputs:** price/technical signals (existing signal engine) **+
  fundamentals** (margins, growth, valuation, debt, profitability — via
  yfinance) **+ analyst coverage count**, now passed to the model as explicit
  context ("13 analysts cover this stock") since thin coverage is itself
  decision-relevant information — a mispricing in a 4-analyst stock persists
  longer than one in a 58-analyst stock.
- **Model:** `claude-sonnet-5`, not Opus — unchanged reasoning from v1. Full
  ~1,500-company refresh ≈ $27 at Sonnet 5 intro pricing (up from ~$9 at
  500-only scope, still trivial). Opus stays a future option for a premium
  deep-dive tier on a small top-conviction subset, not the default.
- **Paper portfolio:** unchanged from the existing engine — the fund puts real paper
  capital behind its highest-conviction names, and that track record is the *proof*
  layer, not the pitch.

## 7. Hero narrative — UI messaging spec

This is the exact story the front page must tell, in order, before any chart or
number. It must be legible to a stranger in under 10 seconds. This is spec, not a
suggestion — the UI rebuild follows this structure exactly.

1. **The problem, stated in one line.** Something in the register of: *"Everyone
   has an opinion on your stocks. Almost none of them keep score."*
2. **The wedge, immediately after.** *"We rated all 500 S&P companies — bull case,
   bear case, and a confidence we're graded on."* This is the hero headline, not
   the equity curve.
3. **Make it tangible instantly.** A live search box in the hero: type any S&P 500
   ticker/name, get its rating right there. This is the single highest-leverage UI
   element in the whole product — it's the "oh, it actually does that" moment.
4. **Then, and only then, the proof layer.** Calibration score front and center
   ("when we say 70%, it happens ~70% of the time — here's 491 graded calls"),
   *then* the paper portfolio track record as evidence the ratings aren't just
   words.

Old hero (the +861.6% number as the headline) is retired. That number becomes a
supporting proof point deep in the page, always paired with its calibration context
so it can't be read as "AI made me rich."

## 8. Success metrics (for this as a portfolio artifact)

Not a real business, so "success" means: a stranger who lands on the page can, in
under 30 seconds, (a) state the problem in their own words, (b) look up a real
company and get a specific — not generic — take, and (c) find the calibration proof
without hunting for it. If a first-time viewer can't do all three, the build isn't
done, regardless of visual polish.

## 9. Biggest open risk

**Reasoning quality/specificity at scale.** If three random company memos read as
interchangeable, the whole accountability pitch collapses into "another wrapper."
Fundamentals-in-the-prompt is the mitigation; needs to be spot-checked against real
output once the coverage engine runs, not just assumed to work.

## 10. Architecture

Unchanged — see [README.md](README.md) for the full technical writeup
(data/signals/broker/backtest/decision/eval). This PRD governs *what we're building
and for whom*; the README governs *how*.

## 11. Roadmap / status

- **Phase 1 — done.** Data layer, signals, paper broker, lookahead-safe backtest engine.
- **Phase 2 — done.** LLM decision engine (per-asset thesis/bear-case/conviction),
  code-side risk gate, immutable memos, calibration eval layer.
- **Phase 3a — done.** FastAPI backend serving results as JSON.
- **Phase 3b — done.** HTML/JS prototype validating the hero narrative, search,
  comparison (radar chart), sector heatmap, upgrades/downgrades feed, calibration
  trend — all working, all on real (mock-mode) data. Branded "The Spread Model."
- **Phase 3c — done.** Coverage engine expanded to S&P 500+400+600 (~1,500
  companies), analyst-coverage-count wired through as a first-class stat and
  model input, Hidden Winners API filter shipped. See §6.
- **Phase 3d — next.** The real production frontend: Vite + React, wired live
  to the FastAPI backend (no more embedded mock JSON in a static HTML file).
  Carries forward the visual language validated in the 3b prototype.
- **Phase 3e — after that.** Full live coverage run once Anthropic billing
  clears (real Claude ratings, not mock) across the full ~1,500-company
  universe (~$27).
- **Phase 4 — later.** Real scheduled autonomous runs (GitHub Actions cron) so
  the desk actually re-rates on a cadence and the change feed / calibration
  trend become fully organic, not seeded. Portfolio-site integration timing:
  TBD, user will confirm when ready.

## 12. Changelog

- **2026-07-19** — Pivoted from "track record as the pitch" to "coverage +
  accountability as the pitch, track record as proof." Added S&P 500 coverage
  engine to scope. Locked model choice at Sonnet 5 for coverage generation.
- **2026-07-19** — Coverage engine built (Phase 3c): `fund/coverage/` (universe,
  fundamentals, schemas, engine) + `/api/coverage` search/filter/detail
  endpoints. Smoke-tested on 31 real, diverse S&P 500 companies in mock mode
  (still waiting on Anthropic billing for live Sonnet 5 runs) — fundamentals
  visibly differentiate output across companies, the PRD §9 risk did not
  materialize. Next: rebuild the UI hero to §7's spec, backed by this real
  coverage data instead of mocked cards.
- **2026-07-19** — UI prototype built and fixed (Phase 3b): hero card with
  inline live search (no scroll to see results), sector heatmap, comparison
  feature with radar chart, upgrades/downgrades feed, calibration trend chart.
  Caught and fixed a real JS bug (temporal-dead-zone crash silently killing
  the entire script on load) and a CSS anomaly (`max-height` transitions not
  applying in the test environment — switched to JS-measured explicit height,
  the more robust classic technique). Branded "The Spread Model."
- **2026-07-19** — User pushback, and it was right: "what do people need info
  on S&P 500 for? It's an index fund for a reason." Rating the most
  analyst-covered stretch of the market wasn't actually filling a coverage
  gap. Expanded universe to S&P 500+400+600 (~1,500 companies), added
  `numberOfAnalystOpinions` as a first-class stat and model input, shipped a
  Hidden Winners filter (bullish calls sorted by fewest analysts, not highest
  conviction). Verified real analyst-count spread end-to-end: NVDA 58 vs.
  Artisan Partners (S&P 600) 4. Considered and rejected Russell 2000 as the
  broader-universe alternative — no profitability requirement, would degrade
  output specificity on the long unprofitable tail. See §6 for full reasoning.
  Next: real Vite+React frontend wired to the live FastAPI backend (Phase 3d),
  replacing the standalone HTML prototype.
