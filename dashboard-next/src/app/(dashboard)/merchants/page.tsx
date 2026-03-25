"use client";
import { useState } from 'react'
import Link from 'next/link'
import {
  Search,
  Store,
  ShieldCheck,
  BarChart3,
  DollarSign,
  ChevronDown,
  AlertCircle,
  Plus,
  Receipt,
  TrendingUp,
} from 'lucide-react'
import clsx from 'clsx'
import StatCard from '@/components/StatCard'
import { useMerchants, useMerchantSessions } from '@/hooks/useApi'

type TrustLevel = 'unknown' | 'low' | 'medium' | 'high' | 'verified'
type TrustFilter = 'all' | TrustLevel

interface MerchantRow {
  id: string
  name: string
  category: string
  trust_level: TrustLevel
  trust_score: number
  transaction_count: number
  volume: number
  dispute_rate: number
  first_seen: string
}

function toMerchantRow(m: any): MerchantRow {
  return {
    id: m.id || m.merchant_id || '',
    name: m.name || 'Unknown',
    category: m.category || m.description || 'Uncategorized',
    trust_level: m.trust_level || 'unknown',
    trust_score: m.trust_score ?? 0,
    transaction_count: m.transaction_count ?? 0,
    volume: m.volume ?? m.total_volume ?? 0,
    dispute_rate: m.dispute_rate ?? 0,
    first_seen: m.first_seen || m.created_at || new Date().toISOString(),
  }
}

const TRUST_LEVEL_CONFIG: Record<TrustLevel, { label: string; color: string; bg: string }> = {
  unknown: { label: 'Unknown', color: 'text-gray-400', bg: 'bg-gray-500/10' },
  low: { label: 'Low', color: 'text-red-400', bg: 'bg-red-500/10' },
  medium: { label: 'Medium', color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  high: { label: 'High', color: 'text-green-400', bg: 'bg-green-500/10' },
  verified: { label: 'Verified', color: 'text-sardis-400', bg: 'bg-sardis-500/10' },
}

function formatVolume(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`
  if (v >= 1_000) return `$${(v / 1_000).toFixed(1)}K`
  return `$${v.toFixed(2)}`
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function SkeletonRow() {
  return (
    <tr className="border-b border-dark-100">
      {Array.from({ length: 8 }).map((_, i) => (
        <td key={i} className="px-6 py-4">
          <div className="h-4 bg-dark-200 animate-pulse rounded w-3/4" />
        </td>
      ))}
    </tr>
  )
}

export default function MerchantsPage() {
  const [search, setSearch] = useState('')
  const [trustFilter, setTrustFilter] = useState<TrustFilter>('all')
  const [filterOpen, setFilterOpen] = useState(false)
  const [selectedMerchantId, setSelectedMerchantId] = useState<string | null>(null)

  const { data: rawMerchants, isLoading, error } = useMerchants()
  const { data: sessions, isLoading: sessionsLoading } = useMerchantSessions(selectedMerchantId)

  const merchants: MerchantRow[] = Array.isArray(rawMerchants)
    ? rawMerchants.map(toMerchantRow)
    : []

  const filtered = merchants.filter((m) => {
    const matchesSearch = m.name.toLowerCase().includes(search.toLowerCase())
    const matchesTrust = trustFilter === 'all' || m.trust_level === trustFilter
    return matchesSearch && matchesTrust
  })

  const totalVolume = merchants.reduce((sum, m) => sum + m.volume, 0)
  const verifiedCount = merchants.filter((m) => m.trust_level === 'verified').length
  const avgTrustScore =
    merchants.length > 0
      ? Math.round(merchants.reduce((sum, m) => sum + m.trust_score, 0) / merchants.length)
      : 0

  // Checkout session stats
  const sessionList = Array.isArray(sessions) ? sessions : []
  const totalRevenue = sessionList
    .filter(s => s.status === 'paid')
    .reduce((sum, s) => sum + parseFloat(s.amount || '0'), 0)
  const conversionRate = sessionList.length > 0
    ? (sessionList.filter(s => s.status === 'paid').length / sessionList.length * 100).toFixed(1)
    : '0.0'
  const avgOrderValue = sessionList.filter(s => s.status === 'paid').length > 0
    ? (totalRevenue / sessionList.filter(s => s.status === 'paid').length).toFixed(2)
    : '0.00'

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Merchant Dashboard</h1>
          <p className="text-gray-400 mt-1">
            Manage your Pay with Sardis merchants and track checkout sessions
          </p>
        </div>
        <Link
          href="/merchants/setup"
          className="flex items-center gap-2 px-5 py-2.5 bg-sardis-500 text-white font-medium hover:bg-sardis-400 transition-colors text-sm"
        >
          <Plus className="w-4 h-4" />
          New Merchant
        </Link>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Merchants"
          value={isLoading ? '—' : merchants.length}
          icon={<Store className="w-5 h-5" />}
          change="+3 this month"
          changeType="positive"
        />
        <StatCard
          title="Verified Merchants"
          value={isLoading ? '—' : verifiedCount}
          icon={<ShieldCheck className="w-5 h-5" />}
          subtitle={
            !isLoading && merchants.length > 0
              ? `${Math.round((verifiedCount / merchants.length) * 100)}% of total`
              : undefined
          }
        />
        <StatCard
          title="Avg Trust Score"
          value={isLoading ? '—' : avgTrustScore}
          icon={<BarChart3 className="w-5 h-5" />}
          change="+4 vs last month"
          changeType="positive"
        />
        <StatCard
          title="Total Volume"
          value={isLoading ? '—' : formatVolume(totalVolume)}
          icon={<DollarSign className="w-5 h-5" />}
          change="+12.3%"
          changeType="positive"
        />
      </div>

      {/* Error state — show as empty rather than alarming error */}
      {error && !isLoading && merchants.length === 0 && (
        <div className="card p-8 text-center">
          <Store className="w-10 h-10 text-gray-600 mx-auto mb-3" />
          <h3 className="text-base font-medium text-white mb-1">No merchants yet</h3>
          <p className="text-sm text-gray-400">
            Merchant profiles will appear here once you start processing payments or set up a merchant.
          </p>
          <Link
            href="/merchants/setup"
            className="inline-flex items-center gap-2 mt-4 px-5 py-2.5 bg-sardis-500 text-white font-medium hover:bg-sardis-400 transition-colors text-sm"
          >
            <Plus className="w-4 h-4" />
            Set Up Your First Merchant
          </Link>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            placeholder="Search merchants..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-dark-200 border border-dark-100 text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50"
          />
        </div>

        {/* Trust Level Dropdown */}
        <div className="relative">
          <button
            onClick={() => setFilterOpen(!filterOpen)}
            className="flex items-center gap-2 px-4 py-3 bg-dark-200 border border-dark-100 text-gray-300 hover:border-sardis-500/50 transition-colors min-w-[180px] justify-between"
          >
            <span className="text-sm">
              {trustFilter === 'all'
                ? 'All Trust Levels'
                : TRUST_LEVEL_CONFIG[trustFilter].label}
            </span>
            <ChevronDown className={clsx('w-4 h-4 transition-transform', filterOpen && 'rotate-180')} />
          </button>
          {filterOpen && (
            <div className="absolute right-0 mt-1 w-full bg-dark-300 border border-dark-100 z-10 shadow-lg">
              {(['all', 'unknown', 'low', 'medium', 'high', 'verified'] as TrustFilter[]).map(
                (level) => (
                  <button
                    key={level}
                    onClick={() => {
                      setTrustFilter(level)
                      setFilterOpen(false)
                    }}
                    className={clsx(
                      'w-full text-left px-4 py-2.5 text-sm hover:bg-dark-200 transition-colors',
                      trustFilter === level ? 'text-sardis-400' : 'text-gray-300'
                    )}
                  >
                    {level === 'all' ? 'All Trust Levels' : TRUST_LEVEL_CONFIG[level].label}
                  </button>
                )
              )}
            </div>
          )}
        </div>
      </div>

      {/* Merchants Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-dark-300">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Category
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Trust Level
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Trust Score
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Transactions
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Volume
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Dispute Rate
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                First Seen
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-100">
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
              : filtered.map((merchant) => {
                  const cfg = TRUST_LEVEL_CONFIG[merchant.trust_level]
                  return (
                    <tr
                      key={merchant.id}
                      onClick={() => setSelectedMerchantId(merchant.id || null)}
                      className={clsx(
                        'hover:bg-dark-200/50 transition-colors cursor-pointer',
                        selectedMerchantId === merchant.id && 'bg-sardis-500/5 border-l-2 border-l-sardis-500'
                      )}
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-sardis-500/10 flex items-center justify-center">
                            <Store className="w-4 h-4 text-sardis-400" />
                          </div>
                          <span className="text-sm font-medium text-white">{merchant.name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-400">{merchant.category}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={clsx(
                            'inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium',
                            cfg.bg,
                            cfg.color
                          )}
                        >
                          <div
                            className={clsx(
                              'w-1.5 h-1.5 rounded-full',
                              merchant.trust_level === 'verified' && 'bg-sardis-400',
                              merchant.trust_level === 'high' && 'bg-green-400',
                              merchant.trust_level === 'medium' && 'bg-yellow-400',
                              merchant.trust_level === 'low' && 'bg-red-400',
                              merchant.trust_level === 'unknown' && 'bg-gray-400'
                            )}
                          />
                          {cfg.label}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-medium text-white mono-numbers w-8">
                            {merchant.trust_score}
                          </span>
                          <div className="w-20 h-1.5 bg-dark-100 overflow-hidden">
                            <div
                              className={clsx(
                                'h-full transition-all',
                                merchant.trust_score >= 90 && 'bg-sardis-400',
                                merchant.trust_score >= 70 && merchant.trust_score < 90 && 'bg-green-400',
                                merchant.trust_score >= 40 && merchant.trust_score < 70 && 'bg-yellow-400',
                                merchant.trust_score >= 1 && merchant.trust_score < 40 && 'bg-red-400',
                                merchant.trust_score === 0 && 'bg-gray-500'
                              )}
                              style={{ width: `${merchant.trust_score}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-white mono-numbers">
                          {merchant.transaction_count.toLocaleString()}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-white mono-numbers">
                          {formatVolume(merchant.volume)}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={clsx(
                            'text-sm mono-numbers',
                            merchant.dispute_rate === 0 && 'text-green-400',
                            merchant.dispute_rate > 0 && merchant.dispute_rate <= 0.01 && 'text-gray-400',
                            merchant.dispute_rate > 0.01 && merchant.dispute_rate <= 0.05 && 'text-yellow-400',
                            merchant.dispute_rate > 0.05 && 'text-red-400'
                          )}
                        >
                          {(merchant.dispute_rate * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-400">{formatDate(merchant.first_seen)}</span>
                      </td>
                    </tr>
                  )
                })}
          </tbody>
        </table>

        {!isLoading && filtered.length === 0 && (
          <div className="p-12 text-center">
            <Store className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No merchants found</h3>
            <p className="text-gray-400">
              {search || trustFilter !== 'all'
                ? 'Try adjusting your search or filter'
                : 'Merchant profiles will appear once transactions are processed'}
            </p>
            <Link
              href="/merchants/setup"
              className="inline-flex items-center gap-2 mt-4 px-5 py-2.5 bg-sardis-500 text-white font-medium hover:bg-sardis-400 transition-colors text-sm"
            >
              <Plus className="w-4 h-4" />
              Set Up Your First Merchant
            </Link>
          </div>
        )}
      </div>

      {/* Checkout Sessions Panel */}
      {selectedMerchantId && (
        <div className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Checkout Sessions</h2>
            <p className="text-gray-400 text-sm mt-1">
              Payment sessions for selected merchant
            </p>
          </div>

          {/* Session Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard
              title="Revenue"
              value={sessionsLoading ? '---' : `$${totalRevenue.toFixed(2)}`}
              icon={<DollarSign className="w-5 h-5" />}
            />
            <StatCard
              title="Conversion Rate"
              value={sessionsLoading ? '---' : `${conversionRate}%`}
              icon={<TrendingUp className="w-5 h-5" />}
            />
            <StatCard
              title="Avg Order Value"
              value={sessionsLoading ? '---' : `$${avgOrderValue}`}
              icon={<Receipt className="w-5 h-5" />}
            />
          </div>

          {/* Session List */}
          <div className="card overflow-hidden">
            <table className="w-full">
              <thead className="bg-dark-300">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Session ID
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Currency
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Settlement
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-100">
                {sessionsLoading ? (
                  Array.from({ length: 3 }).map((_, i) => (
                    <tr key={i} className="border-b border-dark-100">
                      {Array.from({ length: 6 }).map((_, j) => (
                        <td key={j} className="px-6 py-4">
                          <div className="h-4 bg-dark-200 animate-pulse rounded w-3/4" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : sessionList.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center">
                      <Receipt className="w-10 h-10 text-gray-600 mx-auto mb-3" />
                      <p className="text-gray-400">No checkout sessions yet</p>
                    </td>
                  </tr>
                ) : (
                  sessionList.map((session) => (
                    <tr key={session.session_id} className="hover:bg-dark-200/50 transition-colors">
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-300 font-mono">
                          {session.session_id.substring(0, 12)}...
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-white mono-numbers">
                          ${parseFloat(session.amount).toFixed(2)}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-400">{session.currency}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={clsx(
                            'inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium',
                            session.status === 'paid' && 'bg-green-500/10 text-green-400',
                            session.status === 'pending' && 'bg-yellow-500/10 text-yellow-400',
                            session.status === 'expired' && 'bg-red-500/10 text-red-400',
                            !['paid', 'pending', 'expired'].includes(session.status) && 'bg-gray-500/10 text-gray-400'
                          )}
                        >
                          {session.status}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={clsx(
                            'text-sm',
                            session.settlement_status === 'settled' ? 'text-green-400' : 'text-gray-500'
                          )}
                        >
                          {session.settlement_status || '---'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-400">
                          {formatDate(session.created_at)}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
