import { useEffect, useRef, useState } from "react";
import type { SardisSpendWidgetProps, SpendingData } from "./types";
import { getTheme, themeToCSS } from "./theme";
import { BudgetBar } from "./BudgetBar";
import { SpendChart } from "./SpendChart";
import { Sparkline } from "./Sparkline";
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
  const [narrow, setNarrow] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    if (typeof ResizeObserver === "undefined") return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setNarrow(entry.contentRect.width < 320);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const tokens = getTheme(theme);
  const isDark = theme === "dark";
  const cssVars = themeToCSS(tokens);

  const containerStyle: React.CSSProperties = {
    ...cssVars as unknown as React.CSSProperties,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    height,
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
    backgroundColor: tokens.bg,
    color: tokens.text,
    border: `1px solid ${tokens.border}`,
    borderRadius: 8,
    padding: 16,
    boxSizing: "border-box",
  };

  if (loading) {
    return (
      <div ref={containerRef} style={containerStyle} data-testid="sardis-spend-widget">
        <LoadingSkeleton bgColor={tokens.bgSecondary} />
      </div>
    );
  }

  if (error) {
    return (
      <div ref={containerRef} style={containerStyle} data-testid="sardis-spend-widget">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flex: 1, color: tokens.error }}>
          {error}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div ref={containerRef} style={containerStyle} data-testid="sardis-spend-widget">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flex: 1, opacity: 0.5 }}>
          No spending data available
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} style={containerStyle} data-testid="sardis-spend-widget">
      <BudgetBar budget={data.budget} isDark={isDark} />
      {narrow ? (
        <Sparkline chart={data.chart} isDark={isDark} />
      ) : (
        <SpendChart chart={data.chart} isDark={isDark} />
      )}
      <TransactionList transactions={data.transactions} isDark={isDark} />
    </div>
  );
}

function LoadingSkeleton({ bgColor }: { bgColor: string }) {
  const barStyle: React.CSSProperties = {
    height: 12,
    borderRadius: 6,
    backgroundColor: bgColor,
    marginBottom: 8,
  };
  return (
    <div data-testid="loading-skeleton" style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ ...barStyle, width: "60%" }} />
      <div style={{ ...barStyle, height: 20, width: "100%" }} />
      <div style={{ flex: 1, backgroundColor: bgColor, borderRadius: 6 }} />
      <div style={{ ...barStyle, width: "90%" }} />
      <div style={{ ...barStyle, width: "75%" }} />
      <div style={{ ...barStyle, width: "85%" }} />
    </div>
  );
}
