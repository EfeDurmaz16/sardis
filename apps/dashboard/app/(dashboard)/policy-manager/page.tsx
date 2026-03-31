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
} from "@phosphor-icons/react"

type Policy = {
  name: string
  type: "Spending" | "Routing" | "Access" | "Compliance"
  rules: number
  agents: number
  status: "Active" | "Draft" | "Disabled"
  priority: string
  lastModified: string
}

const initialPolicies: Policy[] = [
  { name: "Default Spending Limit", type: "Spending", rules: 5, agents: 18, status: "Active", priority: "High", lastModified: "2 hrs ago" },
  { name: "Cross-chain Routing Policy", type: "Routing", rules: 8, agents: 12, status: "Active", priority: "Critical", lastModified: "4 hrs ago" },
  { name: "API Key Access Control", type: "Access", rules: 3, agents: 24, status: "Active", priority: "High", lastModified: "1 day ago" },
  { name: "AML Compliance Check", type: "Compliance", rules: 12, agents: 24, status: "Active", priority: "Critical", lastModified: "6 hrs ago" },
  { name: "Vendor Payment Limits", type: "Spending", rules: 4, agents: 6, status: "Active", priority: "Medium", lastModified: "2 days ago" },
  { name: "Multi-sig Routing", type: "Routing", rules: 6, agents: 8, status: "Active", priority: "High", lastModified: "12 hrs ago" },
  { name: "New Employee Access", type: "Access", rules: 2, agents: 3, status: "Draft", priority: "Low", lastModified: "3 days ago" },
  { name: "GDPR Data Handling", type: "Compliance", rules: 7, agents: 14, status: "Draft", priority: "Medium", lastModified: "5 days ago" },
]

const stats = [
  { label: "Total Policies", value: "14", icon: Shield },
  { label: "Active", value: "12", icon: CheckCircle },
  { label: "Draft", value: "2", icon: FileText },
  { label: "Last Updated", value: "2h ago", icon: ClockCounterClockwise },
]

const typeVariant: Record<Policy["type"], "outline"> = {
  Spending: "outline",
  Routing: "outline",
  Access: "outline",
  Compliance: "outline",
}

const statusConfig: Record<Policy["status"], { color: string }> = {
  Active: { color: "bg-success" },
  Draft: { color: "bg-warning" },
  Disabled: { color: "bg-destructive" },
}

const typeMap: Record<string, Policy["type"]> = {
  spending: "Spending",
  access: "Access",
  compliance: "Compliance",
}

export default function PolicyManagerPage() {
  const [policies, setPolicies] = useState<Policy[]>(initialPolicies)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newDescription, setNewDescription] = useState("")
  const [newType, setNewType] = useState("spending")

  function handleCreate() {
    if (!newName.trim()) return
    const policy: Policy = {
      name: newName.trim(),
      type: typeMap[newType] ?? "Spending",
      rules: 0,
      agents: 0,
      status: "Draft",
      priority: "Medium",
      lastModified: "Just now",
    }
    setPolicies((prev) => [policy, ...prev])
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
                const st = statusConfig[policy.status]
                return (
                  <TableRow key={policy.name}>
                    <TableCell className="pl-4 font-medium">{policy.name}</TableCell>
                    <TableCell>
                      <Badge variant={typeVariant[policy.type]}>{policy.type}</Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">{policy.rules}</TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">{policy.agents}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1.5">
                        <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                        {policy.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{policy.priority}</TableCell>
                    <TableCell className="text-muted-foreground">{policy.lastModified}</TableCell>
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
