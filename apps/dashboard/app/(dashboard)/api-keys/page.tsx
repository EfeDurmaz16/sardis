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
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import {
  Key,
  ShieldCheck,
  FloppyDisk,
  Plus,
  ArrowUp,
  ArrowDown,
  ArrowsDownUp,
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

type RemoteApiKey = {
  key_id: string
  key_prefix: string
  name: string
  scopes: string[]
  rate_limit: number
  is_active: boolean
  expires_at: string | null
  created_at: string
  last_used_at: string | null
  mode: "test" | "live"
}

type ApiKeysResponse = {
  keys: RemoteApiKey[]
  total: number
}

type CreateApiKeyResponse = RemoteApiKey & {
  key: string
}

type ApiKeyRow = {
  id: string
  name: string
  keyPrefix: string
  permissions: "Full Access" | "Read Only" | "Read/Write"
  created: string
  lastUsed: string
  active: boolean
  mode: "test" | "live"
  rateLimit: number
  scopes: string[]
}

const permissionVariant: Record<ApiKeyRow["permissions"], "default" | "secondary" | "outline"> = {
  "Full Access": "default",
  "Read Only": "secondary",
  "Read/Write": "outline",
}

function parseLastUsed(value: string): number {
  if (value === "Never") return Number.MAX_SAFE_INTEGER
  const match = value.match(/(\d+)\s*(second|minute|hour|day)/)
  if (!match) return 0
  const amount = Number.parseInt(match[1], 10)
  const unit = match[2]
  if (unit === "second") return amount
  if (unit === "minute") return amount * 60
  if (unit === "hour") return amount * 3600
  return amount * 86400
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value))
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

function scopeToPermission(scopes: string[]): ApiKeyRow["permissions"] {
  if (scopes.includes("admin")) return "Full Access"
  if (scopes.includes("write")) return "Read/Write"
  return "Read Only"
}

function toRow(key: RemoteApiKey): ApiKeyRow {
  return {
    id: key.key_id,
    name: key.name,
    keyPrefix: key.key_prefix,
    permissions: scopeToPermission(key.scopes),
    created: formatDate(key.created_at),
    lastUsed: formatRelativeTime(key.last_used_at),
    active: key.is_active,
    mode: key.mode,
    rateLimit: key.rate_limit,
    scopes: key.scopes,
  }
}

export default function ApiKeysPage() {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")
  const [apiKeys, setApiKeys] = useState<ApiKeyRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [successDialogOpen, setSuccessDialogOpen] = useState(false)
  const [generatedKey, setGeneratedKey] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isRevoking, setIsRevoking] = useState<string | null>(null)

  const [keyName, setKeyName] = useState("")
  const [environment, setEnvironment] = useState<"test" | "live">("test")
  const [scopes, setScopes] = useState({ read: true, write: false, admin: false })

  async function loadApiKeys() {
    setLoading(true)
    setError(null)

    try {
      const response = await dashboardApiFetch<ApiKeysResponse>("/api/dashboard/api-keys")
      setApiKeys(response.keys.map(toRow))
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Failed to load API keys"
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadApiKeys()
  }, [])

  function resetForm() {
    setKeyName("")
    setEnvironment("test")
    setScopes({ read: true, write: false, admin: false })
  }

  async function handleGenerate() {
    if (!keyName.trim()) return

    const nextScopes = Object.entries(scopes)
      .filter(([, enabled]) => enabled)
      .map(([scope]) => scope)

    if (nextScopes.length === 0) {
      toast.error("Select at least one scope")
      return
    }

    setIsSubmitting(true)

    try {
      const response = await dashboardApiFetch<CreateApiKeyResponse>("/api/dashboard/api-keys", {
        method: "POST",
        body: JSON.stringify({
          name: keyName.trim(),
          mode: environment,
          scopes: nextScopes,
        }),
      })

      setApiKeys((current) => [toRow(response), ...current])
      setGeneratedKey(response.key)
      setDialogOpen(false)
      setSuccessDialogOpen(true)
      resetForm()
      toast.success("API key generated")
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : "Failed to generate API key"
      toast.error(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleRevoke(id: string) {
    setIsRevoking(id)

    try {
      await dashboardApiFetch(`/api/dashboard/api-keys/${id}`, {
        method: "DELETE",
      })
      setApiKeys((current) => current.filter((key) => key.id !== id))
      toast.success("API key revoked")
    } catch (revokeError) {
      const message = revokeError instanceof Error ? revokeError.message : "Failed to revoke API key"
      toast.error(message)
    } finally {
      setIsRevoking(null)
    }
  }

  function toggleSort(key: string) {
    if (sortKey === key) {
      setSortDir((current) => (current === "asc" ? "desc" : "asc"))
    } else {
      setSortKey(key)
      setSortDir("asc")
    }
  }

  const stats = useMemo(() => {
    const active = apiKeys.filter((key) => key.active).length
    const live = apiKeys.filter((key) => key.mode === "live").length
    const admin = apiKeys.filter((key) => key.scopes.includes("admin")).length

    return [
      { label: "Active Keys", value: active.toString(), icon: Key },
      { label: "Live Keys", value: live.toString(), icon: ShieldCheck },
      { label: "Admin Keys", value: admin.toString(), icon: FloppyDisk },
    ]
  }, [apiKeys])

  const sorted = useMemo(() => {
    return [...apiKeys].sort((a, b) => {
      if (!sortKey) return 0

      let comparison = 0
      if (sortKey === "created") {
        comparison = new Date(a.created).getTime() - new Date(b.created).getTime()
      } else if (sortKey === "lastUsed") {
        comparison = parseLastUsed(a.lastUsed) - parseLastUsed(b.lastUsed)
      } else if (sortKey === "active") {
        comparison = a.active === b.active ? 0 : a.active ? -1 : 1
      } else {
        comparison = String(a[sortKey as keyof ApiKeyRow]).localeCompare(String(b[sortKey as keyof ApiKeyRow]))
      }

      return sortDir === "asc" ? comparison : -comparison
    })
  }, [apiKeys, sortDir, sortKey])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">API Keys</h1>
        <p className="text-sm text-muted-foreground">
          Manage your API keys and access tokens
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
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
          <CardTitle>API Keys</CardTitle>
          <CardAction>
            <Button size="sm" onClick={() => setDialogOpen(true)}>
              <Plus className="h-3.5 w-3.5" />
              Generate New Key
            </Button>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
          {loading ? (
            <div className="px-6 py-10 text-sm text-muted-foreground">Loading API keys…</div>
          ) : error ? (
            <EmptyState
              icon={Key}
              title="API keys unavailable"
              description={error}
              action={() => void loadApiKeys()}
              actionLabel="Retry"
            />
          ) : sorted.length === 0 ? (
            <EmptyState
              icon={Key}
              title="No API keys"
              description="Generate an API key to authenticate dashboard and automation clients."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead
                    className="pl-4 cursor-pointer select-none hover:text-foreground transition-colors"
                    onClick={() => toggleSort("name")}
                  >
                    <span className="flex items-center gap-1">
                      Key Name
                      {sortKey === "name" ? (
                        sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowsDownUp className="h-3 w-3 text-muted-foreground/50" />
                      )}
                    </span>
                  </TableHead>
                  <TableHead>Prefix</TableHead>
                  <TableHead>Permissions</TableHead>
                  <TableHead>Mode</TableHead>
                  <TableHead
                    className="cursor-pointer select-none hover:text-foreground transition-colors"
                    onClick={() => toggleSort("created")}
                  >
                    <span className="flex items-center gap-1">
                      Created
                      {sortKey === "created" ? (
                        sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowsDownUp className="h-3 w-3 text-muted-foreground/50" />
                      )}
                    </span>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none hover:text-foreground transition-colors"
                    onClick={() => toggleSort("lastUsed")}
                  >
                    <span className="flex items-center gap-1">
                      Last Used
                      {sortKey === "lastUsed" ? (
                        sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowsDownUp className="h-3 w-3 text-muted-foreground/50" />
                      )}
                    </span>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none hover:text-foreground transition-colors"
                    onClick={() => toggleSort("active")}
                  >
                    <span className="flex items-center gap-1">
                      Status
                      {sortKey === "active" ? (
                        sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowsDownUp className="h-3 w-3 text-muted-foreground/50" />
                      )}
                    </span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((key) => (
                  <ContextMenu key={key.id}>
                    <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="pl-4 font-medium">{key.name}</TableCell>
                      <TableCell>
                        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">
                          {key.keyPrefix}
                        </code>
                      </TableCell>
                      <TableCell>
                        <Badge variant={permissionVariant[key.permissions]}>{key.permissions}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{key.mode}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{key.created}</TableCell>
                      <TableCell className="text-muted-foreground">{key.lastUsed}</TableCell>
                      <TableCell>
                        <Badge variant={key.active ? "default" : "secondary"}>
                          {key.active ? "Active" : "Revoked"}
                        </Badge>
                      </TableCell>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem
                        onClick={() => {
                          navigator.clipboard.writeText(key.keyPrefix)
                          toast.success("API key prefix copied")
                        }}
                      >
                        Copy Prefix
                      </ContextMenuItem>
                      <ContextMenuItem
                        onClick={() => {
                          navigator.clipboard.writeText(key.id)
                          toast.success("API key ID copied")
                        }}
                      >
                        Copy Key ID
                      </ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem
                        variant="destructive"
                        disabled={isRevoking === key.id}
                        onClick={() => void handleRevoke(key.id)}
                      >
                        {isRevoking === key.id ? "Revoking…" : "Revoke"}
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
            <DialogTitle>Generate New API Key</DialogTitle>
            <DialogDescription>Create a new API key for your application.</DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(event) => {
              event.preventDefault()
              void handleGenerate()
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Key Name</label>
              <Input
                placeholder="e.g. Production API"
                value={keyName}
                onChange={(event) => setKeyName(event.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Environment</label>
              <Select value={environment} onValueChange={(value) => value && setEnvironment(value as "test" | "live")}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="test">Test</SelectItem>
                  <SelectItem value="live">Live</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Scopes</label>
              <div className="flex flex-col gap-2">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={scopes.read}
                    onChange={(event) => setScopes((current) => ({ ...current, read: event.target.checked }))}
                    className="rounded border-input"
                  />
                  Read
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={scopes.write}
                    onChange={(event) => setScopes((current) => ({ ...current, write: event.target.checked }))}
                    className="rounded border-input"
                  />
                  Write
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={scopes.admin}
                    onChange={(event) => setScopes((current) => ({ ...current, admin: event.target.checked }))}
                    className="rounded border-input"
                  />
                  Admin
                </label>
              </div>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Generating…" : "Generate Key"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={successDialogOpen} onOpenChange={setSuccessDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Key Generated</DialogTitle>
            <DialogDescription>
              Copy your API key now. You will not be able to see it again.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-lg bg-muted p-3">
            <code className="break-all font-mono text-xs">{generatedKey}</code>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                navigator.clipboard.writeText(generatedKey)
                toast.success("API key copied")
              }}
            >
              Copy
            </Button>
            <DialogClose render={<Button />}>Done</DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
