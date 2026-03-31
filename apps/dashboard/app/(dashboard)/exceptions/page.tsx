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
  Spinner,
} from "@phosphor-icons/react"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"
import { useSardis } from "@/hooks/use-sardis"

type ExceptionStatus = "active" | "resolved" | "escalated" | "retrying"

type ExceptionEntry = {
  id: string
  rule: string
  description: string
  severity: string
  agent: string
  created_at: string | null
  status: ExceptionStatus
}

const severityVariant: Record<string, "destructive" | "warning" | "info" | "secondary"> = {
  critical: "destructive",
  Critical: "destructive",
  high: "warning",
  High: "warning",
  medium: "info",
  Medium: "info",
  low: "secondary",
  Low: "secondary",
}

const statusVariant: Record<string, "warning" | "success" | "destructive" | "info"> = {
  active: "warning",
  Active: "warning",
  resolved: "success",
  Resolved: "success",
  escalated: "destructive",
  Escalated: "destructive",
  retrying: "info",
  Retrying: "info",
}

function capitalize(val: string): string {
  if (!val) return val
  return val.charAt(0).toUpperCase() + val.slice(1)
}

function formatCreated(val: string | null): string {
  if (!val) return "—"
  const d = new Date(val)
  if (isNaN(d.getTime())) return val
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return "Just now"
  if (diffMin < 60) return `${diffMin} min ago`
  const diffHrs = Math.floor(diffMin / 60)
  if (diffHrs < 24) return `${diffHrs} hr${diffHrs > 1 ? "s" : ""} ago`
  const diffDays = Math.floor(diffHrs / 24)
  return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`
}

export default function ExceptionsPage() {
  const { data: exceptionData, loading } = useSardis<ExceptionEntry[]>("api/v2/exceptions")
  const exceptions = exceptionData ?? []

  const [tab, setTab] = useState("all")

  // Edit dialog state
  const [editOpen, setEditOpen] = useState(false)
  const [editItem, setEditItem] = useState<ExceptionEntry | null>(null)
  const [editRule, setEditRule] = useState("")
  const [editDescription, setEditDescription] = useState("")
  const [editSeverity, setEditSeverity] = useState<string>("Medium")

  const stats = useMemo(() => {
    const activeCount = exceptions.filter((e) => e.status.toLowerCase() === "active").length
    const resolvedToday = exceptions.filter((e) => {
      if (e.status.toLowerCase() !== "resolved") return false
      if (!e.created_at) return false
      const d = new Date(e.created_at)
      const now = new Date()
      return (
        d.getFullYear() === now.getFullYear() &&
        d.getMonth() === now.getMonth() &&
        d.getDate() === now.getDate()
      )
    }).length
    const uniqueRules = new Set(exceptions.map((e) => e.rule)).size

    const resolvedExceptions = exceptions.filter((e) => e.status.toLowerCase() === "resolved" && e.created_at)
    const avgResolution = resolvedExceptions.length > 0 ? "—" : "—"

    return [
      { label: "Active Exceptions", value: String(activeCount), icon: Prohibit },
      { label: "Resolved Today", value: String(resolvedToday), icon: CheckCircle },
      { label: "Total Rules", value: String(uniqueRules), icon: ListBullets },
      { label: "Avg Resolution", value: avgResolution, icon: Clock },
    ]
  }, [exceptions])

  const filtered = tab === "all"
    ? exceptions
    : tab === "rules"
      ? exceptions
      : exceptions.filter((e) => e.status.toLowerCase() === tab)

  function handleEdit(item: ExceptionEntry) {
    setEditItem(item)
    setEditRule(item.rule)
    setEditDescription(item.description)
    setEditSeverity(capitalize(item.severity))
    setEditOpen(true)
  }

  function handleEditSave() {
    if (!editItem) return
    // TODO: PUT to API to update exception
    setEditOpen(false)
    toast.success(`Exception ${editItem.id} updated`)
  }

  function handleRetry(id: string) {
    // TODO: POST to API to retry exception
    toast.info(`Retrying ${id}...`)
  }

  function handleResolve(id: string) {
    // TODO: POST to API to resolve exception
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
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={Prohibit}
              title="No exceptions"
              description="Exceptions will appear here when policy rules are violated by agents"
            />
          ) : (
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
                        <Badge variant={severityVariant[item.severity] ?? "secondary"}>{capitalize(item.severity)}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{item.agent}</TableCell>
                      <TableCell className="text-muted-foreground">{formatCreated(item.created_at)}</TableCell>
                      <TableCell>
                        <Badge variant={statusVariant[item.status] ?? "warning"}>{capitalize(item.status)}</Badge>
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
          )}
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
                onValueChange={(v) => { if (v) setEditSeverity(v) }}
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
