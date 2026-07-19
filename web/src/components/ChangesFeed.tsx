import { motion } from "framer-motion";
import { useChangesFeed } from "../lib/api";

const PILL: Record<string, string> = {
  bullish: "bg-gradient-to-r from-iris to-mint text-[#0c2a20]",
  bearish: "bg-gradient-to-r from-orange-300 to-down text-[#341413]",
  neutral: "border border-white/11 text-muted",
};

export function ChangesFeed() {
  const { data: changes } = useChangesFeed(20);

  return (
    <section className="py-25">
      <div className="mx-auto max-w-6xl px-7.5">
        <motion.span
          className="tick alt"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
        >
          The desk changes its mind
        </motion.span>
        <motion.h2
          className="mt-4.5 max-w-[19ch] font-head text-[clamp(28px,4vw,44px)] font-bold leading-tight tracking-tight text-balance"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
        >
          Upgrades and downgrades, logged as they happen.
        </motion.h2>
        <p className="mt-2.5 max-w-[56ch] text-[16px] text-muted">
          Every rating change is a real diff against the previous run — not a narrative we wrote
          after the fact.
        </p>

        <motion.div
          className="glass mt-10.5"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
        >
          {!changes || changes.length === 0 ? (
            <div className="p-6.5 text-center text-[13.5px] text-muted">
              No changes yet — coverage has only been run once. This feed populates for real once
              the desk re-rates the market on schedule.
            </div>
          ) : (
            changes.map((ch, i) => (
              <div
                key={`${ch.ticker}-${ch.as_of}`}
                className={`flex items-center gap-4 px-5.5 py-4 ${
                  i !== changes.length - 1 ? "border-b border-white/11" : ""
                }`}
              >
                <div className="w-14 flex-none font-display text-[15px] font-semibold">{ch.ticker}</div>
                <div className="flex flex-none items-center gap-2">
                  <span className={`rounded-full px-2.5 py-1 font-mono text-[10px] uppercase ${PILL[ch.from_rating]}`}>
                    {ch.from_rating}
                  </span>
                  <span className="text-[13px] text-faint">→</span>
                  <span className={`rounded-full px-2.5 py-1 font-mono text-[10px] uppercase ${PILL[ch.to_rating]}`}>
                    {ch.to_rating}
                  </span>
                </div>
                <div className="flex-1 text-[12.5px] text-muted">{ch.key_signal}</div>
                <div className="flex-none font-mono text-[11px] text-faint">{ch.as_of.slice(0, 10)}</div>
              </div>
            ))
          )}
        </motion.div>
      </div>
    </section>
  );
}
