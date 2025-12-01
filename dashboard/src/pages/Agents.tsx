import { useState } from 'react'
import { Plus, Search, User, Wallet, ArrowRight } from 'lucide-react'
import clsx from 'clsx'
import { useAgents, useCreateAgent } from '../hooks/useApi'
import ChatInterface from '../components/ChatInterface'

export default function AgentsPage() {
  const { data: agents = [], isLoading } = useAgents()
  const createAgent = useCreateAgent()
  const [showCreate, setShowCreate] = useState(false)
  const [search, setSearch] = useState('')
  const [activeChatAgent, setActiveChatAgent] = useState<any>(null)

  const filteredAgents = agents.filter((agent: any) =>
    agent.name?.toLowerCase().includes(search.toLowerCase()) ||
    agent.agent_id?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Agents</h1>
          <p className="text-gray-400 mt-1">
            Manage your AI agent wallets
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover"
        >
          <Plus className="w-5 h-5" />
          New Agent
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
        <input
          type="text"
          placeholder="Search agents..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-12 pr-4 py-3 bg-dark-200 border border-dark-100 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50"
        />
      </div>

      {/* Agents List */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-6 animate-pulse">
              <div className="h-4 bg-dark-100 rounded w-3/4 mb-4" />
              <div className="h-3 bg-dark-100 rounded w-1/2 mb-2" />
              <div className="h-3 bg-dark-100 rounded w-1/4" />
            </div>
          ))}
        </div>
      ) : filteredAgents.length === 0 ? (
        <div className="card p-12 text-center">
          <User className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No agents found</h3>
          <p className="text-gray-400 mb-4">
            {search ? 'Try a different search term' : 'Create your first AI agent to get started'}
          </p>
          {!search && (
            <button
              onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-sardis-500/10 text-sardis-400 rounded-lg hover:bg-sardis-500/20 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Create Agent
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAgents.map((agent: any) => (
            <AgentCard
              key={agent.agent_id}
              agent={agent}
              onChat={() => setActiveChatAgent(agent)}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <CreateAgentModal
          onClose={() => setShowCreate(false)}
          onSubmit={async (data) => {
            await createAgent.mutateAsync(data)
            setShowCreate(false)
          }}
          isLoading={createAgent.isPending}
        />
      )}

      {/* Chat Modal */}
      {activeChatAgent && (
        <ChatInterface
          agentId={activeChatAgent.agent_id}
          agentName={activeChatAgent.name}
          onClose={() => setActiveChatAgent(null)}
        />
      )}
    </div>
  )
}

function AgentCard({ agent, onChat }: { agent: any, onChat: () => void }) {
  return (
    <div className="card card-hover p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
            <User className="w-5 h-5 text-sardis-400" />
          </div>
          <div>
            <h3 className="font-medium text-white">{agent.name}</h3>
            <p className="text-xs text-gray-500 font-mono">{agent.agent_id}</p>
          </div>
        </div>
        <div className={clsx(
          'status-dot',
          agent.is_active ? 'success' : 'error'
        )} />
      </div>

      {agent.description && (
        <p className="text-sm text-gray-400 mb-4 line-clamp-2">
          {agent.description}
        </p>
      )}

      <div className="flex items-center justify-between pt-4 border-t border-dark-100">
        <div className="flex items-center gap-2 text-gray-400">
          <Wallet className="w-4 h-4" />
          <span className="text-sm">Wallet</span>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onChat}
            className="flex items-center gap-1 text-sm text-sardis-400 hover:text-sardis-300 transition-colors px-3 py-1.5 bg-sardis-500/10 rounded-lg hover:bg-sardis-500/20"
          >
            Chat
          </button>
          <button className="flex items-center gap-1 text-sm text-gray-400 hover:text-white transition-colors px-3 py-1.5 hover:bg-dark-100 rounded-lg">
            View <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

function CreateAgentModal({
  onClose,
  onSubmit,
  isLoading
}: {
  onClose: () => void
  onSubmit: (data: any) => Promise<void>
  isLoading: boolean
}) {
  const [formData, setFormData] = useState({
    name: '',
    owner_id: 'demo_owner',
    description: '',
    initial_balance: '100.00',
    limit_per_tx: '50.00',
    limit_total: '100.00'
  })

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="card max-w-md w-full mx-4 p-6">
        <h2 className="text-xl font-bold text-white mb-6">Create New Agent</h2>

        <form
          onSubmit={async (e) => {
            e.preventDefault()
            await onSubmit(formData)
          }}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              Agent Name
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData(d => ({ ...d, name: e.target.value }))}
              className="w-full px-4 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
              placeholder="shopping_agent_001"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData(d => ({ ...d, description: e.target.value }))}
              className="w-full px-4 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50 resize-none"
              rows={2}
              placeholder="Optional description..."
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Balance
              </label>
              <input
                type="text"
                required
                value={formData.initial_balance}
                onChange={(e) => setFormData(d => ({ ...d, initial_balance: e.target.value }))}
                className="w-full px-4 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Per TX
              </label>
              <input
                type="text"
                required
                value={formData.limit_per_tx}
                onChange={(e) => setFormData(d => ({ ...d, limit_per_tx: e.target.value }))}
                className="w-full px-4 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Total
              </label>
              <input
                type="text"
                required
                value={formData.limit_total}
                onChange={(e) => setFormData(d => ({ ...d, limit_total: e.target.value }))}
                className="w-full px-4 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
              />
            </div>
          </div>

          <div className="flex gap-4 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-dark-100 text-gray-400 rounded-lg hover:bg-dark-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Creating...' : 'Create Agent'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

