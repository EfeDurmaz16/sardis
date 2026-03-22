"use client";
/**
 * Analytics Page - Comprehensive spending analytics dashboard
 *
 * Features:
 * - Date range filtering (7d, 30d, 90d, custom)
 * - Agent filtering
 * - 8 analytics widgets with charts
 * - CSV export functionality
 * - Responsive layout
 */

import { useState, useEffect } from 'react';
import {
  TrendingUp,
  AlertCircle,
  Download,
  Calendar,
  Filter,
  DollarSign,
  Activity,
  Shield,
  Store,
  BarChart3,
} from 'lucide-react';
import { SpendingChart } from '@/components/charts/SpendingChart';
import { AgentSpendingBar } from '@/components/charts/AgentSpendingBar';
import { CategoryPie } from '@/components/charts/CategoryPie';
import { getAuthHeaders } from '@/api/client';

// API base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

// Types matching backend response models
interface TimeSeriesDataPoint {
  date: string;
  amount: number;
  count: number;
}

interface AgentSpending {
  agent_id: string;
  agent_name?: string | null;
  total: number;
  transaction_count: number;
  average: number;
}

interface CategorySpending {
  name: string;
  amount: number;
  count: number;
  percentage: number;
}

interface BudgetUtilization {
  agent_id: string;
  agent_name?: string | null;
  spent: number;
  budget: number;
  utilization: number;
  remaining: number;
}

interface PolicyBlock {
  timestamp: string;
  agent_id: string;
  agent_name?: string | null;
  amount: number;
  merchant: string;
  reason: string;
}

interface TopMerchant {
  merchant: string;
  amount: number;
  count: number;
  percentage: number;
}

interface AnalyticsSummary {
  total_spend: number;
  avg_daily_spend: number;
  active_agents: number;
  total_transactions: number;
  successful_transactions: number;
  blocked_transactions: number;
  block_rate: number;
  top_merchant?: string | null;
  largest_transaction: number;
}

export default function Analytics() {
  const [period, setPeriod] = useState<string>('30d');
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [hasError, setHasError] = useState(false);

  // Analytics data state
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [spendingOverTime, setSpendingOverTime] = useState<TimeSeriesDataPoint[]>([]);
  const [agentSpending, setAgentSpending] = useState<AgentSpending[]>([]);
  const [categorySpending, setCategorySpending] = useState<CategorySpending[]>([]);
  const [budgetUtilization, setBudgetUtilization] = useState<BudgetUtilization[]>([]);
  const [policyBlocks, setPolicyBlocks] = useState<PolicyBlock[]>([]);
  const [topMerchants, setTopMerchants] = useState<TopMerchant[]>([]);

  // Fetch analytics data
  const fetchAnalytics = async () => {
    setLoading(true);
    setHasError(false);
    try {
      const params = new URLSearchParams({ period });
      if (selectedAgent) {
        params.append('agent_id', selectedAgent);
      }

      const headers = getAuthHeaders();

      // Fetch all endpoints in parallel
      const [
        summaryRes,
        spendingRes,
        agentsRes,
        categoriesRes,
        budgetRes,
        blocksRes,
        merchantsRes,
      ] = await Promise.all([
        fetch(`${API_BASE}/api/v2/analytics/summary?${params}`, { headers }).catch(() => null),
        fetch(`${API_BASE}/api/v2/analytics/spending-over-time?${params}`, { headers }).catch(() => null),
        fetch(`${API_BASE}/api/v2/analytics/spending-by-agent?${params}`, { headers }).catch(() => null),
        fetch(`${API_BASE}/api/v2/analytics/spending-by-category?${params}`, { headers }).catch(() => null),
        fetch(`${API_BASE}/api/v2/analytics/budget-utilization?period=${period}`, { headers }).catch(() => null),
        fetch(`${API_BASE}/api/v2/analytics/policy-blocks?${params}`, { headers }).catch(() => null),
        fetch(`${API_BASE}/api/v2/analytics/top-merchants?${params}`, { headers }).catch(() => null),
      ]);

      let hasAnyData = false;

      if (summaryRes && summaryRes.ok) {
        const data = await summaryRes.json();
        setSummary(data);
        hasAnyData = true;
      } else {
        setSummary(null);
      }

      if (spendingRes && spendingRes.ok) {
        const data = await spendingRes.json();
        setSpendingOverTime(data.data || []);
        if ((data.data || []).length > 0) hasAnyData = true;
      } else {
        setSpendingOverTime([]);
      }

      if (agentsRes && agentsRes.ok) {
        const data = await agentsRes.json();
        setAgentSpending(data.agents || []);
        if ((data.agents || []).length > 0) hasAnyData = true;
      } else {
        setAgentSpending([]);
      }

      if (categoriesRes && categoriesRes.ok) {
        const data = await categoriesRes.json();
        setCategorySpending(data.categories || []);
        if ((data.categories || []).length > 0) hasAnyData = true;
      } else {
        setCategorySpending([]);
      }

      if (budgetRes && budgetRes.ok) {
        const data = await budgetRes.json();
        setBudgetUtilization(data.items || []);
        if ((data.items || []).length > 0) hasAnyData = true;
      } else {
        setBudgetUtilization([]);
      }

      if (blocksRes && blocksRes.ok) {
        const data = await blocksRes.json();
        setPolicyBlocks(data.blocks || []);
        if ((data.blocks || []).length > 0) hasAnyData = true;
      } else {
        setPolicyBlocks([]);
      }

      if (merchantsRes && merchantsRes.ok) {
        const data = await merchantsRes.json();
        setTopMerchants(data.merchants || []);
        if ((data.merchants || []).length > 0) hasAnyData = true;
      } else {
        setTopMerchants([]);
      }

      if (!hasAnyData) {
        setHasError(true);
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
      setSummary(null);
      setSpendingOverTime([]);
      setAgentSpending([]);
      setCategorySpending([]);
      setBudgetUtilization([]);
      setPolicyBlocks([]);
      setTopMerchants([]);
      setHasError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [period, selectedAgent]);

  // Export to CSV
  const handleExport = async () => {
    try {
      const params = new URLSearchParams({ period });
      if (selectedAgent) {
        params.append('agent_id', selectedAgent);
      }

      const response = await fetch(`${API_BASE}/api/v2/analytics/export?${params}`, {
        headers: getAuthHeaders(),
      });
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sardis-analytics-${period}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to export:', error);
    }
  };

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const noData = !loading && hasError;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Spending Analytics</h1>
        <p className="text-gray-400 mt-1">Track agent spending, budget utilization, and policy compliance</p>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-4 items-center justify-between">
          <div className="flex gap-2 items-center">
            <Calendar className="w-5 h-5 text-gray-500" />
            <span className="text-sm font-medium text-gray-400">Period:</span>
            <div className="flex gap-2">
              {['7d', '30d', '90d'].map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                    period === p
                      ? 'bg-sardis-500 text-dark-400'
                      : 'bg-dark-200 text-gray-400 hover:bg-dark-100'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setSelectedAgent('')}
              className={`px-3 py-1.5 text-sm font-medium transition-colors flex items-center gap-2 ${
                !selectedAgent
                  ? 'bg-sardis-500 text-dark-400'
                  : 'bg-dark-200 text-gray-400 hover:bg-dark-100'
              }`}
            >
              <Filter className="w-4 h-4" />
              All Agents
            </button>
            <button
              onClick={handleExport}
              className="px-3 py-1.5 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors flex items-center gap-2 glow-green-hover"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-sardis-500 mx-auto mb-4"></div>
            <p className="text-gray-400 text-sm">Loading analytics...</p>
          </div>
        </div>
      )}

      {/* Empty State */}
      {noData && (
        <div className="card p-12 text-center">
          <BarChart3 className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No data yet</h3>
          <p className="text-gray-400">
            Create an agent and make a payment to see analytics here.
          </p>
        </div>
      )}

      {/* Summary Cards */}
      {!loading && summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="card p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-400">Total Spend</span>
              <DollarSign className="w-5 h-5 text-sardis-400" />
            </div>
            <p className="text-2xl font-bold text-white">{formatCurrency(summary.total_spend)}</p>
            <p className="text-xs text-gray-500 mt-1">
              Avg daily: {formatCurrency(summary.avg_daily_spend)}
            </p>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-400">Transactions</span>
              <Activity className="w-5 h-5 text-sardis-400" />
            </div>
            <p className="text-2xl font-bold text-white">{summary.total_transactions}</p>
            <p className="text-xs text-gray-500 mt-1">
              {summary.successful_transactions} successful
            </p>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-400">Active Agents</span>
              <TrendingUp className="w-5 h-5 text-sardis-400" />
            </div>
            <p className="text-2xl font-bold text-white">{summary.active_agents}</p>
            <p className="text-xs text-gray-500 mt-1">
              Top: {summary.top_merchant || 'N/A'}
            </p>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-400">Block Rate</span>
              <Shield className="w-5 h-5 text-red-500" />
            </div>
            <p className="text-2xl font-bold text-white">{summary.block_rate.toFixed(1)}%</p>
            <p className="text-xs text-gray-500 mt-1">
              {summary.blocked_transactions} blocked
            </p>
          </div>
        </div>
      )}

      {/* Charts Grid */}
      {!loading && !noData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Spending Over Time */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Spending Over Time</h3>
            {spendingOverTime.length > 0 ? (
              <SpendingChart data={spendingOverTime} period={period} />
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
                No spending data for this period
              </div>
            )}
          </div>

          {/* Spend by Agent */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Spend by Agent</h3>
            {agentSpending.length > 0 ? (
              <AgentSpendingBar data={agentSpending} onAgentClick={setSelectedAgent} />
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
                No agent spending data for this period
              </div>
            )}
          </div>

          {/* Spend by Category */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Spend by Category</h3>
            {categorySpending.length > 0 ? (
              <CategoryPie data={categorySpending} />
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
                No category data for this period
              </div>
            )}
          </div>

          {/* Budget Utilization */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Budget Utilization</h3>
            <div className="space-y-3">
              {budgetUtilization.slice(0, 5).map((item) => (
                <div key={item.agent_id}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-gray-300">
                      {item.agent_name || item.agent_id.slice(0, 12)}
                    </span>
                    <span className="text-gray-400">
                      {formatCurrency(item.spent)} / {formatCurrency(item.budget)}
                    </span>
                  </div>
                  <div className="w-full bg-dark-100 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        item.utilization > 90
                          ? 'bg-red-500'
                          : item.utilization > 75
                          ? 'bg-amber-500'
                          : 'bg-sardis-500'
                      }`}
                      style={{ width: `${Math.min(item.utilization, 100)}%` }}
                    ></div>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {item.utilization.toFixed(1)}% utilized
                  </div>
                </div>
              ))}
              {budgetUtilization.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  No budget data available
                </div>
              )}
            </div>
          </div>

          {/* Top Merchants */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Store className="w-5 h-5 text-sardis-400" />
              Top Merchants
            </h3>
            <div className="space-y-2">
              {topMerchants.slice(0, 10).map((merchant, index) => (
                <div
                  key={merchant.merchant}
                  className="flex items-center justify-between p-2 hover:bg-dark-200/50 rounded"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-bold text-gray-500 w-6">#{index + 1}</span>
                    <span className="text-sm font-medium text-white">{merchant.merchant}</span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-sardis-400">
                      {formatCurrency(merchant.amount)}
                    </p>
                    <p className="text-xs text-gray-500">{merchant.count} txns</p>
                  </div>
                </div>
              ))}
              {topMerchants.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  No merchant data available
                </div>
              )}
            </div>
          </div>

          {/* Policy Blocks */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-500" />
              Recent Policy Blocks
            </h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {policyBlocks.slice(0, 10).map((block, index) => (
                <div
                  key={index}
                  className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg"
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-sm font-medium text-white">
                      {block.agent_name || block.agent_id.slice(0, 12)}
                    </span>
                    <span className="text-sm font-semibold text-red-400">
                      {formatCurrency(block.amount)}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mb-1">{block.merchant}</p>
                  <p className="text-xs text-red-400">{block.reason}</p>
                </div>
              ))}
              {policyBlocks.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  No policy blocks in this period
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
