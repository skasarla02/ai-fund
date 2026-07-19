import type { CoverageRow } from "../lib/types";

const CMP_COLORS = ["#7fe9c0", "#a99cff", "#ff9ecf"];

interface Axis {
  label: string;
  get: (c: CoverageRow) => number | null;
  min: number;
  max: number;
}

const AXES: Axis[] = [
  { label: "Conviction", get: (c) => c.conviction, min: 0, max: 1 },
  { label: "Margin", get: (c) => c.metrics.profit_margin, min: -0.1, max: 0.5 },
  { label: "Growth", get: (c) => c.metrics.revenue_growth, min: -0.2, max: 0.6 },
  {
    label: "Value",
    get: (c) => (c.metrics.trailing_pe === null ? 0.5 : 1 - Math.min(Math.max(c.metrics.trailing_pe, 0), 60) / 60),
    min: 0,
    max: 1,
  },
  { label: "Momentum", get: (c) => c.metrics.momentum_63d, min: -0.3, max: 0.3 },
];

function normAxis(axis: Axis, company: CoverageRow): number {
  const value = axis.get(company);
  if (value === null) return 0.4;
  const t = (value - axis.min) / (axis.max - axis.min);
  return Math.max(0.04, Math.min(1, t));
}

function polar(cx: number, cy: number, r: number, angle: number, frac: number): [number, number] {
  return [cx + r * frac * Math.cos(angle), cy + r * frac * Math.sin(angle)];
}

export function RadarChart({ companies }: { companies: CoverageRow[] }) {
  const W = 360;
  const H = 340;
  const cx = W / 2;
  const cy = 168;
  const R = 118;
  const N = AXES.length;
  const angle = (i: number) => -Math.PI / 2 + i * ((2 * Math.PI) / N);

  return (
    <div className="flex justify-center">
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        {[1, 2, 3, 4].map((ring) => {
          const frac = ring / 4;
          const points = Array.from({ length: N }, (_, i) => polar(cx, cy, R, angle(i), frac).join(","));
          return (
            <polygon
              key={ring}
              points={points.join(" ")}
              fill="none"
              stroke={`rgba(255,255,255,${ring === 4 ? 0.16 : 0.07})`}
              strokeWidth={1}
            />
          );
        })}
        {AXES.map((axis, i) => {
          const [x, y] = polar(cx, cy, R, angle(i), 1);
          const [lx, ly] = polar(cx, cy, R + 22, angle(i), 1);
          const cos = Math.cos(angle(i));
          const anchor = Math.abs(cos) < 0.3 ? "middle" : cos > 0 ? "start" : "end";
          return (
            <g key={axis.label}>
              <line x1={cx} y1={cy} x2={x} y2={y} stroke="rgba(255,255,255,.10)" strokeWidth={1} />
              <text
                x={lx}
                y={ly}
                textAnchor={anchor}
                dominantBaseline="middle"
                fontFamily="DM Mono, monospace"
                fontSize={11}
                fill="#9e9db4"
              >
                {axis.label}
              </text>
            </g>
          );
        })}
        {companies.map((company, idx) => {
          const color = CMP_COLORS[idx % CMP_COLORS.length];
          const points = AXES.map((axis, i) => polar(cx, cy, R, angle(i), normAxis(axis, company)));
          return (
            <g key={company.ticker} style={{ filter: `drop-shadow(0 0 6px ${color}77)` }}>
              <polygon
                points={points.map((p) => p.join(",")).join(" ")}
                fill={color}
                fillOpacity={0.16}
                stroke={color}
                strokeWidth={2.2}
              />
              {points.map(([x, y], i) => (
                <circle key={i} cx={x} cy={y} r={3.5} fill={color} />
              ))}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export { CMP_COLORS };
