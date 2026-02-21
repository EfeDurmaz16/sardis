/**
 * CategoryPie - Donut/Pie chart for spending categories
 *
 * Displays category breakdown with legend and hover details.
 * Dark theme matching Sardis dashboard design system.
 */

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface CategoryItem {
  name: string;
  amount: number;
  count: number;
  percentage: number;
}

interface CategoryPieProps {
  data: CategoryItem[];
}

// Sardis orange + warm accent palette
const COLORS = [
  '#ff4f00', // Sardis-500
  '#f59e0b', // Amber-500
  '#ff7a3d', // Sardis-400
  '#fbbf24', // Amber-400
  '#fdba74', // Sardis-300
  '#fb923c', // Orange-400
  '#fed7aa', // Sardis-200
  '#fdba74', // Orange-300
  '#ea580c', // Sardis-600
  '#c2410c', // Sardis-700
];

export function CategoryPie({ data }: CategoryPieProps) {
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
          <p className="text-sm font-semibold text-white mb-1 capitalize">
            {data.name}
          </p>
          <p className="text-lg font-bold text-sardis-400">
            {formatCurrency(data.amount)}
          </p>
          <p className="text-xs text-gray-400">
            {data.count} transaction{data.count !== 1 ? 's' : ''}
          </p>
          <p className="text-xs text-gray-400">
            {data.percentage}% of total
          </p>
        </div>
      );
    }
    return null;
  };

  const renderLabel = (entry: any) => {
    return `${entry.percentage}%`;
  };

  const CustomLegend = ({ payload }: any) => {
    return (
      <div className="flex flex-wrap gap-2 justify-center mt-4">
        {payload.map((entry: any, index: number) => (
          <div key={`legend-${index}`} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-xs text-gray-400 capitalize">
              {entry.value}
            </span>
          </div>
        ))}
      </div>
    );
  };

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No category data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={renderLabel}
          outerRadius={80}
          innerRadius={50}
          fill="#ff4f00"
          dataKey="amount"
          nameKey="name"
        >
          {data.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend content={<CustomLegend />} />
      </PieChart>
    </ResponsiveContainer>
  );
}
