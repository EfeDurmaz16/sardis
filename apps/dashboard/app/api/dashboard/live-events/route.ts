import { NextResponse } from "next/server"

import { proxyErrorResponse, sardisProxyFetch } from "@/utils/sardis-proxy"

type DashboardMetrics = {
  api_calls_24h: number
  agent_events_24h: number
  active_sessions: number
  policy_blocked_24h: number
}

type RecentEventsResponse = {
  events: unknown[]
  count: number
  message?: string
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = searchParams.get("limit") || "100"

    const [metrics, recent] = await Promise.all([
      sardisProxyFetch<DashboardMetrics>("/api/v2/dashboard/metrics"),
      sardisProxyFetch<RecentEventsResponse>(`/api/v2/events/recent?limit=${encodeURIComponent(limit)}`),
    ])

    return NextResponse.json({
      metrics,
      recent,
      streamPath: "/api/dashboard/live-events/stream",
    })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
