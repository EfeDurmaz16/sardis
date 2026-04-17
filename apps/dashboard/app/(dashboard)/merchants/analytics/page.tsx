"use client"

import { useState } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  CurrencyDollar,
  Robot,
  ArrowsClockwise,
  ChartLine,
  Spinner,
} from "@phosphor-icons/react"
import { useSardis } from "@/hooks/use-sardis"

type MerchantAnalytics = {
  merchant_id: string
  merchant_name: string
  total_volume: number
  transaction_count: number
  unique_agents: number
  avg_transaction: number
  settlement_method: string
  top_endpoints: { path: string; calls: number; revenue: number }[]
  daily_volume: { date: string; amount: number }[]
}

function formatUSD(value: number): string {
  return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export default function MerchantAnalyticsPage() {
  const { data, loading } = useSardis<MerchantAnalytics>("api/v2/analytics/merchants")

  // Fallback demo data when API not connected
  const analytics: MerchantAnalytics = data ?? {
    merchant_id: "merch_demo",
    merchant_name: "All Merchants",
    total_volume: 0,
    transaction_count: 0,
    unique_agents: 0,
    avg_transaction: 0,
    settlement_method: "stripe_connect",
    top_endpoints: [],
    daily_volume: [],
  }

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Spinner className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const stats = [
    { label: "Total Volume", value: formatUSD(analytics.total_volume), icon: CurrencyDollar },
    { label: "Transactions", value: String(analytics.transaction_count), icon: ArrowsClockwise },
    { label: "Unique Agents", value: String(analytics.unique_agents), icon: Robot },
    { label: "Avg Transaction", value: formatUSD(analytics.avg_transaction), icon: ChartLine },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Merchant Analytics</h1>
        <p className="text-sm text-muted-foreground">Payment volume, agent activity, and endpoint performance</p>
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

      <Card>
        <CardHeader className="border-b">
          <CardTitle>Top Endpoints by Revenue</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {analytics.top_endpoints.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <ChartLine className="h-8 w-8 text-muted-foreground/50 mb-3" />
              <p className="text-sm text-muted-foreground">No endpoint data yet</p>
              <p className="text-xs text-muted-foreground/70 mt-1">Analytics populate as agents make payments</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-4">Endpoint</TableHead>
                  <TableHead className="text-right">Calls</TableHead>
                  <TableHead className="text-right">Revenue</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {analytics.top_endpoints.map((ep) => (
                  <TableRow key={ep.path}>
                    <TableCell className="pl-4 font-mono text-sm">{ep.path}</TableCell>
                    <TableCell className="text-right tabular-nums">{ep.calls.toLocaleString()}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatUSD(ep.revenue)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Settlement</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Settlement Method</p>
              <Badge variant="outline" className="mt-1">
                {analytics.settlement_method === "stripe_connect" ? "Stripe Connect (USD)" : analytics.settlement_method}
              </Badge>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Merchant</p>
              <p className="text-sm font-medium">{analytics.merchant_name}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
