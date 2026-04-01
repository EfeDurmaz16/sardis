import { NextResponse } from "next/server"

import { proxyErrorResponse, sardisProxyFetch } from "@/utils/sardis-proxy"

type RemoteApiKey = {
  key_id: string
  key_prefix: string
  name: string
  scopes: string[]
  rate_limit: number
  is_active: boolean
  expires_at: string | null
  created_at: string
  last_used_at: string | null
  mode: "test" | "live"
}

type ListApiKeysResponse = {
  keys: RemoteApiKey[]
  total: number
}

type CreateApiKeyRequest = {
  name: string
  scopes: string[]
  mode: "test" | "live"
}

export async function GET() {
  try {
    const response = await sardisProxyFetch<ListApiKeysResponse>("/api/v2/api-keys")
    return NextResponse.json(response)
  } catch (error) {
    return proxyErrorResponse(error)
  }
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as CreateApiKeyRequest
    const response = await sardisProxyFetch("/api/v2/api-keys", {
      method: "POST",
      body: JSON.stringify(body),
    })
    return NextResponse.json(response, { status: 201 })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
