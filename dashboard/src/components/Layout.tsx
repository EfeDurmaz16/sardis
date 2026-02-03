
import { ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  ArrowRightLeft,
  Webhook,
  Settings,
  Wallet,
  Lock,
  FileText,
  LogOut
} from 'lucide-react'
import clsx from 'clsx'
import { useHealth } from '../hooks/useApi'
import { useAuth } from '../auth/AuthContext'

interface LayoutProps {
  children: ReactNode
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Agents', href: '/agents', icon: Users },
  { name: 'Transactions', href: '/transactions', icon: ArrowRightLeft },
  { name: 'Holds', href: '/holds', icon: Lock },
  { name: 'Invoices', href: '/invoices', icon: FileText },
  { name: 'Webhooks', href: '/webhooks', icon: Webhook },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { data: health, isError } = useHealth()
  const { logout } = useAuth()

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
            <div className="w-10 h-10 bg-sardis-500 rounded-lg flex items-center justify-center glow-green">
              <Wallet className="w-6 h-6 text-dark-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gradient">Sardis</h1>
              <p className="text-xs text-gray-500">AI Payment Network</p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                className={clsx(
                  'flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200',
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

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-gray-400 hover:text-white hover:bg-dark-200 transition-all duration-200"
          >
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>
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
            <p className="text-xs text-gray-500 mt-1">
              v{health.version}
            </p>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
