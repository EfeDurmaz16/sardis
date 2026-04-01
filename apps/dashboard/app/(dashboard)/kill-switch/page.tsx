"use client"

import { useState, useMemo } from "react"
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
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import {
  Power,
  ShieldCheck,
  Clock,
  Lightning,
  CurrencyDollar,
  Target,
  Pause,
  Prohibit,
  Wallet,
  Key,
  Spinner,
} from "@phosphor-icons/react"
import { toast } from "sonner"
import { useSardis } from "@/hooks/use-sardis"

type HistoryEntry = {
  activatedBy: string
  reason: string
  duration: string
  transactionsBlocked: number
  activatedAt: string
}

type KillSwitchStatus = {
  active: boolean
  lastActivated: string | null
  totalActivations: number
  protectedVolume: string
  history: HistoryEntry[]
  quickActions?: { label: string; description: string; icon: string; active: boolean }[]
}

const quickActionDefs = [
  {
    label: "Pause All Payments",
    description: "Immediately halt all outgoing payment processing",
    icon: Pause,
  },
  {
    label: "Block New Agents",
    description: "Prevent new agent registrations and activations",
    icon: Prohibit,
  },
  {
    label: "Freeze Wallets",
    description: "Lock all wallet balances and prevent transfers",
    icon: Wallet,
  },
  {
    label: "Disable API Access",
    description: "Revoke all active API keys and block new requests",
    icon: Key,
  },
]

export default function KillSwitchPage() {
  const { data: status, loading, refetch } = useSardis<KillSwitchStatus>("api/v2/guardrails/kill-switch/status")

  const [active, setActive] = useState<boolean | null>(null)
  const [toggles, setToggles] = useState<Record<string, boolean>>({})

  const isActive = active ?? status?.active ?? false
  const history = status?.history ?? []

  const stats = useMemo(() => {
    const lastActivated = status?.lastActivated ?? "Never"
    const totalActivations = status?.totalActivations ?? 0
    const protectedVolume = status?.protectedVolume ?? "$0"

    return [
      { label: "Last Activated", value: lastActivated, icon: Clock },
      { label: "Total Activations", value: String(totalActivations), icon: Lightning },
      { label: "Protected Volume", value: protectedVolume, icon: CurrencyDollar },
      { label: "Coverage", value: "100%", icon: Target },
    ]
  }, [status])

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Kill Switch</h1>
          <p className="text-sm text-muted-foreground">Emergency controls to halt all system operations</p>
        </div>
        <div className="flex items-center justify-center py-16">
          <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Kill Switch</h1>
        <p className="text-sm text-muted-foreground">Emergency controls to halt all system operations</p>
      </div>

      {/* Status Card */}
      <Card>
        <CardContent className="flex flex-col items-center gap-4 py-8 text-center">
          <div className={`flex h-16 w-16 items-center justify-center rounded-full ${isActive ? "bg-destructive/10" : "bg-success/10"}`}>
            <Power className={`h-8 w-8 ${isActive ? "text-destructive" : "text-success"}`} weight="bold" />
          </div>
          <div>
            <div className="flex items-center justify-center gap-2 mb-1">
              <h2 className="text-lg font-semibold">Kill Switch Status</h2>
              <Badge variant={isActive ? "destructive" : "success"}>
                {isActive ? "ACTIVE" : "INACTIVE"}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {isActive ? "Emergency shutdown is active -- all operations halted" : "All systems operational"}
            </p>
          </div>
          <Button
            variant={isActive ? "outline" : "destructive"}
            size="lg"
            onClick={async () => {
              try {
                const endpoint = isActive ? "deactivate" : "activate"
                const res = await fetch(`/api/sardis/api/v2/admin/kill-switch/${endpoint}`, {
                  method: "POST",
                })
                if (!res.ok) throw new Error("Failed")
                setActive(!isActive)
                toast.success(isActive ? "Kill switch deactivated" : "Kill switch activated")
                refetch()
              } catch {
                toast.error("Failed to toggle kill switch")
              }
            }}
          >
            <Power className="h-4 w-4" weight="bold" />
            {isActive ? "Deactivate Kill Switch" : "Activate Kill Switch"}
          </Button>
        </CardContent>
      </Card>

      {/* Stats */}
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* History */}
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Kill Switch History</CardTitle>
          </CardHeader>
          <CardContent className="px-0">
            {history.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <ShieldCheck className="h-10 w-10 text-muted-foreground/40 mb-3" />
                <p className="text-sm font-medium text-muted-foreground">No activations recorded</p>
                <p className="text-xs text-muted-foreground/60 mt-1">The kill switch has never been activated</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-4">Activated By</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead className="text-right">Txns Blocked</TableHead>
                    <TableHead>Activated At</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.map((entry, i) => (
                    <TableRow key={i}>
                      <TableCell className="pl-4 font-medium">{entry.activatedBy}</TableCell>
                      <TableCell className="text-muted-foreground">{entry.reason}</TableCell>
                      <TableCell>{entry.duration}</TableCell>
                      <TableCell className="text-right tabular-nums">{entry.transactionsBlocked}</TableCell>
                      <TableCell className="text-muted-foreground">{entry.activatedAt}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="divide-y">
            {quickActionDefs.map((action) => {
              const Ico = action.icon
              const actionActive = toggles[action.label] ?? false
              return (
                <ContextMenu key={action.label}>
                  <ContextMenuTrigger>
                    <div className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                          <Ico className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">{action.label}</p>
                          <p className="text-xs text-muted-foreground">{action.description}</p>
                        </div>
                      </div>
                      <Switch
                        checked={actionActive}
                        onCheckedChange={(checked: boolean) =>
                          setToggles((prev) => ({ ...prev, [action.label]: checked }))
                        }
                      />
                    </div>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => { setToggles((prev) => ({ ...prev, [action.label]: true })); toast.success("Activated") }}>
                      Activate
                    </ContextMenuItem>
                    <ContextMenuItem onClick={() => { setToggles((prev) => ({ ...prev, [action.label]: false })); toast.success("Deactivated") }}>
                      Deactivate
                    </ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              )
            })}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
