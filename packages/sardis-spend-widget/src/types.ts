export interface ChartPoint {
  date: string;
  amount: number;
}

export interface Transaction {
  id: string;
  date: string;
  recipient: string;
  amount: number;
  status: "completed" | "pending" | "blocked";
  explanation?: {
    checks_failed: string[];
    suggested_action: string;
  };
}

export interface SpendingData {
  budget: {
    used: number;
    total: number;
    period: string;
  };
  chart: ChartPoint[];
  transactions: Transaction[];
}

export interface SardisSpendWidgetProps {
  agentId: string;
  apiKey: string;
  theme?: "light" | "dark";
  height?: number;
  period?: "7d" | "30d";
  baseUrl?: string;
}
