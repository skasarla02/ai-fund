export function pct(x: number | null | undefined, digits = 1): string {
  if (x === null || x === undefined) return "—";
  const sign = x >= 0 ? "+" : "−";
  return `${sign}${Math.abs(x * 100).toFixed(digits)}%`;
}

export function peMultiple(x: number | null | undefined): string {
  if (x === null || x === undefined) return "—";
  return `${x.toFixed(1)}x`;
}

export function num(x: number | null | undefined, digits = 2): string {
  if (x === null || x === undefined) return "—";
  return x.toFixed(digits);
}

export function stripMockPrefix(s: string): string {
  return s.replace(/^\[mock\]\s*/, "");
}
