interface BudgetBarProps {
  budget: { used: number; total: number; period: string };
  isDark: boolean;
}

export function BudgetBar({ budget, isDark }: BudgetBarProps) {
  const pct = budget.total > 0 ? (budget.used / budget.total) * 100 : 0;
  const clampedPct = Math.min(pct, 100);

  const barColor = pct >= 95 ? "#ef4444" : pct >= 80 ? "#eab308" : "#22c55e";

  const fmt = (n: number) =>
    n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 });

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
        <span>
          {fmt(budget.used)} / {fmt(budget.total)}
        </span>
        <span style={{ fontWeight: 600 }}>{pct.toFixed(0)}%</span>
      </div>
      <div
        style={{
          width: "100%",
          height: 8,
          borderRadius: 4,
          backgroundColor: isDark ? "#374151" : "#e5e7eb",
          overflow: "hidden",
        }}
      >
        <div
          data-testid="budget-bar-fill"
          style={{
            width: `${clampedPct}%`,
            height: "100%",
            borderRadius: 4,
            backgroundColor: barColor,
            transition: "width 0.3s ease",
          }}
        />
      </div>
      <div style={{ fontSize: 11, opacity: 0.6, marginTop: 2 }}>
        Period: {budget.period}
      </div>
    </div>
  );
}
