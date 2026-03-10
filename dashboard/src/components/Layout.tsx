
import { ReactNode, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  Wallet,
  CreditCard,
  Sparkles,
  LogOut,
  ShieldCheck,
  FlaskConical,
  Activity,
  CheckSquare,
  BarChart3,
  Shield,
  Target,
  Anchor,
  Award,
  AlertTriangle,
  Headset,
  Power,
  FileSearch,
  Store,
  Beaker,
  Radar,
  Receipt,
  Key,
  Webhook,
  Settings,
  ChevronDown,
  ChevronRight,
  FlaskConical as ExperimentalIcon,
  Rocket,
  LayoutGrid,
  GitBranch,
  LayoutTemplate,
  BookUser,
} from 'lucide-react'
import clsx from 'clsx'
import { useHealth } from '../hooks/useApi'
import { useAuth } from '../auth/AuthContext'
import NotificationCenter from './NotificationCenter'

interface LayoutProps {
  children: ReactNode
}

const primaryNavigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Go Live', href: '/go-live', icon: Rocket },
  { name: 'Templates', href: '/templates', icon: LayoutTemplate },
  { name: 'Control Center', href: '/control-center', icon: LayoutGrid },
  { name: 'Control Plane Demo', href: '/demo', icon: Sparkles },
  // ── Control Plane ──
  { name: 'Policy Manager', href: '/policy-manager', icon: GitBranch },
  { name: 'Approvals', href: '/approvals', icon: CheckSquare },
  { name: 'Approval Routing', href: '/approval-config', icon: Settings },
  { name: 'Kill Switch', href: '/kill-switch', icon: Power },
  { name: 'Evidence', href: '/evidence', icon: FileSearch },
  { name: 'Live Dry Run', href: '/simulation', icon: Beaker },
  { name: 'Anomaly Detection', href: '/anomaly', icon: Radar },
  { name: 'Merchants', href: '/merchants', icon: Store },
  { name: 'Counterparties', href: '/counterparties', icon: BookUser },
  { name: 'Fallback Rules', href: '/fallback-rules', icon: GitBranch },
  // ── Operations ──
  { name: 'Agents', href: '/agents', icon: Users },
  { name: 'Cards', href: '/cards', icon: CreditCard },
  { name: 'Stripe Issuing', href: '/stripe-issuing', icon: Wallet },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Policy Analytics', href: '/policy-analytics', icon: BarChart3 },
  { name: 'Live Events', href: '/events', icon: Activity },
  { name: 'Reconciliation', href: '/reconciliation', icon: ShieldCheck },
  { name: 'Enterprise Support', href: '/enterprise-support', icon: Headset },
  { name: 'Billing', href: '/billing', icon: Receipt },
  { name: 'API Keys', href: '/api-keys', icon: Key },
  { name: 'Webhooks', href: '/webhooks', icon: Webhook },
  { name: 'Settings', href: '/settings', icon: Settings },
]

const experimentalNavigation = [
  { name: 'Agent Identity', href: '/agent-identity', icon: Award },
  { name: 'Guardrails', href: '/guardrails', icon: Shield },
  { name: 'Confidence Router', href: '/confidence-router', icon: Target },
  { name: 'Audit Anchors', href: '/audit-anchors', icon: Anchor },
  { name: 'Goal Drift', href: '/goal-drift', icon: AlertTriangle },
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { data: health, isError } = useHealth()
  const { logout } = useAuth()

  const isOnExperimentalPage = experimentalNavigation.some(
    (item) => item.href === location.pathname
  )
  const [experimentalOpen, setExperimentalOpen] = useState(isOnExperimentalPage)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-dark-300 border-r border-dark-100 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-dark-100">
          <Link to="/" className="flex items-center gap-3">
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
          {primaryNavigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
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

          {/* Experimental section */}
          <div className="pt-3 mt-3 border-t border-dark-100/60">
            <button
              onClick={() => setExperimentalOpen((prev) => !prev)}
              className="w-full flex items-center gap-2 px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider hover:text-gray-400 transition-colors"
            >
              <ExperimentalIcon className="w-3.5 h-3.5" />
              <span className="flex-1 text-left">Experimental</span>
              {experimentalOpen ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5" />
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
              <LogOut className="w-5 h-5" />
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
