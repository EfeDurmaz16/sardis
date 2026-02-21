/**
 * AgentSpendingBar - Stacked bar chart for per-agent spending
 *
 * Shows spending breakdown by agent with color-coded bars.
 * Supports click-to-filter interaction.
 */

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface AgentSpending {
  agent_id: string;
  agent_name?: string | null;
  total: number;
  transaction_count: number;
  average: number;
}

interface AgentSpendingBarProps {
  data: AgentSpending[];
  onAgentClick?: (agentId: string) => void;
}

// Color palette for agents (deep purple theme with amber accents)
const COLORS = [
  '#7c3aed', // Purple-600
  '#f59e0b', // Amber-500
  '#8b5cf6', // Purple-500
  '#fbbf24', // Amber-400
  '#a78bfa', // Purple-400
  '#fb923c', // Orange-400
  '#c4b5fd', // Purple-300
  '#fdba74', // Orange-300
];

export function AgentSpendingBar({ data, onAgentClick }: AgentSpendingBarProps) {
  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white border border-purple-200 rounded-lg shadow-lg p-3">
          <p className="text-sm font-semibold text-gray-900 mb-1">
            {data.agent_name || data.agent_id}
          </p>
          <p className="text-lg font-bold text-purple-600">
            {formatCurrency(data.total)}
          </p>
          <p className="text-xs text-gray-600">
            {data.transaction_count} transactions
          </p>
          <p className="text-xs text-gray-600">
            Avg: {formatCurrency(data.average)}
          </p>
        </div>
      );
    }
    return null;
  };

  // Handle bar click
  const handleClick = (data: any) => {
    if (onAgentClick) {
      onAgentClick(data.agent_id);
    }
  };

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No agent spending data available
      </div>
    );
  }

  // Prepare data with display names
  const chartData = data.map(item => ({
    ...item,
    name: item.agent_name || `Agent ${item.agent_id.slice(0, 8)}...`,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="name"
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
          angle={-45}
          textAnchor="end"
          height={80}
        />
        <YAxis
          tickFormatter={(value) => `$${value.toLocaleString()}`}
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar
          dataKey="total"
          onClick={handleClick}
          style={{ cursor: onAgentClick ? 'pointer' : 'default' }}
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
