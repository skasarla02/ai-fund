import { useQuery } from "@tanstack/react-query";
import type {
  CalibrationReport,
  CalibrationTrendPoint,
  ChangeEvent,
  CoverageRow,
  CoverageStats,
  EquityPoint,
  Metrics,
} from "./types";

// In dev, Vite proxies /api -> http://localhost:8000 (see vite.config.ts).
const BASE = "/api";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`${path} -> ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function useCoverageStats() {
  return useQuery({
    queryKey: ["coverage", "stats"],
    queryFn: () => getJSON<CoverageStats>("/coverage/stats"),
    refetchInterval: 60_000,
  });
}

export function useCoverageSearch(q: string) {
  return useQuery({
    queryKey: ["coverage", "search", q],
    queryFn: () => getJSON<CoverageRow[]>(`/coverage?q=${encodeURIComponent(q)}`),
    enabled: q.trim().length > 0,
  });
}

export function useHiddenWinners(limit = 6) {
  return useQuery({
    queryKey: ["coverage", "hidden-winners"],
    queryFn: () => getJSON<CoverageRow[]>("/coverage?hidden_winners=true"),
    select: (rows) => rows.slice(0, limit),
  });
}

export function useTopConviction(limit = 6) {
  return useQuery({
    queryKey: ["coverage", "top-conviction"],
    queryFn: () => getJSON<CoverageRow[]>("/coverage"),
    select: (rows) => {
      const sorted = [...rows].sort((a, b) => b.conviction - a.conviction);
      const top = sorted.slice(0, 3);
      const bottom = sorted.slice(-3).reverse();
      return limit >= 6 ? [...top, ...bottom] : sorted.slice(0, limit);
    },
  });
}

export function useAllCoverage() {
  return useQuery({
    queryKey: ["coverage", "all"],
    queryFn: () => getJSON<CoverageRow[]>("/coverage"),
  });
}

export function useChangesFeed(limit = 20) {
  return useQuery({
    queryKey: ["coverage", "changes", limit],
    queryFn: () => getJSON<ChangeEvent[]>(`/coverage/changes/feed?limit=${limit}`),
  });
}

export function useCalibration() {
  return useQuery({
    queryKey: ["calibration"],
    queryFn: () => getJSON<CalibrationReport>("/calibration"),
    retry: 1,
  });
}

export function useCalibrationTrend() {
  return useQuery({
    queryKey: ["calibration", "trend"],
    queryFn: () => getJSON<CalibrationTrendPoint[]>("/calibration/trend?freq=QS"),
    retry: 1,
  });
}

export function useEquityCurve(universe: "equities" | "crypto") {
  return useQuery({
    queryKey: ["equity", universe],
    queryFn: () => getJSON<EquityPoint[]>(`/equity/${universe}`),
    retry: 1,
  });
}

export function useMetrics(universe: "equities" | "crypto") {
  return useQuery({
    queryKey: ["metrics", universe],
    queryFn: () => getJSON<Metrics>(`/metrics/${universe}`),
    retry: 1,
  });
}
