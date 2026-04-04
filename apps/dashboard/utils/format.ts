/**
 * Shared formatting utilities used across dashboard pages.
 * Consolidates duplicate implementations from wallets, api-keys, agents, overview, billing.
 */

/**
 * Formats an ISO date string (or Date) into a human-readable relative time string.
 * e.g. "3 minutes ago", "2 hours ago", "5 days ago"
 */
export function formatRelativeTime(value: string | Date | null): string {
  if (!value) return "Never"

  const date = typeof value === "string" ? new Date(value) : value
  const deltaSeconds = Math.max(1, Math.floor((Date.now() - date.getTime()) / 1000))

  const buckets = [
    { limit: 60, divisor: 1, unit: "second" as const },
    { limit: 3600, divisor: 60, unit: "minute" as const },
    { limit: 86400, divisor: 3600, unit: "hour" as const },
  ]

  for (const bucket of buckets) {
    if (deltaSeconds < bucket.limit) {
      const amount = Math.floor(deltaSeconds / bucket.divisor)
      return `${amount} ${bucket.unit}${amount === 1 ? "" : "s"} ago`
    }
  }

  const days = Math.floor(deltaSeconds / 86400)
  return `${days} day${days === 1 ? "" : "s"} ago`
}

/**
 * Formats a numeric amount as USD currency string.
 * e.g. formatMoney(1234.56) => "$1,234.56"
 *      formatMoney("50000") => "$50,000"
 */
export function formatMoney(amount: number | string, currency: string = "USD"): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount
  if (!Number.isFinite(num)) return "$0.00"

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: num >= 1000 ? 0 : 2,
    maximumFractionDigits: num >= 1000 ? 0 : 2,
  }).format(num)
}

/**
 * Shortens a blockchain address or long ID for display.
 * e.g. "0x1234567890abcdef1234567890abcdef12345678" => "0x1234...5678"
 */
export function shortenAddress(addr: string, chars: number = 6): string {
  if (!addr) return ""
  if (addr.length <= chars * 2 + 3) return addr
  return `${addr.slice(0, chars)}...${addr.slice(-Math.min(chars, 4))}`
}
