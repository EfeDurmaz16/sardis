/**
 * CategoryPie - Donut/Pie chart for spending categories
 *
 * Displays category breakdown with legend and hover details.
 * Uses deep purple and amber color scheme.
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

// Color palette matching the Sardis theme
const COLORS = [
  '#7c3aed', // Purple-600
  '#f59e0b', // Amber-500
  '#8b5cf6', // Purple-500
  '#fbbf24', // Amber-400
  '#a78bfa', // Purple-400
  '#fb923c', // Orange-400
  '#c4b5fd', // Purple-300
  '#fdba74', // Orange-300
  '#ddd6fe', // Purple-200
  '#fed7aa', // Orange-200
];

export function CategoryPie({ data }: CategoryPieProps) {
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
          <p className="text-sm font-semibold text-gray-900 mb-1 capitalize">
            {data.name}
          </p>
          <p className="text-lg font-bold text-purple-600">
            {formatCurrency(data.amount)}
          </p>
          <p className="text-xs text-gray-600">
            {data.count} transaction{data.count !== 1 ? 's' : ''}
          </p>
          <p className="text-xs text-gray-600">
            {data.percentage}% of total
          </p>
        </div>
      );
    }
    return null;
  };

  // Custom label renderer
  const renderLabel = (entry: any) => {
    return `${entry.percentage}%`;
  };

  // Custom legend
  const CustomLegend = ({ payload }: any) => {
    return (
      <div className="flex flex-wrap gap-2 justify-center mt-4">
        {payload.map((entry: any, index: number) => (
          <div key={`legend-${index}`} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-xs text-gray-700 capitalize">
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
          fill="#8884d8"
          dataKey="amount"
          nameKey="name"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend content={<CustomLegend />} />
      </PieChart>
    </ResponsiveContainer>
  );
}
