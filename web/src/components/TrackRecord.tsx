import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useEquityCurve, useMetrics } from "../lib/api";
import { pct } from "../lib/format";

type Universe = "equities" | "crypto";

function EquityChart({ universe }: { universe: Universe }) {
  const { data: points } = useEquityCurve(universe);
  const [cross, setCross] = useState<{ x: number; strat: number; bench: number } | null>(null);

  const geometry = useMemo(() => {
    if (!points || points.length < 2) return null;
    const W = 1000;
    const H = 340;
    const PL = 8;
    const PR = 8;
    const PB = 26;
    const PT = 14;
    const base = points[0].strategy;
    const strat = points.map((p) => (p.strategy / base) * 100);
    const bench = points.map((p) => (p.benchmark / base) * 100);
    const vmax = Math.max(...strat, ...bench) * 1.03;
    const vmin = Math.min(...strat, ...bench, 100) * 0.97;
    const n = points.length;
    const x = (i: number) => PL + (i / (n - 1)) * (W - PL - PR);
    const y = (v: number) => H - PB - ((v - vmin) / (vmax - vmin)) * (H - PB - PT);
    const line = (arr: number[]) => arr.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
    const area = `${line(strat)} L ${x(n - 1).toFixed(1)} ${H - PB} L ${x(0).toFixed(1)} ${H - PB} Z`;
    return { W, H, x, y, strat, bench, line, area, n };
  }, [points]);

  if (!geometry) return <div className="p-9 text-center text-muted">No data yet.</div>;
  const { W, H, x, area, strat, bench, line, n } = geometry;

  return (
    <div
      className="relative cursor-crosshair"
      onPointerMove={(e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const fx = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const i = Math.round(fx * (n - 1));
        setCross({ x: (x(i) / W) * 100, strat: strat[i] / 100 - 1, bench: bench[i] / 100 - 1 });
      }}
      onPointerLeave={() => setCross(null)}
    >
      <svg viewBox={`0 0 ${W} ${H}`} className="block w-full overflow-visible">
        <defs>
          <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#7fe9c0" stopOpacity=".28" />
            <stop offset="1" stopColor="#7fe9c0" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="ln" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#a99cff" />
            <stop offset="1" stopColor="#7fe9c0" />
          </linearGradient>
        </defs>
        <path d={area} fill="url(#fill)" />
        <path d={line(bench)} fill="none" stroke="#5e5d70" strokeWidth={1.6} strokeDasharray="3 4" />
        <motion.path
          d={line(strat)}
          fill="none"
          stroke="url(#ln)"
          strokeWidth={3}
          strokeLinejoin="round"
          style={{ filter: "drop-shadow(0 0 7px rgba(127,233,192,.5))" }}
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.8, ease: [0.3, 0.6, 0.2, 1] }}
        />
      </svg>
      {cross && (
        <>
          <div className="absolute top-0 bottom-6.5 w-px bg-mint/60" style={{ left: `${cross.x}%` }} />
          <div
            className="absolute -translate-x-1/2 -translate-y-[145%] whitespace-nowrap rounded-xl border border-white/11 bg-[#1c1a28f5] px-2.75 py-1.75 font-mono text-[11.5px]"
            style={{ left: `${cross.x}%`, top: 0 }}
          >
            <b className="text-mint">{pct(cross.strat)}</b> &middot; benchmark {pct(cross.bench)}
          </div>
        </>
      )}
    </div>
  );
}

export function TrackRecord() {
  const [universe, setUniverse] = useState<Universe>("equities");
  const { data: metrics } = useMetrics(universe);

  return (
    <section className="py-25">
      <div className="mx-auto max-w-6xl px-7.5">
        <motion.span
          className="tick alt"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
        >
          The evidence
        </motion.span>
        <motion.h2
          className="mt-4.5 max-w-[19ch] font-head text-[clamp(28px,4vw,44px)] font-bold leading-tight tracking-tight text-balance"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
        >
          And we put paper money behind our own calls.
        </motion.h2>
        <p className="mt-2.5 max-w-[56ch] text-[16px] text-muted">
          The highest-conviction names become a simulated portfolio, marked daily against a
          benchmark. Not the pitch — just more proof the ratings aren't only words.
        </p>

        <motion.div
          className="mt-10.5 grid gap-5 lg:grid-cols-[300px_1fr]"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
        >
          <div className="glass p-6">
            <div className="mb-5.5 inline-flex gap-1 rounded-2xl border border-white/11 bg-white/5 p-1.5">
              {(["equities", "crypto"] as Universe[]).map((u) => (
                <button
                  key={u}
                  onClick={() => setUniverse(u)}
                  className={`rounded-xl px-5 py-2.25 font-sans text-xs font-bold capitalize transition-all ${
                    universe === u
                      ? "bg-gradient-to-r from-mint to-[#9fe9d0] text-[#123] shadow-[0_0_24px_rgba(127,233,192,0.35)]"
                      : "text-muted"
                  }`}
                >
                  {u}
                </button>
              ))}
            </div>
            <div className="font-mono text-[10.5px] uppercase tracking-wide text-muted">
              Simulated total return
            </div>
            <div
              className={`mt-1.5 font-display text-[44px] font-semibold ${
                (metrics?.total_return ?? 0) >= 0 ? "text-up" : "text-down"
              }`}
            >
              {metrics ? pct(metrics.total_return) : "—"}
            </div>
            <div className="mt-5 grid grid-cols-2 gap-px overflow-hidden rounded-2xl bg-white/11">
              {[
                ["Sharpe", metrics?.sharpe?.toFixed(2) ?? "—"],
                ["CAGR", metrics ? pct(metrics.cagr) : "—"],
                ["Max drawdown", metrics ? pct(metrics.max_drawdown) : "—"],
                ["vs benchmark", metrics?.excess_return !== undefined ? pct(metrics.excess_return, 0) : "—"],
              ].map(([label, value]) => (
                <div key={label} className="bg-[#18162296] p-3.5">
                  <div className="font-mono text-[9.5px] uppercase tracking-wide text-muted">{label}</div>
                  <div className="mt-2 font-display text-[19px] font-semibold">{value}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass p-5.5 pb-3">
            <div className="mb-2 flex gap-5 font-mono text-[11.5px] text-muted">
              <span>
                <i className="mr-1.75 inline-block h-0.75 w-3.5 rounded bg-mint align-middle" />
                AI Fund
              </span>
              <span>
                <i className="mr-1.75 inline-block h-0.75 w-3.5 rounded bg-faint align-middle" />
                {metrics?.benchmark ?? "Benchmark"}
              </span>
            </div>
            <EquityChart universe={universe} />
          </div>
        </motion.div>

        <p className="mt-4.5 font-mono text-[11.5px] text-faint">
          Paper trading only. Not investment advice. Equities beat SPY mostly by being long
          megacap tech in a bull market (beta 0.94) — the calibration score above is the honest
          measure, not this number.
        </p>
      </div>
    </section>
  );
}
