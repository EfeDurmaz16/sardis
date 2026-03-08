import { useState } from 'react'
import {
  Search,
  Store,
  ShieldCheck,
  BarChart3,
  DollarSign,
  ChevronDown,
} from 'lucide-react'
import clsx from 'clsx'
import StatCard from '../components/StatCard'

type TrustLevel = 'unknown' | 'low' | 'medium' | 'high' | 'verified'
type TrustFilter = 'all' | TrustLevel

interface Merchant {
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

const MOCK_MERCHANTS: Merchant[] = [
  {
    id: 'mrc_001',
    name: 'OpenAI',
    category: 'AI / API Services',
    trust_level: 'verified',
    trust_score: 98,
    transaction_count: 1247,
    volume: 84320.5,
    dispute_rate: 0.001,
    first_seen: '2025-06-12',
  },
  {
    id: 'mrc_002',
    name: 'Anthropic',
    category: 'AI / API Services',
    trust_level: 'verified',
    trust_score: 97,
    transaction_count: 893,
    volume: 62150.0,
    dispute_rate: 0.0,
    first_seen: '2025-07-03',
  },
  {
    id: 'mrc_003',
    name: 'AWS',
    category: 'Cloud Infrastructure',
    trust_level: 'high',
    trust_score: 91,
    transaction_count: 534,
    volume: 127840.25,
    dispute_rate: 0.004,
    first_seen: '2025-08-15',
  },
  {
    id: 'mrc_004',
    name: 'Hetzner',
    category: 'Cloud Infrastructure',
    trust_level: 'high',
    trust_score: 85,
    transaction_count: 312,
    volume: 18490.0,
    dispute_rate: 0.003,
    first_seen: '2025-09-22',
  },
  {
    id: 'mrc_005',
    name: 'Vercel',
    category: 'Cloud Infrastructure',
    trust_level: 'high',
    trust_score: 88,
    transaction_count: 178,
    volume: 9840.0,
    dispute_rate: 0.0,
    first_seen: '2025-10-01',
  },
  {
    id: 'mrc_006',
    name: 'Fiverr',
    category: 'Freelance Services',
    trust_level: 'medium',
    trust_score: 62,
    transaction_count: 89,
    volume: 4320.75,
    dispute_rate: 0.034,
    first_seen: '2025-11-10',
  },
  {
    id: 'mrc_007',
    name: 'Unknown SaaS Co',
    category: 'Software',
    trust_level: 'low',
    trust_score: 28,
    transaction_count: 12,
    volume: 890.0,
    dispute_rate: 0.083,
    first_seen: '2026-01-18',
  },
  {
    id: 'mrc_008',
    name: 'New Vendor LLC',
    category: 'Uncategorized',
    trust_level: 'unknown',
    trust_score: 0,
    transaction_count: 2,
    volume: 150.0,
    dispute_rate: 0.0,
    first_seen: '2026-03-01',
  },
]

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

export default function MerchantsPage() {
  const [search, setSearch] = useState('')
  const [trustFilter, setTrustFilter] = useState<TrustFilter>('all')
  const [filterOpen, setFilterOpen] = useState(false)

  const merchants = MOCK_MERCHANTS

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

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Merchant Analytics</h1>
        <p className="text-gray-400 mt-1">
          Trust profiles and transaction analytics for merchant counterparties
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Merchants"
          value={merchants.length}
          icon={<Store className="w-5 h-5" />}
          change="+3 this month"
          changeType="positive"
        />
        <StatCard
          title="Verified Merchants"
          value={verifiedCount}
          icon={<ShieldCheck className="w-5 h-5" />}
          subtitle={`${Math.round((verifiedCount / merchants.length) * 100)}% of total`}
        />
        <StatCard
          title="Avg Trust Score"
          value={avgTrustScore}
          icon={<BarChart3 className="w-5 h-5" />}
          change="+4 vs last month"
          changeType="positive"
        />
        <StatCard
          title="Total Volume"
          value={formatVolume(totalVolume)}
          icon={<DollarSign className="w-5 h-5" />}
          change="+12.3%"
          changeType="positive"
        />
      </div>

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
            {filtered.map((merchant) => {
              const cfg = TRUST_LEVEL_CONFIG[merchant.trust_level]
              return (
                <tr key={merchant.id} className="hover:bg-dark-200/50 transition-colors">
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

        {filtered.length === 0 && (
          <div className="p-12 text-center">
            <Store className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No merchants found</h3>
            <p className="text-gray-400">
              {search || trustFilter !== 'all'
                ? 'Try adjusting your search or filter'
                : 'Merchant profiles will appear once transactions are processed'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
