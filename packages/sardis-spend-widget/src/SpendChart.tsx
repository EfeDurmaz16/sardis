import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import type { ChartPoint } from "./types";

interface SpendChartProps {
  chart: ChartPoint[];
  isDark: boolean;
}

export function SpendChart({ chart, isDark }: SpendChartProps) {
  if (chart.length === 0) return null;

  const textColor = isDark ? "#9ca3af" : "#6b7280";
  const gridColor = isDark ? "#374151" : "#e5e7eb";

  return (
    <div style={{ flex: "1 1 auto", minHeight: 100, marginBottom: 12 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chart} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="sardis-area-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={isDark ? "#6b7280" : "#9ca3af"} stopOpacity={0.3} />
              <stop offset="95%" stopColor={isDark ? "#6b7280" : "#9ca3af"} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: textColor }}
            axisLine={{ stroke: gridColor }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: textColor }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `$${v}`}
            width={48}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: isDark ? "#1f2937" : "#fff",
              border: `1px solid ${gridColor}`,
              borderRadius: 6,
              fontSize: 12,
              color: isDark ? "#d1d5db" : "#374151",
            }}
            formatter={(value: number) => [`$${value.toFixed(2)}`, "Spent"]}
          />
          <Area
            type="monotone"
            dataKey="amount"
            stroke={isDark ? "#9ca3af" : "#6b7280"}
            strokeWidth={2}
            fill="url(#sardis-area-fill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
