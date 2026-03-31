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
import { Progress } from "@/components/ui/progress"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
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
  GitMerge,
  Lightning,
  CheckCircle,
  Timer,
  Plus,
} from "@phosphor-icons/react"

type Workflow = {
  name: string
  trigger: "Webhook" | "Schedule" | "Event" | "Manual"
  actions: number
  lastRun: string
  executions24h: number
  successRate: number
  status: "active" | "paused" | "error"
  created: string
}

const initialWorkflows: Workflow[] = [
  { name: "Payment Approval Pipeline", trigger: "Webhook", actions: 5, lastRun: "2 min ago", executions24h: 34, successRate: 100, status: "active", created: "2025-08-12" },
  { name: "Daily Treasury Rebalance", trigger: "Schedule", actions: 8, lastRun: "4 hrs ago", executions24h: 3, successRate: 100, status: "active", created: "2025-09-01" },
  { name: "Fraud Alert Handler", trigger: "Event", actions: 6, lastRun: "18 min ago", executions24h: 12, successRate: 91.7, status: "active", created: "2025-10-15" },
  { name: "Monthly Invoice Generator", trigger: "Schedule", actions: 4, lastRun: "2 days ago", executions24h: 0, successRate: 100, status: "active", created: "2025-07-20" },
  { name: "New Merchant Onboarding", trigger: "Webhook", actions: 12, lastRun: "1 hr ago", executions24h: 8, successRate: 100, status: "active", created: "2025-11-03" },
  { name: "Gas Price Monitor", trigger: "Event", actions: 3, lastRun: "5 min ago", executions24h: 67, successRate: 98.5, status: "active", created: "2025-08-28" },
  { name: "Compliance Report Export", trigger: "Manual", actions: 7, lastRun: "1 day ago", executions24h: 2, successRate: 100, status: "active", created: "2026-01-10" },
  { name: "Failed TX Retry Logic", trigger: "Event", actions: 4, lastRun: "12 min ago", executions24h: 16, successRate: 93.8, status: "active", created: "2025-12-05" },
]

const stats = [
  { label: "Active Workflows", value: "8", icon: GitMerge },
  { label: "Executions Today", value: "142", icon: Lightning },
  { label: "Success Rate", value: "98.6%", icon: CheckCircle },
  { label: "Avg Duration", value: "1.2s", icon: Timer },
]

const triggerVariant: Record<Workflow["trigger"], "outline"> = {
  Webhook: "outline",
  Schedule: "outline",
  Event: "outline",
  Manual: "outline",
}

const statusConfig: Record<Workflow["status"], { color: string; label: string }> = {
  active: { color: "bg-success", label: "Active" },
  paused: { color: "bg-warning", label: "Paused" },
  error: { color: "bg-destructive", label: "Error" },
}

const templateTriggerMap: Record<string, Workflow["trigger"]> = {
  payment_approval: "Webhook",
  scheduled_report: "Schedule",
  event_handler: "Event",
  manual_task: "Manual",
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>(initialWorkflows)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newTemplate, setNewTemplate] = useState("payment_approval")
  const [newDescription, setNewDescription] = useState("")

  function handleCreate() {
    if (!newName.trim()) return
    const workflow: Workflow = {
      name: newName.trim(),
      trigger: templateTriggerMap[newTemplate] ?? "Manual",
      actions: 0,
      lastRun: "Never",
      executions24h: 0,
      successRate: 100,
      status: "active",
      created: new Date().toISOString().slice(0, 10),
    }
    setWorkflows((prev) => [workflow, ...prev])
    setNewName("")
    setNewTemplate("payment_approval")
    setNewDescription("")
    setDialogOpen(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Workflows</h1>
          <p className="text-sm text-muted-foreground">Automated workflows and execution pipelines</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger
            render={
              <Button>
                <Plus className="h-4 w-4" />
                Create Workflow
              </Button>
            }
          />
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Workflow</DialogTitle>
              <DialogDescription>
                Set up a new automated workflow from a template.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Workflow Name</label>
                <Input
                  placeholder="e.g. Weekly Report Pipeline"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Template</label>
                <Select
                  value={newTemplate}
                  onValueChange={(v) => v && setNewTemplate(v)}
                  items={{
                    payment_approval: "Payment Approval",
                    scheduled_report: "Scheduled Report",
                    event_handler: "Event Handler",
                    manual_task: "Manual Task",
                  }}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select template" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="payment_approval">Payment Approval</SelectItem>
                    <SelectItem value="scheduled_report">Scheduled Report</SelectItem>
                    <SelectItem value="event_handler">Event Handler</SelectItem>
                    <SelectItem value="manual_task">Manual Task</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Description</label>
                <Textarea
                  placeholder="Describe what this workflow does..."
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>
                Cancel
              </DialogClose>
              <Button onClick={handleCreate}>Create Workflow</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
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
          <CardTitle>All Workflows</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Workflow Name</TableHead>
                <TableHead>Trigger</TableHead>
                <TableHead className="text-right">Actions</TableHead>
                <TableHead>Last Run</TableHead>
                <TableHead className="text-right">Executions (24h)</TableHead>
                <TableHead className="text-right">Success Rate</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {workflows.map((wf) => {
                const st = statusConfig[wf.status]
                return (
                  <TableRow key={wf.name}>
                    <TableCell className="pl-4 font-medium">{wf.name}</TableCell>
                    <TableCell>
                      <Badge variant={triggerVariant[wf.trigger]}>{wf.trigger}</Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{wf.actions}</TableCell>
                    <TableCell className="text-muted-foreground">{wf.lastRun}</TableCell>
                    <TableCell className="text-right tabular-nums">{wf.executions24h}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16">
                          <Progress value={wf.successRate} />
                        </div>
                        <span className="text-xs tabular-nums text-muted-foreground">{wf.successRate}%</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1.5">
                        <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                        {st.label}
                      </span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{wf.created}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
