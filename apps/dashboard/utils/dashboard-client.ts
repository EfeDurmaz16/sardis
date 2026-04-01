type DashboardApiErrorPayload = {
  error?: string
  detail?: string
  message?: string
}

export async function dashboardApiFetch<T>(input: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  const response = await fetch(input, {
    ...init,
    headers,
    cache: "no-store",
  })

  const text = await response.text()
  const payload = text ? safeJsonParse(text) : null

  if (!response.ok) {
    throw new Error(buildErrorMessage(response.status, payload))
  }

  return payload as T
}

function safeJsonParse(input: string): unknown {
  try {
    return JSON.parse(input)
  } catch {
    return input
  }
}

function buildErrorMessage(status: number, payload: unknown): string {
  if (payload && typeof payload === "object") {
    const candidate = payload as DashboardApiErrorPayload
    return candidate.error || candidate.detail || candidate.message || `Dashboard request failed with status ${status}`
  }
  if (typeof payload === "string" && payload.trim()) {
    return payload
  }
  return `Dashboard request failed with status ${status}`
}
