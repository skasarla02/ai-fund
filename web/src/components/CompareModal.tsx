import { AnimatePresence, motion } from "framer-motion";
import type { CoverageRow } from "../lib/types";
import { pct, peMultiple, num, stripMockPrefix } from "../lib/format";
import { RadarChart, CMP_COLORS } from "./RadarChart";

interface Props {
  companies: CoverageRow[] | null;
  onClose: () => void;
}

export function CompareModal({ companies, onClose }: Props) {
  return (
    <AnimatePresence>
      {companies && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[90] bg-[#0a090f]/72 backdrop-blur-md"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            className="fixed inset-0 z-[91] flex items-center justify-center p-7"
          >
            <div className="glass max-h-[86vh] w-full max-w-3xl overflow-y-auto p-8">
              <div className="mb-2 flex items-start justify-between">
                <div>
                  <div className="mb-2 font-mono text-[11.5px] uppercase tracking-[0.2em] text-iris">
                    Side by side
                  </div>
                  <div className="font-head text-2xl font-bold">
                    Comparing {companies.map((c) => c.ticker).join(" vs ")}
                  </div>
                </div>
                <button
                  className="flex h-8.5 w-8.5 flex-none items-center justify-center rounded-full border border-white/11 bg-white/6 text-base"
                  onClick={onClose}
                >
                  ✕
                </button>
              </div>

              <div className="my-6">
                <RadarChart companies={companies} />
                <div className="mt-1.5 flex flex-wrap justify-center gap-5 font-mono text-xs text-muted">
                  {companies.map((c, i) => (
                    <span key={c.ticker} className="flex items-center gap-1.5">
                      <i
                        className="inline-block h-3 w-3 rounded"
                        style={{ background: CMP_COLORS[i % CMP_COLORS.length] }}
                      />
                      {c.ticker}
                    </span>
                  ))}
                </div>
              </div>

              <div className="overflow-hidden rounded-2xl border border-white/11">
                <table className="w-full border-collapse text-[13px]">
                  <thead>
                    <tr className="font-display font-semibold">
                      <th className="p-3 text-left" />
                      {companies.map((c) => (
                        <th key={c.ticker} className="p-3 text-left">
                          {c.ticker}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="font-mono">
                    {(
                      [
                        ["Rating", (c: CoverageRow) => c.rating],
                        ["Conviction", (c: CoverageRow) => c.conviction.toFixed(2)],
                        ["Analysts covering", (c: CoverageRow) => c.metrics.analyst_coverage ?? "—"],
                        ["Momentum (63d)", (c: CoverageRow) => pct(c.metrics.momentum_63d)],
                        ["Profit margin", (c: CoverageRow) => pct(c.metrics.profit_margin)],
                        ["Revenue growth", (c: CoverageRow) => pct(c.metrics.revenue_growth)],
                        ["Trailing P/E", (c: CoverageRow) => peMultiple(c.metrics.trailing_pe)],
                        ["Beta", (c: CoverageRow) => num(c.metrics.beta)],
                      ] as [string, (c: CoverageRow) => string | number][]
                    ).map(([label, fn]) => (
                      <tr key={label} className="border-t border-white/11 odd:bg-white/2">
                        <td className="p-3 font-mono text-[10px] uppercase tracking-wide text-faint">
                          {label}
                        </td>
                        {companies.map((c) => (
                          <td key={c.ticker} className="p-3">
                            {fn(c)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-5 grid gap-3.5">
                {companies.map((c, i) => (
                  <div
                    key={c.ticker}
                    className="glass p-4"
                    style={{ borderColor: `${CMP_COLORS[i % CMP_COLORS.length]}44` }}
                  >
                    <div
                      className="mb-2 font-display text-[15px] font-semibold"
                      style={{ color: CMP_COLORS[i % CMP_COLORS.length] }}
                    >
                      {c.ticker} — {c.name}
                    </div>
                    <p className="text-[12.5px] leading-relaxed text-[#cfcde0]">
                      <span className="text-mint font-semibold">Bull:</span> {stripMockPrefix(c.thesis)}
                    </p>
                    <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted">
                      <span className="text-down font-semibold">Bear:</span> {stripMockPrefix(c.bear_case)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
