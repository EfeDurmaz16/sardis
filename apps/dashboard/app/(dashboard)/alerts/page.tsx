"use client"

import { useState } from "react"
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
} from "@phosphor-icons/react"

type Alert = {
  name: string
  condition: string
  channel: string
  severity: string
  lastTriggered: string
  active: boolean
}

const initialAlerts: Alert[] = [
  {
    name: "High Transaction Volume",
    condition: "> 1,000 txns/min",
    channel: "Slack",
    severity: "Warning",
    lastTriggered: "2 hrs ago",
    active: true,
  },
  {
    name: "Failed Payment Spike",
    condition: "> 5% failure rate",
    channel: "Email",
    severity: "Critical",
    lastTriggered: "1 day ago",
    active: true,
  },
  {
    name: "Agent Wallet Low Balance",
    condition: "Balance < $1,000",
    channel: "Slack",
    severity: "Warning",
    lastTriggered: "4 hrs ago",
    active: true,
  },
  {
    name: "Webhook Delivery Failure",
    condition: "> 3 consecutive failures",
    channel: "Email",
    severity: "Critical",
    lastTriggered: "3 days ago",
    active: true,
  },
  {
    name: "Unauthorized Access Attempt",
    condition: "> 5 failed logins",
    channel: "SMS",
    severity: "Critical",
    lastTriggered: "12 hrs ago",
    active: true,
  },
  {
    name: "API Latency Threshold",
    condition: "p99 > 500ms",
    channel: "Webhook",
    severity: "Warning",
    lastTriggered: "6 hrs ago",
    active: true,
  },
  {
    name: "Daily Spend Limit",
    condition: "> 80% of limit used",
    channel: "Email",
    severity: "Info",
    lastTriggered: "1 hr ago",
    active: false,
  },
  {
    name: "New Agent Registration",
    condition: "Any new agent created",
    channel: "Slack",
    severity: "Info",
    lastTriggered: "5 hrs ago",
    active: false,
  },
]

const channelVariant: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  Email: "outline",
  Slack: "outline",
  Webhook: "outline",
  SMS: "outline",
}

const severityColor: Record<string, string> = {
  Critical: "bg-destructive",
  Warning: "bg-warning",
  Info: "bg-info",
}

const conditionLabels: Record<string, string> = {
  spend_exceeds: "Spend exceeds threshold",
  tx_count: "Transaction count exceeds threshold",
  agent_inactive: "Agent inactive for threshold minutes",
}

const stats = [
  { label: "Active Alerts", value: "12", icon: Bell },
  { label: "Triggered Today", value: "5", icon: Lightning },
  { label: "Channels", value: "3", icon: Broadcast },
  { label: "Muted", value: "2", icon: SpeakerSimpleSlash },
]

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>(initialAlerts)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newCondition, setNewCondition] = useState("spend_exceeds")
  const [newThreshold, setNewThreshold] = useState("")
  const [newSeverity, setNewSeverity] = useState("Warning")

  function handleCreate() {
    if (!newName.trim() || !newThreshold.trim()) return
    const condLabel = conditionLabels[newCondition] ?? newCondition
    const alert: Alert = {
      name: newName.trim(),
      condition: `${condLabel} (${newThreshold})`,
      channel: "Slack",
      severity: newSeverity,
      lastTriggered: "Never",
      active: true,
    }
    setAlerts((prev) => [alert, ...prev])
    setNewName("")
    setNewCondition("spend_exceeds")
    setNewThreshold("")
    setNewSeverity("Warning")
    setDialogOpen(false)
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
                <TableRow key={a.name}>
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
                  <TableCell className="text-muted-foreground">{a.lastTriggered}</TableCell>
                  <TableCell>
                    <Switch defaultChecked={a.active} size="sm" />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
