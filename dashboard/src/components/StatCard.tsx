import { ReactNode } from 'react'
import clsx from 'clsx'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  change?: string
  changeType?: 'positive' | 'negative' | 'neutral'
  icon?: ReactNode
  subtitle?: string
}

export default function StatCard({
  title,
  value,
  change,
  changeType = 'neutral',
  icon,
  subtitle
}: StatCardProps) {
  return (
    <div className="card card-hover p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-400">{title}</p>
          <p className="mt-2 text-3xl font-bold text-white mono-numbers">
            {value}
          </p>
          {subtitle && (
            <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="p-3 bg-dark-100 rounded-lg text-sardis-400">
            {icon}
          </div>
        )}
      </div>
      
      {change && (
        <div className="mt-4 flex items-center gap-2">
          {changeType === 'positive' && (
            <TrendingUp className="w-4 h-4 text-green-500" />
          )}
          {changeType === 'negative' && (
            <TrendingDown className="w-4 h-4 text-red-500" />
          )}
          {changeType === 'neutral' && (
            <Minus className="w-4 h-4 text-gray-500" />
          )}
          <span className={clsx(
            'text-sm font-medium',
            changeType === 'positive' && 'text-green-500',
            changeType === 'negative' && 'text-red-500',
            changeType === 'neutral' && 'text-gray-500'
          )}>
            {change}
          </span>
        </div>
      )}
    </div>
  )
}

