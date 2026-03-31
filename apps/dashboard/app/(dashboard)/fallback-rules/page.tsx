"use client"

import { useState } from "react"
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
} from "@phosphor-icons/react"
import { toast } from "sonner"

type FallbackRule = {
  id: string
  name: string
  priority: number
  condition: string
  primaryChain: string
  fallbackChains: string[]
  triggers: number
  enabled: boolean
}

const initialRules: FallbackRule[] = [
  {
    id: "1",
    name: "Ethereum Gas Spike Fallback",
    priority: 1,
    condition: "When Ethereum gas exceeds 100 gwei for more than 2 minutes",
    primaryChain: "Ethereum",
    fallbackChains: ["Arbitrum", "Optimism"],
    triggers: 5,
    enabled: true,
  },
  {
    id: "2",
    name: "Polygon RPC Timeout",
    priority: 2,
    condition: "When Polygon RPC response time exceeds 3 seconds",
    primaryChain: "Polygon",
    fallbackChains: ["Ethereum"],
    triggers: 2,
    enabled: true,
  },
  {
    id: "3",
    name: "Bridge Congestion Reroute",
    priority: 3,
    condition: "When cross-chain bridge queue exceeds 50 pending transactions",
    primaryChain: "Arbitrum",
    fallbackChains: ["Optimism", "Base"],
    triggers: 3,
    enabled: true,
  },
  {
    id: "4",
    name: "Low Liquidity Swap Redirect",
    priority: 4,
    condition: "When DEX liquidity pool depth falls below $100k for target pair",
    primaryChain: "Optimism",
    fallbackChains: ["Ethereum", "Arbitrum"],
    triggers: 1,
    enabled: true,
  },
  {
    id: "5",
    name: "Settlement Delay Override",
    priority: 5,
    condition: "When settlement confirmation exceeds 5 minutes on primary chain",
    primaryChain: "Ethereum",
    fallbackChains: ["Polygon"],
    triggers: 3,
    enabled: false,
  },
  {
    id: "6",
    name: "Emergency All-Chain Failover",
    priority: 6,
    condition: "When primary chain experiences block production halt or >30s block time",
    primaryChain: "Any",
    fallbackChains: ["Ethereum", "Polygon", "Arbitrum"],
    triggers: 0,
    enabled: true,
  },
]

const stats = [
  { label: "Active Rules", value: "6", icon: GitBranch },
  { label: "Triggers Last 24h", value: "14", icon: Lightning },
  { label: "Avg Fallback Time", value: "230ms", icon: Timer },
  { label: "Success Rate", value: "96%", icon: CheckCircle },
]

const priorityVariant: Record<number, "outline"> = {
  1: "outline",
  2: "outline",
  3: "outline",
  4: "outline",
  5: "outline",
  6: "outline",
}

export default function FallbackRulesPage() {
  const [rules, setRules] = useState<FallbackRule[]>(initialRules)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)

  // Form state
  const [primaryRail, setPrimaryRail] = useState("")
  const [fallbackRail, setFallbackRail] = useState("")
  const [trigger, setTrigger] = useState<string>("gas-spike")

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
    setPrimaryRail(rule.primaryChain)
    setFallbackRail(rule.fallbackChains.join(", "))
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

  function handleSubmit() {
    if (!primaryRail.trim() || !fallbackRail.trim()) return

    if (editingId) {
      setRules((prev) =>
        prev.map((r) =>
          r.id === editingId
            ? {
                ...r,
                primaryChain: primaryRail.trim(),
                fallbackChains: fallbackRail.split(",").map((s) => s.trim()).filter(Boolean),
                condition: `When ${triggerLabels[trigger] || trigger} detected on ${primaryRail.trim()}`,
              }
            : r
        )
      )
      toast.success("Rule updated")
    } else {
      const nextPriority = Math.max(...rules.map((r) => r.priority), 0) + 1
      const newRule: FallbackRule = {
        id: crypto.randomUUID(),
        name: `${primaryRail.trim()} to ${fallbackRail.trim()} Fallback`,
        priority: nextPriority,
        condition: `When ${triggerLabels[trigger] || trigger} detected on ${primaryRail.trim()}`,
        primaryChain: primaryRail.trim(),
        fallbackChains: fallbackRail.split(",").map((s) => s.trim()).filter(Boolean),
        triggers: 0,
        enabled: true,
      }
      setRules((prev) => [...prev, newRule])
      toast.success("Rule created")
    }
    setDialogOpen(false)
    resetForm()
  }

  function handleDelete(id: string) {
    setRules((prev) => prev.filter((r) => r.id !== id))
    toast.success("Rule deleted")
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
                    <Badge variant="outline">{rule.primaryChain}</Badge>
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
                    {rule.fallbackChains.map((chain) => (
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
