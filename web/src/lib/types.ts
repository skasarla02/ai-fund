export type Rating = "bullish" | "neutral" | "bearish";
export type Tier = "S&P 500" | "S&P 400" | "S&P 600";

export interface CompanyMetrics {
  momentum_63d: number | null;
  volatility_ann: number | null;
  rsi_14: number | null;
  profit_margin: number | null;
  revenue_growth: number | null;
  trailing_pe: number | null;
  return_on_equity: number | null;
  beta: number | null;
  market_cap: number | null;
  analyst_coverage: number | null;
}

export interface CoverageRow {
  ticker: string;
  name: string;
  sector: string;
  sub_industry: string;
  tier: Tier;
  price: number | null;
  as_of: string;
  rating: Rating;
  conviction: number;
  key_signal: string;
  thesis: string;
  bear_case: string;
  metrics: CompanyMetrics;
}

export interface CoverageStats {
  n: number;
  bullish: number;
  neutral: number;
  bearish: number;
  by_tier: Record<string, number>;
  model: string;
  last_updated: string | null;
}

export interface ChangeEvent {
  ticker: string;
  name: string;
  as_of: string;
  from_rating: Rating;
  to_rating: Rating;
  from_conviction: number;
  to_conviction: number;
  key_signal: string;
}

export interface CalibrationBin {
  bucket: string;
  n: number;
  avg_predicted: number;
  empirical: number;
}

export interface CalibrationReport {
  brier: number;
  n: number;
  base_rate: number;
  bins: CalibrationBin[];
}

export interface CalibrationTrendPoint {
  period: string;
  brier: number;
  n: number;
}

export interface EquityPoint {
  timestamp: string;
  strategy: number;
  benchmark: number;
}

export interface Metrics {
  benchmark: string;
  total_return: number;
  cagr: number;
  ann_volatility: number;
  sharpe: number;
  sortino: number;
  max_drawdown: number;
  calmar: number;
  n_days: number;
  benchmark_total_return?: number;
  excess_return?: number;
  beta?: number;
}
