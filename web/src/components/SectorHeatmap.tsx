import { motion } from "framer-motion";
import { useAllCoverage } from "../lib/api";
import type { CoverageRow } from "../lib/types";

function ratingColor(c: CoverageRow): string {
  const k = Math.max(0.15, c.conviction);
  if (c.rating === "bullish") return `rgba(127,233,192,${0.35 + k * 0.65})`;
  if (c.rating === "bearish") return `rgba(255,158,134,${0.35 + k * 0.65})`;
  return `rgba(158,157,180,${0.35 + k * 0.5})`;
}

export function SectorHeatmap({ onSelect }: { onSelect: (ticker: string) => void }) {
  const { data: rows } = useAllCoverage();

  const bySector = new Map<string, CoverageRow[]>();
  for (const row of rows ?? []) {
    const list = bySector.get(row.sector) ?? [];
    list.push(row);
    bySector.set(row.sector, list);
  }
  const sectors = [...bySector.keys()].sort();

  return (
    <section className="py-25">
      <div className="mx-auto max-w-6xl px-7.5">
        <motion.span
          className="tick"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
        >
          The market, at a glance
        </motion.span>
        <motion.h2
          className="mt-4.5 max-w-[19ch] font-head text-[clamp(28px,4vw,44px)] font-bold leading-tight tracking-tight text-balance"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
        >
          Every sector, colored by our stance.
        </motion.h2>
        <p className="mt-2.5 max-w-[56ch] text-[16px] text-muted">
          Green means bullish, coral means bearish, gray means we're not confident either way —
          intensity tracks conviction. Click any tile to look it up.
        </p>

        <motion.div
          className="glass mt-10.5 p-6.5"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
        >
          {sectors.map((sector) => {
            const items = [...bySector.get(sector)!].sort((a, b) => b.conviction - a.conviction);
            return (
              <div key={sector} className="mb-6.5 last:mb-0">
                <div className="mb-2.5 font-mono text-[11px] uppercase tracking-wide text-muted">
                  {sector} <span className="text-faint">({items.length})</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {items.map((c) => (
                    <button
                      key={c.ticker}
                      onClick={() => onSelect(c.ticker)}
                      className="w-[74px] rounded-[10px] border border-white/8 px-1.5 py-2 text-center transition-transform hover:-translate-y-0.5 hover:scale-105"
                      style={{ background: ratingColor(c) }}
                    >
                      <div className="font-display text-[12.5px] font-semibold text-[#0c1210]">
                        {c.ticker}
                      </div>
                      <div className="mt-0.5 font-mono text-[9px] text-[#0c1210cc]">
                        {c.conviction.toFixed(2)}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}
