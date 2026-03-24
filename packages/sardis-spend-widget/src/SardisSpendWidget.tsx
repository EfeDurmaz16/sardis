import { useEffect, useState } from "react";
import type { SardisSpendWidgetProps, SpendingData } from "./types";
import { BudgetBar } from "./BudgetBar";
import { SpendChart } from "./SpendChart";
import { TransactionList } from "./TransactionList";

export function SardisSpendWidget({
  agentId,
  apiKey,
  theme = "light",
  height = 400,
  period = "7d",
  baseUrl = "/api/v2",
}: SardisSpendWidgetProps) {
  const [data, setData] = useState<SpendingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchSpending() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `${baseUrl}/agents/${agentId}/spending?period=${period}`,
          {
            headers: {
              Authorization: `Bearer ${apiKey}`,
              "Content-Type": "application/json",
            },
          },
        );
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        const json: SpendingData = await res.json();
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load spending data");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchSpending();
    return () => { cancelled = true; };
  }, [agentId, apiKey, baseUrl, period]);

  const isDark = theme === "dark";

  const containerStyle: React.CSSProperties = {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    height,
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
    backgroundColor: isDark ? "#1a1a1a" : "#ffffff",
    color: isDark ? "#d1d5db" : "#374151",
    border: `1px solid ${isDark ? "#374151" : "#e5e7eb"}`,
    borderRadius: 8,
    padding: 16,
    boxSizing: "border-box",
  };

  if (loading) {
    return (
      <div style={containerStyle} data-testid="sardis-spend-widget">
        <LoadingSkeleton isDark={isDark} />
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle} data-testid="sardis-spend-widget">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flex: 1, color: isDark ? "#f87171" : "#dc2626" }}>
          {error}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div style={containerStyle} data-testid="sardis-spend-widget">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flex: 1, opacity: 0.5 }}>
          No spending data available
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle} data-testid="sardis-spend-widget">
      <BudgetBar budget={data.budget} isDark={isDark} />
      <SpendChart chart={data.chart} isDark={isDark} />
      <TransactionList transactions={data.transactions} isDark={isDark} />
    </div>
  );
}

function LoadingSkeleton({ isDark }: { isDark: boolean }) {
  const pulseColor = isDark ? "#2d2d2d" : "#f3f4f6";
  const barStyle: React.CSSProperties = {
    height: 12,
    borderRadius: 6,
    backgroundColor: pulseColor,
    marginBottom: 8,
  };
  return (
    <div data-testid="loading-skeleton" style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ ...barStyle, width: "60%" }} />
      <div style={{ ...barStyle, height: 20, width: "100%" }} />
      <div style={{ flex: 1, backgroundColor: pulseColor, borderRadius: 6 }} />
      <div style={{ ...barStyle, width: "90%" }} />
      <div style={{ ...barStyle, width: "75%" }} />
      <div style={{ ...barStyle, width: "85%" }} />
    </div>
  );
}
