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
  TrendingDown,
  AlertCircle,
  Download,
  Calendar,
  Filter,
  DollarSign,
  Activity,
  Shield,
  Store,
} from 'lucide-react';
import { SpendingChart } from '../components/charts/SpendingChart';
import { AgentSpendingBar } from '../components/charts/AgentSpendingBar';
import { CategoryPie } from '../components/charts/CategoryPie';

// API base URL
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

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
    try {
      const params = new URLSearchParams({ period });
      if (selectedAgent) {
        params.append('agent_id', selectedAgent);
      }

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
        fetch(`${API_BASE}/api/v2/analytics/summary?${params}`),
        fetch(`${API_BASE}/api/v2/analytics/spending-over-time?${params}`),
        fetch(`${API_BASE}/api/v2/analytics/spending-by-agent?${params}`),
        fetch(`${API_BASE}/api/v2/analytics/spending-by-category?${params}`),
        fetch(`${API_BASE}/api/v2/analytics/budget-utilization?period=${period}`),
        fetch(`${API_BASE}/api/v2/analytics/policy-blocks?${params}`),
        fetch(`${API_BASE}/api/v2/analytics/top-merchants?${params}`),
      ]);

      if (summaryRes.ok) {
        const data = await summaryRes.json();
        setSummary(data);
      }

      if (spendingRes.ok) {
        const data = await spendingRes.json();
        setSpendingOverTime(data.data || []);
      }

      if (agentsRes.ok) {
        const data = await agentsRes.json();
        setAgentSpending(data.agents || []);
      }

      if (categoriesRes.ok) {
        const data = await categoriesRes.json();
        setCategorySpending(data.categories || []);
      }

      if (budgetRes.ok) {
        const data = await budgetRes.json();
        setBudgetUtilization(data.items || []);
      }

      if (blocksRes.ok) {
        const data = await blocksRes.json();
        setPolicyBlocks(data.blocks || []);
      }

      if (merchantsRes.ok) {
        const data = await merchantsRes.json();
        setTopMerchants(data.merchants || []);
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
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

      const response = await fetch(`${API_BASE}/api/v2/analytics/export?${params}`);
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

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Spending Analytics</h1>
        <p className="text-gray-600">Track agent spending, budget utilization, and policy compliance</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-center justify-between">
          <div className="flex gap-2 items-center">
            <Calendar className="w-5 h-5 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Period:</span>
            <div className="flex gap-2">
              {['7d', '30d', '90d'].map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                    period === p
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
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
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-2 ${
                !selectedAgent
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Filter className="w-4 h-4" />
              All Agents
            </button>
            <button
              onClick={handleExport}
              className="px-3 py-1.5 text-sm font-medium rounded-md bg-amber-500 text-white hover:bg-amber-600 transition-colors flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Total Spend</span>
              <DollarSign className="w-5 h-5 text-purple-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{formatCurrency(summary.total_spend)}</p>
            <p className="text-xs text-gray-500 mt-1">
              Avg daily: {formatCurrency(summary.avg_daily_spend)}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Transactions</span>
              <Activity className="w-5 h-5 text-amber-500" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{summary.total_transactions}</p>
            <p className="text-xs text-gray-500 mt-1">
              {summary.successful_transactions} successful
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Active Agents</span>
              <TrendingUp className="w-5 h-5 text-purple-600" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{summary.active_agents}</p>
            <p className="text-xs text-gray-500 mt-1">
              Top: {summary.top_merchant || 'N/A'}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Block Rate</span>
              <Shield className="w-5 h-5 text-red-500" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{summary.block_rate.toFixed(1)}%</p>
            <p className="text-xs text-gray-500 mt-1">
              {summary.blocked_transactions} blocked
            </p>
          </div>
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Spending Over Time */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Spending Over Time</h3>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
            </div>
          ) : (
            <SpendingChart data={spendingOverTime} period={period} />
          )}
        </div>

        {/* Spend by Agent */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Spend by Agent</h3>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
            </div>
          ) : (
            <AgentSpendingBar data={agentSpending} onAgentClick={setSelectedAgent} />
          )}
        </div>

        {/* Spend by Category */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Spend by Category</h3>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
            </div>
          ) : (
            <CategoryPie data={categorySpending} />
          )}
        </div>

        {/* Budget Utilization */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Budget Utilization</h3>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
            </div>
          ) : (
            <div className="space-y-3">
              {budgetUtilization.slice(0, 5).map((item) => (
                <div key={item.agent_id}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-gray-700">
                      {item.agent_name || item.agent_id.slice(0, 12)}
                    </span>
                    <span className="text-gray-600">
                      {formatCurrency(item.spent)} / {formatCurrency(item.budget)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        item.utilization > 90
                          ? 'bg-red-500'
                          : item.utilization > 75
                          ? 'bg-amber-500'
                          : 'bg-purple-600'
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
          )}
        </div>

        {/* Top Merchants */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Store className="w-5 h-5 text-purple-600" />
            Top Merchants
          </h3>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
            </div>
          ) : (
            <div className="space-y-2">
              {topMerchants.slice(0, 10).map((merchant, index) => (
                <div
                  key={merchant.merchant}
                  className="flex items-center justify-between p-2 hover:bg-gray-50 rounded"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-bold text-gray-400 w-6">#{index + 1}</span>
                    <span className="text-sm font-medium text-gray-900">{merchant.merchant}</span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-purple-600">
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
          )}
        </div>

        {/* Policy Blocks */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-500" />
            Recent Policy Blocks
          </h3>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
            </div>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {policyBlocks.slice(0, 10).map((block, index) => (
                <div
                  key={index}
                  className="p-3 bg-red-50 border border-red-200 rounded-lg"
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-sm font-medium text-gray-900">
                      {block.agent_name || block.agent_id.slice(0, 12)}
                    </span>
                    <span className="text-sm font-semibold text-red-600">
                      {formatCurrency(block.amount)}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 mb-1">{block.merchant}</p>
                  <p className="text-xs text-red-600">{block.reason}</p>
                </div>
              ))}
              {policyBlocks.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  No policy blocks in this period
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
