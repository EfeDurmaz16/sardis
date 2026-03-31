import { NextResponse } from "next/server"

import { proxyErrorResponse, sardisProxyFetch } from "@/utils/sardis-proxy"

export async function DELETE(_: Request, context: { params: Promise<{ webhookId: string }> }) {
  try {
    const { webhookId } = await context.params
    await sardisProxyFetch(`/api/v2/webhooks/${webhookId}`, {
      method: "DELETE",
    })
    return new NextResponse(null, { status: 204 })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
