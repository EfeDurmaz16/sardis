"use client"

import { useState } from "react"
import { usePathname } from "next/navigation"
import Link from "next/link"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import {
  SquaresFour, Robot, ArrowsLeftRight, ShieldCheck, Wallet, Storefront,
  CreditCard, Pause, FileText, ArrowsClockwise,
  Lightning, Terminal,
  Shield, Play, ChartBar, Code, UserCheck, Users, GitBranch, GitMerge,
  Power, Faders, CheckCircle, Broadcast, Lock, Eye,
  Warning, Anchor, Prohibit, ShieldWarning, Heartbeat,
  Gear, Key, PaperPlaneTilt, CurrencyDollar, Rocket, Bell, Headset, Stack,
  CaretDown, CaretUpDown, CaretLineLeft, CaretLineRight,
  type Icon,
} from "@phosphor-icons/react"

type NavItem = {
  label: string
  href: string
  icon: Icon
  badge?: string
  tourId?: string
}

type NavSection = {
  title?: string
  collapsible?: boolean
  defaultOpen?: boolean
  items: NavItem[]
}

const navSections: NavSection[] = [
  {
    items: [
      { label: "Overview", href: "/", icon: SquaresFour, tourId: "nav-overview" },
      { label: "Agents", href: "/agents", icon: Robot, tourId: "nav-agents" },
      { label: "Transactions", href: "/transactions", icon: ArrowsLeftRight, tourId: "nav-ledger" },
      { label: "Mandates", href: "/mandates", icon: ShieldCheck, tourId: "nav-mandates" },
      { label: "Wallets", href: "/wallets", icon: Wallet, tourId: "nav-wallets" },
      { label: "Merchants", href: "/merchants", icon: Storefront },
    ],
  },
  {
    title: "Payments",
    items: [
      { label: "Virtual Cards", href: "/virtual-cards", icon: CreditCard },
      { label: "Facility Gate", href: "/facility-gate", icon: ShieldCheck },
      { label: "Holds", href: "/holds", icon: Pause },
      { label: "Invoices", href: "/invoices", icon: FileText },
      { label: "Reconciliation", href: "/reconciliation", icon: ArrowsClockwise },
    ],
  },
  {
    title: "Monitoring",
    items: [
      { label: "Live Events", href: "/live-events", icon: Lightning },
      { label: "MPP Sessions", href: "/mpp-sessions", icon: Terminal },
    ],
  },
  {
    title: "Policies",
    collapsible: true,
    defaultOpen: true,
    items: [
      { label: "Policy Manager", href: "/policy-manager", icon: Shield },
      { label: "Simulation", href: "/simulation", icon: Play },
      { label: "Analytics", href: "/analytics", icon: ChartBar },
      { label: "API Playground", href: "/api-playground", icon: Code },
      { label: "Approval Config", href: "/approval-config", icon: UserCheck },
      { label: "Counterparties", href: "/counterparties", icon: Users },
      { label: "Fallback Rules", href: "/fallback-rules", icon: GitBranch },
      { label: "Workflows", href: "/workflows", icon: GitMerge },
    ],
  },
  {
    title: "Security",
    collapsible: true,
    defaultOpen: true,
    items: [
      { label: "Kill Switch", href: "/kill-switch", icon: Power },
      { label: "Control Center", href: "/control-center", icon: Faders },
      { label: "Approvals", href: "/approvals", icon: CheckCircle, badge: "3" },
      { label: "Checkout Controls", href: "/checkout-controls", icon: Broadcast },
      { label: "Evidence", href: "/evidence", icon: Lock },
      { label: "Observability", href: "/observability", icon: Eye },
      { label: "Anomaly Detection", href: "/anomaly-detection", icon: Warning },
      { label: "Audit Anchors", href: "/audit-anchors", icon: Anchor },
      { label: "Exceptions", href: "/exceptions", icon: Prohibit },
      { label: "Guardrails", href: "/guardrails", icon: ShieldWarning },
      { label: "Provider Health", href: "/provider-health", icon: Heartbeat },
    ],
  },
  {
    title: "Settings",
    collapsible: true,
    defaultOpen: false,
    items: [
      { label: "Settings", href: "/settings", icon: Gear },
      { label: "Security", href: "/account/security", icon: Lock },
      { label: "API Keys", href: "/api-keys", icon: Key, tourId: "nav-api-keys" },
      { label: "Webhooks", href: "/webhooks", icon: PaperPlaneTilt, tourId: "nav-webhooks" },
      { label: "Billing", href: "/billing", icon: CurrencyDollar },
      { label: "Go Live", href: "/go-live", icon: Rocket },
      { label: "Alerts", href: "/alerts", icon: Bell },
      { label: "Support", href: "/support", icon: Headset },
      { label: "Environments", href: "/environments", icon: Stack },
    ],
  },
]

/* ── Nav Item (icon-only with tooltip when collapsed) ── */
function NavLink({
  item,
  pathname,
  isCollapsed,
  onNavigate,
}: {
  item: NavItem
  pathname: string
  isCollapsed: boolean
  onNavigate?: () => void
}) {
  const active = pathname === item.href
  const Ico = item.icon

  const link = (
    <Link
      href={item.href}
      onClick={onNavigate}
      data-tour-id={item.tourId}
      className={cn(
        "flex items-center gap-2 rounded-md text-[12.5px] text-muted-foreground transition-colors duration-150",
        "hover:bg-accent hover:text-foreground",
        active && "bg-accent text-foreground font-medium",
        isCollapsed ? "justify-center px-2 py-2" : "px-2.5 py-1.5"
      )}
    >
      <Ico weight={active ? "fill" : "regular"} className="w-4 h-4 flex-shrink-0" />
      {!isCollapsed && <span className="truncate">{item.label}</span>}
      {!isCollapsed && item.badge && (
        <span className="ml-auto text-[10px] font-mono text-muted-foreground bg-muted border rounded px-1">
          {item.badge}
        </span>
      )}
    </Link>
  )

  if (isCollapsed) {
    return (
      <Tooltip>
        <TooltipTrigger>{link}</TooltipTrigger>
        <TooltipContent side="right" sideOffset={8}>
          <span>{item.label}</span>
          {item.badge && <span className="ml-1.5 text-muted-foreground">({item.badge})</span>}
        </TooltipContent>
      </Tooltip>
    )
  }

  return link
}

/* ── Sidebar Content ── */
function SidebarContent({
  isCollapsed,
  onCollapsedChange,
  onNavigate,
}: {
  isCollapsed: boolean
  onCollapsedChange?: (v: boolean) => void
  onNavigate?: () => void
}) {
  const pathname = usePathname()
  const [sectionCollapsed, setSectionCollapsed] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {}
    navSections.forEach((s) => {
      if (s.collapsible && s.title) init[s.title] = !s.defaultOpen
    })
    return init
  })

  return (
    <>
      {/* Workspace header */}
      <div className={cn(
        "flex items-center border-b cursor-pointer hover:bg-accent/50 transition-colors",
        isCollapsed ? "justify-center px-2 py-3" : "gap-2.5 px-4 py-3"
      )}>
        {isCollapsed ? (
          <Tooltip>
            <TooltipTrigger>
              <svg width="24" height="24" viewBox="0 0 28 28" fill="none" className="flex-shrink-0">
                <path d="M20 5H10a7 7 0 000 14h2" stroke="currentColor" strokeWidth="3" strokeLinecap="round" fill="none" />
                <path d="M8 23h10a7 7 0 000-14h-2" stroke="currentColor" strokeWidth="3" strokeLinecap="round" fill="none" />
              </svg>
            </TooltipTrigger>
            <TooltipContent side="right">Sardis</TooltipContent>
          </Tooltip>
        ) : (
          <>
            <svg width="24" height="24" viewBox="0 0 28 28" fill="none" className="flex-shrink-0">
              <path d="M20 5H10a7 7 0 000 14h2" stroke="currentColor" strokeWidth="3" strokeLinecap="round" fill="none" />
              <path d="M8 23h10a7 7 0 000-14h-2" stroke="currentColor" strokeWidth="3" strokeLinecap="round" fill="none" />
            </svg>
            <div className="flex items-center gap-1.5 flex-1 min-w-0">
              <span className="font-semibold text-sm truncate">Sardis</span>
              <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 font-medium uppercase tracking-wider">
                Pro
              </Badge>
            </div>
            <CaretUpDown className="w-3 h-3 text-muted-foreground flex-shrink-0" />
          </>
        )}
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <nav className={cn("space-y-1", isCollapsed ? "p-1.5" : "p-2")}>
          {navSections.map((section, sIdx) => (
            <div key={sIdx} className={cn(sIdx > 0 && "mt-3")}>
              {/* Section title (non-collapsible) */}
              {section.title && !section.collapsible && !isCollapsed && (
                <div className="px-2.5 py-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                  {section.title}
                </div>
              )}
              {/* Section title (collapsible) */}
              {section.title && section.collapsible && !isCollapsed && (
                <button
                  onClick={() =>
                    setSectionCollapsed((prev) => ({ ...prev, [section.title!]: !prev[section.title!] }))
                  }
                  className="flex items-center justify-between w-full px-2.5 py-1"
                >
                  <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    {section.title}
                  </span>
                  <CaretDown
                    className={cn(
                      "w-3 h-3 text-muted-foreground transition-transform duration-150",
                      sectionCollapsed[section.title!] && "-rotate-90"
                    )}
                  />
                </button>
              )}
              {/* Collapsed sidebar: show separator line for titled sections */}
              {section.title && isCollapsed && (
                <div className="mx-2 my-1 border-t" />
              )}
              {/* Items */}
              {(!section.collapsible || isCollapsed || !sectionCollapsed[section.title!]) && (
                <div className="space-y-0.5">
                  {section.items.map((item) => (
                    <NavLink
                      key={item.href}
                      item={item}
                      pathname={pathname}
                      isCollapsed={isCollapsed}
                      onNavigate={onNavigate}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </nav>
      </div>

      {/* Footer — always pinned to bottom */}
      <div className="flex-shrink-0">
        {!isCollapsed && (
          <div className="p-2 border-t">
            <div className="bg-muted/50 border rounded-lg p-3">
              <div className="text-[10px] font-medium text-muted-foreground mb-0.5">Plan</div>
              <div className="text-sm font-semibold">Free</div>
              <div className="text-[10px] text-muted-foreground mt-1">Upgrade in Billing</div>
            </div>
          </div>
        )}

        {/* Collapse toggle */}
        {onCollapsedChange && (
          <div className={cn("border-t", isCollapsed ? "p-1.5" : "p-2")}>
            <button
              onClick={() => onCollapsedChange(!isCollapsed)}
              className={cn(
                "flex items-center gap-2 rounded-md text-[12px] text-muted-foreground hover:bg-accent hover:text-foreground transition-colors w-full",
                isCollapsed ? "justify-center px-2 py-2" : "px-2.5 py-1.5"
              )}
            >
              {isCollapsed ? (
                <CaretLineRight className="w-4 h-4" />
              ) : (
                <>
                  <CaretLineLeft className="w-4 h-4" />
                  <span>Collapse</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </>
  )
}

/* ── Sidebar Root ── */
export function AppSidebar({
  open,
  onOpenChange,
  collapsed = false,
  onCollapsedChange,
}: {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  collapsed?: boolean
  onCollapsedChange?: (collapsed: boolean) => void
}) {
  return (
    <>
      {/* Desktop */}
      <aside
        className={cn(
          "hidden md:flex flex-col bg-card border-r h-full overflow-hidden transition-[width] duration-200 ease-out",
          collapsed ? "w-[52px] min-w-[52px]" : "w-[228px] min-w-[228px]"
        )}
      >
        <SidebarContent
          isCollapsed={collapsed}
          onCollapsedChange={onCollapsedChange}
        />
      </aside>

      {/* Mobile */}
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent side="left" className="w-[228px] p-0 flex flex-col [&>button:first-child]:hidden">
          <SidebarContent
            isCollapsed={false}
            onNavigate={() => onOpenChange?.(false)}
          />
        </SheetContent>
      </Sheet>
    </>
  )
}
