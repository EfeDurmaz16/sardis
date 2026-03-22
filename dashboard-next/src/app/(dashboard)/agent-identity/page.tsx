"use client";
import { useState, useMemo } from 'react'
import {
  Users,
  Shield,
  Award,
  CheckCircle,
  AlertCircle,
  Code,
  TrendingUp,
  Plus,
  Eye,
  Star
} from 'lucide-react'
import clsx from 'clsx'
import StatCard from '@/components/StatCard'
import { useAgents } from '@/hooks/useApi'

interface AgentIdentity {
  id: string
  did: string
  name: string
  reputation_score: number
  validation_count: number
  total_volume: number
  first_seen: string
  last_active: string
  status: 'verified' | 'pending' | 'suspended'
  metadata: {
    version: string
    capabilities: string[]
    trusted_by: number
  }
}

interface AgentCard {
  did: string
  name: string
  description: string
  publicKey: string
  created: string
  issuer: string
  capabilities: string[]
  metadata: Record<string, unknown>
}

interface ReputationEvent {
  id: string
  agent_did: string
  event_type: 'validation' | 'violation' | 'transaction'
  impact: number
  description: string
  timestamp: string
}

export default function AgentIdentityPage() {
  const { data: apiAgents = [], isLoading } = useAgents()

  // Map API agents to AgentIdentity shape
  const agents: AgentIdentity[] = useMemo(() => {
    if (!apiAgents.length) return []
    return apiAgents.map((a) => ({
      id: a.agent_id,
      did: `did:sardis:agent:${a.agent_id}`,
      name: a.name || a.agent_id,
      reputation_score: 0,
      validation_count: 0,
      total_volume: 0,
      first_seen: a.created_at || new Date().toISOString(),
      last_active: a.created_at || new Date().toISOString(),
      status: (a.is_active ? 'verified' : 'pending') as AgentIdentity['status'],
      metadata: {
        version: '1.0.0',
        capabilities: ['payments'],
        trusted_by: 0,
      },
    }))
  }, [apiAgents])

  const [selectedAgent, setSelectedAgent] = useState<AgentIdentity | null>(null)
  const [viewingCard, setViewingCard] = useState(false)
  const [showRegisterForm, setShowRegisterForm] = useState(false)
  const [showReputationForm, setShowReputationForm] = useState(false)

  const [reputationEvents] = useState<ReputationEvent[]>([])

  const getAgentCard = (agent: AgentIdentity): AgentCard => {
    return {
      did: agent.did,
      name: agent.name,
      description: `AI agent with ${agent.metadata.capabilities.length} capabilities`,
      publicKey: `0x${agent.id.replace(/[^a-f0-9]/gi, '').padEnd(64, '0')}`,
      created: agent.first_seen,
      issuer: 'did:sardis:platform',
      capabilities: agent.metadata.capabilities,
      metadata: {
        reputation: agent.reputation_score,
        validations: agent.validation_count,
        version: agent.metadata.version,
      },
    }
  }

  const handleViewCard = (agent: AgentIdentity) => {
    setSelectedAgent(agent)
    setViewingCard(true)
  }

  const getStatusBadge = (status: AgentIdentity['status']) => {
    switch (status) {
      case 'verified':
        return <span className="badge badge-success">Verified</span>
      case 'pending':
        return <span className="badge badge-warning">Pending</span>
      case 'suspended':
        return <span className="badge badge-error">Suspended</span>
    }
  }

  const getReputationColor = (score: number) => {
    if (score >= 90) return 'text-sardis-400'
    if (score >= 75) return 'text-yellow-500'
    if (score >= 60) return 'text-orange-500'
    return 'text-red-500'
  }

  const getReputationBgColor = (score: number) => {
    if (score >= 90) return 'bg-sardis-500'
    if (score >= 75) return 'bg-yellow-500'
    if (score >= 60) return 'bg-orange-500'
    return 'bg-red-500'
  }

  const verifiedAgents = agents.filter(a => a.status === 'verified').length
  const avgReputation = agents.length > 0
    ? (agents.reduce((sum, a) => sum + a.reputation_score, 0) / agents.length).toFixed(1)
    : '0'
  const totalValidations = agents.reduce((sum, a) => sum + a.validation_count, 0)
  const totalTrustedBy = agents.reduce((sum, a) => sum + a.metadata.trusted_by, 0)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Agent Identity</h1>
          <p className="text-gray-400 mt-1">
            ERC-8004 agent identity registry and reputation system
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowReputationForm(true)}
            className="px-4 py-2 bg-dark-200 text-gray-400 hover:bg-dark-100 hover:text-white transition-colors font-medium flex items-center gap-2"
          >
            <Star className="w-4 h-4" />
            Submit Reputation
          </button>
          <button
            onClick={() => setShowRegisterForm(true)}
            className="px-4 py-2 bg-sardis-500 text-white hover:bg-sardis-600 transition-colors font-medium flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Register Agent
          </button>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-sardis-500 mx-auto mb-4" />
            <p className="text-gray-400 text-sm">Loading agents...</p>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && agents.length === 0 && (
        <div className="card p-12 text-center">
          <Users className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No agents registered</h3>
          <p className="text-gray-400">
            Create an agent to see it in the identity registry.
          </p>
        </div>
      )}

      {!isLoading && agents.length > 0 && (
        <>
          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              title="Registered Agents"
              value={agents.length}
              change={`${verifiedAgents} verified`}
              changeType="positive"
              icon={<Users className="w-6 h-6" />}
            />
            <StatCard
              title="Avg Reputation"
              value={avgReputation}
              change="Out of 100"
              changeType="positive"
              icon={<Award className="w-6 h-6" />}
            />
            <StatCard
              title="Total Validations"
              value={totalValidations.toLocaleString()}
              change="All time"
              changeType="positive"
              icon={<CheckCircle className="w-6 h-6" />}
            />
            <StatCard
              title="Trust Network"
              value={totalTrustedBy.toString()}
              change="Connected entities"
              changeType="positive"
              icon={<Shield className="w-6 h-6" />}
            />
          </div>

          {/* Agent Registry */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-white">Agent Registry</h2>
                <p className="text-sm text-gray-400 mt-1">Decentralized identity and reputation scores</p>
              </div>
              <Users className="w-5 h-5 text-sardis-400" />
            </div>

            <div className="space-y-3">
              {agents.map((agent) => (
                <div
                  key={agent.id}
                  className="p-4 bg-dark-200 border border-dark-100 hover:border-sardis-500/30 transition-all"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={clsx(
                        'w-12 h-12 rounded-full flex items-center justify-center',
                        agent.status === 'verified' && 'bg-sardis-500/10',
                        agent.status === 'pending' && 'bg-yellow-500/10',
                        agent.status === 'suspended' && 'bg-red-500/10'
                      )}>
                        <Users className={clsx(
                          'w-6 h-6',
                          agent.status === 'verified' && 'text-sardis-400',
                          agent.status === 'pending' && 'text-yellow-500',
                          agent.status === 'suspended' && 'text-red-500'
                        )} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-semibold text-white">{agent.name}</span>
                          {getStatusBadge(agent.status)}
                        </div>
                        <code className="text-xs text-gray-500 font-mono">{agent.did}</code>
                      </div>
                    </div>
                    <button
                      onClick={() => handleViewCard(agent)}
                      className="px-3 py-1.5 text-xs font-medium bg-dark-300 text-gray-400 hover:bg-sardis-500/20 hover:text-sardis-400 transition-colors flex items-center gap-1"
                    >
                      <Eye className="w-3 h-3" />
                      View Card
                    </button>
                  </div>

                  <div className="grid grid-cols-4 gap-4 mb-3">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Reputation</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-dark-300 rounded-full h-2">
                          <div
                            className={clsx('h-2 rounded-full', getReputationBgColor(agent.reputation_score))}
                            style={{ width: `${Math.max(agent.reputation_score, 1)}%` }}
                          />
                        </div>
                        <span className={clsx('text-sm font-bold mono-numbers', getReputationColor(agent.reputation_score))}>
                          {agent.reputation_score}
                        </span>
                      </div>
                    </div>

                    <div>
                      <p className="text-xs text-gray-500 mb-1">Validations</p>
                      <p className="text-sm font-medium text-white mono-numbers">{agent.validation_count}</p>
                    </div>

                    <div>
                      <p className="text-xs text-gray-500 mb-1">Total Volume</p>
                      <p className="text-sm font-medium text-sardis-400 mono-numbers">
                        ${agent.total_volume.toLocaleString()}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs text-gray-500 mb-1">Trusted By</p>
                      <p className="text-sm font-medium text-white mono-numbers">{agent.metadata.trusted_by}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-3 border-t border-dark-100">
                    <div className="flex-1 flex items-center gap-2 text-xs text-gray-500">
                      <Code className="w-3 h-3" />
                      <span>v{agent.metadata.version}</span>
                      <span>-</span>
                      <span>{agent.metadata.capabilities.length} capabilities</span>
                    </div>
                    <span className="text-xs text-gray-500">
                      Last active: {new Date(agent.last_active).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Agent Card Viewer & Recent Events */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Agent Card Viewer */}
            <div className="card p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-lg font-semibold text-white">Agent Card</h2>
                  <p className="text-sm text-gray-400 mt-1">ERC-8004 verifiable credential</p>
                </div>
                <Shield className="w-5 h-5 text-sardis-400" />
              </div>

              {viewingCard && selectedAgent ? (
                <div className="space-y-4">
                  <div className="p-4 bg-dark-200 border border-sardis-500/30 rounded-lg">
                    <div className="flex items-center gap-2 mb-3">
                      <CheckCircle className="w-5 h-5 text-sardis-400" />
                      <span className="font-semibold text-white">{selectedAgent.name}</span>
                    </div>

                    <div className="space-y-3 text-sm">
                      <div>
                        <p className="text-gray-500 text-xs mb-1">DID</p>
                        <code className="block text-xs text-sardis-400 font-mono bg-dark-300 px-2 py-1 rounded break-all">
                          {getAgentCard(selectedAgent).did}
                        </code>
                      </div>

                      <div>
                        <p className="text-gray-500 text-xs mb-1">Public Key</p>
                        <code className="block text-xs text-gray-400 font-mono bg-dark-300 px-2 py-1 rounded break-all">
                          {getAgentCard(selectedAgent).publicKey}
                        </code>
                      </div>

                      <div>
                        <p className="text-gray-500 text-xs mb-1">Capabilities</p>
                        <div className="flex flex-wrap gap-1">
                          {getAgentCard(selectedAgent).capabilities.map((cap, i) => (
                            <span key={i} className="px-2 py-0.5 bg-sardis-500/10 text-sardis-400 rounded text-xs">
                              {cap}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div>
                        <p className="text-gray-500 text-xs mb-1">Metadata</p>
                        <pre className="text-xs text-gray-300 font-mono bg-dark-300 px-2 py-2 rounded overflow-x-auto">
{JSON.stringify(getAgentCard(selectedAgent).metadata, null, 2)}
                        </pre>
                      </div>

                      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-dark-100">
                        <div>
                          <p className="text-gray-500 text-xs">Issued</p>
                          <p className="text-white text-xs">{new Date(getAgentCard(selectedAgent).created).toLocaleDateString()}</p>
                        </div>
                        <div>
                          <p className="text-gray-500 text-xs">Issuer</p>
                          <p className="text-white text-xs">{getAgentCard(selectedAgent).issuer}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => setViewingCard(false)}
                    className="w-full px-4 py-2 bg-dark-300 text-gray-400 hover:bg-dark-200 transition-colors text-sm font-medium"
                  >
                    Close
                  </button>
                </div>
              ) : (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <Shield className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                    <p className="text-sm text-gray-400">
                      Select an agent to view their verifiable credential card
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Reputation Events */}
            <div className="card p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-lg font-semibold text-white">Reputation Events</h2>
                  <p className="text-sm text-gray-400 mt-1">Recent validation and violation events</p>
                </div>
                <TrendingUp className="w-5 h-5 text-sardis-400" />
              </div>

              {reputationEvents.length === 0 ? (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <TrendingUp className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                    <p className="text-sm text-gray-400">
                      No reputation events yet
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3 max-h-[400px] overflow-y-auto custom-scrollbar">
                  {reputationEvents.map((event) => (
                    <div
                      key={event.id}
                      className={clsx(
                        'p-3 border rounded-lg',
                        event.event_type === 'validation' && 'bg-sardis-500/10 border-sardis-500/30',
                        event.event_type === 'violation' && 'bg-red-500/10 border-red-500/30',
                        event.event_type === 'transaction' && 'bg-blue-500/10 border-blue-500/30'
                      )}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {event.event_type === 'validation' && (
                            <CheckCircle className="w-4 h-4 text-sardis-400" />
                          )}
                          {event.event_type === 'violation' && (
                            <AlertCircle className="w-4 h-4 text-red-500" />
                          )}
                          {event.event_type === 'transaction' && (
                            <TrendingUp className="w-4 h-4 text-blue-500" />
                          )}
                          <span className="text-xs font-medium text-white capitalize">{event.event_type}</span>
                        </div>
                        <span className={clsx(
                          'text-xs font-bold mono-numbers',
                          event.impact > 0 ? 'text-sardis-400' : 'text-red-500'
                        )}>
                          {event.impact > 0 ? '+' : ''}{event.impact}
                        </span>
                      </div>

                      <p className="text-xs text-gray-300 mb-2">{event.description}</p>

                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <code className="font-mono">{event.agent_did.split(':').pop()}</code>
                        <span>{new Date(event.timestamp).toLocaleString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Register Form Modal (simplified placeholder) */}
      {showRegisterForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="card p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-white mb-4">Register New Agent</h3>
            <p className="text-sm text-gray-400 mb-4">
              Form to register a new agent identity (implementation pending)
            </p>
            <button
              onClick={() => setShowRegisterForm(false)}
              className="w-full px-4 py-2 bg-sardis-500 text-white hover:bg-sardis-600 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Reputation Form Modal (simplified placeholder) */}
      {showReputationForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="card p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-white mb-4">Submit Reputation Event</h3>
            <p className="text-sm text-gray-400 mb-4">
              Form to submit reputation validation or violation (implementation pending)
            </p>
            <button
              onClick={() => setShowReputationForm(false)}
              className="w-full px-4 py-2 bg-sardis-500 text-white hover:bg-sardis-600 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
