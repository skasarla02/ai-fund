import { forwardRef, useMemo } from "react";
import { motion } from "framer-motion";
import { useCoverageSearch, useCoverageStats, useTopConviction } from "../lib/api";
import { CompanyCard } from "./CompanyCard";
import type { CoverageRow } from "../lib/types";

const TOTAL_UNIVERSE = 1505;

interface Props {
  selected: string[];
  onToggleCompare: (ticker: string) => void;
  query: string;
  onQueryChange: (q: string) => void;
}

export const Hero = forwardRef<HTMLInputElement, Props>(function Hero(
  { selected, onToggleCompare, query, onQueryChange },
  inputRef,
) {
  const { data: stats } = useCoverageStats();
  const { data: topConviction } = useTopConviction(6);
  const { data: searchResults, isFetching } = useCoverageSearch(query);

  const results: CoverageRow[] | undefined = query.trim() ? searchResults : topConviction;
  const label = query.trim()
    ? results && results.length
      ? `${results.length} match${results.length > 1 ? "es" : ""} for "${query}"`
      : `No match for "${query}"`
    : "Showing our highest-conviction calls, both directions";

  const n = stats?.n ?? 0;
  const progressPct = useMemo(() => Math.min(100, (n / TOTAL_UNIVERSE) * 100), [n]);

  return (
    <div className="px-7.5 pb-15 pt-[118px]">
      <motion.div
        className="mx-auto max-w-6xl"
        initial="hidden"
        animate="show"
        variants={{ hidden: {}, show: { transition: { staggerChildren: 0.08 } } }}
      >
        {[
          <span key="eyebrow" className="tick">
            The problem
          </span>,
          <div
            key="problem"
            className="mt-5 max-w-[20ch] font-head text-[clamp(26px,3.6vw,42px)] font-bold leading-[1.14] tracking-tight text-balance"
          >
            Everyone has a hot take on your stocks.{" "}
            <span className="text-muted">Almost none of them keep score.</span>
          </div>,
          <div
            key="wedge"
            className="mt-2.5 max-w-[44ch] font-display text-[clamp(20px,2.6vw,28px)] font-semibold leading-[1.3] text-[#dcdaee]"
          >
            We rate every{" "}
            <span className="bg-gradient-to-r from-mint to-iris bg-clip-text text-transparent">
              S&amp;P 500
            </span>{" "}
            company — bull case, bear case, and a confidence{" "}
            <span className="bg-gradient-to-r from-mint to-iris bg-clip-text text-transparent">
              we're graded on.
            </span>{" "}
            Search one, or select a few to compare.
          </div>,
          <div key="card" className="glass mt-7.5 p-5.5">
            <div className="flex items-center gap-3.5 rounded-2xl border border-white/11 bg-white/4 py-1.5 pl-4.5">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="flex-none opacity-50">
                <circle cx="11" cy="11" r="7" stroke="#9e9db4" strokeWidth="2" />
                <path d="M21 21l-4.3-4.3" stroke="#9e9db4" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <input
                ref={inputRef}
                type="text"
                placeholder="Search any S&P 500 company — try Tesla, Apple, Exxon…"
                autoComplete="off"
                value={query}
                onChange={(e) => onQueryChange(e.target.value)}
                className="flex-1 bg-transparent py-3.5 font-sans text-[17px] font-semibold text-ink outline-none placeholder:font-medium placeholder:text-faint"
              />
              <span className="whitespace-nowrap rounded-lg border border-white/11 bg-white/6 px-2.5 py-1.5 font-mono text-[10.5px] tracking-wide text-muted">
                ↵ SEARCH
              </span>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2.5 px-1.5 pb-1 pt-3.5">
              <span className="font-mono text-xs text-muted">
                <b className="text-mint">{n}</b> of {TOTAL_UNIVERSE} S&amp;P companies rated so far —{" "}
                <b className="text-mint">growing daily</b>
              </span>
              <div className="h-1.5 w-[150px] overflow-hidden rounded-full bg-white/8">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-iris to-mint"
                  initial={{ width: 0 }}
                  animate={{ width: `${progressPct}%` }}
                  transition={{ duration: 1.4, ease: [0.2, 0.7, 0.2, 1] }}
                />
              </div>
            </div>

            <div className="mb-3 mt-5 px-1 font-mono text-[10.5px] uppercase tracking-[0.12em] text-faint">
              {isFetching ? "Searching…" : label}
            </div>
            <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
              {results?.slice(0, 9).map((c) => (
                <CompanyCard
                  key={c.ticker}
                  company={c}
                  selected={selected.includes(c.ticker)}
                  compareDisabled={selected.length >= 3}
                  onToggleCompare={onToggleCompare}
                />
              ))}
              {results && results.length === 0 && (
                <div className="col-span-full p-7.5 text-center text-[14px] text-muted">
                  No match in our rated companies yet — coverage is still growing ({n}/{TOTAL_UNIVERSE}).
                </div>
              )}
            </div>
          </div>,
          <p key="foot" className="mt-4 font-mono text-[13px] text-faint">
            → ratings use price signals <b className="text-mint">+ real fundamentals</b>. Open a card for
            the full factor breakdown. Select cards to compare.
          </p>,
        ].map((el, i) => (
          <motion.div key={i} variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }}>
            {el}
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
});
