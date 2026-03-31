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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
  ContextMenuSeparator,
} from "@/components/ui/context-menu"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Prohibit,
  CheckCircle,
  ListBullets,
  Clock,
} from "@phosphor-icons/react"
import { toast } from "sonner"

type ExceptionStatus = "Active" | "Resolved" | "Escalated" | "Retrying"

type ExceptionItem = {
  id: string
  rule: string
  description: string
  severity: "Critical" | "High" | "Medium" | "Low"
  agent: string
  created: string
  status: ExceptionStatus
}

const initialExceptions: ExceptionItem[] = [
  { id: "EXC-0089", rule: "Max Single Transaction", description: "Transaction exceeded $50,000 single-transfer limit", severity: "Critical", agent: "Payment Router Alpha", created: "5 min ago", status: "Active" },
  { id: "EXC-0088", rule: "Velocity Check", description: "Agent exceeded 30 transactions per minute threshold", severity: "High", agent: "Gas Optimizer v3", created: "18 min ago", status: "Active" },
  { id: "EXC-0087", rule: "New Merchant Cooldown", description: "Transfer to merchant added less than 24 hours ago", severity: "Medium", agent: "Vendor Pay Agent", created: "42 min ago", status: "Active" },
  { id: "EXC-0086", rule: "Cross-chain Limit", description: "Daily cross-chain transfer volume exceeded", severity: "High", agent: "Cross-chain Bridge", created: "1 hr ago", status: "Active" },
  { id: "EXC-0085", rule: "Balance Threshold", description: "Wallet balance dropped below minimum reserve", severity: "Medium", agent: "Yield Harvester", created: "2 hrs ago", status: "Resolved" },
  { id: "EXC-0084", rule: "Max Single Transaction", description: "Large transfer flagged for manual review", severity: "Critical", agent: "Treasury Sweep Bot", created: "3 hrs ago", status: "Resolved" },
  { id: "EXC-0083", rule: "API Rate Limit", description: "Provider API rate limit exceeded temporarily", severity: "Low", agent: "Expense Tracker v2", created: "4 hrs ago", status: "Resolved" },
  { id: "EXC-0082", rule: "Duplicate Detection", description: "Potential duplicate invoice payment detected", severity: "Medium", agent: "Invoice Settler", created: "5 hrs ago", status: "Resolved" },
]

const stats = [
  { label: "Active Exceptions", value: "4", icon: Prohibit },
  { label: "Resolved Today", value: "8", icon: CheckCircle },
  { label: "Total Rules", value: "12", icon: ListBullets },
  { label: "Avg Resolution", value: "2.4h", icon: Clock },
]

const severityVariant: Record<ExceptionItem["severity"], "destructive" | "warning" | "info" | "secondary"> = {
  Critical: "destructive",
  High: "warning",
  Medium: "info",
  Low: "secondary",
}

const statusVariant: Record<ExceptionStatus, "warning" | "success" | "destructive" | "info"> = {
  Active: "warning",
  Resolved: "success",
  Escalated: "destructive",
  Retrying: "info",
}

export default function ExceptionsPage() {
  const [tab, setTab] = useState("all")
  const [exceptions, setExceptions] = useState<ExceptionItem[]>(initialExceptions)

  // Edit dialog state
  const [editOpen, setEditOpen] = useState(false)
  const [editItem, setEditItem] = useState<ExceptionItem | null>(null)
  const [editRule, setEditRule] = useState("")
  const [editDescription, setEditDescription] = useState("")
  const [editSeverity, setEditSeverity] = useState<ExceptionItem["severity"]>("Medium")

  const filtered = tab === "all"
    ? exceptions
    : tab === "rules"
      ? exceptions
      : exceptions.filter((e) => e.status.toLowerCase() === tab)

  function handleEdit(item: ExceptionItem) {
    setEditItem(item)
    setEditRule(item.rule)
    setEditDescription(item.description)
    setEditSeverity(item.severity)
    setEditOpen(true)
  }

  function handleEditSave() {
    if (!editItem) return
    setExceptions((prev) => prev.map((e) =>
      e.id === editItem.id
        ? { ...e, rule: editRule, description: editDescription, severity: editSeverity }
        : e
    ))
    setEditOpen(false)
    toast.success(`Exception ${editItem.id} updated`)
  }

  function handleRetry(id: string) {
    setExceptions((prev) => prev.map((e) =>
      e.id === id ? { ...e, status: "Retrying" as ExceptionStatus } : e
    ))
    toast.info(`Retrying ${id}...`)
  }

  function handleResolve(id: string) {
    setExceptions((prev) => prev.map((e) =>
      e.id === id ? { ...e, status: "Resolved" as ExceptionStatus } : e
    ))
    toast.success(`Exception ${id} resolved`)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Exceptions</h1>
        <p className="text-sm text-muted-foreground">Exception handling and rule violation management</p>
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
          <CardTitle>Exception Log</CardTitle>
          <CardAction>
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="active">Active</TabsTrigger>
                <TabsTrigger value="resolved">Resolved</TabsTrigger>
                <TabsTrigger value="rules">Rules</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Exception ID</TableHead>
                <TableHead>Rule</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Agent</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((item) => (
                <ContextMenu key={item.id}>
                  <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="pl-4"><Badge variant="outline" className="font-mono">{item.id}</Badge></TableCell>
                      <TableCell className="font-medium">{item.rule}</TableCell>
                      <TableCell className="max-w-[260px] truncate">{item.description}</TableCell>
                      <TableCell>
                        <Badge variant={severityVariant[item.severity]}>{item.severity}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{item.agent}</TableCell>
                      <TableCell className="text-muted-foreground">{item.created}</TableCell>
                      <TableCell>
                        <Badge variant={statusVariant[item.status]}>{item.status}</Badge>
                      </TableCell>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(item.id); toast.success("Copied to clipboard") }}>
                      Copy ID
                    </ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={() => handleEdit(item)}>
                      Edit
                    </ContextMenuItem>
                    <ContextMenuItem onClick={() => handleRetry(item.id)}>
                      Retry
                    </ContextMenuItem>
                    <ContextMenuItem onClick={() => handleResolve(item.id)}>
                      Resolve
                    </ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Edit Exception Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Exception</DialogTitle>
            <DialogDescription>{editItem?.id}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Rule</label>
              <Input value={editRule} onChange={(e) => setEditRule(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <Input value={editDescription} onChange={(e) => setEditDescription(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Severity</label>
              <Select
                value={editSeverity}
                onValueChange={(v) => { if (v) setEditSeverity(v as ExceptionItem["severity"]) }}
                items={{ Critical: "Critical", High: "High", Medium: "Medium", Low: "Low" }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Critical">Critical</SelectItem>
                  <SelectItem value="High">High</SelectItem>
                  <SelectItem value="Medium">Medium</SelectItem>
                  <SelectItem value="Low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={handleEditSave}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
