import type { ChartPoint } from "./types";

interface SparklineProps {
  chart: ChartPoint[];
  isDark: boolean;
}

/** Compact sparkline for narrow containers (<320px) */
export function Sparkline({ chart, isDark }: SparklineProps) {
  if (chart.length < 2) return null;

  const amounts = chart.map((p) => p.amount);
  const min = Math.min(...amounts);
  const max = Math.max(...amounts);
  const range = max - min || 1;

  const w = 280;
  const h = 40;
  const step = w / (amounts.length - 1);

  const points = amounts
    .map((a, i) => {
      const x = i * step;
      const y = h - ((a - min) / range) * (h - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");

  const strokeColor = isDark ? "#9ca3af" : "#6b7280";

  return (
    <div style={{ marginBottom: 8, display: "flex", justifyContent: "center" }}>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        width="100%"
        height={h}
        style={{ maxWidth: w }}
        role="img"
        aria-label="Spending sparkline"
      >
        <polyline
          points={points}
          fill="none"
          stroke={strokeColor}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}
