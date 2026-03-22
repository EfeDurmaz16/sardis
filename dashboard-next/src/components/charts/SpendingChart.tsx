/**
 * SpendingChart - Line chart component for spending over time
 *
 * Displays spending trends with gradient fill and interactive tooltips.
 * Dark theme matching Sardis dashboard design system.
 */

import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
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

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
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
            {formatDate(data.date)}
          </p>
          <p className="text-lg font-bold text-sardis-400">
            {formatCurrency(data.amount)}
          </p>
          <p className="text-xs text-gray-400">
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
            <stop offset="5%" stopColor="#ff4f00" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#ff4f00" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#2f2e2c" />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
          tick={{ fill: '#9ca3af' }}
        />
        <YAxis
          tickFormatter={(value) => `$${value.toLocaleString()}`}
          stroke="#6b7280"
          style={{ fontSize: '12px' }}
          tick={{ fill: '#9ca3af' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="amount"
          stroke="#ff4f00"
          strokeWidth={2}
          fillOpacity={1}
          fill="url(#colorAmount)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
