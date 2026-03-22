/**
 * AgentSpendingBar - Bar chart for per-agent spending
 *
 * Shows spending breakdown by agent with color-coded bars.
 * Dark theme matching Sardis dashboard design system.
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

// Sardis orange + warm accent palette for dark theme
const COLORS = [
  '#ff4f00', // Sardis-500
  '#f59e0b', // Amber-500
  '#ff7a3d', // Sardis-400
  '#fbbf24', // Amber-400
  '#fdba74', // Sardis-300
  '#fb923c', // Orange-400
  '#fed7aa', // Sardis-200
  '#fdba74', // Orange-300
];

export function AgentSpendingBar({ data, onAgentClick }: AgentSpendingBarProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-dark-200 border border-dark-100 p-3" style={{ boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}>
          <p className="text-sm font-semibold text-white mb-1">
            {data.agent_name || data.agent_id}
          </p>
          <p className="text-lg font-bold text-sardis-400">
            {formatCurrency(data.total)}
          </p>
          <p className="text-xs text-gray-400">
            {data.transaction_count} transactions
          </p>
          <p className="text-xs text-gray-400">
            Avg: {formatCurrency(data.average)}
          </p>
        </div>
      );
    }
    return null;
  };

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

  const chartData = data.map(item => ({
    ...item,
    name: item.agent_name || `Agent ${item.agent_id.slice(0, 8)}...`,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2f2e2c" />
        <XAxis
          dataKey="name"
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
          tick={{ fill: '#9ca3af' }}
          angle={-45}
          textAnchor="end"
          height={80}
        />
        <YAxis
          tickFormatter={(value) => `$${value.toLocaleString()}`}
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
          tick={{ fill: '#9ca3af' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar
          dataKey="total"
          onClick={handleClick}
          style={{ cursor: onAgentClick ? 'pointer' : 'default' }}
        >
          {chartData.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
