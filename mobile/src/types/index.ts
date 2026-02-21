export interface Agent {
  id: string;
  name: string;
  status: 'active' | 'paused' | 'blocked';
  totalSpent: number;
  budgetLimit: number;
  currency: string;
  lastActivity: string;
}

export interface Alert {
  id: string;
  severity: 'info' | 'warning' | 'critical';
  agentId: string;
  agentName: string;
  message: string;
  timestamp: string;
  read: boolean;
  metadata?: Record<string, any>;
}

export interface ApprovalRequest {
  id: string;
  agentId: string;
  agentName: string;
  amount: number;
  currency: string;
  merchant: string;
  category: string;
  policyViolation?: string;
  timestamp: string;
  status: 'pending' | 'approved' | 'rejected';
  transactionDetails?: {
    chain?: string;
    token?: string;
    recipient?: string;
    mandate?: string;
  };
}

export interface SpendingPolicy {
  id: string;
  agentId: string;
  agentName: string;
  enabled: boolean;
  dailyLimit?: number;
  monthlyLimit?: number;
  allowedCategories?: string[];
  blockedMerchants?: string[];
  requireApprovalAbove?: number;
  currency: string;
}

export interface SpendingSummary {
  totalSpent: number;
  currency: string;
  period: '7d' | '30d' | '90d';
  agentBreakdown: {
    agentId: string;
    agentName: string;
    amount: number;
    percentage: number;
  }[];
  categoryBreakdown: {
    category: string;
    amount: number;
    percentage: number;
  }[];
  dailySpending: {
    date: string;
    amount: number;
  }[];
}

export interface QuickStats {
  activeAgents: number;
  totalAgents: number;
  activeCards: number;
  blockedTransactions: number;
}
