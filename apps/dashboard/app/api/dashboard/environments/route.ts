import { NextResponse } from "next/server"

import { getSardisApiConfig, proxyErrorResponse } from "@/utils/sardis-proxy"

type LightweightHealth = {
  status?: string
  service?: string
  version?: string
}

type DeepHealth = {
  status?: string
  components?: Record<string, { status?: string; [key: string]: unknown }>
  critical_failures?: Array<{ component: string; detail: string }>
  non_critical_failures?: Array<{ component: string; detail: string }>
}

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const response = await fetch(url, { cache: "no-store" })
    if (!response.ok) {
      return null
    }
    return (await response.json()) as T
  } catch {
    return null
  }
}

export async function GET() {
  try {
    const { baseUrl } = getSardisApiConfig()

    const [lightweight, deep] = await Promise.all([
      fetchJson<LightweightHealth>(`${baseUrl}/api/v2/health`),
      fetchJson<DeepHealth>(`${baseUrl}/health`),
    ])

    return NextResponse.json({
      proxy: {
        baseUrl,
        apiKeyConfigured: Boolean(process.env.SARDIS_API_KEY),
        browserBaseUrlConfigured: Boolean(process.env.NEXT_PUBLIC_SARDIS_API_BASE_URL),
      },
      upstream: {
        lightweight: lightweight ?? { status: "unreachable" },
        deep: deep ?? { status: "unreachable", components: {} },
      },
    })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}
