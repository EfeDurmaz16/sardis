"use client"

import { useEffect, useState } from "react"
import { useTheme } from "next-themes"
import { usePathname, useRouter } from "next/navigation"
import Link from "next/link"
import { UserButton } from "@daveyplate/better-auth-ui"
import { Button, buttonVariants } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { toast } from "sonner"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  MagnifyingGlass, List, Sun, Moon, Plus, CreditCard, CaretDown, CaretRight,
} from "@phosphor-icons/react"
import { Bell } from "@phosphor-icons/react"

// TODO: Wire to real notification API — these are placeholder items
const notifications = [
  {
    message: "Agent #12 exceeded daily spending limit",
    type: "warning" as const,
    time: "2m ago",
  },
  {
    message: "Payment to MerchantCo completed",
    type: "success" as const,
    time: "15m ago",
  },
  {
    message: "Kill switch deactivated by admin",
    type: "info" as const,
    time: "1h ago",
  },
  {
    message: "Anomaly detected: unusual transaction pattern",
    type: "warning" as const,
    time: "2h ago",
  },
  {
    message: "New API key created",
    type: "info" as const,
    time: "3h ago",
  },
]

const dotColor: Record<string, string> = {
  warning: "bg-amber-500",
  success: "bg-emerald-500",
  info: "bg-blue-500",
}

/* ── Breadcrumb types & route mapping ── */

type BreadcrumbItem = {
  label: string
  href: string
}

/**
 * Maps route paths to their full breadcrumb trail.
 * Parent sections (Payments, Monitoring, etc.) mirror the sidebar groupings.
 */
const routeBreadcrumbs: Record<string, BreadcrumbItem[]> = {
  "/": [{ label: "Overview", href: "/" }],

  // Top-level nav (no parent section)
  "/agents": [
    { label: "Overview", href: "/" },
    { label: "Agents", href: "/agents" },
  ],
  "/transactions": [
    { label: "Overview", href: "/" },
    { label: "Transactions", href: "/transactions" },
  ],
  "/mandates": [
    { label: "Overview", href: "/" },
    { label: "Mandates", href: "/mandates" },
  ],
  "/wallets": [
    { label: "Overview", href: "/" },
    { label: "Wallets", href: "/wallets" },
  ],
  "/merchants": [
    { label: "Overview", href: "/" },
    { label: "Merchants", href: "/merchants" },
  ],

  // Payments
  "/virtual-cards": [
    { label: "Overview", href: "/" },
    { label: "Payments", href: "/" },
    { label: "Virtual Cards", href: "/virtual-cards" },
  ],
  "/holds": [
    { label: "Overview", href: "/" },
    { label: "Payments", href: "/" },
    { label: "Holds", href: "/holds" },
  ],
  "/invoices": [
    { label: "Overview", href: "/" },
    { label: "Payments", href: "/" },
    { label: "Invoices", href: "/invoices" },
  ],
  "/reconciliation": [
    { label: "Overview", href: "/" },
    { label: "Payments", href: "/" },
    { label: "Reconciliation", href: "/reconciliation" },
  ],

  // Monitoring
  "/live-events": [
    { label: "Overview", href: "/" },
    { label: "Monitoring", href: "/" },
    { label: "Live Events", href: "/live-events" },
  ],
  "/mpp-sessions": [
    { label: "Overview", href: "/" },
    { label: "Monitoring", href: "/" },
    { label: "MPP Sessions", href: "/mpp-sessions" },
  ],

  // Policies
  "/policy-manager": [
    { label: "Overview", href: "/" },
    { label: "Policies", href: "/" },
    { label: "Policy Manager", href: "/policy-manager" },
  ],
  "/simulation": [
    { label: "Overview", href: "/" },
    { label: "Policies", href: "/" },
    { label: "Simulation", href: "/simulation" },
  ],
  "/analytics": [
    { label: "Overview", href: "/" },
    { label: "Policies", href: "/" },
    { label: "Analytics", href: "/analytics" },
  ],
  "/api-playground": [
    { label: "Overview", href: "/" },
    { label: "Policies", href: "/" },
    { label: "API Playground", href: "/api-playground" },
  ],
  "/approval-config": [
    { label: "Overview", href: "/" },
    { label: "Policies", href: "/" },
    { label: "Approval Config", href: "/approval-config" },
  ],
  "/counterparties": [
    { label: "Overview", href: "/" },
    { label: "Policies", href: "/" },
    { label: "Counterparties", href: "/counterparties" },
  ],
  "/fallback-rules": [
    { label: "Overview", href: "/" },
    { label: "Policies", href: "/" },
    { label: "Fallback Rules", href: "/fallback-rules" },
  ],
  "/workflows": [
    { label: "Overview", href: "/" },
    { label: "Policies", href: "/" },
    { label: "Workflows", href: "/workflows" },
  ],

  // Security
  "/kill-switch": [
    { label: "Overview", href: "/" },
    { label: "Security", href: "/" },
    { label: "Kill Switch", href: "/kill-switch" },
  ],
  "/control-center": [
    { label: "Overview", href: "/" },
    { label: "Security", href: "/" },
    { label: "Control Center", href: "/control-center" },
  ],
  "/approvals": [
    { label: "Overview", href: "/" },
    { label: "Security", href: "/" },
    { label: "Approvals", href: "/approvals" },
  ],
  "/checkout-controls": [
    { label: "Overview", href: "/" },
    { label: "Security", href: "/" },
    { label: "Checkout Controls", href: "/checkout-controls" },
  ],
  "/evidence": [
    { label: "Overview", href: "/" },
    { label: "Security", href: "/" },
    { label: "Evidence", href: "/evidence" },
  ],
  "/observability": [
    { label: "Overview", href: "/" },
    { label: "Security", href: "/" },
    { label: "Observability", href: "/observability" },
  ],
  "/anomaly-detection": [
    { label: "Overview", href: "/" },
    { label: "Security", href: "/" },
    { label: "Anomaly Detection", href: "/anomaly-detection" },
  ],
  "/audit-anchors": [
    { label: "Overview", href: "/" },
    { label: "Security", href: "/" },
    { label: "Audit Anchors", href: "/audit-anchors" },
  ],
  "/exceptions": [
    { label: "Overview", href: "/" },
    { label: "Security", href: "/" },
    { label: "Exceptions", href: "/exceptions" },
  ],
  "/guardrails": [
    { label: "Overview", href: "/" },
    { label: "Security", href: "/" },
    { label: "Guardrails", href: "/guardrails" },
  ],
  "/provider-health": [
    { label: "Overview", href: "/" },
    { label: "Security", href: "/" },
    { label: "Provider Health", href: "/provider-health" },
  ],

  // Settings
  "/settings": [
    { label: "Overview", href: "/" },
    { label: "Settings", href: "/" },
    { label: "Settings", href: "/settings" },
  ],
  "/api-keys": [
    { label: "Overview", href: "/" },
    { label: "Settings", href: "/" },
    { label: "API Keys", href: "/api-keys" },
  ],
  "/webhooks": [
    { label: "Overview", href: "/" },
    { label: "Settings", href: "/" },
    { label: "Webhooks", href: "/webhooks" },
  ],
  "/billing": [
    { label: "Overview", href: "/" },
    { label: "Settings", href: "/" },
    { label: "Billing", href: "/billing" },
  ],
  "/go-live": [
    { label: "Overview", href: "/" },
    { label: "Settings", href: "/" },
    { label: "Go Live", href: "/go-live" },
  ],
  "/alerts": [
    { label: "Overview", href: "/" },
    { label: "Settings", href: "/" },
    { label: "Alerts", href: "/alerts" },
  ],
  "/support": [
    { label: "Overview", href: "/" },
    { label: "Settings", href: "/" },
    { label: "Support", href: "/support" },
  ],
  "/environments": [
    { label: "Overview", href: "/" },
    { label: "Settings", href: "/" },
    { label: "Environments", href: "/environments" },
  ],
}

function getBreadcrumbs(pathname: string): BreadcrumbItem[] {
  if (routeBreadcrumbs[pathname]) {
    return routeBreadcrumbs[pathname]
  }

  // Fallback: generate breadcrumbs from path segments
  const segments = pathname.split("/").filter(Boolean)
  const crumbs: BreadcrumbItem[] = [{ label: "Overview", href: "/" }]
  segments.forEach((segment, i) => {
    const href = "/" + segments.slice(0, i + 1).join("/")
    const label = segment
      .split("-")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
    crumbs.push({ label, href })
  })
  return crumbs
}

export function AppHeader({ onMenuClick, onSearchClick }: { onMenuClick?: () => void; onSearchClick?: () => void }) {
  const router = useRouter()

  const [paymentOpen, setPaymentOpen] = useState(false)
  const [paymentRecipient, setPaymentRecipient] = useState("")
  const [paymentAmount, setPaymentAmount] = useState("")
  const [paymentChain, setPaymentChain] = useState("Base")

  function handleSendPayment() {
    if (!paymentRecipient || !paymentAmount) { toast.error("Fill in recipient and amount"); return }
    toast.success(`Payment of $${paymentAmount} to ${paymentRecipient} on ${paymentChain}`)
    setPaymentOpen(false)
    setPaymentRecipient(""); setPaymentAmount(""); setPaymentChain("Base")
  }

  // Open Stripe Crypto Onramp directly to crypto.link.com with the caller's
  // first on-chain wallet address. This mirrors the original flow from the
  // legacy dashboard (dashboard-next/src/app/(dashboard)/wallets/fund/page.tsx)
  // which has been shipping in production and is known to work —
  // crypto.link.com accepts the wallet_addresses[ethereum] query param and
  // renders its Stripe-hosted buy flow with no server-minted session.
  //
  // Previous attempts tried two flavors that both failed:
  //   1. window.open("about:blank") + async popup.location.href — browsers
  //      with `noopener` features return null from window.open, so our
  //      `if (!popup)` branch false-flagged it as blocked and early-
  //      returned, leaving the already-opened tab stuck on about:blank.
  //   2. POST /api/v2/onramp/session — the backend handler was looking at
  //      STRIPE_SECRET_KEY (unset in prod, the real var is STRIPE_API_KEY)
  //      and fell through to the Coinbase fallback every time.
  //
  // The fix: pre-fetch the wallets lazily once (cached in state), then on
  // click synchronously build the crypto.link.com URL and call
  // window.open(url, "_blank") in the same user-gesture tick. No null check
  // shenanigans, no popup.location.href, no backend round-trip.
  const [cachedPrimaryAddress, setCachedPrimaryAddress] = useState<{
    address: string
    network: string
  } | null>(null)

  // Fetch the first on-chain wallet once on mount — we cache BOTH the
  // address (for display + Stripe fallback) and the wallet_id (for the
  // Coinbase Onramp backend call which keys off wallet_id).
  useEffect(() => {
    let cancelled = false
    async function loadPrimaryAddress() {
      try {
        const res = await fetch("/api/dashboard/wallets", {
          credentials: "include",
          cache: "no-store",
        })
        if (!res.ok) return
        const json = (await res.json()) as {
          wallets?: Array<{ walletId: string; primaryAddress: string | null; primaryChain: string | null }>
        }
        const wallet = (json.wallets || []).find(
          (w) => typeof w.primaryAddress === "string" && w.primaryAddress.length > 0,
        )
        if (!cancelled && wallet?.primaryAddress && wallet.walletId) {
          const rawChain = wallet.primaryChain || "base"
          const network = rawChain === "base_sepolia" ? "base" : rawChain
          setCachedPrimaryAddress({ address: wallet.primaryAddress, network })
          setCachedWalletId(wallet.walletId)
        }
      } catch {
        // Silent — Add Funds falls back to routing the user to /wallets.
      }
    }
    void loadPrimaryAddress()
    return () => { cancelled = true }
  }, [])

  // Cache the first wallet_id (not just address) for the backend onramp call.
  const [cachedWalletId, setCachedWalletId] = useState<string | null>(null)

  // Coinbase Onramp now requires a server-minted sessionToken (the old
  // "raw URL with appId + addresses" flow was deprecated). The backend
  // already has a /api/v2/wallets/{wallet_id}/onramp handler
  // (packages/sardis-api/src/sardis_api/routers/wallets.py _get_cdp_onramp_session_token)
  // that generates an Ed25519 CDP JWT, calls api.developer.coinbase.com/
  // onramp/v1/token, and returns a pay.coinbase.com URL with the token
  // baked in. We hit that.
  //
  // Coinbase Onramp for USDC on Base is free for the developer and the
  // buyer pays standard fiat-crypto spread (far lower than Stripe Link's
  // ~5%). This is the preferred funding path.
  //
  // Fee comparison (April 2026, for reference):
  //   Coinbase Onramp  — 0% dev fee, ~0.5-1% buyer spread
  //   Conduit Pay      — ~0.5-1% (Tempo-native)
  //   Banxa            — 1-2%
  //   Ramp Network     — 1.5-3%
  //   MoonPay          — 1-4.5%
  //   Stripe Link      — ~5% (preview API)
  async function handleAddFunds() {
    if (!cachedPrimaryAddress || !cachedWalletId) {
      toast.error("No on-chain wallet ready yet. Visit /wallets to provision one.")
      router.push("/wallets")
      return
    }
    // window.open SYNCHRONOUSLY in the click handler so Safari/Chrome
    // popup blockers honor the user gesture. Drop noopener/noreferrer so
    // we get a real Window reference back — we'll navigate it once the
    // backend returns the sessionToken URL.
    const popup = window.open("about:blank", "_blank")
    if (!popup) {
      toast.error("Pop-up blocked — allow pop-ups for app.sardis.sh and try again")
      return
    }
    try {
      const res = await fetch(`/api/sardis/api/v2/wallets/${cachedWalletId}/onramp`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_chain: cachedPrimaryAddress.network,
          destination_chain: cachedPrimaryAddress.network,
          preset_amount: "100",
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => null) as { detail?: string; error?: string } | null
        throw new Error(err?.detail || err?.error || `onramp ${res.status}`)
      }
      const body = (await res.json()) as { onramp_url?: string }
      if (!body.onramp_url) {
        throw new Error("Backend returned no onramp_url")
      }
      popup.location.href = body.onramp_url
      toast.success("Opening Coinbase Onramp (free for USDC on Base)")
    } catch (err) {
      popup.close()
      const message = err instanceof Error ? err.message : "Failed to start funding flow"
      toast.error(message)
    }
  }

  const { theme, setTheme } = useTheme()
  const pathname = usePathname()
  const breadcrumbs = getBreadcrumbs(pathname)

  return (
    <header className="flex items-center gap-3 px-5 py-2.5 bg-card border-b flex-shrink-0">
      <Button variant="outline" size="icon" className="md:hidden h-8 w-8" onClick={onMenuClick}>
        <List className="w-4 h-4" />
      </Button>

      {/* Breadcrumb navigation */}
      <nav aria-label="Breadcrumb" className="hidden sm:flex items-center gap-1 text-sm shrink-0">
        {breadcrumbs.map((crumb, index) => {
          const isLast = index === breadcrumbs.length - 1
          return (
            <span key={`${crumb.href}-${index}`} className="flex items-center gap-1">
              {index > 0 && (
                <CaretRight className="w-3 h-3 text-muted-foreground/60" />
              )}
              {isLast ? (
                <span className="text-foreground font-medium">{crumb.label}</span>
              ) : (
                <Link
                  href={crumb.href}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  {crumb.label}
                </Link>
              )}
            </span>
          )
        })}
      </nav>

      <button
        type="button"
        onClick={onSearchClick}
        className="flex-1 max-w-sm flex items-center gap-2 rounded-md border bg-muted/50 px-2.5 h-8 text-sm text-muted-foreground hover:bg-muted transition-colors cursor-pointer"
      >
        <MagnifyingGlass className="w-3.5 h-3.5 shrink-0" />
        <span className="truncate">Search...</span>
        <kbd className="ml-auto text-[10px] font-mono text-muted-foreground bg-background border rounded px-1.5 py-0.5 shrink-0">
          ⌘K
        </kbd>
      </button>

      <div className="flex items-center gap-1.5 ml-auto">
        <Button
          variant="outline"
          size="sm"
          className="hidden sm:flex gap-1 text-xs h-8"
          onClick={handleAddFunds}
        >
          <Plus className="w-3 h-3" /> Add Funds
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="hidden sm:flex gap-1 text-xs h-8"
          onClick={() => router.push("/agents/new")}
        >
          <Plus className="w-3 h-3" /> Create Agent
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="hidden lg:flex gap-1 text-xs h-8"
          onClick={() => router.push("/virtual-cards")}
        >
          <CreditCard className="w-3 h-3" /> Issue Card
        </Button>

        <Popover>
          <PopoverTrigger
            aria-label="Notifications"
            className={buttonVariants({ variant: "outline", size: "icon", className: "relative" })}
          >
            <Bell className="w-4 h-4" />
            {/* TODO: Replace static badge count with real notification count */}
            <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-destructive text-destructive-foreground text-[10px] rounded-full flex items-center justify-center">
              3
            </span>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-80 p-0">
            <div className="flex items-center justify-between px-3 py-2.5 border-b">
              <span className="text-sm font-medium">Notifications</span>
              <button
                type="button"
                className="text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              >
                Mark all read
              </button>
            </div>
            <ul className="flex flex-col">
              {notifications.map((n) => (
                <li
                  key={n.message}
                  className="flex items-start gap-2.5 px-3 py-2.5 hover:bg-muted/50 transition-colors"
                >
                  <span
                    className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${dotColor[n.type]}`}
                  />
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <span className="text-sm leading-snug">{n.message}</span>
                    <span className="text-xs text-muted-foreground">
                      {n.time}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
            <div className="border-t px-3 py-2 text-center">
              <button
                type="button"
                className="text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              >
                View all notifications
              </button>
            </div>
          </PopoverContent>
        </Popover>

        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          <Sun className="w-4 h-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute w-4 h-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>

        <div className="flex rounded-md overflow-hidden ml-1">
          <Button size="sm" className="rounded-r-none gap-1 text-xs h-8" onClick={() => setPaymentOpen(true)}>
            <Plus className="w-3 h-3" weight="bold" /> New Payment
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger className="inline-flex shrink-0 items-center justify-center rounded-l-none rounded-r-md border-l border-primary-foreground/20 bg-primary text-primary-foreground px-2 h-8 text-xs font-medium hover:bg-primary/90 cursor-pointer">
              <CaretDown className="w-3 h-3" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" sideOffset={8}>
              <DropdownMenuItem onClick={() => setPaymentOpen(true)}>New Payment</DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push("/agents/new")}>Create Agent</DropdownMenuItem>
              <DropdownMenuItem onClick={handleAddFunds}>Add Funds</DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push("/virtual-cards")}>Issue Card</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <div className="[&_button]:bg-transparent [&_button]:border-border [&_button]:text-foreground [&_img]:rounded-full [&_button]:rounded-lg [&_button]:h-9 [&_button]:px-2">
          <UserButton />
        </div>
      </div>

      {/* New Payment Dialog */}
      <Dialog open={paymentOpen} onOpenChange={setPaymentOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New Payment</DialogTitle>
            <DialogDescription>Create a new payment transaction</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="payment-recipient" className="text-sm font-medium">Recipient</label>
              <Input id="payment-recipient" value={paymentRecipient} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPaymentRecipient(e.target.value)} placeholder="e.g. MerchantCo or 0x..." />
            </div>
            <div className="space-y-2">
              <label htmlFor="payment-amount" className="text-sm font-medium">Amount ($)</label>
              <Input id="payment-amount" type="number" value={paymentAmount} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPaymentAmount(e.target.value)} placeholder="0.00" />
            </div>
            <div className="space-y-2">
              <span className="text-sm font-medium">Chain</span>
              <div className="flex gap-2 flex-wrap">
                {["Base", "Polygon", "Arbitrum", "Optimism", "Ethereum"].map((chain) => (
                  <Button key={chain} variant={paymentChain === chain ? "default" : "outline"} size="sm" onClick={() => setPaymentChain(chain)}>
                    {chain}
                  </Button>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={handleSendPayment}>Send Payment</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </header>
  )
}
