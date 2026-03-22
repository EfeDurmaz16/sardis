"use client";

import { ReactNode, useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  LayoutDashboard,
  Users,
  Wallet,
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
} from 'lucide-react'
import clsx from 'clsx'
import { useHealth } from '@/hooks/useApi'
import { useSession, signOut } from '@/lib/auth-client'
import { shouldShowTour, startDashboardTour } from '@/lib/tour'
import NotificationCenter from '@/components/NotificationCenter'

interface LayoutProps {
  children: ReactNode
}

// --- Sidebar navigation structure ---

interface NavItem {
  name: string
  href: string
  icon: typeof LayoutDashboard
  tour?: string
}

interface NavSection {
  label: string
  items: NavItem[]
}

// Core section -- always visible, no collapsing
const coreNavigation: NavItem[] = [
  { name: 'Overview', href: '/', icon: LayoutDashboard, tour: 'overview' },
  { name: 'Agents', href: '/agents', icon: Users, tour: 'agents' },
  { name: 'Transactions', href: '/transactions', icon: ArrowRightLeft, tour: 'transactions' },
  { name: 'Mandates', href: '/mandates', icon: Shield, tour: 'mandates' },
]

// Collapsible grouped sections
const navSections: NavSection[] = [
  {
    label: 'Policies',
    items: [
      { name: 'Policy Manager', href: '/policy-manager', icon: GitBranch },
      { name: 'Simulation', href: '/simulation', icon: Beaker },
      { name: 'Analytics', href: '/analytics', icon: BarChart3 },
    ],
  },
  {
    label: 'Security',
    items: [
      { name: 'Kill Switch', href: '/kill-switch', icon: Power },
      { name: 'Approvals', href: '/approvals', icon: CheckSquare },
      { name: 'Control Center', href: '/control-center', icon: LayoutGrid },
      { name: 'Evidence', href: '/evidence', icon: FileSearch },
    ],
  },
  {
    label: 'Settings',
    items: [
      { name: 'API Keys', href: '/api-keys', icon: Key, tour: 'api-keys' },
      { name: 'Webhooks', href: '/webhooks', icon: Webhook },
      { name: 'Go Live', href: '/go-live', icon: Rocket, tour: 'go-live' },
      { name: 'Settings', href: '/settings', icon: Settings },
      { name: 'Billing', href: '/billing', icon: Receipt },
    ],
  },
]

// Helper: decode JWT payload from a raw token string
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded)
  } catch {
    return null
  }
}

export default function DashboardLayout({ children }: LayoutProps) {
  const pathname = usePathname()
  const router = useRouter()
  const { data: health, isError } = useHealth()
  const { data: session } = useSession()

  // Resolve user email: try better-auth session first, fall back to JWT in localStorage
  const userEmail = useMemo(() => {
    // 1. From better-auth session object
    if (session?.user?.email) return session.user.email as string

    // 2. Decode JWT stored in localStorage
    if (typeof window === 'undefined') return null
    try {
      const raw = localStorage.getItem('sardis_session')
      if (!raw) return null
      const payload = decodeJwtPayload(raw)
      if (payload && typeof payload.email === 'string') return payload.email
    } catch {
      // ignore decode errors
    }
    return null
  }, [session])

  // Auto-expand sections that contain the active page
  const getInitialOpenSections = () => {
    const open: Record<string, boolean> = {}
    navSections.forEach((section) => {
      open[section.label] = section.items.some((item) => item.href === pathname)
    })
    return open
  }

  const [openSections, setOpenSections] = useState<Record<string, boolean>>(getInitialOpenSections)

  // Tour trigger
  useEffect(() => {
    if (shouldShowTour()) {
      startDashboardTour()
    }
  }, [])

  const toggleSection = (label: string) => {
    setOpenSections((prev) => ({ ...prev, [label]: !prev[label] }))
  }

  const handleLogout = async () => {
    // Clear better-auth session via SDK
    await signOut()
    // Clear localStorage session / JWT
    localStorage.removeItem('sardis_session')
    // Clear the session cookie
    document.cookie = 'better-auth.session_token=; path=/; max-age=0'
    // Redirect to login
    router.push('/login')
  }

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-dark-300 border-r border-dark-100 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-dark-100">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-10 h-10 bg-sardis-500 flex items-center justify-center glow-green">
              <Wallet className="w-6 h-6 text-dark-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold font-display text-gradient">Sardis</h1>
              <p className="text-xs text-gray-500 tracking-wider uppercase">Control Plane</p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {/* Section header: Core */}
          <div className="px-4 pt-1 pb-2">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Core</span>
          </div>

          {/* Core -- always visible */}
          {coreNavigation.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.name}
                href={item.href}
                {...(item.tour ? { 'data-tour': item.tour } : {})}
                className={clsx(
                  'flex items-center gap-3 px-4 py-3 text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'bg-sardis-500/10 text-sardis-400 border border-sardis-500/30'
                    : 'text-gray-400 hover:text-white hover:bg-dark-200'
                )}
              >
                <item.icon className="w-5 h-5" />
                {item.name}
              </Link>
            )
          })}

          {/* Collapsible sections */}
          {navSections.map((section) => (
            <div key={section.label} className="pt-2 mt-2 border-t border-dark-100/40">
              <button
                onClick={() => toggleSection(section.label)}
                className="w-full flex items-center gap-2 px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider hover:text-gray-400 transition-colors"
              >
                <span className="flex-1 text-left">{section.label}</span>
                {openSections[section.label] ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" />
                )}
              </button>
              {openSections[section.label] && (
                <div className="mt-1 space-y-0.5">
                  {section.items.map((item) => {
                    const isActive = pathname === item.href
                    return (
                      <Link
                        key={item.name}
                        href={item.href}
                        {...(item.tour ? { 'data-tour': item.tour } : {})}
                        className={clsx(
                          'flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition-all duration-200',
                          isActive
                            ? 'bg-sardis-500/10 text-sardis-400 border border-sardis-500/30'
                            : 'text-gray-400 hover:text-white hover:bg-dark-200'
                        )}
                      >
                        <item.icon className="w-4 h-4" />
                        {item.name}
                      </Link>
                    )
                  })}
                </div>
              )}
            </div>
          ))}
        </nav>

        {/* Sidebar footer: user email + sign out + status */}
        <div className="border-t border-dark-100">
          {/* User info */}
          {userEmail && (
            <div className="px-4 pt-4 pb-2 flex items-center gap-2">
              <User className="w-4 h-4 text-gray-500 flex-shrink-0" />
              <span className="text-xs text-gray-400 truncate" title={userEmail}>
                {userEmail}
              </span>
            </div>
          )}

          {/* Sign out */}
          <div className="px-4 pb-2">
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-500 hover:text-white hover:bg-dark-200 transition-all duration-200"
            >
              <LogOut className="w-5 h-5" />
              Sign Out
            </button>
          </div>

          {/* API status */}
          <div className="p-4 border-t border-dark-100">
            <div className="flex items-center gap-2 text-sm">
              <div className={clsx(
                'status-dot',
                isError ? 'error' : 'success'
              )} />
              <span className="text-gray-400">
                {isError ? 'API Offline' : 'API Connected'}
              </span>
            </div>
            {health && (
              <p className="text-xs text-gray-500 mt-1 font-mono">
                v{health.version}
              </p>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto flex flex-col">
        {/* Top header bar */}
        <header className="flex items-center justify-end px-8 py-3 border-b border-dark-100 bg-dark-300/50 flex-shrink-0">
          <NotificationCenter />
        </header>
        <div className="p-8 flex-1">
          {children}
        </div>
      </main>
    </div>
  )
}
