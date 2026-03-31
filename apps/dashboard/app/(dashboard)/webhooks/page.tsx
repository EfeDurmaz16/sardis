"use client"

import { useEffect, useMemo, useState } from "react"
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
  WarningCircle,
  Plus,
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
import { dashboardApiFetch } from "@/utils/dashboard-client"

type RemoteWebhook = {
  subscription_id: string
  url: string
  events: string[]
  secret?: string | null
  is_active: boolean
  total_deliveries: number
  successful_deliveries: number
  failed_deliveries: number
  last_delivery_at: string | null
  created_at: string
}

type WebhooksResponse = {
  webhooks: RemoteWebhook[]
  eventTypes: string[]
}

type WebhookRow = {
  id: string
  url: string
  events: string[]
  status: "Active" | "Failing" | "Disabled"
  successRate: string
  lastDelivery: string
  totalDeliveries: number
  failedDeliveries: number
}

const statusConfig: Record<WebhookRow["status"], { variant: "default" | "secondary" | "destructive" | "success" }> = {
  Active: { variant: "success" },
  Failing: { variant: "destructive" },
  Disabled: { variant: "secondary" },
}

function formatRelativeTime(value: string | null) {
  if (!value) return "Never"

  const deltaSeconds = Math.max(1, Math.floor((Date.now() - new Date(value).getTime()) / 1000))
  const buckets = [
    { limit: 60, divisor: 1, unit: "second" as const },
    { limit: 3600, divisor: 60, unit: "minute" as const },
    { limit: 86400, divisor: 3600, unit: "hour" as const },
  ]

  for (const bucket of buckets) {
    if (deltaSeconds < bucket.limit) {
      const amount = Math.floor(deltaSeconds / bucket.divisor)
      return `${amount} ${bucket.unit}${amount === 1 ? "" : "s"} ago`
    }
  }

  const days = Math.floor(deltaSeconds / 86400)
  return `${days} day${days === 1 ? "" : "s"} ago`
}

function toRow(webhook: RemoteWebhook): WebhookRow {
  const successRate = webhook.total_deliveries === 0
    ? "No deliveries"
    : `${((webhook.successful_deliveries / webhook.total_deliveries) * 100).toFixed(1)}%`

  let status: WebhookRow["status"] = "Active"
  if (!webhook.is_active) {
    status = "Disabled"
  } else if (webhook.failed_deliveries > 0 && webhook.total_deliveries > 0) {
    status = "Failing"
  }

  return {
    id: webhook.subscription_id,
    url: webhook.url,
    events: webhook.events,
    status,
    successRate,
    lastDelivery: formatRelativeTime(webhook.last_delivery_at),
    totalDeliveries: webhook.total_deliveries,
    failedDeliveries: webhook.failed_deliveries,
  }
}

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<WebhookRow[]>([])
  const [availableEvents, setAvailableEvents] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [url, setUrl] = useState("")
  const [selectedEvents, setSelectedEvents] = useState<Record<string, boolean>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isDeleting, setIsDeleting] = useState<string | null>(null)

  async function loadWebhooks() {
    setLoading(true)
    setError(null)

    try {
      const response = await dashboardApiFetch<WebhooksResponse>("/api/dashboard/webhooks")
      setWebhooks(response.webhooks.map(toRow))
      setAvailableEvents(response.eventTypes)
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Failed to load webhooks"
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadWebhooks()
  }, [])

  function resetForm() {
    setUrl("")
    setSelectedEvents({})
  }

  async function handleCreate() {
    if (!url.trim()) return

    const events = Object.entries(selectedEvents)
      .filter(([, enabled]) => enabled)
      .map(([event]) => event)

    if (events.length === 0) {
      toast.error("Select at least one event")
      return
    }

    setIsSubmitting(true)

    try {
      const created = await dashboardApiFetch<RemoteWebhook>("/api/dashboard/webhooks", {
        method: "POST",
        body: JSON.stringify({
          url: url.trim(),
          events,
        }),
      })

      setWebhooks((current) => [toRow(created), ...current])
      setDialogOpen(false)
      resetForm()
      toast.success("Webhook endpoint added")
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : "Failed to add webhook endpoint"
      toast.error(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleDelete(id: string) {
    setIsDeleting(id)

    try {
      await dashboardApiFetch(`/api/dashboard/webhooks/${id}`, {
        method: "DELETE",
      })
      setWebhooks((current) => current.filter((webhook) => webhook.id !== id))
      toast.success("Webhook deleted")
    } catch (deleteError) {
      const message = deleteError instanceof Error ? deleteError.message : "Failed to delete webhook"
      toast.error(message)
    } finally {
      setIsDeleting(null)
    }
  }

  const stats = useMemo(() => {
    const active = webhooks.filter((webhook) => webhook.status === "Active").length
    const totalDeliveries = webhooks.reduce((sum, webhook) => sum + webhook.totalDeliveries, 0)
    const failedDeliveries = webhooks.reduce((sum, webhook) => sum + webhook.failedDeliveries, 0)
    const successfulDeliveries = totalDeliveries - failedDeliveries
    const successRate = totalDeliveries === 0 ? "No deliveries" : `${((successfulDeliveries / totalDeliveries) * 100).toFixed(1)}%`

    return [
      { label: "Active Webhooks", value: active.toString(), icon: PaperPlaneTilt },
      { label: "Delivery Attempts", value: totalDeliveries.toLocaleString("en-US"), icon: Lightning },
      { label: "Success Rate", value: successRate, icon: CheckCircle },
      { label: "Failed Deliveries", value: failedDeliveries.toLocaleString("en-US"), icon: WarningCircle },
    ]
  }, [webhooks])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Webhooks</h1>
        <p className="text-sm text-muted-foreground">
          Configure webhook endpoints and monitor event delivery
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label} size="sm">
              <CardContent className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                  <p className="text-lg font-semibold tracking-tight tabular-nums">{stat.value}</p>
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
          {loading ? (
            <div className="px-6 py-10 text-sm text-muted-foreground">Loading webhook endpoints…</div>
          ) : error ? (
            <EmptyState
              icon={PaperPlaneTilt}
              title="Webhooks unavailable"
              description={error}
              action={() => void loadWebhooks()}
              actionLabel="Retry"
            />
          ) : webhooks.length === 0 ? (
            <EmptyState
              icon={PaperPlaneTilt}
              title="No webhooks"
              description="Set up webhook endpoints to receive real-time payment and agent events."
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
                {webhooks.map((webhook) => (
                  <ContextMenu key={webhook.id}>
                    <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="pl-4 max-w-[240px]">
                        <code className="block truncate font-mono text-xs text-muted-foreground">
                          {webhook.url}
                        </code>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {webhook.events.map((event) => (
                            <Badge key={event} variant="outline" className="text-[10px]">
                              {event}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusConfig[webhook.status].variant}>{webhook.status}</Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">{webhook.successRate}</TableCell>
                      <TableCell className="text-muted-foreground">{webhook.lastDelivery}</TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" onClick={() => void handleDelete(webhook.id)} disabled={isDeleting === webhook.id}>
                          {isDeleting === webhook.id ? "Deleting…" : "Delete"}
                        </Button>
                      </TableCell>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem
                        onClick={() => {
                          navigator.clipboard.writeText(webhook.id)
                          toast.success("Webhook ID copied")
                        }}
                      >
                        Copy ID
                      </ContextMenuItem>
                      <ContextMenuItem
                        onClick={() => {
                          navigator.clipboard.writeText(webhook.url)
                          toast.success("Webhook URL copied")
                        }}
                      >
                        Copy URL
                      </ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem
                        variant="destructive"
                        disabled={isDeleting === webhook.id}
                        onClick={() => void handleDelete(webhook.id)}
                      >
                        {isDeleting === webhook.id ? "Deleting…" : "Delete"}
                      </ContextMenuItem>
                    </ContextMenuContent>
                  </ContextMenu>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Webhook Endpoint</DialogTitle>
            <DialogDescription>Configure a new URL to receive event notifications.</DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              void handleCreate()
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Endpoint URL</label>
              <Input
                placeholder="https://example.com/webhooks"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                type="url"
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Events</label>
              <div className="flex max-h-64 flex-col gap-2 overflow-y-auto rounded-lg border p-3">
                {availableEvents.map((event) => (
                  <label key={event} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={!!selectedEvents[event]}
                      onChange={(inputEvent) =>
                        setSelectedEvents((current) => ({ ...current, [event]: inputEvent.target.checked }))
                      }
                      className="rounded border-input"
                    />
                    <code className="text-xs">{event}</code>
                  </label>
                ))}
              </div>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Adding…" : "Add Endpoint"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
