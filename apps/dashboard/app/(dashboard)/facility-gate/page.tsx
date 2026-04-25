"use client"

import { useMemo, useState } from "react"
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/empty-state"
import { useSardis, useSardisList } from "@/hooks/use-sardis"
import {
  CheckCircle,
  ClockCounterClockwise,
  Export,
  Eye,
  ShieldCheck,
  Siren,
  Warning,
  XCircle,
} from "@phosphor-icons/react"
import { toast } from "sonner"

type FacilityRequestState = {
  request_id?: string
  id?: string
  state?: string
  status?: string
  verdict?: string
  decision?: string
  agent_id?: string
  facility_id?: string
  mandate_id?: string
  merchant?: string | { name?: string; category?: string; merchant_id?: string }
  amount?: string | number
  currency?: string
  risk_tier?: string
  risk_score?: number
  created_at?: string
  updated_at?: string
  submitted_at?: string
}

type ManualReviewResponse = {
  requests?: FacilityRequestState[]
  items?: FacilityRequestState[]
}

type FacilityException = {
  event_id?: string
  id?: string
  severity?: string
  status?: string
}

type ExceptionsResponse = {
  exceptions?: FacilityException[]
  items?: FacilityException[]
}

type LimitsResponse = {
  limiter?: Record<string, unknown>
  limits?: Record<string, unknown>
  approval_fatigue?: Record<string, unknown>
}

const verdictVariant: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  approved: "default",
  denied: "destructive",
  rejected: "destructive",
  step_up_required: "secondary",
  pending: "outline",
  created: "outline",
  executed: "default",
  revoked: "destructive",
}

function requestId(request: FacilityRequestState) {
  return request.request_id || request.id || "unknown"
}

function requestVerdict(request: FacilityRequestState) {
  return request.verdict || request.decision || request.state || request.status || "pending"
}

function merchantLabel(merchant: FacilityRequestState["merchant"]) {
  if (!merchant) return "—"
  if (typeof merchant === "string") return merchant
  return merchant.name || merchant.merchant_id || "—"
}

function formatAmount(request: FacilityRequestState) {
  if (request.amount === undefined || request.amount === null) return "—"
  return `${request.currency || "USD"} ${request.amount}`
}

function formatTime(value?: string) {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

async function fetchJson(path: string, init: RequestInit = {}) {
  const response = await fetch(`/api/sardis/api/v2${path}`, {
    ...init,
    credentials: "include",
    cache: "no-store",
    headers: {
      "Accept": "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string; message?: string; error?: string } | null
    throw new Error(body?.detail || body?.message || body?.error || `Request failed with HTTP ${response.status}`)
  }
  return response.json() as Promise<unknown>
}

export default function FacilityGatePage() {
  const { data: requests, loading, error, refetch } = useSardisList<FacilityRequestState>(
    "api/v2/facility-requests",
    "Facility requests",
  )
  const { data: manualReview, refetch: refetchManualReview } = useSardis<ManualReviewResponse>(
    "api/v2/facility-requests/manual-review",
  )
  const { data: exceptionData, refetch: refetchExceptions } = useSardis<ExceptionsResponse>(
    "api/v2/facility-requests/exceptions",
  )
  const { data: limits } = useSardis<LimitsResponse>("api/v2/facility-requests/limits")
  const [busyRequestId, setBusyRequestId] = useState<string | null>(null)

  const manualReviewRequests = manualReview?.requests ?? manualReview?.items ?? []
  const exceptions = exceptionData?.exceptions ?? exceptionData?.items ?? []

  const stats = useMemo(() => {
    const rows = requests ?? []
    const approved = rows.filter((request) => requestVerdict(request).toLowerCase() === "approved").length
    const denied = rows.filter((request) => {
      const verdict = requestVerdict(request).toLowerCase()
      return verdict === "denied" || verdict === "rejected"
    }).length
    return [
      { label: "Requests", value: rows.length, icon: ShieldCheck },
      { label: "Manual Review", value: manualReviewRequests.length, icon: Warning },
      { label: "Approved", value: approved, icon: CheckCircle },
      { label: "Denied", value: denied, icon: XCircle },
      { label: "Exceptions", value: exceptions.length, icon: Siren },
    ]
  }, [requests, manualReviewRequests.length, exceptions.length])

  async function exportAudit(id: string) {
    setBusyRequestId(id)
    try {
      const payload = await fetchJson(`/facility-requests/${id}/audit/export`)
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2))
      toast.success("Audit export copied")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to export audit")
    } finally {
      setBusyRequestId(null)
    }
  }

  async function inspectAudit(id: string) {
    setBusyRequestId(id)
    try {
      const payload = await fetchJson(`/facility-requests/${id}/audit`)
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2))
      toast.success("Audit reconstruction copied")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to fetch audit")
    } finally {
      setBusyRequestId(null)
    }
  }

  async function revokeAgent(id: string, agentId?: string) {
    const target = agentId || window.prompt("Agent ID to revoke")
    if (!target) return
    setBusyRequestId(id)
    try {
      await fetchJson("/facility-requests/revocations", {
        method: "POST",
        body: JSON.stringify({
          scope: "agent",
          target_id: target,
          reason: `Revoked from Facility Gate dashboard for request ${id}`,
          idempotency_key: `dashboard_revoke_${target}_${Date.now()}`,
        }),
      })
      toast.success("Agent facility authority revoked")
      refetch()
      refetchManualReview()
      refetchExceptions()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to revoke")
    } finally {
      setBusyRequestId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Facility Gate</h1>
        <p className="text-sm text-muted-foreground">Programmable facility access, review, audit, and exception control</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label} size="sm">
              <CardContent className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                  <p className="text-lg font-semibold tracking-tight tabular-nums">{loading ? "—" : stat.value}</p>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Card>
        <CardHeader className="border-b">
          <div>
            <CardTitle>Facility Requests</CardTitle>
            <p className="text-sm text-muted-foreground">Decision state, review queue pressure, and audit export access</p>
          </div>
          <CardAction>
            <Button size="sm" variant="outline" onClick={refetch}>
              <ClockCounterClockwise className="h-4 w-4" />
              Refresh
            </Button>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
          {error ? (
            <EmptyState icon={Siren} title="Facility Gate unavailable" description={error} />
          ) : (requests ?? []).length === 0 ? (
            <EmptyState
              icon={ShieldCheck}
              title="No facility requests"
              description="Facility requests will appear here after agents submit delegated facility access requests"
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-4">Request</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Merchant</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Facility</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead className="pr-4 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(requests ?? []).map((request) => {
                  const id = requestId(request)
                  const verdict = requestVerdict(request).toLowerCase()
                  const busy = busyRequestId === id
                  return (
                    <TableRow key={id}>
                      <TableCell className="pl-4">
                        <Badge variant="outline" className="font-mono">{id}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={verdictVariant[verdict] ?? "outline"}>{verdict}</Badge>
                      </TableCell>
                      <TableCell className="max-w-[220px] truncate">{merchantLabel(request.merchant)}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{request.agent_id || "—"}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{request.facility_id || "—"}</TableCell>
                      <TableCell className="text-right font-medium tabular-nums">{formatAmount(request)}</TableCell>
                      <TableCell>
                        <span className="text-sm text-muted-foreground">
                          {request.risk_tier || (request.risk_score === undefined ? "—" : request.risk_score)}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{formatTime(request.updated_at || request.created_at || request.submitted_at)}</TableCell>
                      <TableCell className="pr-4">
                        <div className="flex justify-end gap-1.5">
                          <Button size="xs" variant="outline" disabled={busy} onClick={() => inspectAudit(id)}>
                            <Eye className="h-3.5 w-3.5" />
                            Audit
                          </Button>
                          <Button size="xs" variant="outline" disabled={busy} onClick={() => exportAudit(id)}>
                            <Export className="h-3.5 w-3.5" />
                            Export
                          </Button>
                          <Button size="xs" variant="destructive" disabled={busy} onClick={() => revokeAgent(id, request.agent_id)}>
                            Revoke
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Manual Review</CardTitle>
          </CardHeader>
          <CardContent className="px-0">
            {manualReviewRequests.length === 0 ? (
              <EmptyState icon={Warning} title="No requests waiting" description="Step-up decisions will appear here" />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-4">Request</TableHead>
                    <TableHead>Agent</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {manualReviewRequests.map((request) => (
                    <TableRow key={requestId(request)}>
                      <TableCell className="pl-4 font-mono text-xs">{requestId(request)}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{request.agent_id || "—"}</TableCell>
                      <TableCell className="text-right tabular-nums">{formatAmount(request)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle>Limiter Snapshot</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-56 overflow-auto rounded-md bg-muted p-3 text-xs text-muted-foreground">
              {JSON.stringify(limits ?? {}, null, 2)}
            </pre>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
