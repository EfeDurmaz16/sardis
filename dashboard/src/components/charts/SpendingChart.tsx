/**
 * SpendingChart - Line chart component for spending over time
 *
 * Displays spending trends with gradient fill and interactive tooltips.
 * Designed for use in the Analytics dashboard.
 */

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { format, parseISO } from 'date-fns';

interface DataPoint {
  date: string;
  amount: number;
  count: number;
}

interface SpendingChartProps {
  data: DataPoint[];
  period: string;
  currency?: string;
}

export function SpendingChart({ data, period, currency = 'USD' }: SpendingChartProps) {
  // Format date based on period
  const formatDate = (dateString: string) => {
    try {
      const date = parseISO(dateString);

      if (period === '7d' || period?.includes('day')) {
        return format(date, 'MMM d');
      } else if (period?.includes('week')) {
        return format(date, 'MMM d');
      } else if (period?.includes('month')) {
        return format(date, 'MMM yyyy');
      }

      return format(date, 'MMM d');
    } catch {
      return dateString;
    }
  };

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
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
            {formatDate(data.date)}
          </p>
          <p className="text-lg font-bold text-purple-600">
            {formatCurrency(data.amount)}
          </p>
          <p className="text-xs text-gray-600">
            {data.count} transaction{data.count !== 1 ? 's' : ''}
          </p>
        </div>
      );
    }
    return null;
  };

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No spending data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#7c3aed" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
        />
        <YAxis
          tickFormatter={(value) => `$${value.toLocaleString()}`}
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="amount"
          stroke="#7c3aed"
          strokeWidth={2}
          fillOpacity={1}
          fill="url(#colorAmount)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
