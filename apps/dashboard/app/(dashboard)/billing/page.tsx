"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import {
  CreditCard,
  Lightning,
  Users,
  TrendUp,
  CheckCircle,
  WarningCircle,
  ArrowSquareOut,
  Buildings,
  SpinnerGap,
} from "@phosphor-icons/react"
import { toast } from "sonner"

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").trim()

interface BillingPlan {
  plan: string
  price_monthly_cents: number
  api_calls_per_month: number | null
  agents: number | null
  tx_fee_bps: number
  monthly_tx_volume_cents: number | null
}

interface BillingUsage {
  api_calls_used: number
  api_calls_limit: number | null
  tx_volume_cents: number
  tx_volume_limit_cents: number | null
  agents_used: number
  agents_limit: number | null
}

interface BillingAccount {
  plan: string
  status: string
  usage: BillingUsage
  stripe_customer_id: string | null
  current_period_end: string | null
}

const PLAN_LABELS: Record<string, string> = {
  dev: "Dev",
  starter: "Starter",
  growth: "Growth",
  enterprise: "Enterprise",
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
  }).format(cents / 100)
}

function formatNumber(n: number | null): string {
  if (n === null) return "Unlimited"
  return new Intl.NumberFormat("en-US").format(n)
}

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {}
  try {
    const token = localStorage.getItem("sardis_session")
    if (token) return { Authorization: `Bearer ${token}` }
  } catch { /* SSR safety */ }
  return {}
}

export default function BillingPage() {
  const [loading, setLoading] = useState(true)
  const [account, setAccount] = useState<BillingAccount | null>(null)
  const [plans, setPlans] = useState<BillingPlan[]>([])
  const [error, setError] = useState(false)
  const [upgrading, setUpgrading] = useState<string | null>(null)
  const [portalLoading, setPortalLoading] = useState(false)
  const [provider, setProvider] = useState<{ provider: string; portal_label: string }>({ provider: "stripe", portal_label: "Manage Billing" })

  useEffect(() => {
    fetchBillingData()
    fetchProvider()
  }, [])

  async function fetchProvider() {
    try {
      const res = await fetch(`${API_URL}/api/v2/billing/provider`)
      if (res.ok) {
        const data = await res.json()
        setProvider(data)
      }
    } catch { /* fallback to stripe labels */ }
  }

  async function fetchBillingData() {
    setLoading(true)
    try {
      const headers = { ...getAuthHeaders(), "Content-Type": "application/json" }

      const [accountRes, plansRes] = await Promise.all([
        fetch(`${API_URL}/api/v2/billing/account`, { headers }).catch(() => null),
        fetch(`${API_URL}/api/v2/billing/plans`, { headers }).catch(() => null),
      ])

      if (accountRes?.ok) {
        const raw = await accountRes.json()
        if (raw.account) {
          setAccount({
            plan: raw.account.plan ?? "dev",
            status: raw.account.status ?? "active",
            usage: raw.usage ?? { api_calls_used: 0, api_calls_limit: null, tx_volume_cents: 0, tx_volume_limit_cents: null, agents_used: 0, agents_limit: null },
            stripe_customer_id: raw.account.stripe_customer_id ?? null,
            current_period_end: raw.account.current_period_end ?? null,
          })
        } else {
          setAccount(raw)
        }
      } else {
        setError(true)
      }

      if (plansRes?.ok) {
        const data = await plansRes.json()
        const order = ["dev", "starter", "growth", "enterprise"]
        const sorted = [...(data.plans ?? [])].sort(
          (a: BillingPlan, b: BillingPlan) => order.indexOf(a.plan) - order.indexOf(b.plan)
        )
        setPlans(sorted)
      }
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  async function handleUpgrade(plan: string) {
    setUpgrading(plan)
    try {
      const headers = { ...getAuthHeaders(), "Content-Type": "application/json" }
      const res = await fetch(`${API_URL}/api/v2/billing/checkout`, {
        method: "POST",
        headers,
        body: JSON.stringify({ plan }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data.checkout_url) {
          window.open(data.checkout_url, "_blank")
          toast.success("Checkout opened in a new tab")
        }
      } else {
        const err = await res.json().catch(() => null)
        toast.error(err?.detail || "Billing is being set up. Contact support@sardis.sh")
      }
    } catch {
      toast.error("Network error. Please try again.")
    } finally {
      setUpgrading(null)
    }
  }

  async function handlePortal() {
    setPortalLoading(true)
    try {
      const headers = getAuthHeaders()
      const res = await fetch(`${API_URL}/api/v2/billing/portal`, {
        method: "POST",
        headers,
      })
      if (res.ok) {
        const data = await res.json()
        if (data.portal_url) {
          window.open(data.portal_url, "_blank")
        }
      } else {
        toast.error("Billing portal unavailable. Contact support@sardis.sh")
      }
    } catch {
      toast.error("Network error.")
    } finally {
      setPortalLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <SpinnerGap className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const currentPlan = account?.plan ?? "dev"
  const status = account?.status ?? "active"
  const usage = account?.usage ?? {
    api_calls_used: 0, api_calls_limit: null,
    tx_volume_cents: 0, tx_volume_limit_cents: null,
    agents_used: 0, agents_limit: null,
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
        <p className="text-sm text-muted-foreground">Manage your plan, usage, and payment details</p>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
          <WarningCircle className="w-4 h-4 text-amber-600 shrink-0" />
          <p className="text-sm text-amber-800">Billing not configured. You are on the Free plan.</p>
        </div>
      )}

      {/* Current Plan + Usage */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-muted-foreground" />
              Current Plan
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-lg font-semibold">{PLAN_LABELS[currentPlan] ?? currentPlan}</p>
                <Badge variant={status === "active" ? "default" : "secondary"} className="mt-1">
                  {status}
                </Badge>
              </div>
              {plans.find((p) => p.plan === currentPlan) && (
                <p className="text-2xl font-bold tabular-nums">
                  {formatCents(plans.find((p) => p.plan === currentPlan)!.price_monthly_cents)}
                  <span className="text-sm font-normal text-muted-foreground">/mo</span>
                </p>
              )}
            </div>
            {account?.current_period_end && (
              <p className="text-xs text-muted-foreground">
                Current period ends {new Date(account.current_period_end).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
              </p>
            )}
            <Button variant="outline" size="sm" onClick={handlePortal} disabled={portalLoading} className="w-full">
              {portalLoading ? <SpinnerGap className="w-4 h-4 mr-2 animate-spin" /> : <ArrowSquareOut className="w-4 h-4 mr-2" />}
              {provider.portal_label}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendUp className="w-4 h-4 text-muted-foreground" />
              Usage
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* API Calls */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-1.5"><Lightning className="w-3.5 h-3.5" /> API Calls</span>
                <span className="text-muted-foreground tabular-nums">
                  {formatNumber(usage.api_calls_used)} / {formatNumber(usage.api_calls_limit)}
                </span>
              </div>
              <Progress value={usage.api_calls_limit ? Math.min((usage.api_calls_used / usage.api_calls_limit) * 100, 100) : 5} />
            </div>

            {/* Agents */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-1.5"><Users className="w-3.5 h-3.5" /> Agents</span>
                <span className="text-muted-foreground tabular-nums">
                  {formatNumber(usage.agents_used)} / {formatNumber(usage.agents_limit)}
                </span>
              </div>
              <Progress value={usage.agents_limit ? Math.min((usage.agents_used / usage.agents_limit) * 100, 100) : 5} />
            </div>

            {/* Tx Volume */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-1.5"><TrendUp className="w-3.5 h-3.5" /> Transaction Volume</span>
                <span className="text-muted-foreground tabular-nums">
                  {formatCents(usage.tx_volume_cents)} / {usage.tx_volume_limit_cents ? formatCents(usage.tx_volume_limit_cents) : "Unlimited"}
                </span>
              </div>
              <Progress value={usage.tx_volume_limit_cents ? Math.min((usage.tx_volume_cents / usage.tx_volume_limit_cents) * 100, 100) : 5} />
            </div>
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Plans Grid */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Available Plans</h2>
        <div className="grid gap-4 md:grid-cols-4">
          {plans.map((plan) => {
            const isCurrent = plan.plan === currentPlan
            const isPopular = plan.plan === "starter"
            const isEnterprise = plan.plan === "enterprise"
            const priceLabel = plan.price_monthly_cents === 0 ? "Free" : `${formatCents(plan.price_monthly_cents)}/mo`

            return (
              <Card key={plan.plan} className={`relative flex flex-col ${isCurrent ? "border-primary ring-1 ring-primary/20" : ""} ${isPopular && !isCurrent ? "border-primary/40" : ""}`}>
                {isPopular && !isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-primary text-primary-foreground text-[10px]">Most Popular</Badge>
                  </div>
                )}
                <CardHeader className="pb-3 pt-6 px-6">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-sm">{PLAN_LABELS[plan.plan] ?? plan.plan}</CardTitle>
                    {isCurrent && <Badge variant="outline" className="text-[10px]">Current</Badge>}
                  </div>
                  <p className="text-2xl font-bold mt-2">{priceLabel}</p>
                </CardHeader>
                <CardContent className="flex-1 space-y-3.5 text-sm text-muted-foreground px-6 pb-6">
                  <div className="flex justify-between py-0.5"><span>API calls</span><span className="font-medium text-foreground">{formatNumber(plan.api_calls_per_month)}</span></div>
                  <div className="flex justify-between py-0.5"><span>Agents</span><span className="font-medium text-foreground">{plan.agents === null ? "Unlimited" : plan.agents}</span></div>
                  <div className="flex justify-between py-0.5"><span>Tx fee</span><span className="font-medium text-foreground">{plan.tx_fee_bps} bps</span></div>
                  <div className="flex justify-between py-0.5"><span>Volume</span><span className="font-medium text-foreground">{plan.monthly_tx_volume_cents === null ? "Unlimited" : formatCents(plan.monthly_tx_volume_cents)}</span></div>
                </CardContent>
                <div className="p-6 pt-0">
                  {isCurrent ? (
                    <div className="flex items-center justify-center gap-1.5 py-2 text-sm text-primary font-medium">
                      <CheckCircle className="w-4 h-4" />
                      Current Plan
                    </div>
                  ) : isEnterprise ? (
                    <Button variant="outline" className="w-full" onClick={() => window.open("https://cal.com/sardis/15min", "_blank")}>
                      <Buildings className="w-4 h-4 mr-2" />
                      Talk to Sales
                    </Button>
                  ) : (
                    <Button
                      className="w-full"
                      onClick={() => handleUpgrade(plan.plan)}
                      disabled={upgrading !== null}
                    >
                      {upgrading === plan.plan ? <SpinnerGap className="w-4 h-4 mr-2 animate-spin" /> : null}
                      {upgrading === plan.plan ? "Redirecting..." : "Upgrade"}
                    </Button>
                  )}
                </div>
              </Card>
            )
          })}
        </div>
      </div>
    </div>
  )
}
