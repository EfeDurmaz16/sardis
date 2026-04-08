"use client"

import { useMemo } from "react"
import {
  Card,
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
import {
  Users,
  CheckCircle,
  CurrencyDollar,
  Terminal,
  Spinner,
} from "@phosphor-icons/react"
import { useSardisList } from "@/hooks/use-sardis"
import { EmptyState } from "@/components/empty-state"

type MppSession = {
  id: string
  participants: number
  total_amount: string
  chain: string
  status: "active" | "pending" | "completed" | "failed"
  created: string
  duration: string
}

const statusConfig: Record<MppSession["status"], { variant: "success" | "warning" | "secondary" | "destructive" }> = {
  active: { variant: "success" },
  pending: { variant: "warning" },
  completed: { variant: "secondary" },
  failed: { variant: "destructive" },
}

const chainVariant: Record<string, "default" | "secondary" | "outline"> = {
  Ethereum: "default",
  Polygon: "secondary",
  Arbitrum: "outline",
  Optimism: "secondary",
}

function parseAmount(raw: string): number {
  return parseFloat(raw.replace(/[^0-9.]/g, "")) || 0
}

export default function MppSessionsPage() {
  const { data, loading, error, refetch } = useSardisList<MppSession>("api/v2/mpp/sessions", "MPP sessions")

  const sessions = data ?? []

  const stats = useMemo(() => {
    const active = sessions.filter(s => s.status === "active").length
    const completed = sessions.filter(s => s.status === "completed").length
    const avgParticipants = sessions.length > 0
      ? (sessions.reduce((sum, s) => sum + s.participants, 0) / sessions.length).toFixed(1)
      : "0"
    const totalVolume = sessions.reduce((sum, s) => sum + parseAmount(s.total_amount), 0)
    const volumeLabel = totalVolume >= 1000 ? `$${(totalVolume / 1000).toFixed(0)}k` : `$${totalVolume.toLocaleString()}`
    return [
      { label: "Active Sessions", value: String(active), icon: Terminal },
      { label: "Completed Today", value: String(completed), icon: CheckCircle },
      { label: "Avg Participants", value: avgParticipants, icon: Users },
      { label: "Total Volume", value: volumeLabel, icon: CurrencyDollar },
    ]
  }, [sessions])

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">MPP Sessions</h1>
          <p className="text-sm text-muted-foreground">Multi-party payment sessions across chains</p>
        </div>
        <div className="flex items-center justify-center py-16">
          <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">MPP Sessions</h1>
          <p className="text-sm text-muted-foreground">Multi-party payment sessions across chains</p>
        </div>
        <EmptyState
          icon={Terminal}
          title="MPP sessions unavailable"
          description={error || "Multi-party payment sessions will appear here once MPP flows are initiated."}
          action={refetch}
          actionLabel="Retry"
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">MPP Sessions</h1>
        <p className="text-sm text-muted-foreground">Multi-party payment sessions across chains</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => {
          const Ico = s.icon
          return (
            <Card key={s.label} size="sm">
              <CardContent className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                  <Ico className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{s.label}</p>
                  <p className="text-lg font-semibold tracking-tight tabular-nums">{s.value}</p>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle>All Sessions</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {sessions.length === 0 ? (
            <EmptyState
              icon={Terminal}
              title="No sessions"
              description="MPP sessions will appear here once multi-party payment flows are created."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-4">Session ID</TableHead>
                  <TableHead className="text-right">Participants</TableHead>
                  <TableHead className="text-right">Total Amount</TableHead>
                  <TableHead>Chain</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Duration</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.map((session) => {
                  const st = statusConfig[session.status]
                  return (
                    <TableRow key={session.id}>
                      <TableCell className="pl-4 font-mono text-xs">{session.id}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        <Badge variant="outline">{session.participants}</Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-medium">{session.total_amount}</TableCell>
                      <TableCell>
                        <Badge variant={chainVariant[session.chain] ?? "outline"}>{session.chain}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={st.variant}>
                          {session.status.charAt(0).toUpperCase() + session.status.slice(1)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{session.created}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{session.duration}</TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
