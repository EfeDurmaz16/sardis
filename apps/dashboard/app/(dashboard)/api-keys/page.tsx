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
import { Switch } from "@/components/ui/switch"
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
  Lightning,
  Gauge,
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

type ApiKey = {
  id: string
  name: string
  key: string
  permissions: "Full Access" | "Read Only" | "Read/Write"
  created: string
  lastUsed: string
  active: boolean
}

const initialApiKeys: ApiKey[] = [
  {
    id: "1",
    name: "Production API",
    key: "demo_live_redacted_abc...x9z",
    permissions: "Full Access",
    created: "Jan 15, 2026",
    lastUsed: "2 min ago",
    active: true,
  },
  {
    id: "2",
    name: "Analytics Service",
    key: "demo_live_redacted_def...w8y",
    permissions: "Read Only",
    created: "Feb 3, 2026",
    lastUsed: "1 hr ago",
    active: true,
  },
  {
    id: "3",
    name: "Webhook Handler",
    key: "demo_live_redacted_ghi...v7x",
    permissions: "Read/Write",
    created: "Feb 20, 2026",
    lastUsed: "15 min ago",
    active: true,
  },
  {
    id: "4",
    name: "Staging Integration",
    key: "demo_test_redacted_jkl...u6w",
    permissions: "Full Access",
    created: "Mar 1, 2026",
    lastUsed: "3 days ago",
    active: false,
  },
]

const permissionVariant: Record<string, "default" | "secondary" | "outline"> = {
  "Full Access": "outline",
  "Read Only": "outline",
  "Read/Write": "outline",
}

const stats = [
  { label: "Active Keys", value: "4", icon: Key },
  { label: "Total Requests (24h)", value: "12,847", icon: Lightning },
  { label: "Rate Limit", value: "1,000/min", icon: Gauge },
]

function parseLastUsed(val: string): number {
  const match = val.match(/(\d+)\s*(min|hr|hrs|day|days|sec)/)
  if (!match) return 0
  const num = parseInt(match[1])
  const unit = match[2]
  if (unit === "sec") return num
  if (unit === "min") return num * 60
  if (unit === "hr" || unit === "hrs") return num * 3600
  if (unit === "day" || unit === "days") return num * 86400
  return 0
}

const scopeToPermission = (scopes: { read: boolean; write: boolean; admin: boolean }): ApiKey["permissions"] => {
  if (scopes.admin) return "Full Access"
  if (scopes.write) return "Read/Write"
  return "Read Only"
}

export default function ApiKeysPage() {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")
  const [apiKeys, setApiKeys] = useState<ApiKey[]>(initialApiKeys)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [successDialogOpen, setSuccessDialogOpen] = useState(false)
  const [generatedKey, setGeneratedKey] = useState("")

  // Form state
  const [keyName, setKeyName] = useState("")
  const [environment, setEnvironment] = useState<string>("test")
  const [scopes, setScopes] = useState({ read: true, write: false, admin: false })

  function resetForm() {
    setKeyName("")
    setEnvironment("test")
    setScopes({ read: true, write: false, admin: false })
  }

  function handleGenerate() {
    if (!keyName.trim()) return
    const randomStr = Math.random().toString(36).substring(2, 14)
    const prefix = environment === "live" ? "demo_live_" : "demo_test_"
    const fullKey = `${prefix}${randomStr}`
    const newKey: ApiKey = {
      id: crypto.randomUUID(),
      name: keyName.trim(),
      key: `${prefix}${randomStr.slice(0, 3)}...${randomStr.slice(-3)}`,
      permissions: scopeToPermission(scopes),
      created: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
      lastUsed: "Never",
      active: true,
    }
    setApiKeys((prev) => [...prev, newKey])
    setGeneratedKey(fullKey)
    setDialogOpen(false)
    resetForm()
    setSuccessDialogOpen(true)
    toast.success("API key generated")
  }

  function handleRevoke(id: string) {
    setApiKeys((prev) => prev.filter((k) => k.id !== id))
    toast.success("Key revoked")
  }

  function toggleSort(key: string) {
    if (sortKey === key) {
      setSortDir(d => d === "asc" ? "desc" : "asc")
    } else {
      setSortKey(key)
      setSortDir("asc")
    }
  }

  const sorted = [...apiKeys].sort((a, b) => {
    if (!sortKey) return 0
    let cmp = 0
    if (sortKey === "created") {
      cmp = new Date(a.created).getTime() - new Date(b.created).getTime()
    } else if (sortKey === "lastUsed") {
      cmp = parseLastUsed(a.lastUsed) - parseLastUsed(b.lastUsed)
    } else if (sortKey === "active") {
      cmp = (a.active === b.active) ? 0 : a.active ? -1 : 1
    } else {
      const av = a[sortKey as keyof ApiKey] as string
      const bv = b[sortKey as keyof ApiKey] as string
      cmp = av.localeCompare(bv)
    }
    return sortDir === "asc" ? cmp : -cmp
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">API Keys</h1>
        <p className="text-sm text-muted-foreground">
          Manage your API keys and access tokens
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
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
          <CardTitle>API Keys</CardTitle>
          <CardAction>
            <Button size="sm" onClick={() => setDialogOpen(true)}>
              <Plus className="h-3.5 w-3.5" />
              Generate New Key
            </Button>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
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
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                    )}
                  </span>
                </TableHead>
                <TableHead>Key</TableHead>
                <TableHead>Permissions</TableHead>
                <TableHead
                  className="cursor-pointer select-none hover:text-foreground transition-colors"
                  onClick={() => toggleSort("created")}
                >
                  <span className="flex items-center gap-1">
                    Created
                    {sortKey === "created" ? (
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
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
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
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
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                    )}
                  </span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((k) => (
                <ContextMenu key={k.id}>
                  <ContextMenuTrigger render={<TableRow />}>
                    <TableCell className="pl-4 font-medium">{k.name}</TableCell>
                    <TableCell>
                      <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">
                        ••••{k.key}
                      </code>
                    </TableCell>
                    <TableCell>
                      <Badge variant={permissionVariant[k.permissions] ?? "outline"}>
                        {k.permissions}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{k.created}</TableCell>
                    <TableCell className="text-muted-foreground">{k.lastUsed}</TableCell>
                    <TableCell>
                      <Switch defaultChecked={k.active} size="sm" />
                    </TableCell>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(k.key); toast.success("Copied to clipboard") }}>
                      Copy Key
                    </ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem variant="destructive" onClick={() => handleRevoke(k.id)}>Revoke</ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Generate New Key Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate New API Key</DialogTitle>
            <DialogDescription>Create a new API key for your application.</DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleGenerate()
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Key Name</label>
              <Input
                placeholder="e.g. Production API"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Environment</label>
              <Select value={environment} onValueChange={(v) => v && setEnvironment(v)}>
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
                    onChange={(e) => setScopes((s) => ({ ...s, read: e.target.checked }))}
                    className="rounded border-input"
                  />
                  Read
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={scopes.write}
                    onChange={(e) => setScopes((s) => ({ ...s, write: e.target.checked }))}
                    className="rounded border-input"
                  />
                  Write
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={scopes.admin}
                    onChange={(e) => setScopes((s) => ({ ...s, admin: e.target.checked }))}
                    className="rounded border-input"
                  />
                  Admin
                </label>
              </div>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button type="submit">Generate Key</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Success Dialog showing the generated key */}
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
                toast.success("Copied to clipboard")
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
