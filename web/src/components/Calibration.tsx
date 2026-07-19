import { motion } from "framer-motion";
import { useCalibration, useCalibrationTrend } from "../lib/api";

function TrendChart({ points }: { points: { period: string; brier: number }[] }) {
  if (points.length < 2) return null;
  const W = 1000;
  const H = 180;
  const PL = 10;
  const PR = 10;
  const PT = 16;
  const PB = 28;
  const values = points.map((p) => p.brier);
  const vmin = Math.min(...values, 0.1);
  const vmax = Math.max(...values, 0.35);
  const x = (i: number) => PL + (i / (points.length - 1)) * (W - PL - PR);
  const y = (v: number) => H - PB - ((v - vmin) / (vmax - vmin)) * (H - PT - PB);
  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(p.brier).toFixed(1)}`).join(" ");
  const coinY = y(0.25);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="block w-full">
      <line x1={PL} y1={coinY} x2={W - PR} y2={coinY} stroke="rgba(255,255,255,.16)" strokeWidth={1} strokeDasharray="3 4" />
      <text x={W - PR} y={coinY - 6} textAnchor="end" fontFamily="DM Mono, monospace" fontSize={10.5} fill="#5e5d70">
        0.25 coin flip
      </text>
      <motion.path
        d={line}
        fill="none"
        stroke="#7fe9c0"
        strokeWidth={2.4}
        strokeLinejoin="round"
        style={{ filter: "drop-shadow(0 0 6px rgba(127,233,192,.4))" }}
        initial={{ pathLength: 0 }}
        whileInView={{ pathLength: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1.6, ease: [0.3, 0.6, 0.2, 1] }}
      />
      <text x={PL} y={H - 6} fontFamily="DM Mono, monospace" fontSize={10.5} fill="#5e5d70">
        {points[0].period.slice(0, 7)}
      </text>
      <text x={W - PR} y={H - 6} textAnchor="end" fontFamily="DM Mono, monospace" fontSize={10.5} fill="#5e5d70">
        {points[points.length - 1].period.slice(0, 7)}
      </text>
    </svg>
  );
}

export function Calibration() {
  const { data: report } = useCalibration();
  const { data: trend } = useCalibrationTrend();

  return (
    <section className="py-25">
      <div className="mx-auto max-w-6xl px-7.5">
        <motion.span
          className="tick alt"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
        >
          The proof
        </motion.span>
        <motion.h2
          className="mt-4.5 max-w-[19ch] font-head text-[clamp(28px,4vw,44px)] font-bold leading-tight tracking-tight text-balance"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
        >
          Does the confidence actually mean anything?
        </motion.h2>
        <p className="mt-2.5 max-w-[56ch] text-[16px] text-muted">
          When we say 0.7, does it happen ~70% of the time? This is what separates a real edge
          from a lucky streak — and it's the one thing no AI stock-take publishes.
        </p>

        <motion.div
          className="glass mt-10.5 p-9"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
        >
          {report ? (
            <>
              <div className="grid items-center gap-11 md:grid-cols-[260px_1fr]">
                <div>
                  <div className="font-display text-[78px] font-semibold leading-none text-mint drop-shadow-[0_0_46px_rgba(127,233,192,0.35)]">
                    {report.brier.toFixed(3)}
                  </div>
                  <div className="mt-4 font-mono text-[11px] uppercase leading-relaxed tracking-wide text-muted">
                    Brier score · {report.n} graded calls
                    <br />
                    0.25 = an uninformative coin flip
                  </div>
                </div>
                <div>
                  {report.bins.map((bin, i) => (
                    <div
                      key={bin.bucket}
                      className={`grid grid-cols-[92px_1fr] items-center gap-4 py-3.5 ${i !== 0 ? "border-t border-white/11" : ""}`}
                    >
                      <div className="font-mono text-xs text-muted">{bin.bucket}</div>
                      <div className="relative h-7.5">
                        <div
                          className="absolute top-0 h-full rounded-lg bg-white/8"
                          style={{ width: `${bin.avg_predicted * 100}%` }}
                        />
                        <motion.div
                          className="absolute top-0 h-full rounded-lg bg-gradient-to-r from-iris to-mint shadow-[0_0_20px_rgba(127,233,192,0.4)]"
                          initial={{ width: 0 }}
                          whileInView={{ width: `${bin.empirical * 100}%` }}
                          viewport={{ once: true }}
                          transition={{ duration: 1, ease: [0.2, 0.7, 0.2, 1] }}
                        />
                        <span
                          className="absolute top-1.5 font-mono text-[11px] font-bold text-[#0c2a20]"
                          style={{ left: `calc(${bin.empirical * 100}% - 62px)` }}
                        >
                          {(bin.empirical * 100).toFixed(0)}% actual
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              {trend && trend.length > 1 && (
                <div className="mt-8.5 border-t border-white/11 pt-7.5">
                  <div className="mb-3.5 font-mono text-[11px] uppercase tracking-wide text-muted">
                    Calibration over time — quarterly Brier score, real backtest data
                  </div>
                  <TrendChart points={trend} />
                </div>
              )}
            </>
          ) : (
            <div className="text-center text-muted">
              Not enough resolved outcomes to score calibration yet.
            </div>
          )}
        </motion.div>
      </div>
    </section>
  );
}
