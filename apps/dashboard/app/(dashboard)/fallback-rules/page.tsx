"use client"

import { useState, useMemo } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardAction,
} from "@/components/ui/card"
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
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
  ContextMenuSeparator,
} from "@/components/ui/context-menu"
import {
  GitBranch,
  Lightning,
  Timer,
  CheckCircle,
  Plus,
  ArrowRight,
  Spinner,
} from "@phosphor-icons/react"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"
import { useSardisList } from "@/hooks/use-sardis"

type FallbackRule = {
  id: string
  name: string
  priority: number
  condition: string
  primary_chain: string
  fallback_chains: string[]
  triggers: number
  enabled: boolean
}

const priorityVariant: Record<number, "outline"> = {
  1: "outline",
  2: "outline",
  3: "outline",
  4: "outline",
  5: "outline",
  6: "outline",
}

export default function FallbackRulesPage() {
  const { data: ruleData, loading, refetch } = useSardisList<FallbackRule>("api/v2/fallback-policies", "Fallback rules")
  const rules = ruleData ?? []

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)

  // Form state
  const [primaryRail, setPrimaryRail] = useState("")
  const [fallbackRail, setFallbackRail] = useState("")
  const [trigger, setTrigger] = useState<string>("gas-spike")

  const stats = useMemo(() => {
    const activeCount = rules.filter((r) => r.enabled).length
    const totalTriggers = rules.reduce((sum, r) => sum + r.triggers, 0)
    const successRate = rules.length > 0
      ? Math.round((rules.filter((r) => r.enabled).length / rules.length) * 100)
      : 0

    return [
      { label: "Active Rules", value: String(activeCount), icon: GitBranch },
      { label: "Triggers Last 24h", value: String(totalTriggers), icon: Lightning },
      { label: "Avg Fallback Time", value: "—", icon: Timer },
      { label: "Success Rate", value: rules.length > 0 ? `${successRate}%` : "—", icon: CheckCircle },
    ]
  }, [rules])

  function resetForm() {
    setPrimaryRail("")
    setFallbackRail("")
    setTrigger("gas-spike")
    setEditingId(null)
  }

  function openCreateDialog() {
    resetForm()
    setDialogOpen(true)
  }

  function openEditDialog(rule: FallbackRule) {
    setPrimaryRail(rule.primary_chain)
    setFallbackRail(rule.fallback_chains.join(", "))
    setTrigger("gas-spike")
    setEditingId(rule.id)
    setDialogOpen(true)
  }

  const triggerLabels: Record<string, string> = {
    "gas-spike": "Gas price spike",
    "rpc-timeout": "RPC timeout",
    "congestion": "Network congestion",
    "low-liquidity": "Low liquidity",
    "settlement-delay": "Settlement delay",
  }

  async function handleSubmit() {
    if (!primaryRail.trim() || !fallbackRail.trim()) return
    try {
      if (editingId) {
        const res = await fetch(`/api/sardis/api/v2/fallback-rules/${editingId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            primary_chain: primaryRail.trim(),
            fallback_chains: fallbackRail.split(",").map((s) => s.trim()).filter(Boolean),
            trigger,
          }),
        })
        if (!res.ok) throw new Error("Failed")
        toast.success("Rule updated")
      } else {
        const res = await fetch("/api/sardis/api/v2/fallback-rules", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            primary_chain: primaryRail.trim(),
            fallback_chains: fallbackRail.split(",").map((s) => s.trim()).filter(Boolean),
            trigger,
          }),
        })
        if (!res.ok) throw new Error("Failed")
        toast.success("Rule created")
      }
      setDialogOpen(false)
      resetForm()
      refetch()
    } catch {
      toast.error(editingId ? "Failed to update rule" : "Failed to create rule")
    }
  }

  async function handleDelete(id: string) {
    try {
      const res = await fetch(`/api/sardis/api/v2/fallback-rules/${id}`, {
        method: "DELETE",
      })
      if (!res.ok) throw new Error("Failed")
      toast.success("Rule deleted")
      refetch()
    } catch {
      toast.error("Failed to delete rule")
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Fallback Rules</h1>
          <p className="text-sm text-muted-foreground">Configure automatic routing fallbacks for chain failures</p>
        </div>
        <Button onClick={openCreateDialog}>
          <Plus className="h-4 w-4" />
          Create Rule
        </Button>
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

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      ) : rules.length === 0 ? (
        <EmptyState
          icon={GitBranch}
          title="No fallback rules"
          description="Fallback rules will appear here once you configure automatic routing fallbacks for chain failures"
          action={openCreateDialog}
          actionLabel="Create Rule"
        />
      ) : (
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {rules.map((rule) => (
          <ContextMenu key={rule.id}>
            <ContextMenuTrigger>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {rule.name}
                    <Badge variant={priorityVariant[rule.priority] ?? "outline"}>
                      P{rule.priority}
                    </Badge>
                  </CardTitle>
                  <CardAction>
                    <Switch defaultChecked={rule.enabled} />
                  </CardAction>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-muted-foreground">{rule.condition}</p>
                  <div className="flex items-center gap-2 text-sm">
                    <Badge variant="outline">{rule.primary_chain}</Badge>
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
                    {rule.fallback_chains.map((chain) => (
                      <Badge key={chain} variant="secondary">{chain}</Badge>
                    ))}
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground pt-1 border-t">
                    <span>Triggers (24h): <span className="font-semibold text-foreground tabular-nums">{rule.triggers}</span></span>
                    <span className={rule.enabled ? "text-success" : "text-muted-foreground"}>
                      {rule.enabled ? "Active" : "Disabled"}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </ContextMenuTrigger>
            <ContextMenuContent>
              <ContextMenuItem onClick={() => { navigator.clipboard.writeText(rule.name); toast.success("Copied to clipboard") }}>
                Copy ID
              </ContextMenuItem>
              <ContextMenuSeparator />
              <ContextMenuItem onClick={() => openEditDialog(rule)}>
                Edit
              </ContextMenuItem>
              <ContextMenuItem variant="destructive" onClick={() => handleDelete(rule.id)}>
                Delete
              </ContextMenuItem>
            </ContextMenuContent>
          </ContextMenu>
        ))}
      </div>
      )}

      {/* Create / Edit Rule Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Rule" : "Create Fallback Rule"}</DialogTitle>
            <DialogDescription>
              {editingId ? "Update the routing fallback configuration." : "Define a new routing fallback rule."}
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSubmit()
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Primary Rail</label>
              <Input
                placeholder="e.g. Ethereum"
                value={primaryRail}
                onChange={(e) => setPrimaryRail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Fallback Rail(s)</label>
              <Input
                placeholder="e.g. Arbitrum, Optimism"
                value={fallbackRail}
                onChange={(e) => setFallbackRail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Trigger</label>
              <Select value={trigger} onValueChange={(v) => v && setTrigger(v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gas-spike">Gas price spike</SelectItem>
                  <SelectItem value="rpc-timeout">RPC timeout</SelectItem>
                  <SelectItem value="congestion">Network congestion</SelectItem>
                  <SelectItem value="low-liquidity">Low liquidity</SelectItem>
                  <SelectItem value="settlement-delay">Settlement delay</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button type="submit">{editingId ? "Save Changes" : "Create Rule"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
