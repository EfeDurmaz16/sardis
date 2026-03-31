"use client"

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
} from "@phosphor-icons/react"
import { type Icon } from "@phosphor-icons/react"

type ChecklistItem = {
  title: string
  description: string
  status: "Complete" | "Pending" | "Required"
  icon: Icon
}

const checklist: ChecklistItem[] = [
  {
    title: "API Integration",
    description: "Connect your application to the Sardis API with valid credentials",
    status: "Complete",
    icon: Code,
  },
  {
    title: "Webhook Setup",
    description: "Configure at least one webhook endpoint for event notifications",
    status: "Complete",
    icon: PaperPlaneTilt,
  },
  {
    title: "KYC Verification",
    description: "Complete identity verification for your organization",
    status: "Complete",
    icon: UserCheck,
  },
  {
    title: "Fund Initial Wallet",
    description: "Deposit funds into your primary wallet to enable transactions",
    status: "Complete",
    icon: Wallet,
  },
  {
    title: "Set Spending Limits",
    description: "Configure daily, weekly, and monthly spending limits for agents",
    status: "Complete",
    icon: Gauge,
  },
  {
    title: "Configure Policies",
    description: "Set up transaction policies and approval rules",
    status: "Complete",
    icon: Shield,
  },
  {
    title: "Enable 2FA",
    description: "Require two-factor authentication for all team members",
    status: "Pending",
    icon: Lock,
  },
  {
    title: "Set Up Alerts",
    description: "Configure alerts for critical events and threshold breaches",
    status: "Pending",
    icon: Bell,
  },
  {
    title: "Test Transactions",
    description: "Run at least 3 test transactions in sandbox environment",
    status: "Required",
    icon: Terminal,
  },
  {
    title: "Review Security",
    description: "Complete a security review and sign off on the configuration",
    status: "Required",
    icon: Eye,
  },
]

const statusConfig: Record<string, { variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning"; dotColor: string }> = {
  Complete: { variant: "success", dotColor: "text-success" },
  Pending: { variant: "warning", dotColor: "text-warning" },
  Required: { variant: "destructive", dotColor: "text-destructive" },
}

const completedCount = checklist.filter((c) => c.status === "Complete").length

export default function GoLivePage() {
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
                {completedCount}/{checklist.length} complete
              </p>
            </div>
            <span className="text-2xl font-bold tracking-tight tabular-nums">
              {Math.round((completedCount / checklist.length) * 100)}%
            </span>
          </div>
          <Progress value={(completedCount / checklist.length) * 100} />
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        {checklist.map((item) => {
          const Ico = item.icon
          const cfg = statusConfig[item.status]
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
