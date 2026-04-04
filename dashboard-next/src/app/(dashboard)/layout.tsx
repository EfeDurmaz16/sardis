"use client";

import { ReactNode, useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  LayoutDashboard,
  Users,
  Wallet,
  CreditCard,
  LogOut,
  CheckSquare,
  BarChart3,
  Shield,
  Power,
  FileSearch,
  Beaker,
  Receipt,
  Key,
  Webhook,
  Settings,
  ChevronDown,
  ChevronRight,
  Rocket,
  LayoutGrid,
  GitBranch,
  ArrowRightLeft,
  User,
  Terminal,
  Store,
  SlidersHorizontal,
  Zap,
  TerminalSquare,
  FileText,
  Activity,
  PauseCircle,
  Eye,
  AlertTriangle,
  Anchor,
  OctagonAlert,
  Heart,
  Bell,
  Headphones,
  Layers,
  Menu,
  X,
} from 'lucide-react'
import clsx from 'clsx'
import { useHealth } from '@/hooks/useApi'
import { useSession, signOut } from '@/lib/auth-client'
import { shouldShowTour, startDashboardTour } from '@/lib/tour'
import KYCBanner from '@/components/KYCBanner'
import NotificationCenter from '@/components/NotificationCenter'

interface LayoutProps {
  children: ReactNode
}

interface NavItem {
  name: string
  href: string
  icon: typeof LayoutDashboard
  tour?: string
  badge?: string
}

interface NavSection {
  label: string
  items: NavItem[]
  defaultOpen?: boolean
}

// Core — always visible
const coreNavigation: NavItem[] = [
  { name: 'Overview', href: '/overview', icon: LayoutDashboard, tour: 'overview' },
  { name: 'Agents', href: '/agents', icon: Users, tour: 'agents' },
  { name: 'Transactions', href: '/transactions', icon: ArrowRightLeft, tour: 'transactions' },
  { name: 'Mandates', href: '/mandates', icon: Shield, tour: 'mandates' },
  { name: 'Wallets', href: '/wallets', icon: Wallet },
  { name: 'Merchants', href: '/merchants', icon: Store },
]

// Static sections with labels
const paymentsNavigation: NavItem[] = [
  { name: 'Virtual Cards', href: '/virtual-cards', icon: CreditCard },
  { name: 'Holds', href: '/holds', icon: PauseCircle },
  { name: 'Invoices', href: '/invoices', icon: FileText },
  { name: 'Reconciliation', href: '/reconciliation', icon: Activity },
]

const monitoringNavigation: NavItem[] = [
  { name: 'Live Events', href: '/events', icon: Zap },
  { name: 'MPP Sessions', href: '/mpp-sessions', icon: TerminalSquare },
]

// Collapsible sections
const navSections: NavSection[] = [
  {
    label: 'Policies',
    items: [
      { name: 'Policy Manager', href: '/policy-manager', icon: GitBranch },
      { name: 'Simulation', href: '/simulation', icon: Beaker },
      { name: 'Analytics', href: '/analytics', icon: BarChart3 },
      { name: 'API Playground', href: '/playground', icon: Terminal },
    ],
  },
  {
    label: 'Security',
    items: [
      { name: 'Kill Switch', href: '/kill-switch', icon: Power },
      { name: 'Control Center', href: '/control-center', icon: LayoutGrid },
      { name: 'Approvals', href: '/approvals', icon: CheckSquare },
      { name: 'Checkout Controls', href: '/checkout-controls', icon: SlidersHorizontal },
      { name: 'Evidence', href: '/evidence', icon: FileSearch },
      { name: 'Observability', href: '/agent-observability', icon: Eye },
      { name: 'Anomaly Detection', href: '/anomaly', icon: AlertTriangle },
      { name: 'Audit Anchors', href: '/audit-anchors', icon: Anchor },
      { name: 'Exceptions', href: '/exceptions', icon: OctagonAlert },
      { name: 'Guardrails', href: '/guardrails', icon: Shield },
      { name: 'Provider Health', href: '/provider-health', icon: Heart },
    ],
  },
  {
    label: 'Settings',
    defaultOpen: false,
    items: [
      { name: 'Settings', href: '/settings', icon: Settings },
      { name: 'API Keys', href: '/api-keys', icon: Key, tour: 'api-keys' },
      { name: 'Webhooks', href: '/webhooks', icon: Webhook },
      { name: 'Billing', href: '/billing', icon: Receipt },
      { name: 'Go Live', href: '/go-live', icon: Rocket, tour: 'go-live' },
      { name: 'Alerts', href: '/alert-preferences', icon: Bell },
      { name: 'Support', href: '/enterprise-support', icon: Headphones },
      { name: 'Environments', href: '/environment-templates', icon: Layers },
    ],
  },
]

// Decode JWT payload
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const decoded = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded)
  } catch {
    return null
  }
}

// Nav item component
function NavLink({ item, pathname, onClick }: { item: NavItem; pathname: string; onClick?: () => void }) {
  const isActive = pathname === item.href
  return (
    <Link
      href={item.href}
      onClick={onClick}
      {...(item.tour ? { 'data-tour': item.tour } : {})}
      className={clsx(
        'flex items-center gap-[9px] px-[10px] py-[6px] rounded-[6px] text-[12.5px] transition-all duration-100',
        isActive
          ? 'bg-[#ebebeb] text-[#111] font-medium'
          : 'text-[#666] hover:text-[#111] hover:bg-[#f2f2f2]'
      )}
    >
      <item.icon className="w-[15px] h-[15px] flex-shrink-0" strokeWidth={1.6} />
      <span className="flex-1">{item.name}</span>
      {item.badge && (
        <span className="text-[10px] font-mono text-[#888] bg-[#f7f7f7] border border-[#eaeaea] rounded-[3px] px-[4px]">
          {item.badge}
        </span>
      )}
    </Link>
  )
}

export default function DashboardLayout({ children }: LayoutProps) {
  const pathname = usePathname()
  const router = useRouter()
  const { data: health, isError } = useHealth()
  const { data: session } = useSession()

  const userEmail = useMemo(() => {
    if (session?.user?.email) return session.user.email as string
    if (typeof window === 'undefined') return null
    try {
      const raw = localStorage.getItem('sardis_session')
      if (!raw) return null
      const payload = decodeJwtPayload(raw)
      if (payload && typeof payload.email === 'string') return payload.email
    } catch { /* ignore */ }
    return null
  }, [session])

  const getInitialOpenSections = () => {
    const open: Record<string, boolean> = {}
    navSections.forEach((section) => {
      const hasActive = section.items.some((item) => item.href === pathname)
      open[section.label] = hasActive || (section.defaultOpen !== false)
    })
    return open
  }

  const [openSections, setOpenSections] = useState<Record<string, boolean>>(getInitialOpenSections)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    if (shouldShowTour()) startDashboardTour()
  }, [])

  const toggleSection = (label: string) => {
    setOpenSections((prev) => ({ ...prev, [label]: !prev[label] }))
  }

  const handleLogout = async () => {
    await signOut()
    localStorage.removeItem('sardis_session')
    document.cookie = 'better-auth.session_token=; path=/; max-age=0; domain=.sardis.sh'
    router.push('/login')
  }

  const closeSidebar = () => setSidebarOpen(false)

  const sidebarContent = (
    <>
      {/* Context Switcher */}
      <div className="flex items-center gap-[10px] px-[16px] py-[12px] border-b border-[#eaeaea]">
        <Link href="/overview" className="flex items-center gap-[10px] flex-1 min-w-0" onClick={closeSidebar}>
          <svg width="24" height="24" viewBox="0 0 28 28" fill="none" className="flex-shrink-0">
            <path d="M20 5H10a7 7 0 000 14h2" stroke="#111" strokeWidth="3" strokeLinecap="round" fill="none" />
            <path d="M8 23h10a7 7 0 000-14h-2" stroke="#111" strokeWidth="3" strokeLinecap="round" fill="none" />
          </svg>
          <span className="text-[13px] font-semibold text-[#111] flex items-center gap-[6px]">
            Sardis
            <span className="text-[9px] font-medium text-[#888] bg-[#f7f7f7] border border-[#eaeaea] rounded-[3px] px-[5px] uppercase tracking-[0.04em]">
              Pro
            </span>
          </span>
        </Link>
        {/* Close button — mobile only */}
        <button
          onClick={closeSidebar}
          className="lg:hidden p-1 text-[#888] hover:text-[#111]"
          aria-label="Close sidebar"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-[8px] overflow-y-auto">
        {/* Core */}
        <div className="space-y-[1px]">
          {coreNavigation.map((item) => (
            <NavLink key={item.name} item={item} pathname={pathname} onClick={closeSidebar} />
          ))}
        </div>

        {/* Payments */}
        <div className="mt-[10px]">
          <div className="px-[10px] py-[3px]">
            <span className="text-[10px] font-medium uppercase tracking-[0.06em] text-[#888]">Payments</span>
          </div>
          <div className="space-y-[1px]">
            {paymentsNavigation.map((item) => (
              <NavLink key={item.name} item={item} pathname={pathname} onClick={closeSidebar} />
            ))}
          </div>
        </div>

        {/* Monitoring */}
        <div className="mt-[10px]">
          <div className="px-[10px] py-[3px]">
            <span className="text-[10px] font-medium uppercase tracking-[0.06em] text-[#888]">Monitoring</span>
          </div>
          <div className="space-y-[1px]">
            {monitoringNavigation.map((item) => (
              <NavLink key={item.name} item={item} pathname={pathname} onClick={closeSidebar} />
            ))}
          </div>
        </div>

        {/* Collapsible sections */}
        {navSections.map((section) => (
          <div key={section.label} className="mt-[8px]">
            <button
              onClick={() => toggleSection(section.label)}
              aria-expanded={!!openSections[section.label]}
              className="w-full flex items-center justify-between px-[10px] py-[3px] group"
            >
              <span className="text-[10px] font-medium uppercase tracking-[0.06em] text-[#888] group-hover:text-[#666] transition-colors">
                {section.label}
              </span>
              {openSections[section.label] ? (
                <ChevronDown className="w-[11px] h-[11px] text-[#888] transition-transform" strokeWidth={2} />
              ) : (
                <ChevronRight className="w-[11px] h-[11px] text-[#888] transition-transform" strokeWidth={2} />
              )}
            </button>
            {openSections[section.label] && (
              <div className="mt-[1px] space-y-[1px]">
                {section.items.map((item) => (
                  <NavLink key={item.name} item={item} pathname={pathname} onClick={closeSidebar} />
                ))}
              </div>
            )}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-[#eaeaea]">
        {userEmail && (
          <div className="px-[16px] pt-[12px] pb-[4px] flex items-center gap-[8px]">
            <User className="w-[14px] h-[14px] text-[#888] flex-shrink-0" strokeWidth={1.6} />
            <span className="text-[11px] text-[#666] truncate" title={userEmail}>
              {userEmail}
            </span>
          </div>
        )}
        <div className="px-[12px] pb-[4px]">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-[9px] px-[10px] py-[6px] rounded-[6px] text-[12.5px] text-[#888] hover:text-[#111] hover:bg-[#f2f2f2] transition-all"
          >
            <LogOut className="w-[15px] h-[15px]" strokeWidth={1.6} />
            Sign Out
          </button>
        </div>
        <div className="px-[16px] py-[10px] border-t border-[#eaeaea]">
          <div className="flex items-center gap-[7px] text-[12px]">
            <div className={clsx(
              'w-[6px] h-[6px] rounded-full',
              isError ? 'bg-[#ef4444]' : 'bg-[#22c55e]'
            )} />
            <span className="text-[#888]">
              {isError ? 'API Offline' : 'API Connected'}
            </span>
          </div>
          {health && (
            <p className="text-[11px] text-[#bbb] mt-[2px] font-mono">
              v{health.version}
            </p>
          )}
        </div>
      </div>
    </>
  )

  return (
    <div className="light-dash min-h-screen flex bg-[#fafafa]">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-white focus:text-black focus:rounded">
        Skip to content
      </a>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/20 lg:hidden"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'w-[228px] bg-white border-r border-[#eaeaea] flex flex-col',
          'fixed inset-y-0 left-0 z-40 transform transition-transform duration-200 lg:relative lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        aria-label="Main navigation"
      >
        {sidebarContent}
      </aside>

      {/* Main */}
      <main id="main-content" className="flex-1 overflow-auto flex flex-col min-w-0">
        {/* Top bar */}
        <header className="flex items-center justify-between px-[20px] py-[10px] border-b border-[#eaeaea] bg-white flex-shrink-0 min-h-[48px]">
          {/* Mobile hamburger */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 text-[#666] hover:text-[#111]"
            aria-label="Open sidebar"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="lg:hidden" />
          <NotificationCenter />
        </header>
        <div className="p-[20px] lg:p-[24px] flex-1">
          <KYCBanner />
          {children}
        </div>
      </main>
    </div>
  )
}
