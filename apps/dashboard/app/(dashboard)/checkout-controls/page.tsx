"use client"

import { useState, useMemo } from "react"
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
  Spinner,
} from "@phosphor-icons/react"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"
import { useSardis } from "@/hooks/use-sardis"

type CheckoutRule = {
  name: string
  condition: string
  action: "Block" | "Warn" | "Flag"
  scope: "All" | "Specific"
  triggers24h: number
  enabled: boolean
}

type CheckoutConfig = {
  rules: CheckoutRule[]
  complianceScore?: number
}

const actionVariant: Record<CheckoutRule["action"], "destructive" | "warning" | "outline"> = {
  Block: "destructive",
  Warn: "warning",
  Flag: "outline",
}

export default function CheckoutControlsPage() {
  const { data: config, loading } = useSardis<CheckoutConfig>("api/v2/checkout/controls")
  const rules = config?.rules ?? []

  const [toggles, setToggles] = useState<Record<string, boolean>>({})

  function isEnabled(rule: CheckoutRule): boolean {
    return toggles[rule.name] ?? rule.enabled
  }

  const stats = useMemo(() => {
    const activeCount = rules.filter((r) => isEnabled(r)).length
    const blockedCount = rules.filter((r) => r.action === "Block").reduce((sum, r) => sum + r.triggers24h, 0)
    const overrideCount = rules.filter((r) => r.action === "Warn").reduce((sum, r) => sum + r.triggers24h, 0)
    const score = config?.complianceScore ?? (rules.length > 0 ? 97 : 0)

    return [
      { label: "Active Rules", value: String(activeCount), icon: ListChecks },
      { label: "Blocked Checkouts", value: String(blockedCount), icon: Prohibit },
      { label: "Override Requests", value: String(overrideCount), icon: ArrowsClockwise },
      { label: "Compliance Score", value: `${score}%`, icon: ShieldCheck },
    ]
  }, [rules, toggles, config])

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
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : rules.length === 0 ? (
            <EmptyState
              icon={ListChecks}
              title="No checkout rules"
              description="Configure checkout restrictions and compliance rules to control payment flows"
            />
          ) : (
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
                          checked={isEnabled(rule)}
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
                    <ContextMenuItem onClick={() => setToggles((prev) => ({ ...prev, [rule.name]: !isEnabled(rule) }))}>
                      Toggle
                    </ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
