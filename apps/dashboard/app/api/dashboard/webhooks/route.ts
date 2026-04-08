import { NextResponse } from "next/server"

import { proxyErrorResponse, sardisProxyFetch, sardisProxyListFetch } from "@/utils/sardis-proxy"

type RemoteWebhook = {
  subscription_id: string
  url: string
  events: string[]
  secret?: string | null
  is_active: boolean
  total_deliveries: number
  successful_deliveries: number
  failed_deliveries: number
  last_delivery_at: string | null
  created_at: string
}

type RemoteWebhookEventTypes = {
  event_types: string[]
}

type CreateWebhookRequest = {
  url: string
  events: string[]
}

export async function GET() {
  try {
    const [webhooks, eventTypes] = await Promise.all([
      sardisProxyListFetch<RemoteWebhook>("/api/v2/webhooks"),
      sardisProxyFetch<RemoteWebhookEventTypes>("/api/v2/webhooks/event-types"),
    ])

    return NextResponse.json({
      webhooks,
      eventTypes: eventTypes.event_types,
    })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as CreateWebhookRequest
    const response = await sardisProxyFetch("/api/v2/webhooks", {
      method: "POST",
      body: JSON.stringify(body),
    })
    return NextResponse.json(response, { status: 201 })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
