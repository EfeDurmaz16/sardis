import { NextResponse } from "next/server"

import { proxyErrorResponse, sardisProxyFetch } from "@/utils/sardis-proxy"

export async function DELETE(_: Request, context: { params: Promise<{ keyId: string }> }) {
  try {
    const { keyId } = await context.params
    await sardisProxyFetch(`/api/v2/api-keys/${keyId}`, {
      method: "DELETE",
    })
    return new NextResponse(null, { status: 204 })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
