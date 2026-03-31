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
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
  ContextMenuSeparator,
} from "@/components/ui/context-menu"
import {
  ListChecks,
  Prohibit,
  ArrowsClockwise,
  ShieldCheck,
} from "@phosphor-icons/react"
import { toast } from "sonner"

type CheckoutRule = {
  name: string
  condition: string
  action: "Block" | "Warn" | "Flag"
  scope: "All" | "Specific"
  triggers24h: number
  enabled: boolean
}

const rules: CheckoutRule[] = [
  { name: "Max single transaction", condition: "Amount > $10,000", action: "Block", scope: "All", triggers24h: 3, enabled: true },
  { name: "Blocked merchant categories", condition: "MCC in restricted list", action: "Block", scope: "All", triggers24h: 1, enabled: true },
  { name: "Velocity check", condition: "> 5 transactions in 10 min", action: "Flag", scope: "All", triggers24h: 4, enabled: true },
  { name: "New merchant threshold", condition: "First-time merchant > $1,000", action: "Warn", scope: "Specific", triggers24h: 2, enabled: true },
  { name: "International transaction limit", condition: "Cross-border amount > $5,000", action: "Warn", scope: "All", triggers24h: 5, enabled: true },
  { name: "After-hours restriction", condition: "Transaction outside 6AM-10PM local", action: "Flag", scope: "Specific", triggers24h: 3, enabled: false },
  { name: "Duplicate detection", condition: "Same amount + merchant within 5 min", action: "Block", scope: "All", triggers24h: 2, enabled: true },
  { name: "Cumulative daily limit", condition: "Agent daily total > $25,000", action: "Block", scope: "All", triggers24h: 3, enabled: true },
]

const stats = [
  { label: "Active Rules", value: "8", icon: ListChecks },
  { label: "Blocked Checkouts", value: "23", icon: Prohibit },
  { label: "Override Requests", value: "4", icon: ArrowsClockwise },
  { label: "Compliance Score", value: "97%", icon: ShieldCheck },
]

const actionVariant: Record<CheckoutRule["action"], "destructive" | "warning" | "outline"> = {
  Block: "destructive",
  Warn: "warning",
  Flag: "outline",
}

export default function CheckoutControlsPage() {
  const [toggles, setToggles] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {}
    rules.forEach((r) => { init[r.name] = r.enabled })
    return init
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Checkout Controls</h1>
        <p className="text-sm text-muted-foreground">Manage checkout restrictions and compliance rules</p>
      </div>

      {/* Stats */}
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

      {/* Rules Table */}
      <Card>
        <CardHeader className="border-b">
          <CardTitle>Checkout Rules</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Rule Name</TableHead>
                <TableHead>Condition</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Scope</TableHead>
                <TableHead className="text-right">Triggers (24h)</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rules.map((rule) => (
                <ContextMenu key={rule.name}>
                  <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="pl-4 font-medium">{rule.name}</TableCell>
                      <TableCell className="text-muted-foreground">{rule.condition}</TableCell>
                      <TableCell>
                        <Badge variant={actionVariant[rule.action]}>{rule.action}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{rule.scope}</Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums font-mono text-muted-foreground">{rule.triggers24h}</TableCell>
                      <TableCell>
                        <Switch
                          checked={toggles[rule.name] ?? false}
                          onCheckedChange={(checked: boolean) =>
                            setToggles((prev) => ({ ...prev, [rule.name]: checked }))
                          }
                        />
                      </TableCell>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(JSON.stringify(rule, null, 2)); toast.success("Copied to clipboard") }}>
                      Copy
                    </ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={() => setToggles((prev) => ({ ...prev, [rule.name]: !(prev[rule.name] ?? rule.enabled) }))}>
                      Toggle
                    </ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
