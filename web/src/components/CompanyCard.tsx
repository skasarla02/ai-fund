import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { CoverageRow } from "../lib/types";
import { pct, peMultiple, stripMockPrefix } from "../lib/format";

const RATING_PILL: Record<CoverageRow["rating"], string> = {
  bullish: "bg-gradient-to-r from-iris to-mint text-[#0c2a20] border-transparent",
  bearish: "bg-gradient-to-r from-orange-300 to-down text-[#341413] border-transparent",
  neutral: "text-muted border-white/11",
};

const BAR_COLOR: Record<CoverageRow["rating"], string> = {
  bullish: "bg-gradient-to-r from-iris to-mint",
  bearish: "bg-gradient-to-r from-orange-300 to-down",
  neutral: "bg-faint",
};

/** Diverging bar: value in [0,1], 0.5 = neutral midpoint. */
function WhyRow({ label, value }: { label: string; value: number }) {
  const dev = value - 0.5;
  const pctWidth = Math.abs(dev) * 100;
  const positive = dev >= 0;
  return (
    <div className="mt-1.5 grid grid-cols-[64px_1fr] items-center gap-2">
      <div className="font-mono text-[9px] uppercase tracking-wide text-faint">{label}</div>
      <div className="relative h-1.5 rounded-full bg-white/6">
        <div className="absolute top-[-2px] bottom-[-2px] left-1/2 w-px bg-white/18" />
        <div
          className={`absolute top-0 h-full rounded-full ${positive ? "bg-mint" : "bg-down"}`}
          style={{
            left: positive ? "50%" : `${50 - pctWidth}%`,
            width: `${pctWidth}%`,
          }}
        />
      </div>
    </div>
  );
}

function normalize(value: number | null, min: number, max: number): number {
  if (value === null) return 0.5;
  const t = (value - min) / (max - min);
  return Math.max(0.02, Math.min(1, t));
}

interface Props {
  company: CoverageRow;
  selected: boolean;
  compareDisabled: boolean;
  onToggleCompare: (ticker: string) => void;
}

export function CompanyCard({ company: c, selected, compareDisabled, onToggleCompare }: Props) {
  const [open, setOpen] = useState(false);
  const m = c.metrics;

  return (
    <motion.div
      layout
      className={`glass cursor-pointer p-[17px] transition-shadow ${
        selected ? "shadow-[0_0_0_2px_var(--color-mint)]" : ""
      }`}
      whileHover={{ y: -5 }}
      onClick={() => setOpen((o) => !o)}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-display text-[19px] font-semibold leading-tight">{c.ticker}</div>
          <div className="max-w-[14ch] truncate text-[11px] text-muted">{c.name}</div>
        </div>
        <span
          className={`whitespace-nowrap rounded-full border px-2.5 py-1 font-sans text-[9.5px] font-bold uppercase tracking-wide ${RATING_PILL[c.rating]}`}
        >
          {c.rating}
        </span>
      </div>

      <div className="mt-3">
        <div className="flex justify-between font-mono text-[10px] uppercase tracking-wide text-muted">
          <span>Conviction</span>
          <span>{c.conviction.toFixed(2)}</span>
        </div>
        <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/7">
          <div
            className={`h-full rounded-full ${BAR_COLOR[c.rating]}`}
            style={{ width: `${Math.round(c.conviction * 100)}%` }}
          />
        </div>
      </div>

      <div className="mt-2.5 text-[12px] leading-snug text-[#cfcde0]">
        <span className="text-mint font-semibold">Signal:</span> {c.key_signal}
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-2.5 text-[12px] leading-snug">
              <span className="text-mint font-semibold">Bull:</span> {stripMockPrefix(c.thesis)}
            </div>
            <div className="mt-2.5 border-t border-white/11 pt-2.5 text-[12px] leading-snug text-muted">
              <span className="text-down font-semibold">Bear:</span> {stripMockPrefix(c.bear_case)}
            </div>

            <div className="mt-3 border-t border-white/11 pt-3">
              <div className="mb-2 font-mono text-[9px] uppercase tracking-wide text-faint">
                Why this rating
              </div>
              <WhyRow label="Conviction" value={c.conviction} />
              <WhyRow label="Margin" value={normalize(m.profit_margin, -0.1, 0.5)} />
              <WhyRow label="Growth" value={normalize(m.revenue_growth, -0.2, 0.6)} />
              <WhyRow label="Momentum" value={normalize(m.momentum_63d, -0.3, 0.3)} />
              <WhyRow
                label="Value"
                value={m.trailing_pe === null ? 0.5 : 1 - Math.min(Math.max(m.trailing_pe, 0), 60) / 60}
              />
            </div>

            {m.analyst_coverage !== null && (
              <div className="mt-3 font-mono text-[10.5px] text-muted">
                <span className="text-iris font-semibold">{m.analyst_coverage}</span> analysts covering
                &middot; P/E {peMultiple(m.trailing_pe)} &middot; margin {pct(m.profit_margin)}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mt-3 flex items-center justify-between">
        <div className="font-mono text-[9px] uppercase tracking-wide text-faint">
          {open ? "− collapse" : "+ open full call"}
        </div>
        <button
          className={`rounded-lg border px-2.5 py-1.5 font-mono text-[9.5px] uppercase tracking-wide transition-colors ${
            selected
              ? "border-transparent bg-gradient-to-r from-iris to-mint font-bold text-[#141225]"
              : "border-white/11 bg-white/5 text-muted hover:text-ink hover:border-iris"
          } ${compareDisabled && !selected ? "opacity-40" : ""}`}
          disabled={compareDisabled && !selected}
          onClick={(e) => {
            e.stopPropagation();
            onToggleCompare(c.ticker);
          }}
        >
          {selected ? "✓ added" : "+ compare"}
        </button>
      </div>
    </motion.div>
  );
}
