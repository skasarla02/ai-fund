import { useRef, useState } from "react";
import { WebGLBackground } from "./components/WebGLBackground";
import { Header } from "./components/Header";
import { Hero } from "./components/Hero";
import { SectorHeatmap } from "./components/SectorHeatmap";
import { ChangesFeed } from "./components/ChangesFeed";
import { Calibration } from "./components/Calibration";
import { TrackRecord } from "./components/TrackRecord";
import { CompareBar } from "./components/CompareBar";
import { CompareModal } from "./components/CompareModal";
import { useAllCoverage } from "./lib/api";

const MAX_COMPARE = 3;

function App() {
  const [selected, setSelected] = useState<string[]>([]);
  const [comparing, setComparing] = useState(false);
  const [query, setQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);
  const { data: allCoverage } = useAllCoverage();

  function toggleCompare(ticker: string) {
    setSelected((prev) => {
      if (prev.includes(ticker)) return prev.filter((t) => t !== ticker);
      if (prev.length >= MAX_COMPARE) return prev;
      return [...prev, ticker];
    });
  }

  function jumpToSearch(ticker: string) {
    setQuery(ticker);
    searchInputRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  const compareCompanies = comparing
    ? (allCoverage?.filter((c) => selected.includes(c.ticker)) ?? null)
    : null;

  return (
    <>
      <WebGLBackground />
      <Header />
      <Hero
        ref={searchInputRef}
        query={query}
        onQueryChange={setQuery}
        selected={selected}
        onToggleCompare={toggleCompare}
      />
      <SectorHeatmap onSelect={jumpToSearch} />
      <ChangesFeed />
      <Calibration />
      <TrackRecord />
      <footer className="border-t border-white/6 py-17.5">
        <div className="mx-auto flex max-w-6xl flex-wrap justify-between gap-4 px-7.5 font-mono text-xs text-faint">
          <span>the spread model — coverage that keeps score</span>
          <span>simulated · not investment advice</span>
        </div>
      </footer>

      <CompareBar tickers={selected} onRemove={toggleCompare} onCompare={() => setComparing(true)} />
      <CompareModal companies={compareCompanies} onClose={() => setComparing(false)} />
    </>
  );
}

export default App;
