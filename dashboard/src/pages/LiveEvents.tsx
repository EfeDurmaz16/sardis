import { useState, useEffect, useRef, useMemo } from 'react'
import {
  Activity,
  Pause,
  Play,
  Circle,
  DollarSign,
  ShieldCheck,
  CreditCard,
  AlertTriangle,
  Users,
  Target,
} from 'lucide-react'
import clsx from 'clsx'

/* ─── Types ─── */

type EventCategory = 'policy' | 'spend' | 'approval' | 'card' | 'compliance' | 'group' | 'all'

interface LiveEvent {
  id: string
  timestamp: Date
  type: string
  category: EventCategory
  agentId: string
  amount?: number
  status: 'success' | 'warning' | 'error' | 'info'
  message: string
  metadata?: Record<string, any>
}

/* ─── Constants ─── */

const EVENT_TYPES = {
  // Policy
  'policy.created': { category: 'policy' as EventCategory, label: 'Policy Created', status: 'info' as const },
  'policy.updated': { category: 'policy' as EventCategory, label: 'Policy Updated', status: 'info' as const },
  'policy.violated': { category: 'policy' as EventCategory, label: 'Policy Violated', status: 'error' as const },
  'policy.check.passed': { category: 'policy' as EventCategory, label: 'Policy Check', status: 'success' as const },

  // Spend
  'spend.threshold.warning': { category: 'spend' as EventCategory, label: 'Threshold Warning', status: 'warning' as const },
  'spend.threshold.reached': { category: 'spend' as EventCategory, label: 'Limit Reached', status: 'error' as const },
  'spend.daily.summary': { category: 'spend' as EventCategory, label: 'Daily Summary', status: 'info' as const },
  'payment.initiated': { category: 'spend' as EventCategory, label: 'Payment Started', status: 'info' as const },
  'payment.completed': { category: 'spend' as EventCategory, label: 'Payment Complete', status: 'success' as const },
  'payment.failed': { category: 'spend' as EventCategory, label: 'Payment Failed', status: 'error' as const },

  // Approval
  'approval.requested': { category: 'approval' as EventCategory, label: 'Approval Requested', status: 'warning' as const },
  'approval.granted': { category: 'approval' as EventCategory, label: 'Approval Granted', status: 'success' as const },
  'approval.denied': { category: 'approval' as EventCategory, label: 'Approval Denied', status: 'error' as const },

  // Card
  'card.created': { category: 'card' as EventCategory, label: 'Card Created', status: 'success' as const },
  'card.transaction': { category: 'card' as EventCategory, label: 'Card Transaction', status: 'info' as const },
  'card.declined': { category: 'card' as EventCategory, label: 'Card Declined', status: 'error' as const },

  // Compliance
  'compliance.check.passed': { category: 'compliance' as EventCategory, label: 'Compliance Check', status: 'success' as const },
  'compliance.check.failed': { category: 'compliance' as EventCategory, label: 'Compliance Failed', status: 'error' as const },
  'compliance.alert': { category: 'compliance' as EventCategory, label: 'Compliance Alert', status: 'warning' as const },

  // Group
  'group.budget.warning': { category: 'group' as EventCategory, label: 'Group Budget Warning', status: 'warning' as const },
  'group.budget.exceeded': { category: 'group' as EventCategory, label: 'Group Budget Exceeded', status: 'error' as const },
}

const AGENT_POOL = [
  'agent_research_001',
  'agent_marketing_002',
  'agent_ops_003',
  'agent_devrel_004',
  'agent_analytics_005',
  'agent_support_006',
]

const MERCHANTS = ['OpenAI', 'Anthropic', 'AWS', 'Vercel', 'Stripe', 'GitHub']

/* ─── Helpers ─── */

function generateMockEvent(): LiveEvent {
  const eventTypeKeys = Object.keys(EVENT_TYPES)
  const randomType = eventTypeKeys[Math.floor(Math.random() * eventTypeKeys.length)]
  const eventConfig = EVENT_TYPES[randomType as keyof typeof EVENT_TYPES]

  const agentId = AGENT_POOL[Math.floor(Math.random() * AGENT_POOL.length)]
  const amount = eventConfig.category === 'spend' || eventConfig.category === 'card'
    ? Math.random() * 500 + 5
    : undefined

  let message = ''
  if (eventConfig.category === 'policy') {
    if (randomType === 'policy.violated') {
      message = 'Transaction exceeds per-tx limit of $50'
    } else if (randomType === 'policy.check.passed') {
      message = 'All policy checks passed'
    } else {
      message = 'Natural language policy updated'
    }
  } else if (eventConfig.category === 'spend') {
    const merchant = MERCHANTS[Math.floor(Math.random() * MERCHANTS.length)]
    if (randomType === 'payment.completed') {
      message = `Payment to ${merchant} completed`
    } else if (randomType === 'payment.failed') {
      message = `Payment to ${merchant} failed: insufficient balance`
    } else if (randomType === 'spend.threshold.warning') {
      message = '80% of daily spend limit reached'
    } else {
      message = `Payment to ${merchant} initiated`
    }
  } else if (eventConfig.category === 'approval') {
    message = randomType === 'approval.granted'
      ? 'High-value transaction approved'
      : randomType === 'approval.denied'
      ? 'Transaction denied by approver'
      : 'Requires manual approval (>$100)'
  } else if (eventConfig.category === 'card') {
    const merchant = MERCHANTS[Math.floor(Math.random() * MERCHANTS.length)]
    message = randomType === 'card.declined'
      ? `Card declined at ${merchant}: policy violation`
      : `Card transaction at ${merchant}`
  } else if (eventConfig.category === 'compliance') {
    message = randomType === 'compliance.check.failed'
      ? 'Sanctions screening failed'
      : 'AML check passed'
  } else {
    message = 'Group budget threshold exceeded'
  }

  return {
    id: `evt_${Math.random().toString(36).substring(2, 10)}`,
    timestamp: new Date(),
    type: randomType,
    category: eventConfig.category,
    agentId,
    amount,
    status: eventConfig.status,
    message,
  }
}

function getCategoryIcon(category: EventCategory) {
  switch (category) {
    case 'policy': return ShieldCheck
    case 'spend': return DollarSign
    case 'approval': return AlertTriangle
    case 'card': return CreditCard
    case 'compliance': return Target
    case 'group': return Users
    default: return Activity
  }
}

function getCategoryColor(category: EventCategory) {
  switch (category) {
    case 'policy': return 'text-blue-400'
    case 'spend': return 'text-sardis-400'
    case 'approval': return 'text-yellow-400'
    case 'card': return 'text-purple-400'
    case 'compliance': return 'text-orange-400'
    case 'group': return 'text-pink-400'
    default: return 'text-gray-400'
  }
}

function getStatusColor(status: LiveEvent['status']) {
  switch (status) {
    case 'success': return 'bg-sardis-500/10 text-sardis-400 border-sardis-500/30'
    case 'warning': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30'
    case 'error': return 'bg-red-500/10 text-red-400 border-red-500/30'
    case 'info': return 'bg-blue-500/10 text-blue-400 border-blue-500/30'
  }
}

/* ─── Main Component ─── */

export default function LiveEventsPage() {
  const [events, setEvents] = useState<LiveEvent[]>([])
  const [isPaused, setIsPaused] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<EventCategory>('all')
  const [isConnected, setIsConnected] = useState(true)
  const eventsEndRef = useRef<HTMLDivElement>(null)
  const shouldAutoScrollRef = useRef(true)

  // Stats
  const stats = useMemo(() => {
    const now = Date.now()
    const oneMinuteAgo = now - 60000
    const recentEvents = events.filter(e => e.timestamp.getTime() > oneMinuteAgo)
    const activeAgents = new Set(events.slice(0, 50).map(e => e.agentId)).size

    return {
      eventsPerMinute: recentEvents.length,
      totalEvents: events.length,
      activeAgents,
    }
  }, [events])

  // Filtered events
  const filteredEvents = useMemo(() => {
    if (selectedCategory === 'all') return events
    return events.filter(e => e.category === selectedCategory)
  }, [events, selectedCategory])

  // Auto-scroll to bottom
  useEffect(() => {
    if (shouldAutoScrollRef.current && !isPaused) {
      eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [filteredEvents, isPaused])

  // Simulate WebSocket with setInterval
  useEffect(() => {
    if (isPaused) return

    // Initial burst
    const initialEvents = Array.from({ length: 10 }, () => generateMockEvent())
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
    setEvents(initialEvents)

    // Generate events at random intervals (1-4 seconds)
    let timeoutId: NodeJS.Timeout

    const scheduleNext = () => {
      const delay = Math.random() * 3000 + 1000 // 1-4 seconds
      timeoutId = setTimeout(() => {
        setEvents(prev => {
          const newEvents = [...prev, generateMockEvent()]
          // Keep last 200 events
          return newEvents.slice(-200)
        })
        scheduleNext()
      }, delay)
    }

    scheduleNext()

    return () => {
      clearTimeout(timeoutId)
    }
  }, [isPaused])

  // Simulate occasional disconnection
  useEffect(() => {
    const interval = setInterval(() => {
      if (Math.random() > 0.95) {
        setIsConnected(false)
        setTimeout(() => setIsConnected(true), 2000)
      }
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  const categories: { value: EventCategory; label: string; icon: any }[] = [
    { value: 'all', label: 'All Events', icon: Activity },
    { value: 'policy', label: 'Policy', icon: ShieldCheck },
    { value: 'spend', label: 'Spend', icon: DollarSign },
    { value: 'approval', label: 'Approval', icon: AlertTriangle },
    { value: 'card', label: 'Card', icon: CreditCard },
    { value: 'compliance', label: 'Compliance', icon: Target },
    { value: 'group', label: 'Group', icon: Users },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Live Events</h1>
          <p className="text-gray-400 mt-1">
            Real-time event stream from the Sardis platform
          </p>
        </div>
        <div className="flex items-center gap-4">
          {/* Connection status */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-dark-200 rounded-lg border border-dark-100">
            <div className={clsx(
              'w-2 h-2 rounded-full transition-colors',
              isConnected ? 'bg-sardis-500 animate-pulse' : 'bg-red-500'
            )} />
            <span className={clsx(
              'text-sm font-medium',
              isConnected ? 'text-sardis-400' : 'text-red-400'
            )}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          {/* Pause/Resume */}
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 text-sm font-medium',
              isPaused
                ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30'
                : 'bg-sardis-500/10 text-sardis-400 border border-sardis-500/30 hover:bg-sardis-500/20'
            )}
          >
            {isPaused ? (
              <>
                <Play className="w-4 h-4" />
                Resume
              </>
            ) : (
              <>
                <Pause className="w-4 h-4" />
                Pause
              </>
            )}
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Events/Minute</p>
              <p className="text-2xl font-bold text-white font-mono mono-numbers mt-1">
                {stats.eventsPerMinute}
              </p>
            </div>
            <Activity className="w-8 h-8 text-sardis-400/50" />
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Total Events</p>
              <p className="text-2xl font-bold text-white font-mono mono-numbers mt-1">
                {stats.totalEvents}
              </p>
            </div>
            <Circle className="w-8 h-8 text-blue-400/50" />
          </div>
        </div>

        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Active Agents</p>
              <p className="text-2xl font-bold text-white font-mono mono-numbers mt-1">
                {stats.activeAgents}
              </p>
            </div>
            <Users className="w-8 h-8 text-purple-400/50" />
          </div>
        </div>
      </div>

      {/* Filter Chips */}
      <div className="flex flex-wrap gap-2">
        {categories.map(cat => {
          const Icon = cat.icon
          const isActive = selectedCategory === cat.value
          return (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value)}
              className={clsx(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all duration-200 text-sm font-medium border',
                isActive
                  ? 'bg-sardis-500/10 text-sardis-400 border-sardis-500/30'
                  : 'bg-dark-200 text-gray-400 border-dark-100 hover:text-white hover:border-dark-100/80'
              )}
            >
              <Icon className="w-4 h-4" />
              {cat.label}
              {cat.value === 'all' && (
                <span className="px-1.5 py-0.5 text-xs bg-dark-300 rounded mono-numbers">
                  {events.length}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Event Feed */}
      <div className="card">
        <div className="border-b border-dark-100 px-6 py-4">
          <h2 className="text-lg font-semibold text-white">Event Stream</h2>
        </div>

        <div
          className="h-[600px] overflow-y-auto"
          onScroll={(e) => {
            const el = e.currentTarget
            const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
            shouldAutoScrollRef.current = isNearBottom
          }}
        >
          <div className="divide-y divide-dark-100">
            {filteredEvents.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-500 py-20">
                <Activity className="w-12 h-12 mb-3" />
                <p className="text-sm">No events yet. Waiting for activity...</p>
              </div>
            ) : (
              <>
                {filteredEvents.map(event => {
                  const CategoryIcon = getCategoryIcon(event.category)
                  const categoryColor = getCategoryColor(event.category)
                  const eventConfig = EVENT_TYPES[event.type as keyof typeof EVENT_TYPES]

                  return (
                    <div
                      key={event.id}
                      className="px-6 py-3 hover:bg-dark-200/30 transition-colors"
                    >
                      <div className="flex items-start gap-4">
                        {/* Timestamp */}
                        <div className="flex-shrink-0 w-20">
                          <p className="text-xs text-gray-500 font-mono mono-numbers">
                            {event.timestamp.toLocaleTimeString('en-US', {
                              hour12: false,
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit'
                            })}
                          </p>
                        </div>

                        {/* Event Type Badge */}
                        <div className="flex-shrink-0">
                          <div className={clsx(
                            'flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-medium',
                            getStatusColor(event.status)
                          )}>
                            <CategoryIcon className={clsx('w-3.5 h-3.5', categoryColor)} />
                            {eventConfig?.label || event.type}
                          </div>
                        </div>

                        {/* Agent ID */}
                        <div className="flex-shrink-0 min-w-[140px]">
                          <p className="text-sm text-gray-400 font-mono truncate">
                            {event.agentId}
                          </p>
                        </div>

                        {/* Amount */}
                        <div className="flex-shrink-0 w-24 text-right">
                          {event.amount !== undefined ? (
                            <p className="text-sm text-white font-mono mono-numbers">
                              ${event.amount.toFixed(2)}
                            </p>
                          ) : (
                            <p className="text-sm text-gray-600">--</p>
                          )}
                        </div>

                        {/* Message */}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-300 truncate">
                            {event.message}
                          </p>
                        </div>

                        {/* Status indicator */}
                        <div className="flex-shrink-0">
                          <div className={clsx(
                            'w-2 h-2 rounded-full',
                            event.status === 'success' && 'bg-sardis-500',
                            event.status === 'warning' && 'bg-yellow-500',
                            event.status === 'error' && 'bg-red-500',
                            event.status === 'info' && 'bg-blue-500',
                          )} />
                        </div>
                      </div>
                    </div>
                  )
                })}
                <div ref={eventsEndRef} />
              </>
            )}
          </div>
        </div>

        {isPaused && (
          <div className="border-t border-dark-100 px-6 py-3 bg-yellow-500/5">
            <div className="flex items-center gap-2 text-yellow-400">
              <Pause className="w-4 h-4" />
              <span className="text-sm font-medium">Stream paused</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
