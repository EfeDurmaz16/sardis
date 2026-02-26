import { useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, Clock, Headset, LifeBuoy, ShieldCheck } from 'lucide-react'
import clsx from 'clsx'

import {
  useAcknowledgeSupportTicket,
  useCreateSupportTicket,
  useResolveSupportTicket,
  useSupportProfile,
  useSupportTickets,
} from '../hooks/useApi'

type TicketPriority = 'low' | 'medium' | 'high' | 'urgent'
type TicketStatus = 'open' | 'acknowledged' | 'resolved' | 'closed'
type TicketCategory = 'payments' | 'compliance' | 'infrastructure' | 'cards' | 'other'

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '-'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString()
}

function priorityBadge(priority: TicketPriority): string {
  switch (priority) {
    case 'urgent':
      return 'text-red-300 bg-red-500/10 border-red-500/30'
    case 'high':
      return 'text-orange-300 bg-orange-500/10 border-orange-500/30'
    case 'medium':
      return 'text-yellow-300 bg-yellow-500/10 border-yellow-500/30'
    default:
      return 'text-slate-300 bg-slate-500/10 border-slate-500/30'
  }
}

function planBadge(plan: 'free' | 'pro' | 'enterprise'): string {
  switch (plan) {
    case 'enterprise':
      return 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30'
    case 'pro':
      return 'text-blue-300 bg-blue-500/10 border-blue-500/30'
    default:
      return 'text-slate-300 bg-slate-500/10 border-slate-500/30'
  }
}

export default function EnterpriseSupportPage() {
  const [statusFilter, setStatusFilter] = useState<TicketStatus | 'all'>('open')
  const [priorityFilter, setPriorityFilter] = useState<TicketPriority | 'all'>('all')
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<TicketPriority>('medium')
  const [category, setCategory] = useState<TicketCategory>('other')

  const { data: profile } = useSupportProfile()
  const { data: tickets = [], isLoading } = useSupportTickets({
    status_filter: statusFilter === 'all' ? undefined : statusFilter,
    priority: priorityFilter === 'all' ? undefined : priorityFilter,
    limit: 100,
  })

  const createTicket = useCreateSupportTicket()
  const acknowledgeTicket = useAcknowledgeSupportTicket()
  const resolveTicket = useResolveSupportTicket()

  const slaBreaches = useMemo(() => {
    return tickets.filter((ticket) => ticket.response_sla_breached || ticket.resolution_sla_breached).length
  }, [tickets])

  const openCount = useMemo(() => {
    return tickets.filter((ticket) => ticket.status === 'open' || ticket.status === 'acknowledged').length
  }, [tickets])

  const onCreateTicket = async () => {
    if (!subject.trim() || !description.trim()) return
    await createTicket.mutateAsync({
      subject: subject.trim(),
      description: description.trim(),
      priority,
      category,
      metadata: {
        source: 'dashboard',
      },
    })
    setSubject('')
    setDescription('')
    setPriority('medium')
    setCategory('other')
    setStatusFilter('open')
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Enterprise Support</h1>
          <p className="text-gray-400 mt-1">
            SLA-backed support operations for payment-critical incidents.
          </p>
        </div>
        {profile ? (
          <span className={clsx('px-3 py-1.5 text-xs border uppercase tracking-wide', planBadge(profile.plan))}>
            {profile.plan} plan
          </span>
        ) : null}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4 border border-dark-100">
          <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-wide mb-1">
            <LifeBuoy className="w-4 h-4" />
            First Response SLA
          </div>
          <p className="text-white text-2xl font-semibold mono-numbers">
            {profile ? `${profile.first_response_sla_minutes}m` : '-'}
          </p>
        </div>
        <div className="card p-4 border border-dark-100">
          <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-wide mb-1">
            <Clock className="w-4 h-4" />
            Resolution SLA
          </div>
          <p className="text-white text-2xl font-semibold mono-numbers">
            {profile ? `${profile.resolution_sla_hours}h` : '-'}
          </p>
        </div>
        <div className="card p-4 border border-dark-100">
          <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-wide mb-1">
            <Headset className="w-4 h-4" />
            Active Tickets
          </div>
          <p className="text-white text-2xl font-semibold mono-numbers">{openCount}</p>
        </div>
        <div className="card p-4 border border-dark-100">
          <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-wide mb-1">
            <AlertTriangle className="w-4 h-4" />
            SLA Breaches
          </div>
          <p className="text-white text-2xl font-semibold mono-numbers">{slaBreaches}</p>
        </div>
      </div>

      <div className="card p-6 border border-dark-100">
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheck className="w-5 h-5 text-sardis-400" />
          <h2 className="text-lg text-white font-semibold">Open Support Ticket</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <input
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            placeholder="Subject"
            className="w-full bg-dark-200 border border-dark-100 px-3 py-2 text-white focus:outline-none focus:border-sardis-500"
          />
          <select
            value={priority}
            onChange={(event) => setPriority(event.target.value as TicketPriority)}
            className="w-full bg-dark-200 border border-dark-100 px-3 py-2 text-white focus:outline-none focus:border-sardis-500"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
          <select
            value={category}
            onChange={(event) => setCategory(event.target.value as TicketCategory)}
            className="w-full bg-dark-200 border border-dark-100 px-3 py-2 text-white focus:outline-none focus:border-sardis-500"
          >
            <option value="payments">Payments</option>
            <option value="compliance">Compliance</option>
            <option value="infrastructure">Infrastructure</option>
            <option value="cards">Cards</option>
            <option value="other">Other</option>
          </select>
          <button
            type="button"
            onClick={onCreateTicket}
            disabled={createTicket.isPending || !subject.trim() || !description.trim()}
            className="px-4 py-2 bg-sardis-500 text-dark-400 font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {createTicket.isPending ? 'Creating...' : 'Create Ticket'}
          </button>
        </div>
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Describe impact, affected rails, and urgency."
          rows={4}
          className="w-full bg-dark-200 border border-dark-100 px-3 py-2 text-white focus:outline-none focus:border-sardis-500"
        />
      </div>

      <div className="card p-6 border border-dark-100">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h2 className="text-lg text-white font-semibold">Tickets</h2>
          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as TicketStatus | 'all')}
              className="bg-dark-200 border border-dark-100 px-3 py-2 text-sm text-white"
            >
              <option value="all">All statuses</option>
              <option value="open">Open</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
            <select
              value={priorityFilter}
              onChange={(event) => setPriorityFilter(event.target.value as TicketPriority | 'all')}
              className="bg-dark-200 border border-dark-100 px-3 py-2 text-sm text-white"
            >
              <option value="all">All priorities</option>
              <option value="urgent">Urgent</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>

        {isLoading ? (
          <p className="text-gray-400">Loading support tickets...</p>
        ) : tickets.length === 0 ? (
          <p className="text-gray-400">No support tickets match current filters.</p>
        ) : (
          <div className="space-y-3">
            {tickets.map((ticket) => (
              <div key={ticket.id} className="bg-dark-200 border border-dark-100 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={clsx('px-2 py-0.5 text-xs border uppercase tracking-wide', priorityBadge(ticket.priority))}>
                        {ticket.priority}
                      </span>
                      <span className="px-2 py-0.5 text-xs border border-dark-100 text-gray-300 uppercase tracking-wide">
                        {ticket.status}
                      </span>
                      {(ticket.response_sla_breached || ticket.resolution_sla_breached) && (
                        <span className="px-2 py-0.5 text-xs border border-red-500/40 text-red-300 uppercase tracking-wide">
                          SLA breach
                        </span>
                      )}
                    </div>
                    <p className="text-white font-medium">{ticket.subject}</p>
                    <p className="text-gray-400 text-sm mt-1">{ticket.description}</p>
                    <div className="text-xs text-gray-500 mt-2 space-x-4">
                      <span>Created: {formatDate(ticket.created_at)}</span>
                      <span>Response due: {formatDate(ticket.first_response_due_at)}</span>
                      <span>Resolution due: {formatDate(ticket.resolution_due_at)}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {ticket.status === 'open' && (
                      <button
                        type="button"
                        onClick={() => acknowledgeTicket.mutate(ticket.id)}
                        disabled={acknowledgeTicket.isPending}
                        className="px-3 py-1.5 text-xs bg-dark-300 border border-dark-100 text-white hover:border-sardis-500 disabled:opacity-50"
                      >
                        Acknowledge
                      </button>
                    )}
                    {(ticket.status === 'open' || ticket.status === 'acknowledged') && (
                      <button
                        type="button"
                        onClick={() => resolveTicket.mutate({ ticketId: ticket.id })}
                        disabled={resolveTicket.isPending}
                        className="px-3 py-1.5 text-xs bg-sardis-500 text-dark-400 font-semibold disabled:opacity-50"
                      >
                        <span className="inline-flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Resolve
                        </span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

