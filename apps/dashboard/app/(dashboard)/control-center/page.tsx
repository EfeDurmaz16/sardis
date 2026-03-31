"use client"

import { useState } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
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
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuTrigger, ContextMenuSeparator,
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
  ShieldWarning,
  Faders,
  Prohibit,
  ChartBar,
  Eye,
  Timer,
  GlobeHemisphereWest,
  ListBullets,
  LockKey,
  Fingerprint,
  Warning,
} from "@phosphor-icons/react"
import { toast } from "sonner"

const stats = [
  { label: "Threat Level", value: "Low", icon: ShieldWarning, badgeVariant: "success" as const },
  { label: "Active Controls", value: "12", icon: Faders },
  { label: "Blocked Today", value: "7", icon: Prohibit },
  { label: "Security Score", value: "94/100", icon: ChartBar },
]

const securityControls = [
  { label: "Transaction Monitoring", description: "Real-time monitoring of all transaction activity", icon: Eye, enabled: true },
  { label: "Rate Limiting", description: "Throttle excessive API calls and transaction attempts", icon: Timer, enabled: true },
  { label: "Geo Blocking", description: "Block transactions from restricted geographic regions", icon: GlobeHemisphereWest, enabled: true },
  { label: "IP Allowlist", description: "Only allow connections from approved IP addresses", icon: ListBullets, enabled: false },
  { label: "2FA Enforcement", description: "Require two-factor authentication for all actions", icon: LockKey, enabled: true },
  { label: "Fraud Detection", description: "AI-powered detection of fraudulent transaction patterns", icon: Fingerprint, enabled: true },
]

type ThreatEvent = {
  message: string
  severity: "low" | "medium" | "high" | "critical"
  time: string
}

const initialThreatEvents: ThreatEvent[] = [
  { message: "Unusual login attempt from new IP region", severity: "medium", time: "2 min ago" },
  { message: "Rate limit threshold reached for API key ...x4f2", severity: "low", time: "15 min ago" },
  { message: "Geo-blocked transaction attempt from restricted zone", severity: "high", time: "32 min ago" },
  { message: "Failed authentication attempt (3rd in 10 min)", severity: "medium", time: "1 hr ago" },
  { message: "New device fingerprint detected for admin user", severity: "low", time: "2 hrs ago" },
  { message: "Suspicious transaction pattern flagged by ML model", severity: "high", time: "3 hrs ago" },
]

type BlockedEntity = {
  entity: string
  type: string
  reason: string
  blockedAt: string
  expiresAt: string
}

const initialBlockedEntities: BlockedEntity[] = [
  { entity: "192.168.14.22", type: "IP Address", reason: "Brute force attempts", blockedAt: "Mar 26, 10:14 AM", expiresAt: "Apr 2, 10:14 AM" },
  { entity: "0x9a3F...7d1B", type: "Wallet", reason: "Flagged by fraud detection", blockedAt: "Mar 25, 3:42 PM", expiresAt: "Manual review" },
  { entity: "agent-0xf2c8", type: "Agent", reason: "Exceeded daily mandate limit", blockedAt: "Mar 25, 11:08 AM", expiresAt: "Mar 26, 11:08 AM" },
  { entity: "api-key-...e4a1", type: "API Key", reason: "Suspicious request patterns", blockedAt: "Mar 24, 8:55 PM", expiresAt: "Manual review" },
  { entity: "merchant-4821", type: "Merchant", reason: "Compliance violation flagged", blockedAt: "Mar 24, 2:30 PM", expiresAt: "Apr 7, 2:30 PM" },
]

const severityColor: Record<ThreatEvent["severity"], string> = {
  low: "bg-success",
  medium: "bg-warning",
  high: "bg-warning",
  critical: "bg-destructive",
}

const mockAuditLog = [
  { time: "Mar 28, 2026 09:14 AM", action: "Control enabled by Admin" },
  { time: "Mar 27, 2026 03:42 PM", action: "Configuration updated — threshold changed to 100" },
  { time: "Mar 25, 2026 11:08 AM", action: "Control temporarily disabled for maintenance" },
  { time: "Mar 24, 2026 08:55 PM", action: "Alert triggered — 3 violations detected" },
  { time: "Mar 22, 2026 02:30 PM", action: "Control created and activated" },
]

export default function ControlCenterPage() {
  const [controls, setControls] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {}
    securityControls.forEach((c) => { init[c.label] = c.enabled })
    return init
  })
  const [threatEvents, setThreatEvents] = useState<ThreatEvent[]>(initialThreatEvents)
  const [blockedEntities, setBlockedEntities] = useState<BlockedEntity[]>(initialBlockedEntities)

  // Dialog state
  const [auditLogOpen, setAuditLogOpen] = useState(false)
  const [auditLogControl, setAuditLogControl] = useState("")
  const [configOpen, setConfigOpen] = useState(false)
  const [configControl, setConfigControl] = useState("")
  const [configThreshold, setConfigThreshold] = useState("100")
  const [configCooldown, setConfigCooldown] = useState("60")
  const [extendBlockOpen, setExtendBlockOpen] = useState(false)
  const [extendBlockEntity, setExtendBlockEntity] = useState<BlockedEntity | null>(null)
  const [extendBlockDate, setExtendBlockDate] = useState("")

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
                    <Badge variant={s.badgeVariant}>
                      {s.value}
                    </Badge>
                  ) : (
                    <p className="text-lg font-semibold tracking-tight tabular-nums">{s.value}</p>
                  )}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* 2-col: Controls + Threats */}
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
                <ContextMenu key={control.label}>
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
                        checked={controls[control.label] ?? false}
                        onCheckedChange={(checked: boolean) =>
                          setControls((prev) => ({ ...prev, [control.label]: checked }))
                        }
                      />
                    </div>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => { setControls((prev) => ({ ...prev, [control.label]: !prev[control.label] })); toast.success(controls[control.label] ? "Deactivated" : "Activated") }}>
                      {controls[control.label] ? "Disable" : "Enable"} {control.label}
                    </ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={() => { setAuditLogControl(control.label); setAuditLogOpen(true) }}>View Audit Log</ContextMenuItem>
                    <ContextMenuItem onClick={() => { setConfigControl(control.label); setConfigThreshold("100"); setConfigCooldown("60"); setConfigOpen(true) }}>Configure Rules</ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              )
            })}
          </CardContent>
        </Card>

        {/* Threat Overview */}
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Threat Overview</CardTitle>
          </CardHeader>
          <CardContent className="divide-y">
            {threatEvents.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">No active threats</p>
            ) : (
              threatEvents.map((event, i) => (
                <ContextMenu key={`${event.message}-${i}`}>
                  <ContextMenuTrigger>
                    <div className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
                      <span className={`mt-1.5 h-1.5 w-1.5 rounded-full flex-shrink-0 ${severityColor[event.severity]}`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm">{event.message}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <p className="text-xs text-muted-foreground">{event.time}</p>
                          {event.severity === "critical" && <Badge variant="destructive" className="text-[10px] px-1.5 py-0 h-4">Critical</Badge>}
                        </div>
                      </div>
                    </div>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(event.message); toast.success("Copied to clipboard") }}>Copy Message</ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={() => toast.info("Opening investigation...")}>Investigate Threat</ContextMenuItem>
                    <ContextMenuItem onClick={() => { setThreatEvents((prev) => prev.filter((_, idx) => idx !== i)); toast.success("Threat dismissed") }}>Dismiss</ContextMenuItem>
                    <ContextMenuItem onClick={() => { setThreatEvents((prev) => prev.map((e, idx) => idx === i ? { ...e, severity: "critical" } : e)); toast.warning("Escalated to critical") }}>Escalate to Critical</ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Active Blocks Table */}
      <Card>
        <CardHeader className="border-b">
          <CardTitle>Active Blocks</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          <div className="overflow-x-auto -mx-4 sm:mx-0">
            {blockedEntities.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">No active blocks</p>
            ) : (
              <Table className="min-w-[600px]">
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-4">Entity</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead>Blocked At</TableHead>
                    <TableHead>Expires At</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {blockedEntities.map((entity, i) => (
                    <ContextMenu key={`${entity.entity}-${i}`}>
                      <ContextMenuTrigger render={<TableRow />}>
                        <TableCell className="pl-4 font-mono text-xs">{entity.entity}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{entity.type}</Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground truncate max-w-[200px]">{entity.reason}</TableCell>
                        <TableCell className="text-muted-foreground">{entity.blockedAt}</TableCell>
                        <TableCell className="text-muted-foreground">{entity.expiresAt}</TableCell>
                      </ContextMenuTrigger>
                      <ContextMenuContent>
                        <ContextMenuItem onClick={() => { navigator.clipboard.writeText(entity.entity); toast.success("Copied to clipboard") }}>Copy Entity</ContextMenuItem>
                        <ContextMenuItem onClick={() => { navigator.clipboard.writeText(entity.reason); toast.success("Copied to clipboard") }}>Copy Reason</ContextMenuItem>
                        <ContextMenuSeparator />
                        <ContextMenuItem onClick={() => { setBlockedEntities((prev) => prev.filter((_, idx) => idx !== i)); toast.success(`Unblocked ${entity.entity}`) }}>Unblock Entity</ContextMenuItem>
                        <ContextMenuItem onClick={() => { setExtendBlockEntity(entity); setExtendBlockDate(""); setExtendBlockOpen(true) }}>Extend Block</ContextMenuItem>
                        <ContextMenuItem onClick={() => toast.info("Opening history...")}>View Full History</ContextMenuItem>
                      </ContextMenuContent>
                    </ContextMenu>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Audit Log Dialog */}
      <Dialog open={auditLogOpen} onOpenChange={setAuditLogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Audit Log</DialogTitle>
            <DialogDescription>{auditLogControl}</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            {mockAuditLog.map((entry, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                <span className="text-xs text-muted-foreground whitespace-nowrap mt-0.5">{entry.time}</span>
                <span>{entry.action}</span>
              </div>
            ))}
          </div>
          <DialogFooter showCloseButton />
        </DialogContent>
      </Dialog>

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
            <Button onClick={() => { setConfigOpen(false); toast.success(`Configuration saved for ${configControl}`) }}>Save Configuration</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Extend Block Dialog */}
      <Dialog open={extendBlockOpen} onOpenChange={setExtendBlockOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Extend Block</DialogTitle>
            <DialogDescription>
              Extend the block duration for {extendBlockEntity?.entity}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Current Expiry</label>
              <p className="text-sm text-muted-foreground">{extendBlockEntity?.expiresAt}</p>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">New Expiry Date</label>
              <Input type="date" value={extendBlockDate} onChange={(e) => setExtendBlockDate(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={() => {
              if (!extendBlockDate || !extendBlockEntity) return
              const formatted = new Date(extendBlockDate).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
              setBlockedEntities((prev) => prev.map((e) => e.entity === extendBlockEntity.entity ? { ...e, expiresAt: formatted } : e))
              setExtendBlockOpen(false)
              toast.success(`Block extended for ${extendBlockEntity.entity} until ${formatted}`)
            }}>Extend Block</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
