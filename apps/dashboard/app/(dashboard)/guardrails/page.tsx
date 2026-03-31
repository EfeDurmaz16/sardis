"use client"

import { useMemo } from "react"
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
  Spinner,
} from "@phosphor-icons/react"
import { EmptyState } from "@/components/empty-state"
import { useSardis } from "@/hooks/use-sardis"

type Guardrail = {
  name: string
  description: string
  triggerCondition: string
  action: "Block" | "Warn" | "Limit"
  overrideAllowed: boolean
  triggers: number
}

type GuardrailConfig = {
  guardrails: Guardrail[]
  overrideRate?: number
}

const actionVariant: Record<Guardrail["action"], "destructive" | "warning" | "info"> = {
  Block: "destructive",
  Warn: "warning",
  Limit: "info",
}

export default function GuardrailsPage() {
  const { data: config, loading } = useSardis<GuardrailConfig>("api/v2/guardrails/config")
  const guardrails = config?.guardrails ?? []

  const stats = useMemo(() => {
    const totalTriggers = guardrails.reduce((sum, g) => sum + g.triggers, 0)
    const overridable = guardrails.filter((g) => g.overrideAllowed).length
    const overrideRate = guardrails.length > 0
      ? ((overridable / guardrails.length) * 100).toFixed(1)
      : "0.0"

    return [
      { label: "Active Guardrails", value: String(guardrails.length), icon: ShieldWarning },
      { label: "Triggers Today", value: String(totalTriggers), icon: Lightning },
      { label: "Override Rate", value: `${overrideRate}%`, icon: ArrowsClockwise },
      { label: "Coverage", value: guardrails.length > 0 ? "100%" : "0%", icon: ShieldCheck },
    ]
  }, [guardrails])

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Guardrails</h1>
          <p className="text-sm text-muted-foreground">Safety guardrails and automated protection rules</p>
        </div>
        <div className="flex items-center justify-center py-16">
          <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (guardrails.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Guardrails</h1>
          <p className="text-sm text-muted-foreground">Safety guardrails and automated protection rules</p>
        </div>
        <Card>
          <CardContent className="px-0">
            <EmptyState
              icon={ShieldWarning}
              title="No guardrails configured"
              description="Configure safety guardrails to automatically protect your agents from unauthorized or risky transactions"
            />
          </CardContent>
        </Card>
      </div>
    )
  }

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
