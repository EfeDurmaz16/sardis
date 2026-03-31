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
  PaperPlaneTilt,
  Lightning,
  CheckCircle,
  Timer,
  Plus,
  DotsThree,
} from "@phosphor-icons/react"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"

type Webhook = {
  id: string
  url: string
  events: string[]
  status: "Active" | "Failing" | "Disabled"
  successRate: string
  lastDelivery: string
}

const availableEvents = [
  "payment.completed",
  "payment.failed",
  "payment.created",
  "agent.created",
  "agent.started",
  "agent.stopped",
  "agent.error",
  "hold.placed",
  "hold.released",
]

const initialWebhooks: Webhook[] = [
  {
    id: "1",
    url: "https://api.example.com/webhooks/payments",
    events: ["payment.created", "payment.completed", "payment.failed"],
    status: "Active",
    successRate: "99.9%",
    lastDelivery: "30 sec ago",
  },
  {
    id: "2",
    url: "https://hooks.internal.io/agent-events",
    events: ["agent.started", "agent.stopped", "agent.error"],
    status: "Active",
    successRate: "99.7%",
    lastDelivery: "2 min ago",
  },
  {
    id: "3",
    url: "https://notify.acme.co/hold-updates",
    events: ["hold.placed", "hold.released"],
    status: "Failing",
    successRate: "87.2%",
    lastDelivery: "15 min ago",
  },
]

const statusConfig: Record<string, { variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" }> = {
  Active: { variant: "success" },
  Failing: { variant: "destructive" },
  Disabled: { variant: "secondary" },
}

const stats = [
  { label: "Active Webhooks", value: "3", icon: PaperPlaneTilt },
  { label: "Events Delivered (24h)", value: "4,521", icon: Lightning },
  { label: "Success Rate", value: "99.8%", icon: CheckCircle },
  { label: "Avg Latency", value: "120ms", icon: Timer },
]

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<Webhook[]>(initialWebhooks)
  const [dialogOpen, setDialogOpen] = useState(false)

  // Form state
  const [url, setUrl] = useState("")
  const [selectedEvents, setSelectedEvents] = useState<Record<string, boolean>>({})

  function resetForm() {
    setUrl("")
    setSelectedEvents({})
  }

  function handleCreate() {
    if (!url.trim()) return
    const events = Object.entries(selectedEvents)
      .filter(([, v]) => v)
      .map(([k]) => k)
    if (events.length === 0) return

    const newWebhook: Webhook = {
      id: crypto.randomUUID(),
      url: url.trim(),
      events,
      status: "Active",
      successRate: "100%",
      lastDelivery: "Never",
    }
    setWebhooks((prev) => [...prev, newWebhook])
    setDialogOpen(false)
    resetForm()
    toast.success("Webhook endpoint added")
  }

  function handleDelete(id: string) {
    setWebhooks((prev) => prev.filter((wh) => wh.id !== id))
    toast.success("Webhook deleted")
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Webhooks</h1>
        <p className="text-sm text-muted-foreground">
          Configure webhook endpoints and monitor event delivery
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
          <CardTitle>Endpoints</CardTitle>
          <CardAction>
            <Button size="sm" onClick={() => setDialogOpen(true)}>
              <Plus className="h-3.5 w-3.5" />
              Add Endpoint
            </Button>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
          {webhooks.length === 0 ? (
            <EmptyState
              icon={PaperPlaneTilt}
              title="No webhooks"
              description="Set up webhooks to receive real-time payment events"
            />
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">URL</TableHead>
                <TableHead>Events</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Success Rate</TableHead>
                <TableHead>Last Delivery</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {webhooks.map((wh) => (
                <ContextMenu key={wh.id}>
                  <ContextMenuTrigger render={<TableRow />}>
                    <TableCell className="pl-4 max-w-[240px]">
                      <code className="truncate block font-mono text-xs text-muted-foreground">
                        {wh.url}
                      </code>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {wh.events.map((e) => (
                          <Badge key={e} variant="outline" className="text-[10px]">
                            {e}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusConfig[wh.status]?.variant ?? "outline"}>
                        {wh.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">{wh.successRate}</TableCell>
                    <TableCell className="text-muted-foreground">{wh.lastDelivery}</TableCell>
                    <TableCell>
                      <Button variant="ghost" size="icon-sm">
                        <DotsThree className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(wh.url); toast.success("Copied to clipboard") }}>
                      Copy ID
                    </ContextMenuItem>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(wh.url); toast.success("Copied to clipboard") }}>
                      Copy URL
                    </ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem variant="destructive" onClick={() => handleDelete(wh.id)}>Delete</ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>

      {/* Add Endpoint Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Webhook Endpoint</DialogTitle>
            <DialogDescription>Configure a new URL to receive event notifications.</DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleCreate()
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Endpoint URL</label>
              <Input
                placeholder="https://example.com/webhooks"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                type="url"
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Events</label>
              <div className="flex flex-col gap-2 rounded-lg border p-3">
                {availableEvents.map((evt) => (
                  <label key={evt} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={!!selectedEvents[evt]}
                      onChange={(e) =>
                        setSelectedEvents((prev) => ({ ...prev, [evt]: e.target.checked }))
                      }
                      className="rounded border-input"
                    />
                    <code className="text-xs">{evt}</code>
                  </label>
                ))}
              </div>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button type="submit">Add Endpoint</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
