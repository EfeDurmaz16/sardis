export interface ThemeTokens {
  bg: string;
  bgSecondary: string;
  text: string;
  textMuted: string;
  border: string;
  chartStroke: string;
  chartFill: string;
  error: string;
}

const lightTheme: ThemeTokens = {
  bg: "#ffffff",
  bgSecondary: "#f9fafb",
  text: "#374151",
  textMuted: "#6b7280",
  border: "#e5e7eb",
  chartStroke: "#6b7280",
  chartFill: "#9ca3af",
  error: "#dc2626",
};

const darkTheme: ThemeTokens = {
  bg: "#1a1a1a",
  bgSecondary: "#1f2937",
  text: "#d1d5db",
  textMuted: "#9ca3af",
  border: "#374151",
  chartStroke: "#9ca3af",
  chartFill: "#6b7280",
  error: "#f87171",
};

export function getTheme(mode: "light" | "dark"): ThemeTokens {
  return mode === "dark" ? darkTheme : lightTheme;
}

export function themeToCSS(tokens: ThemeTokens): Record<string, string> {
  return {
    "--sardis-bg": tokens.bg,
    "--sardis-bg-secondary": tokens.bgSecondary,
    "--sardis-text": tokens.text,
    "--sardis-text-muted": tokens.textMuted,
    "--sardis-border": tokens.border,
    "--sardis-chart-stroke": tokens.chartStroke,
    "--sardis-chart-fill": tokens.chartFill,
    "--sardis-error": tokens.error,
  };
}
