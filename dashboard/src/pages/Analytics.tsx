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
} from 'lucide-react';
import { SpendingChart } from '../components/charts/SpendingChart';
import { AgentSpendingBar } from '../components/charts/AgentSpendingBar';
import { CategoryPie } from '../components/charts/CategoryPie';

// API base URL
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

// Demo data for when API is unavailable
const DEMO_SUMMARY = {
  total_spend: 24680,
  avg_daily_spend: 822,
  active_agents: 12,
  total_transactions: 347,
  successful_transactions: 328,
  blocked_transactions: 19,
  block_rate: 5.5,
  top_merchant: 'OpenAI API',
  largest_transaction: 2500,
};

const DEMO_SPENDING_OVER_TIME = [
  { date: '2026-02-01', amount: 780, count: 12 },
  { date: '2026-02-03', amount: 920, count: 15 },
  { date: '2026-02-05', amount: 650, count: 9 },
  { date: '2026-02-07', amount: 1100, count: 18 },
  { date: '2026-02-09', amount: 840, count: 13 },
  { date: '2026-02-11', amount: 1350, count: 22 },
  { date: '2026-02-13', amount: 960, count: 14 },
  { date: '2026-02-15', amount: 1200, count: 19 },
  { date: '2026-02-17', amount: 780, count: 11 },
  { date: '2026-02-19', amount: 1450, count: 24 },
];

const DEMO_AGENT_SPENDING = [
  { agent_id: 'agent_001', agent_name: 'Shopping Agent', total: 4200, transaction_count: 56, average: 75 },
  { agent_id: 'agent_002', agent_name: 'Travel Booker', total: 6800, transaction_count: 23, average: 296 },
  { agent_id: 'agent_003', agent_name: 'SaaS Manager', total: 3100, transaction_count: 89, average: 35 },
  { agent_id: 'agent_004', agent_name: 'Cloud Ops', total: 5200, transaction_count: 42, average: 124 },
  { agent_id: 'agent_005', agent_name: 'Marketing AI', total: 2800, transaction_count: 67, average: 42 },
];

const DEMO_CATEGORY_SPENDING = [
  { name: 'SaaS & Software', amount: 8200, count: 124, percentage: 33 },
  { name: 'Cloud Infrastructure', amount: 6400, count: 45, percentage: 26 },
  { name: 'Travel', amount: 4800, count: 18, percentage: 19 },
  { name: 'Marketing', amount: 3200, count: 89, percentage: 13 },
  { name: 'Other', amount: 2080, count: 71, percentage: 9 },
];

const DEMO_BUDGET_UTILIZATION = [
  { agent_id: 'agent_002', agent_name: 'Travel Booker', spent: 6800, budget: 8000, utilization: 85, remaining: 1200 },
  { agent_id: 'agent_004', agent_name: 'Cloud Ops', spent: 5200, budget: 7000, utilization: 74, remaining: 1800 },
  { agent_id: 'agent_001', agent_name: 'Shopping Agent', spent: 4200, budget: 10000, utilization: 42, remaining: 5800 },
  { agent_id: 'agent_003', agent_name: 'SaaS Manager', spent: 3100, budget: 5000, utilization: 62, remaining: 1900 },
  { agent_id: 'agent_005', agent_name: 'Marketing AI', spent: 2800, budget: 5000, utilization: 56, remaining: 2200 },
];

const DEMO_TOP_MERCHANTS = [
  { merchant: 'OpenAI API', amount: 4200, count: 89, percentage: 17 },
  { merchant: 'AWS', amount: 3800, count: 34, percentage: 15 },
  { merchant: 'Google Cloud', amount: 2600, count: 28, percentage: 11 },
  { merchant: 'Vercel', amount: 1800, count: 45, percentage: 7 },
  { merchant: 'Stripe', amount: 1400, count: 23, percentage: 6 },
];

const DEMO_POLICY_BLOCKS = [
  { timestamp: new Date().toISOString(), agent_id: 'agent_002', agent_name: 'Travel Booker', amount: 3500, merchant: 'Luxury Hotels Inc', reason: 'Exceeds per-transaction limit ($2000)' },
  { timestamp: new Date(Date.now() - 3600000).toISOString(), agent_id: 'agent_005', agent_name: 'Marketing AI', amount: 800, merchant: 'Casino Online', reason: 'Blocked merchant category: gambling' },
  { timestamp: new Date(Date.now() - 7200000).toISOString(), agent_id: 'agent_001', agent_name: 'Shopping Agent', amount: 150, merchant: 'Unknown Store', reason: 'Merchant not in allowlist' },
];

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
        fetch(`${API_BASE}/api/v2/analytics/summary?${params}`).catch(() => null),
        fetch(`${API_BASE}/api/v2/analytics/spending-over-time?${params}`).catch(() => null),
        fetch(`${API_BASE}/api/v2/analytics/spending-by-agent?${params}`).catch(() => null),
        fetch(`${API_BASE}/api/v2/analytics/spending-by-category?${params}`).catch(() => null),
        fetch(`${API_BASE}/api/v2/analytics/budget-utilization?period=${period}`).catch(() => null),
        fetch(`${API_BASE}/api/v2/analytics/policy-blocks?${params}`).catch(() => null),
        fetch(`${API_BASE}/api/v2/analytics/top-merchants?${params}`).catch(() => null),
      ]);

      if (summaryRes && summaryRes.ok) {
        setSummary(await summaryRes.json());
      } else {
        setSummary(DEMO_SUMMARY);
      }

      if (spendingRes && spendingRes.ok) {
        const data = await spendingRes.json();
        setSpendingOverTime(data.data || []);
      } else {
        setSpendingOverTime(DEMO_SPENDING_OVER_TIME);
      }

      if (agentsRes && agentsRes.ok) {
        const data = await agentsRes.json();
        setAgentSpending(data.agents || []);
      } else {
        setAgentSpending(DEMO_AGENT_SPENDING);
      }

      if (categoriesRes && categoriesRes.ok) {
        const data = await categoriesRes.json();
        setCategorySpending(data.categories || []);
      } else {
        setCategorySpending(DEMO_CATEGORY_SPENDING);
      }

      if (budgetRes && budgetRes.ok) {
        const data = await budgetRes.json();
        setBudgetUtilization(data.items || []);
      } else {
        setBudgetUtilization(DEMO_BUDGET_UTILIZATION);
      }

      if (blocksRes && blocksRes.ok) {
        const data = await blocksRes.json();
        setPolicyBlocks(data.blocks || []);
      } else {
        setPolicyBlocks(DEMO_POLICY_BLOCKS);
      }

      if (merchantsRes && merchantsRes.ok) {
        const data = await merchantsRes.json();
        setTopMerchants(data.merchants || []);
      } else {
        setTopMerchants(DEMO_TOP_MERCHANTS);
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
      // Fall back to demo data
      setSummary(DEMO_SUMMARY);
      setSpendingOverTime(DEMO_SPENDING_OVER_TIME);
      setAgentSpending(DEMO_AGENT_SPENDING);
      setCategorySpending(DEMO_CATEGORY_SPENDING);
      setBudgetUtilization(DEMO_BUDGET_UTILIZATION);
      setPolicyBlocks(DEMO_POLICY_BLOCKS);
      setTopMerchants(DEMO_TOP_MERCHANTS);
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

      {/* Summary Cards */}
      {summary && (
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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Spending Over Time */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Spending Over Time</h3>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sardis-500"></div>
            </div>
          ) : (
            <SpendingChart data={spendingOverTime} period={period} />
          )}
        </div>

        {/* Spend by Agent */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Spend by Agent</h3>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sardis-500"></div>
            </div>
          ) : (
            <AgentSpendingBar data={agentSpending} onAgentClick={setSelectedAgent} />
          )}
        </div>

        {/* Spend by Category */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Spend by Category</h3>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sardis-500"></div>
            </div>
          ) : (
            <CategoryPie data={categorySpending} />
          )}
        </div>

        {/* Budget Utilization */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Budget Utilization</h3>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sardis-500"></div>
            </div>
          ) : (
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
          )}
        </div>

        {/* Top Merchants */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Store className="w-5 h-5 text-sardis-400" />
            Top Merchants
          </h3>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sardis-500"></div>
            </div>
          ) : (
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
          )}
        </div>

        {/* Policy Blocks */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-500" />
            Recent Policy Blocks
          </h3>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sardis-500"></div>
            </div>
          ) : (
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
          )}
        </div>
      </div>
    </div>
  );
}
