"use client"

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import {
  ShieldWarning,
  Lightning,
  ArrowsClockwise,
  ShieldCheck,
} from "@phosphor-icons/react"

type Guardrail = {
  name: string
  description: string
  triggerCondition: string
  action: "Block" | "Warn" | "Limit"
  overrideAllowed: boolean
  triggers: number
}

const guardrails: Guardrail[] = [
  { name: "Max Transaction Amount", description: "Blocks transactions exceeding the per-agent maximum single transfer limit", triggerCondition: "Amount > $50,000", action: "Block", overrideAllowed: false, triggers: 4 },
  { name: "Daily Spending Limit", description: "Enforces cumulative daily spending caps for each agent", triggerCondition: "Daily total > configured limit", action: "Block", overrideAllowed: true, triggers: 7 },
  { name: "New Merchant Cooldown", description: "Requires 24-hour waiting period before transacting with newly added merchants", triggerCondition: "Merchant age < 24h", action: "Warn", overrideAllowed: true, triggers: 2 },
  { name: "Cross-chain Transfer Limit", description: "Limits volume of cross-chain transfers within a rolling 24-hour window", triggerCondition: "Cross-chain volume > $100,000/day", action: "Limit", overrideAllowed: true, triggers: 3 },
  { name: "Velocity Throttle", description: "Rate-limits rapid successive transactions to prevent automated attacks", triggerCondition: "Transactions > 30/min", action: "Block", overrideAllowed: false, triggers: 1 },
  { name: "Balance Reserve", description: "Prevents transactions that would reduce wallet balance below the minimum reserve", triggerCondition: "Post-txn balance < $1,000", action: "Block", overrideAllowed: true, triggers: 2 },
  { name: "Duplicate Payment Detection", description: "Warns when a similar payment to the same recipient is detected within 1 hour", triggerCondition: "Same amount + recipient in 1h", action: "Warn", overrideAllowed: true, triggers: 3 },
  { name: "Off-hours Transaction Block", description: "Blocks high-value transactions outside business hours unless pre-approved", triggerCondition: "Amount > $10,000 outside 9am-6pm", action: "Block", overrideAllowed: true, triggers: 1 },
]

const stats = [
  { label: "Active Guardrails", value: "15", icon: ShieldWarning },
  { label: "Triggers Today", value: "23", icon: Lightning },
  { label: "Override Rate", value: "4.2%", icon: ArrowsClockwise },
  { label: "Coverage", value: "100%", icon: ShieldCheck },
]

const actionVariant: Record<Guardrail["action"], "destructive" | "warning" | "info"> = {
  Block: "destructive",
  Warn: "warning",
  Limit: "info",
}

export default function GuardrailsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Guardrails</h1>
        <p className="text-sm text-muted-foreground">Safety guardrails and automated protection rules</p>
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

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {guardrails.map((g) => (
          <Card key={g.name}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{g.name}</span>
                <Badge variant={actionVariant[g.action]}>{g.action}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">{g.description}</p>
              <div className="flex items-center justify-between rounded-lg border bg-muted/30 px-3 py-2">
                <span className="text-xs font-medium text-muted-foreground">Trigger Condition</span>
                <span className="text-xs font-mono">{g.triggerCondition}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Override Allowed</span>
                  <Switch checked={g.overrideAllowed} size="sm" />
                </div>
                <span className="text-xs text-muted-foreground">
                  <span className="font-semibold tabular-nums text-foreground">{g.triggers}</span> triggers today
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
