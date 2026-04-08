const COMMON_LIST_KEYS = [
  "items",
  "data",
  "results",
  "entries",
  "transactions",
  "approvals",
  "alerts",
  "anchors",
  "cards",
  "counterparties",
  "evidence",
  "exceptions",
  "invoices",
  "mandates",
  "merchants",
  "policies",
  "rules",
  "sessions",
  "tickets",
  "webhooks",
  "workflows",
] as const

function objectValues(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null
  }

  return value as Record<string, unknown>
}

export function extractListFromPayload<T>(payload: unknown): T[] | null {
  if (Array.isArray(payload)) {
    return payload as T[]
  }

  const record = objectValues(payload)
  if (!record) {
    return null
  }

  for (const key of COMMON_LIST_KEYS) {
    if (Array.isArray(record[key])) {
      return record[key] as T[]
    }
  }

  const arrayEntries = Object.values(record).filter(Array.isArray) as T[][]
  if (arrayEntries.length === 1) {
    return arrayEntries[0]
  }

  return null
}

export function extractListOrThrow<T>(payload: unknown, label: string): T[] {
  const list = extractListFromPayload<T>(payload)
  if (list) {
    return list
  }

  throw new Error(`${label} did not return a list`)
}
