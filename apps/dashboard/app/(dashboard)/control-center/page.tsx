"use client"

import { useState } from "react"
import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuTrigger, ContextMenuSeparator,
} from "@/components/ui/context-menu"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose,
} from "@/components/ui/dialog"
import {
  ShieldWarning, Faders, Prohibit, ChartBar, Eye, Timer, GlobeHemisphereWest,
  ListBullets, LockKey, Fingerprint, Spinner,
} from "@phosphor-icons/react"
import { toast } from "sonner"
import { useSardis } from "@/hooks/use-sardis"

type KillSwitchStatus = {
  global_kill: boolean
  chain_pauses: Record<string, boolean>
  agent_pauses: string[]
  pause_count: number
}

const securityControls = [
  { label: "Transaction Monitoring", description: "Real-time monitoring of all transaction activity", icon: Eye, key: "monitoring" },
  { label: "Rate Limiting", description: "Throttle excessive API calls and transaction attempts", icon: Timer, key: "rate_limiting" },
  { label: "Geo Blocking", description: "Block transactions from restricted geographic regions", icon: GlobeHemisphereWest, key: "geo_blocking" },
  { label: "IP Allowlist", description: "Only allow connections from approved IP addresses", icon: ListBullets, key: "ip_allowlist" },
  { label: "2FA Enforcement", description: "Require two-factor authentication for all actions", icon: LockKey, key: "2fa" },
  { label: "Fraud Detection", description: "AI-powered detection of fraudulent transaction patterns", icon: Fingerprint, key: "fraud_detection" },
]

export default function ControlCenterPage() {
  const { data: ksStatus, loading, refetch } = useSardis<KillSwitchStatus>("api/v2/guardrails/kill-switch/status")

  const [controls, setControls] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {}
    securityControls.forEach((c) => { init[c.key] = false })
    return init
  })

  // Dialog state
  const [configOpen, setConfigOpen] = useState(false)
  const [configControl, setConfigControl] = useState("")
  const [configThreshold, setConfigThreshold] = useState("100")
  const [configCooldown, setConfigCooldown] = useState("60")

  const globalKill = ksStatus?.global_kill ?? false
  const pauseCount = ksStatus?.pause_count ?? 0
  const chainPauses = ksStatus?.chain_pauses ?? {}
  const pausedChains = Object.entries(chainPauses).filter(([, paused]) => paused).map(([chain]) => chain)

  const stats = [
    { label: "Kill Switch", value: globalKill ? "Active" : "Inactive", icon: ShieldWarning, badgeVariant: globalKill ? "destructive" as const : "success" as const },
    { label: "Controls", value: `${securityControls.length}`, icon: Faders },
    { label: "Chain Pauses", value: String(pausedChains.length), icon: Prohibit },
    { label: "Agent Pauses", value: String(ksStatus?.agent_pauses?.length ?? 0), icon: ChartBar },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Control Center</h1>
        <p className="text-sm text-muted-foreground">Central security dashboard and threat management</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
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
                  {s.badgeVariant ? (
                    <Badge variant={s.badgeVariant}>{loading ? "…" : s.value}</Badge>
                  ) : (
                    <p className="text-lg font-semibold tracking-tight tabular-nums">{loading ? "—" : s.value}</p>
                  )}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* 2-col: Controls + Chain Pauses */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Security Controls */}
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Security Controls</CardTitle>
          </CardHeader>
          <CardContent className="divide-y">
            {securityControls.map((control) => {
              const Ico = control.icon
              return (
                <ContextMenu key={control.key}>
                  <ContextMenuTrigger>
                    <div className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                          <Ico className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">{control.label}</p>
                          <p className="text-xs text-muted-foreground">{control.description}</p>
                        </div>
                      </div>
                      <Switch
                        checked={controls[control.key] ?? false}
                        onCheckedChange={(checked: boolean) =>
                          setControls((prev) => ({ ...prev, [control.key]: checked }))
                        }
                      />
                    </div>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={async () => {
                      const newState = !controls[control.key]
                      setControls((prev) => ({ ...prev, [control.key]: newState }))
                      try {
                        const res = await fetch("/api/sardis/api/v2/control-center/config", {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ control: control.key, enabled: newState }),
                        })
                        if (!res.ok) throw new Error("Failed")
                        toast.success(newState ? "Activated" : "Deactivated")
                        refetch()
                      } catch {
                        setControls((prev) => ({ ...prev, [control.key]: !newState }))
                        toast.error("Failed to toggle control")
                      }
                    }}>
                      {controls[control.key] ? "Disable" : "Enable"} {control.label}
                    </ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={() => { setConfigControl(control.label); setConfigThreshold("100"); setConfigCooldown("60"); setConfigOpen(true) }}>Configure Rules</ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              )
            })}
          </CardContent>
        </Card>

        {/* Chain Pause Status */}
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Chain Status</CardTitle>
          </CardHeader>
          <CardContent className="divide-y">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : Object.keys(chainPauses).length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">No chain status data available. Kill switch not configured.</p>
            ) : (
              Object.entries(chainPauses).map(([chain, paused]) => (
                <div key={chain} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                  <div className="flex items-center gap-3">
                    <span className={`h-2 w-2 rounded-full ${paused ? "bg-destructive" : "bg-success"}`} />
                    <span className="text-sm font-medium">{chain}</span>
                  </div>
                  <Badge variant={paused ? "destructive" : "success"}>
                    {paused ? "Paused" : "Active"}
                  </Badge>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Agent Pauses */}
      {(ksStatus?.agent_pauses?.length ?? 0) > 0 && (
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Paused Agents</CardTitle>
          </CardHeader>
          <CardContent className="px-0">
            <div className="overflow-x-auto -mx-4 sm:mx-0">
              <Table className="min-w-[400px]">
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-4">Agent ID</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(ksStatus?.agent_pauses ?? []).map((agentId) => (
                    <TableRow key={agentId}>
                      <TableCell className="pl-4 font-mono text-xs">{agentId}</TableCell>
                      <TableCell>
                        <Badge variant="destructive">Paused</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Configure Rules Dialog */}
      <Dialog open={configOpen} onOpenChange={setConfigOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Configure Rules</DialogTitle>
            <DialogDescription>{configControl}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Alert Threshold</label>
              <Input type="number" value={configThreshold} onChange={(e) => setConfigThreshold(e.target.value)} placeholder="100" />
              <p className="text-xs text-muted-foreground">Number of violations before alert triggers</p>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Cooldown Period (seconds)</label>
              <Input type="number" value={configCooldown} onChange={(e) => setConfigCooldown(e.target.value)} placeholder="60" />
              <p className="text-xs text-muted-foreground">Minimum time between consecutive alerts</p>
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={async () => {
              try {
                const res = await fetch("/api/sardis/api/v2/control-center/config", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    control: configControl,
                    threshold: parseInt(configThreshold),
                    cooldown: parseInt(configCooldown),
                  }),
                })
                if (!res.ok) throw new Error("Failed")
                toast.success(`Configuration saved for ${configControl}`)
                setConfigOpen(false)
                refetch()
              } catch {
                toast.error("Failed to save configuration")
              }
            }}>Save Configuration</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
