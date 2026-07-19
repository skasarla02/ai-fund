import { AnimatePresence, motion } from "framer-motion";

interface Props {
  tickers: string[];
  onRemove: (ticker: string) => void;
  onCompare: () => void;
}

export function CompareBar({ tickers, onRemove, onCompare }: Props) {
  return (
    <AnimatePresence>
      {tickers.length > 0 && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ type: "spring", damping: 22, stiffness: 260 }}
          className="glass fixed bottom-6 left-1/2 z-[70] flex max-w-[92vw] -translate-x-1/2 items-center gap-3.5 py-3 pl-5 pr-3.5"
        >
          <span className="font-mono text-[11px] tracking-wide text-muted whitespace-nowrap">COMPARE</span>
          <div className="flex flex-wrap gap-2">
            {tickers.map((t) => (
              <span
                key={t}
                className="flex items-center gap-1.5 rounded-full border border-white/11 bg-white/6 py-1.5 pl-3.5 pr-2 font-display text-[13px] font-semibold"
              >
                {t}
                <button className="p-0.5 text-muted hover:text-ink" onClick={() => onRemove(t)}>
                  ✕
                </button>
              </span>
            ))}
          </div>
          <button
            className="whitespace-nowrap rounded-full bg-gradient-to-r from-mint to-iris px-4.5 py-2.5 font-sans text-[13px] font-bold text-[#141225] transition-transform hover:scale-105 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:scale-100"
            disabled={tickers.length < 2}
            onClick={onCompare}
          >
            {tickers.length < 2 ? "Select 1 more →" : `Compare ${tickers.length} →`}
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
