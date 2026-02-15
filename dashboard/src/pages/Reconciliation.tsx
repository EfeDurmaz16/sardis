import { useMemo, useState } from 'react'
import { AlertTriangle, Download, RefreshCw, ShieldAlert } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { treasuryOpsApi } from '../api/client'

type Dict = Record<string, unknown>

function asText(value: unknown): string {
  if (value === null || value === undefined) return ''
  return String(value)
}

function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function ReconciliationPage() {
  const queryClient = useQueryClient()
  const [journeyIdForExport, setJourneyIdForExport] = useState('')
  const [reviewFilter, setReviewFilter] = useState('queued')
  const [stateFilter, setStateFilter] = useState('')
  const [breakFilter, setBreakFilter] = useState('')

  const journeysQuery = useQuery({
    queryKey: ['ops-journeys', stateFilter, breakFilter],
    queryFn: () => treasuryOpsApi.listJourneys({
      canonical_state: stateFilter || undefined,
      break_status: breakFilter || undefined,
      limit: 200,
    }),
  })

  const driftQuery = useQuery({
    queryKey: ['ops-drift'],
    queryFn: () => treasuryOpsApi.listDrift('open', 200),
  })

  const returnsQuery = useQuery({
    queryKey: ['ops-returns'],
    queryFn: () => treasuryOpsApi.listReturns('R01,R09,R29', 200),
  })

  const reviewsQuery = useQuery({
    queryKey: ['ops-manual-reviews', reviewFilter],
    queryFn: () => treasuryOpsApi.listManualReviews(reviewFilter, 200),
  })

  const resolveReview = useMutation({
    mutationFn: ({ reviewId, status }: { reviewId: string; status: 'resolved' | 'dismissed' | 'in_review' }) =>
      treasuryOpsApi.resolveManualReview(reviewId, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ops-manual-reviews'] })
      queryClient.invalidateQueries({ queryKey: ['ops-journeys'] })
      queryClient.invalidateQueries({ queryKey: ['ops-drift'] })
    },
  })

  const loading = journeysQuery.isLoading || driftQuery.isLoading || returnsQuery.isLoading || reviewsQuery.isLoading
  const journeys = (journeysQuery.data?.items || []) as Dict[]
  const driftItems = (driftQuery.data?.items || []) as Dict[]
  const returnItems = (returnsQuery.data?.items || []) as Dict[]
  const manualReviews = (reviewsQuery.data?.items || []) as Dict[]

  const highRiskCount = useMemo(
    () => returnItems.filter((x) => asText(x.last_return_code) === 'R29').length,
    [returnItems]
  )

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Reconciliation Ops</h1>
          <p className="text-gray-400 mt-1">
            Canonical cross-rail state machine, drift detection, return-code handling, and manual reviews.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: ['ops-journeys'] })
              queryClient.invalidateQueries({ queryKey: ['ops-drift'] })
              queryClient.invalidateQueries({ queryKey: ['ops-returns'] })
              queryClient.invalidateQueries({ queryKey: ['ops-manual-reviews'] })
            }}
            className="inline-flex items-center gap-2 px-3 py-2 bg-dark-200 border border-dark-100 rounded-lg text-gray-200 hover:text-white hover:border-sardis-500/40"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={async () => {
              const data = await treasuryOpsApi.exportAuditEvidence(journeyIdForExport || undefined, 1000)
              downloadJson('sardis-audit-evidence.json', data)
            }}
            className="inline-flex items-center gap-2 px-3 py-2 bg-sardis-500/10 border border-sardis-500/30 rounded-lg text-sardis-300 hover:bg-sardis-500/20"
          >
            <Download className="w-4 h-4" />
            Export Evidence
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="text-sm text-gray-400">Journeys</p>
          <p className="text-2xl font-semibold text-white mt-1">{journeys.length}</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Open Drift Breaks</p>
          <p className="text-2xl font-semibold text-yellow-400 mt-1">{driftItems.length}</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Manual Reviews</p>
          <p className="text-2xl font-semibold text-orange-400 mt-1">{manualReviews.length}</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">High Risk Returns (R29)</p>
          <p className="text-2xl font-semibold text-red-400 mt-1">{highRiskCount}</p>
        </div>
      </div>

      <div className="card p-4 space-y-3">
        <div className="flex flex-wrap gap-3 items-end">
          <label className="text-sm text-gray-400">
            Journey state
            <select
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              className="ml-2 px-2 py-1 bg-dark-300 border border-dark-100 rounded text-sm text-white"
            >
              <option value="">all</option>
              <option value="created">created</option>
              <option value="authorized">authorized</option>
              <option value="processing">processing</option>
              <option value="settled">settled</option>
              <option value="returned">returned</option>
              <option value="failed">failed</option>
            </select>
          </label>
          <label className="text-sm text-gray-400">
            Break status
            <select
              value={breakFilter}
              onChange={(e) => setBreakFilter(e.target.value)}
              className="ml-2 px-2 py-1 bg-dark-300 border border-dark-100 rounded text-sm text-white"
            >
              <option value="">all</option>
              <option value="ok">ok</option>
              <option value="drift_open">drift_open</option>
              <option value="review_open">review_open</option>
              <option value="resolved">resolved</option>
            </select>
          </label>
          <label className="text-sm text-gray-400">
            Export journey id
            <input
              value={journeyIdForExport}
              onChange={(e) => setJourneyIdForExport(e.target.value)}
              placeholder="optional"
              className="ml-2 px-2 py-1 bg-dark-300 border border-dark-100 rounded text-sm text-white"
            />
          </label>
        </div>
      </div>

      <div className="card p-4">
        <h2 className="text-lg font-semibold text-white mb-3">Manual Review Queue</h2>
        <div className="mb-3">
          <select
            value={reviewFilter}
            onChange={(e) => setReviewFilter(e.target.value)}
            className="px-2 py-1 bg-dark-300 border border-dark-100 rounded text-sm text-white"
          >
            <option value="queued">queued</option>
            <option value="in_review">in_review</option>
            <option value="resolved">resolved</option>
            <option value="dismissed">dismissed</option>
          </select>
        </div>
        <div className="space-y-2">
          {manualReviews.length === 0 ? (
            <p className="text-sm text-gray-400">No manual reviews in this filter.</p>
          ) : (
            manualReviews.map((item) => {
              const reviewId = asText(item.review_id)
              return (
                <div key={reviewId} className="p-3 bg-dark-200 border border-dark-100 rounded-lg flex items-center justify-between gap-2">
                  <div>
                    <p className="text-sm text-white font-medium">{asText(item.reason_code)} · {asText(item.priority)}</p>
                    <p className="text-xs text-gray-400">review_id: {reviewId}</p>
                    <p className="text-xs text-gray-400">journey: {asText(item.journey_id)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => resolveReview.mutate({ reviewId, status: 'in_review' })}
                      className="px-2 py-1 text-xs rounded bg-dark-300 border border-dark-100 text-gray-200 hover:text-white"
                    >
                      In Review
                    </button>
                    <button
                      onClick={() => resolveReview.mutate({ reviewId, status: 'resolved' })}
                      className="px-2 py-1 text-xs rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300"
                    >
                      Resolve
                    </button>
                    <button
                      onClick={() => resolveReview.mutate({ reviewId, status: 'dismissed' })}
                      className="px-2 py-1 text-xs rounded bg-red-500/10 border border-red-500/30 text-red-300"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-4">
          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-400" />
            Drift Breaks
          </h2>
          <div className="space-y-2 max-h-[420px] overflow-auto">
            {driftItems.length === 0 ? (
              <p className="text-sm text-gray-400">No open drift breaks.</p>
            ) : (
              driftItems.map((item) => (
                <div key={asText(item.break_id)} className="p-3 bg-dark-200 border border-dark-100 rounded-lg">
                  <p className="text-sm text-white">{asText(item.break_type)} · {asText(item.severity)}</p>
                  <p className="text-xs text-gray-400">journey: {asText(item.journey_id)}</p>
                  <p className="text-xs text-gray-400">delta_minor: {asText(item.delta_minor)}</p>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="card p-4">
          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-400" />
            ACH Return Codes
          </h2>
          <div className="space-y-2 max-h-[420px] overflow-auto">
            {returnItems.length === 0 ? (
              <p className="text-sm text-gray-400">No return-code journeys.</p>
            ) : (
              returnItems.map((item) => (
                <div key={asText(item.journey_id)} className="p-3 bg-dark-200 border border-dark-100 rounded-lg">
                  <p className="text-sm text-white">
                    {asText(item.last_return_code)} · {asText(item.canonical_state)}
                  </p>
                  <p className="text-xs text-gray-400">journey: {asText(item.journey_id)}</p>
                  <p className="text-xs text-gray-400">reference: {asText(item.external_reference)}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {loading && (
        <p className="text-sm text-gray-400">Loading reconciliation data...</p>
      )}
    </div>
  )
}

