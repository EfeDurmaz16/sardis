"use client"

import { useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"
import {
  SquaresFour, Robot, ArrowsLeftRight, ShieldCheck, Wallet, Storefront,
  CreditCard, Pause, FileText, ArrowsClockwise,
  Lightning, Terminal,
  Shield, Play, ChartBar, Code, UserCheck, Users, GitBranch, GitMerge,
  Power, Faders, CheckCircle, Broadcast, Lock, Eye,
  Warning, Anchor, Prohibit, ShieldWarning, Heartbeat,
  Gear, Key, PaperPlaneTilt, CurrencyDollar, Rocket, Bell, Headset, Stack,
  Plus,
  type Icon,
} from "@phosphor-icons/react"

type PageItem = {
  label: string
  href: string
  icon: Icon
}

const pages: PageItem[] = [
  { label: "Overview", href: "/", icon: SquaresFour },
  { label: "Agents", href: "/agents", icon: Robot },
  { label: "Transactions", href: "/transactions", icon: ArrowsLeftRight },
  { label: "Mandates", href: "/mandates", icon: ShieldCheck },
  { label: "Wallets", href: "/wallets", icon: Wallet },
  { label: "Merchants", href: "/merchants", icon: Storefront },
  { label: "Virtual Cards", href: "/virtual-cards", icon: CreditCard },
  { label: "Facility Gate", href: "/facility-gate", icon: ShieldCheck },
  { label: "Holds", href: "/holds", icon: Pause },
  { label: "Invoices", href: "/invoices", icon: FileText },
  { label: "Reconciliation", href: "/reconciliation", icon: ArrowsClockwise },
  { label: "Live Events", href: "/live-events", icon: Lightning },
  { label: "MPP Sessions", href: "/mpp-sessions", icon: Terminal },
  { label: "Policy Manager", href: "/policy-manager", icon: Shield },
  { label: "Simulation", href: "/simulation", icon: Play },
  { label: "Analytics", href: "/analytics", icon: ChartBar },
  { label: "API Playground", href: "/api-playground", icon: Code },
  { label: "Approval Config", href: "/approval-config", icon: UserCheck },
  { label: "Counterparties", href: "/counterparties", icon: Users },
  { label: "Fallback Rules", href: "/fallback-rules", icon: GitBranch },
  { label: "Workflows", href: "/workflows", icon: GitMerge },
  { label: "Kill Switch", href: "/kill-switch", icon: Power },
  { label: "Control Center", href: "/control-center", icon: Faders },
  { label: "Approvals", href: "/approvals", icon: CheckCircle },
  { label: "Checkout Controls", href: "/checkout-controls", icon: Broadcast },
  { label: "Evidence", href: "/evidence", icon: Lock },
  { label: "Observability", href: "/observability", icon: Eye },
  { label: "Anomaly Detection", href: "/anomaly-detection", icon: Warning },
  { label: "Audit Anchors", href: "/audit-anchors", icon: Anchor },
  { label: "Exceptions", href: "/exceptions", icon: Prohibit },
  { label: "Guardrails", href: "/guardrails", icon: ShieldWarning },
  { label: "Provider Health", href: "/provider-health", icon: Heartbeat },
  { label: "Settings", href: "/settings", icon: Gear },
  { label: "API Keys", href: "/api-keys", icon: Key },
  { label: "Webhooks", href: "/webhooks", icon: PaperPlaneTilt },
  { label: "Billing", href: "/billing", icon: CurrencyDollar },
  { label: "Go Live", href: "/go-live", icon: Rocket },
  { label: "Alerts", href: "/alerts", icon: Bell },
  { label: "Support", href: "/support", icon: Headset },
  { label: "Environments", href: "/environments", icon: Stack },
]

type QuickAction = {
  label: string
  icon: Icon
  href: string
}

const quickActions: QuickAction[] = [
  { label: "Create Agent", icon: Robot, href: "/agents/new" },
  { label: "New Payment", icon: CurrencyDollar, href: "/payments/new" },
  { label: "Add Funds", icon: Wallet, href: "/wallets/add-funds" },
  { label: "Issue Card", icon: CreditCard, href: "/virtual-cards/issue" },
]

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const router = useRouter()

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        onOpenChange(!open)
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [open, onOpenChange])

  const runAction = useCallback(
    (href: string) => {
      onOpenChange(false)
      router.push(href)
    },
    [router, onOpenChange]
  )

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <Command>
        <CommandInput placeholder="Type a command or search..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Pages">
            {pages.map((page) => {
              const Ico = page.icon
              return (
                <CommandItem
                  key={page.href}
                  value={page.label}
                  onSelect={() => runAction(page.href)}
                >
                  <Ico className="w-4 h-4 shrink-0" />
                  <span>{page.label}</span>
                </CommandItem>
              )
            })}
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Quick Actions">
            {quickActions.map((action) => {
              const Ico = action.icon
              return (
                <CommandItem
                  key={action.label}
                  value={action.label}
                  onSelect={() => runAction(action.href)}
                >
                  <Plus className="w-4 h-4 shrink-0" />
                  <span>{action.label}</span>
                </CommandItem>
              )
            })}
          </CommandGroup>
        </CommandList>
      </Command>
    </CommandDialog>
  )
}
