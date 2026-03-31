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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
  DialogDescription,
} from "@/components/ui/dialog"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
  ContextMenuSeparator,
} from "@/components/ui/context-menu"
import { toast } from "sonner"
import {
  Headset,
  Timer,
  CheckCircle,
  Star,
  Plus,
} from "@phosphor-icons/react"

type Ticket = {
  id: string
  subject: string
  priority: "Urgent" | "High" | "Normal" | "Low"
  status: "Open" | "In Progress" | "Resolved"
  created: string
  lastUpdate: string
}

const initialTickets: Ticket[] = [
  {
    id: "TKT-1042",
    subject: "API rate limiting not applying correctly",
    priority: "Urgent",
    status: "Open",
    created: "Mar 26, 2026",
    lastUpdate: "1 hr ago",
  },
  {
    id: "TKT-1041",
    subject: "Webhook delivery delays during peak hours",
    priority: "High",
    status: "In Progress",
    created: "Mar 25, 2026",
    lastUpdate: "3 hrs ago",
  },
  {
    id: "TKT-1039",
    subject: "Need help configuring multi-chain agent",
    priority: "Normal",
    status: "Open",
    created: "Mar 24, 2026",
    lastUpdate: "1 day ago",
  },
  {
    id: "TKT-1037",
    subject: "Transaction reconciliation mismatch",
    priority: "High",
    status: "In Progress",
    created: "Mar 23, 2026",
    lastUpdate: "4 hrs ago",
  },
  {
    id: "TKT-1035",
    subject: "Sandbox environment data reset request",
    priority: "Low",
    status: "Resolved",
    created: "Mar 22, 2026",
    lastUpdate: "2 days ago",
  },
  {
    id: "TKT-1033",
    subject: "Invoice PDF generation failing",
    priority: "Normal",
    status: "Resolved",
    created: "Mar 20, 2026",
    lastUpdate: "3 days ago",
  },
]

const priorityConfig: Record<string, { variant: "default" | "secondary" | "destructive" | "outline" | "warning" }> = {
  Urgent: { variant: "destructive" },
  High: { variant: "warning" },
  Normal: { variant: "outline" },
  Low: { variant: "outline" },
}

const statusVariant: Record<string, "default" | "secondary" | "outline" | "warning" | "info" | "success"> = {
  Open: "warning",
  "In Progress": "info",
  Resolved: "success",
}

const stats = [
  { label: "Open Tickets", value: "2", icon: Headset },
  { label: "Avg Response", value: "4h", icon: Timer },
  { label: "Resolved This Week", value: "8", icon: CheckCircle },
  { label: "Satisfaction", value: "4.8/5", icon: Star },
]

export default function SupportPage() {
  const [tab, setTab] = useState("all")
  const [tickets, setTickets] = useState<Ticket[]>(initialTickets)
  const [dialogOpen, setDialogOpen] = useState(false)

  // Form state
  const [subject, setSubject] = useState("")
  const [priority, setPriority] = useState<string>("Normal")
  const [description, setDescription] = useState("")

  function resetForm() {
    setSubject("")
    setPriority("Normal")
    setDescription("")
  }

  function handleCreate() {
    if (!subject.trim()) return
    const nextId = Math.max(...tickets.map((t) => parseInt(t.id.replace("TKT-", ""))), 1000) + 1
    const newTicket: Ticket = {
      id: `TKT-${nextId}`,
      subject: subject.trim(),
      priority: priority as Ticket["priority"],
      status: "Open",
      created: new Date().toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" }),
      lastUpdate: "Just now",
    }
    setTickets((prev) => [newTicket, ...prev])
    setDialogOpen(false)
    resetForm()
    toast.success("Ticket created")
  }

  function handleClose(id: string) {
    setTickets((prev) => prev.map((t) => t.id === id ? { ...t, status: "Resolved" as const, lastUpdate: "Just now" } : t))
    toast.success("Ticket closed")
  }

  const filtered = tab === "all"
    ? tickets
    : tickets.filter((t) => {
        if (tab === "open") return t.status === "Open"
        if (tab === "in-progress") return t.status === "In Progress"
        if (tab === "resolved") return t.status === "Resolved"
        return true
      })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Support</h1>
        <p className="text-sm text-muted-foreground">
          Manage support tickets and track resolutions
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
          <CardTitle>Tickets</CardTitle>
          <CardAction>
            <div className="flex items-center gap-2">
              <Tabs value={tab} onValueChange={setTab}>
                <TabsList>
                  <TabsTrigger value="all">All</TabsTrigger>
                  <TabsTrigger value="open">Open</TabsTrigger>
                  <TabsTrigger value="in-progress">In Progress</TabsTrigger>
                  <TabsTrigger value="resolved">Resolved</TabsTrigger>
                </TabsList>
              </Tabs>
              <Button size="sm" onClick={() => setDialogOpen(true)}>
                <Plus className="h-3.5 w-3.5" />
                New Ticket
              </Button>
            </div>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Ticket #</TableHead>
                <TableHead>Subject</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Last Update</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((t) => (
                <ContextMenu key={t.id}>
                  <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="pl-4">
                        <Badge variant="outline" className="font-mono">
                          {t.id}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium max-w-[300px] truncate">
                        {t.subject}
                      </TableCell>
                      <TableCell>
                        <Badge variant={priorityConfig[t.priority]?.variant ?? "outline"}>
                          {t.priority}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariant[t.status] ?? "outline"}>
                          {t.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{t.created}</TableCell>
                      <TableCell className="text-muted-foreground">{t.lastUpdate}</TableCell>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(t.id); toast.success("Copied to clipboard") }}>
                      Copy ID
                    </ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={() => console.log("View ticket", t.id)}>
                      View
                    </ContextMenuItem>
                    <ContextMenuItem
                      disabled={t.status === "Resolved"}
                      onClick={() => handleClose(t.id)}
                    >
                      Close
                    </ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* New Ticket Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Support Ticket</DialogTitle>
            <DialogDescription>Describe your issue and we will get back to you.</DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleCreate()
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Subject</label>
              <Input
                placeholder="Brief description of the issue"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Priority</label>
              <Select value={priority} onValueChange={(v) => v && setPriority(v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Low">Low</SelectItem>
                  <SelectItem value="Normal">Normal</SelectItem>
                  <SelectItem value="High">High</SelectItem>
                  <SelectItem value="Urgent">Urgent</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Description</label>
              <Textarea
                placeholder="Provide more details about the issue..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
              />
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button type="submit">Create Ticket</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
