"use client"

import { useMemo } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import {
  CheckCircle,
  Circle,
  Code,
  PaperPlaneTilt,
  UserCheck,
  Wallet,
  Gauge,
  Shield,
  Lock,
  Bell,
  Terminal,
  Eye,
  Spinner,
} from "@phosphor-icons/react"
import { type Icon } from "@phosphor-icons/react"
import { EmptyState } from "@/components/empty-state"
import { useSardis } from "@/hooks/use-sardis"

type ChecklistItem = {
  title: string
  description: string
  status: "Complete" | "Pending" | "Required"
  icon?: string
}

type GoLiveChecklist = {
  items: ChecklistItem[]
}

const iconMap: Record<string, Icon> = {
  Code,
  PaperPlaneTilt,
  UserCheck,
  Wallet,
  Gauge,
  Shield,
  Lock,
  Bell,
  Terminal,
  Eye,
}

const statusConfig: Record<string, { variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning"; dotColor: string }> = {
  Complete: { variant: "success", dotColor: "text-success" },
  Pending: { variant: "warning", dotColor: "text-warning" },
  Required: { variant: "destructive", dotColor: "text-destructive" },
}

export default function GoLivePage() {
  const { data: checklist, loading } = useSardis<GoLiveChecklist>("api/v2/go-live/status")
  const items = checklist?.items ?? []

  const completedCount = useMemo(() => items.filter((c) => c.status === "Complete").length, [items])
  const totalCount = items.length
  const progressPct = totalCount > 0 ? (completedCount / totalCount) * 100 : 0

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Go Live</h1>
          <p className="text-sm text-muted-foreground">Complete the checklist to launch your production environment</p>
        </div>
        <div className="flex items-center justify-center py-16">
          <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Go Live</h1>
          <p className="text-sm text-muted-foreground">Complete the checklist to launch your production environment</p>
        </div>
        <Card>
          <CardContent className="px-0">
            <EmptyState
              icon={CheckCircle}
              title="No checklist available"
              description="The go-live checklist will appear here once your environment is configured"
            />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Go Live</h1>
        <p className="text-sm text-muted-foreground">
          Complete the checklist to launch your production environment
        </p>
      </div>

      <Card>
        <CardContent className="space-y-3 pt-1">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Production Readiness</p>
              <p className="text-xs text-muted-foreground">
                {completedCount}/{totalCount} complete
              </p>
            </div>
            <span className="text-2xl font-bold tracking-tight tabular-nums">
              {Math.round(progressPct)}%
            </span>
          </div>
          <Progress value={progressPct} />
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        {items.map((item) => {
          const Ico = (item.icon && iconMap[item.icon]) ? iconMap[item.icon] : Code
          const cfg = statusConfig[item.status] ?? statusConfig.Pending
          const isComplete = item.status === "Complete"
          return (
            <Card key={item.title} size="sm">
              <CardContent className="flex items-start gap-3">
                <div className="mt-0.5 flex-shrink-0">
                  {isComplete ? (
                    <CheckCircle weight="fill" className="h-5 w-5 text-success" />
                  ) : (
                    <Circle className={`h-5 w-5 ${cfg.dotColor}`} />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Ico className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <p className="text-sm font-medium truncate">{item.title}</p>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">{item.description}</p>
                </div>
                <Badge variant={cfg.variant} className="flex-shrink-0 text-[10px]">
                  {item.status}
                </Badge>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
