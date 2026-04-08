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
  Spinner,
} from "@phosphor-icons/react"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"
import { useSardisList } from "@/hooks/use-sardis"

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
  const { data: workflowData, loading, refetch } = useSardisList<Workflow>("api/v2/workflow-templates", "Workflow templates")

  const workflows = workflowData ?? []

  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newTemplate, setNewTemplate] = useState("payment_approval")
  const [newDescription, setNewDescription] = useState("")

  const stats = useMemo(() => {
    const activeCount = workflows.filter((w) => w.status === "active").length
    const totalExecutions = workflows.reduce((sum, w) => sum + w.executions24h, 0)
    const avgSuccess = workflows.length > 0
      ? (workflows.reduce((sum, w) => sum + w.successRate, 0) / workflows.length).toFixed(1)
      : "0.0"
    return [
      { label: "Active Workflows", value: String(activeCount), icon: GitMerge },
      { label: "Executions Today", value: String(totalExecutions), icon: Lightning },
      { label: "Success Rate", value: `${avgSuccess}%`, icon: CheckCircle },
      { label: "Total Workflows", value: String(workflows.length), icon: Timer },
    ]
  }, [workflows])

  async function handleCreate() {
    if (!newName.trim()) return
    try {
      const res = await fetch("/api/sardis/api/v2/workflows", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newName.trim(),
          template: newTemplate,
          description: newDescription.trim(),
        }),
      })
      if (!res.ok) throw new Error("Failed to create workflow")
      toast.success("Workflow created")
      setNewName("")
      setNewTemplate("payment_approval")
      setNewDescription("")
      setDialogOpen(false)
      refetch()
    } catch {
      toast.error("Failed to create workflow")
    }
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
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : workflows.length === 0 ? (
            <EmptyState
              icon={GitMerge}
              title="No workflows"
              description="Create automated workflows to handle payment approvals, scheduled reports, and event-driven processes"
            />
          ) : (
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
          )}
        </CardContent>
      </Card>
    </div>
  )
}
