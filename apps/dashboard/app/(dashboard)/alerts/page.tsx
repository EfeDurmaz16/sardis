"use client"

import { useState, useMemo } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardAction,
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
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog"
import {
  Bell,
  Lightning,
  Broadcast,
  SpeakerSimpleSlash,
  Plus,
  Spinner,
} from "@phosphor-icons/react"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"
import { useSardisList } from "@/hooks/use-sardis"

type AlertRule = {
  id: string
  name: string
  condition: string
  channel: string
  severity: string
  last_triggered: string | null
  active: boolean
}

const channelVariant: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  Email: "outline",
  Slack: "outline",
  Webhook: "outline",
  SMS: "outline",
}

const severityColor: Record<string, string> = {
  Critical: "bg-destructive",
  critical: "bg-destructive",
  Warning: "bg-warning",
  warning: "bg-warning",
  Info: "bg-info",
  info: "bg-info",
}

const conditionLabels: Record<string, string> = {
  spend_exceeds: "Spend exceeds threshold",
  tx_count: "Transaction count exceeds threshold",
  agent_inactive: "Agent inactive for threshold minutes",
}

export default function AlertsPage() {
  const { data: alertRules, loading, refetch } = useSardisList<AlertRule>("api/v2/alerts", "Alerts")
  const alerts = alertRules ?? []

  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newCondition, setNewCondition] = useState("spend_exceeds")
  const [newThreshold, setNewThreshold] = useState("")
  const [newSeverity, setNewSeverity] = useState("Warning")

  // Compute stats from real data
  const stats = useMemo(() => {
    const activeCount = alerts.filter((a) => a.active).length
    const mutedCount = alerts.filter((a) => !a.active).length
    const triggeredToday = alerts.filter((a) => {
      if (!a.last_triggered) return false
      const triggered = new Date(a.last_triggered)
      const now = new Date()
      return (
        triggered.getFullYear() === now.getFullYear() &&
        triggered.getMonth() === now.getMonth() &&
        triggered.getDate() === now.getDate()
      )
    }).length
    const channels = new Set(alerts.map((a) => a.channel)).size

    return [
      { label: "Active Alerts", value: String(activeCount), icon: Bell },
      { label: "Triggered Today", value: String(triggeredToday), icon: Lightning },
      { label: "Channels", value: String(channels), icon: Broadcast },
      { label: "Muted", value: String(mutedCount), icon: SpeakerSimpleSlash },
    ]
  }, [alerts])

  async function handleCreate() {
    if (!newName.trim() || !newThreshold.trim()) return
    try {
      const res = await fetch("/api/sardis/api/v2/alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newName.trim(),
          condition: newCondition,
          threshold: newThreshold,
          severity: newSeverity,
        }),
      })
      if (!res.ok) throw new Error("Failed to create alert")
      toast.success("Alert rule created")
      setNewName("")
      setNewCondition("spend_exceeds")
      setNewThreshold("")
      setNewSeverity("Warning")
      setDialogOpen(false)
      refetch()
    } catch {
      toast.error("Failed to create alert rule")
    }
  }

  function formatLastTriggered(val: string | null): string {
    if (!val) return "Never"
    const d = new Date(val)
    if (isNaN(d.getTime())) return val
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    if (diffMin < 1) return "Just now"
    if (diffMin < 60) return `${diffMin}m ago`
    const diffHrs = Math.floor(diffMin / 60)
    if (diffHrs < 24) return `${diffHrs}h ago`
    const diffDays = Math.floor(diffHrs / 24)
    return `${diffDays}d ago`
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Alerts</h1>
        <p className="text-sm text-muted-foreground">
          Configure alert rules and notification channels
        </p>
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
          <CardTitle>Alert Rules</CardTitle>
          <CardAction>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger
                render={
                  <Button size="sm">
                    <Plus className="h-3.5 w-3.5" />
                    Create Alert
                  </Button>
                }
              />
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create Alert</DialogTitle>
                  <DialogDescription>
                    Define a new alert rule with conditions and severity.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">Alert Name</label>
                    <Input
                      placeholder="e.g. High Spend Alert"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">Condition</label>
                    <Select
                      value={newCondition}
                      onValueChange={(v) => v && setNewCondition(v)}
                      items={{
                        spend_exceeds: "Spend Exceeds",
                        tx_count: "Transaction Count",
                        agent_inactive: "Agent Inactive",
                      }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select condition" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="spend_exceeds">Spend Exceeds</SelectItem>
                        <SelectItem value="tx_count">Transaction Count</SelectItem>
                        <SelectItem value="agent_inactive">Agent Inactive</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">Threshold</label>
                    <Input
                      placeholder="e.g. 1000"
                      value={newThreshold}
                      onChange={(e) => setNewThreshold(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">Severity</label>
                    <Select
                      value={newSeverity}
                      onValueChange={(v) => v && setNewSeverity(v)}
                      items={{
                        Critical: "Critical",
                        Warning: "Warning",
                        Info: "Info",
                      }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select severity" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Critical">Critical</SelectItem>
                        <SelectItem value="Warning">Warning</SelectItem>
                        <SelectItem value="Info">Info</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <DialogClose render={<Button variant="outline" />}>
                    Cancel
                  </DialogClose>
                  <Button onClick={handleCreate}>Create Alert</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : alerts.length === 0 ? (
            <EmptyState
              icon={Bell}
              title="No alert rules"
              description="Create alert rules to get notified about important events like spend thresholds, failures, and agent activity"
            />
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Alert Name</TableHead>
                <TableHead>Condition</TableHead>
                <TableHead>Channel</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Last Triggered</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {alerts.map((a) => (
                <TableRow key={a.id ?? a.name}>
                  <TableCell className="pl-4 font-medium">{a.name}</TableCell>
                  <TableCell>
                    <code className="text-xs text-muted-foreground">{a.condition}</code>
                  </TableCell>
                  <TableCell>
                    <Badge variant={channelVariant[a.channel] ?? "outline"}>
                      {a.channel}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="inline-flex items-center gap-1.5 text-sm">
                      <span className={`h-1.5 w-1.5 rounded-full ${severityColor[a.severity] ?? "bg-gray-500"}`} />
                      {a.severity}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatLastTriggered(a.last_triggered)}
                  </TableCell>
                  <TableCell>
                    <Switch defaultChecked={a.active} size="sm" />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
