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
  Shield,
  ClockCounterClockwise,
  FileText,
  CheckCircle,
  Plus,
  Spinner,
} from "@phosphor-icons/react"
import { EmptyState } from "@/components/empty-state"
import { useSardis } from "@/hooks/use-sardis"

type Policy = {
  id: string
  name: string
  type: string
  rules_count: number
  agents_count: number
  status: string
  priority: string
  last_modified: string | null
}

const typeVariant: Record<string, "outline"> = {
  Spending: "outline",
  spending: "outline",
  Routing: "outline",
  routing: "outline",
  Access: "outline",
  access: "outline",
  Compliance: "outline",
  compliance: "outline",
}

const statusConfig: Record<string, { color: string }> = {
  active: { color: "bg-success" },
  Active: { color: "bg-success" },
  draft: { color: "bg-warning" },
  Draft: { color: "bg-warning" },
  disabled: { color: "bg-destructive" },
  Disabled: { color: "bg-destructive" },
}

const typeMap: Record<string, string> = {
  spending: "Spending",
  access: "Access",
  compliance: "Compliance",
}

function formatLastModified(val: string | null): string {
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

function capitalize(val: string): string {
  if (!val) return val
  return val.charAt(0).toUpperCase() + val.slice(1)
}

export default function PolicyManagerPage() {
  const { data: policyData, loading } = useSardis<Policy[]>("api/v2/policies")
  const policies = policyData ?? []

  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newDescription, setNewDescription] = useState("")
  const [newType, setNewType] = useState("spending")

  const stats = useMemo(() => {
    const total = policies.length
    const active = policies.filter((p) => p.status.toLowerCase() === "active").length
    const draft = policies.filter((p) => p.status.toLowerCase() === "draft").length

    const lastModified = policies.reduce<string | null>((latest, p) => {
      if (!p.last_modified) return latest
      if (!latest) return p.last_modified
      return new Date(p.last_modified) > new Date(latest) ? p.last_modified : latest
    }, null)

    return [
      { label: "Total Policies", value: String(total), icon: Shield },
      { label: "Active", value: String(active), icon: CheckCircle },
      { label: "Draft", value: String(draft), icon: FileText },
      { label: "Last Updated", value: formatLastModified(lastModified), icon: ClockCounterClockwise },
    ]
  }, [policies])

  function handleCreate() {
    if (!newName.trim()) return
    // TODO: POST to API to create policy
    setNewName("")
    setNewDescription("")
    setNewType("spending")
    setDialogOpen(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Policy Manager</h1>
          <p className="text-sm text-muted-foreground">Create and manage your agent policies</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger
            render={
              <Button>
                <Plus weight="bold" />
                Create Policy
              </Button>
            }
          />
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Policy</DialogTitle>
              <DialogDescription>
                Define a new policy with a name, description, and type.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Policy Name</label>
                <Input
                  placeholder="e.g. Daily Spending Cap"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Description</label>
                <Textarea
                  placeholder="Describe what this policy enforces..."
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Type</label>
                <Select
                  value={newType}
                  onValueChange={(v) => v && setNewType(v)}
                  items={{
                    spending: "Spending",
                    access: "Access",
                    compliance: "Compliance",
                  }}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="spending">Spending</SelectItem>
                    <SelectItem value="access">Access</SelectItem>
                    <SelectItem value="compliance">Compliance</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>
                Cancel
              </DialogClose>
              <Button onClick={handleCreate}>Create Policy</Button>
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
          <CardTitle>All Policies</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : policies.length === 0 ? (
            <EmptyState
              icon={Shield}
              title="No policies"
              description="Policies will appear here once you create spending, routing, or compliance rules for your agents"
            />
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Policy Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Rules</TableHead>
                <TableHead className="text-right">Assigned Agents</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Last Modified</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {policies.map((policy) => {
                const st = statusConfig[policy.status] ?? { color: "bg-muted" }
                return (
                  <TableRow key={policy.id ?? policy.name}>
                    <TableCell className="pl-4 font-medium">{policy.name}</TableCell>
                    <TableCell>
                      <Badge variant={typeVariant[policy.type] ?? "outline"}>{capitalize(policy.type)}</Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">{policy.rules_count}</TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">{policy.agents_count}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1.5">
                        <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                        {capitalize(policy.status)}
                      </span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{capitalize(policy.priority)}</TableCell>
                    <TableCell className="text-muted-foreground">{formatLastModified(policy.last_modified)}</TableCell>
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
