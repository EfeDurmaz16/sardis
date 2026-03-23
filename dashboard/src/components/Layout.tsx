
import { ReactNode, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  AddressBook,
  Anchor,
  ArrowsLeftRight,
  CaretDown,
  CaretRight,
  ChartBar,
  CheckSquare,
  CreditCard,
  Eye,
  FileMagnifyingGlass,
  Flask,
  Flask as ExperimentalIcon,
  Gear,
  GitBranch,
  GridFour,
  Headset,
  Key,
  Layout,
  List,
  Medal,
  Power,
  Pulse,
  Receipt,
  Rocket,
  Crosshair,
  Shield,
  ShieldCheck,
  SignOut,
  Sparkle,
  SquaresFour,
  Storefront,
  Target,
  Users,
  Wallet,
  Warning,
  WebhooksLogo,
  X,
} from '@phosphor-icons/react'
import clsx from 'clsx'
import { useHealth } from '../hooks/useApi'
import { useAuth } from '../auth/AuthContext'
import NotificationCenter from './NotificationCenter'

interface LayoutProps {
  children: ReactNode
}

// Always visible — core product pages
const coreNavigation = [
  { name: 'Dashboard', href: '/', icon: SquaresFour },
  { name: 'Agents', href: '/agents', icon: Users },
  { name: 'Spending Mandates', href: '/mandates', icon: Shield },
  { name: 'Policy Manager', href: '/policy-manager', icon: GitBranch },
  { name: 'Transactions', href: '/transactions', icon: ArrowsLeftRight },
  { name: 'Cards', href: '/cards', icon: CreditCard },
  { name: 'Analytics', href: '/analytics', icon: ChartBar },
]

// Collapsible grouped sections
const navSections = [
  {
    label: 'Control Plane',
    items: [
      { name: 'Control Center', href: '/control-center', icon: GridFour },
      { name: 'Control Plane Demo', href: '/demo', icon: Sparkle },
      { name: 'Approvals', href: '/approvals', icon: CheckSquare },
      { name: 'Approval Routing', href: '/approval-config', icon: Gear },
      { name: 'Kill Switch', href: '/kill-switch', icon: Power },
      { name: 'Fallback Rules', href: '/fallback-rules', icon: GitBranch },
    ],
  },
  {
    label: 'Monitoring',
    items: [
      { name: 'Live Events', href: '/events', icon: Pulse },
      { name: 'Policy Analytics', href: '/policy-analytics', icon: ChartBar },
      { name: 'Anomaly Detection', href: '/anomaly', icon: Crosshair },
      { name: 'Live Dry Run', href: '/simulation', icon: Flask },
      { name: 'Evidence', href: '/evidence', icon: FileMagnifyingGlass },
      { name: 'Reconciliation', href: '/reconciliation', icon: ShieldCheck },
      { name: 'Agent Observability', href: '/agent-observability', icon: Eye },
    ],
  },
  {
    label: 'Payments',
    items: [
      { name: 'Merchants', href: '/merchants', icon: Storefront },
      { name: 'Counterparties', href: '/counterparties', icon: AddressBook },
      { name: 'MPP Sessions', href: '/mpp-sessions', icon: Pulse },
      { name: 'Stripe Issuing', href: '/stripe-issuing', icon: Wallet },
    ],
  },
  {
    label: 'Gear',
    items: [
      { name: 'API Keys', href: '/api-keys', icon: Key },
      { name: 'Webhooks', href: '/webhooks', icon: WebhooksLogo },
      { name: 'Billing', href: '/billing', icon: Receipt },
      { name: 'Enterprise Support', href: '/enterprise-support', icon: Headset },
      { name: 'Env Templates', href: '/environment-templates', icon: Flask },
      { name: 'Go Live', href: '/go-live', icon: Rocket },
      { name: 'Templates', href: '/templates', icon: Layout },
      { name: 'Gear', href: '/settings', icon: Gear },
    ],
  },
]

const experimentalNavigation = [
  { name: 'Agent Identity', href: '/agent-identity', icon: Medal },
  { name: 'Guardrails', href: '/guardrails', icon: Shield },
  { name: 'Confidence Router', href: '/confidence-router', icon: Target },
  { name: 'Audit Anchors', href: '/audit-anchors', icon: Anchor },
  { name: 'Goal Drift', href: '/goal-drift', icon: Warning },
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { data: health, isError } = useHealth()
  const { logout } = useAuth()

  const isOnExperimentalPage = experimentalNavigation.some(
    (item) => item.href === location.pathname
  )

  // Auto-expand sections that contain the active page
  const getInitialOpenSections = () => {
    const open: Record<string, boolean> = {}
    navSections.forEach((section) => {
      open[section.label] = section.items.some((item) => item.href === location.pathname)
    })
    return open
  }

  const [openSections, setOpenSections] = useState<Record<string, boolean>>(getInitialOpenSections)
  const [experimentalOpen, setExperimentalOpen] = useState(isOnExperimentalPage)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const toggleSection = (label: string) => {
    setOpenSections((prev) => ({ ...prev, [label]: !prev[label] }))
  }

  const closeSidebar = () => setSidebarOpen(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="p-6 border-b border-dark-100 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3" onClick={closeSidebar}>
          <div className="w-10 h-10 bg-sardis-500 flex items-center justify-center glow-green">
            <Wallet className="w-6 h-6 text-dark-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold font-display text-gradient">Sardis</h1>
            <p className="text-xs text-gray-500 tracking-wider uppercase">Control Plane</p>
          </div>
        </Link>
        {/* Close button — mobile only */}
        <button
          onClick={closeSidebar}
          className="lg:hidden p-1.5 text-gray-400 hover:text-white transition-colors"
          aria-label="Close sidebar"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto" aria-label="Primary">
        {/* Core — always visible */}
        {coreNavigation.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.name}
              to={item.href}
              onClick={closeSidebar}
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
                <CaretDown className="w-3.5 h-3.5" />
              ) : (
                <CaretRight className="w-3.5 h-3.5" />
              )}
            </button>
            {openSections[section.label] && (
              <div className="mt-1 space-y-0.5">
                {section.items.map((item) => {
                  const isActive = location.pathname === item.href
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      onClick={closeSidebar}
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

        {/* Experimental section */}
        <div className="pt-3 mt-3 border-t border-dark-100/60">
          <button
            onClick={() => setExperimentalOpen((prev) => !prev)}
            className="w-full flex items-center gap-2 px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider hover:text-gray-400 transition-colors"
          >
            <ExperimentalIcon className="w-3.5 h-3.5" />
            <span className="flex-1 text-left">Experimental</span>
            {experimentalOpen ? (
              <CaretDown className="w-3.5 h-3.5" />
            ) : (
              <CaretRight className="w-3.5 h-3.5" />
            )}
          </button>

          {experimentalOpen && (
            <div className="mt-1 space-y-1">
              {experimentalNavigation.map((item) => {
                const isActive = location.pathname === item.href
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    onClick={closeSidebar}
                    className={clsx(
                      'flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition-all duration-200',
                      isActive
                        ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30'
                        : 'text-gray-500 hover:text-gray-300 hover:bg-dark-200'
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

        <div className="pt-4 mt-4 border-t border-dark-100">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-500 hover:text-white hover:bg-dark-200 transition-all duration-200"
          >
            <SignOut className="w-5 h-5" />
            Sign Out
          </button>
        </div>
      </nav>

      {/* Status */}
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
    </>
  )

  return (
    <div className="min-h-screen flex">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-white focus:text-black focus:rounded">
        Skip to content
      </a>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 lg:hidden transition-opacity"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* Sidebar — desktop: always visible; mobile: slide-in overlay */}
      <aside
        className={clsx(
          'w-64 bg-dark-300 border-r border-dark-100 flex flex-col',
          // Mobile: fixed overlay with slide transition
          'fixed inset-y-0 left-0 z-40 transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        aria-label="Main navigation"
      >
        {sidebarContent}
      </aside>

      {/* Main Content */}
      <main id="main-content" className="flex-1 overflow-auto flex flex-col min-w-0">
        {/* Top header bar */}
        <header className="flex items-center justify-between px-4 lg:px-8 py-3 border-b border-dark-100 bg-dark-300/50 flex-shrink-0">
          {/* Hamburger — mobile only */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 text-gray-400 hover:text-white transition-colors"
            aria-label="Open sidebar"
          >
            <List className="w-6 h-6" />
          </button>
          <div className="lg:hidden" />
          <NotificationCenter />
        </header>
        <div className="p-4 lg:p-8 flex-1">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </div>
      </main>
    </div>
  )
}
