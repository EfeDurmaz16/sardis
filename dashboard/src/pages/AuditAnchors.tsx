import { useState, useEffect } from 'react'
import {
  Anchor,
  CheckCircle,
  Clock,
  AlertCircle,
  GitBranch,
  Hash,
  FileText,
  Shield,
  ExternalLink,
  Search
} from 'lucide-react'
import clsx from 'clsx'
import StatCard from '../components/StatCard'

// Mock data - will be replaced with API calls later
interface AuditAnchor {
  id: string
  merkle_root: string
  tx_hash: string
  block_number: number
  chain: string
  entry_count: number
  status: 'pending' | 'confirmed' | 'failed'
  created_at: string
  confirmed_at?: string
}

interface MerkleProof {
  entry_hash: string
  merkle_root: string
  proof: string[]
  is_valid: boolean
}

interface LedgerEntry {
  id: string
  entry_hash: string
  agent_id: string
  transaction_id: string
  amount: number
  timestamp: string
  anchor_id?: string
}

export default function AuditAnchorsPage() {
  const [anchors, setAnchors] = useState<AuditAnchor[]>([
    {
      id: 'anchor_1',
      merkle_root: '0x8f4d7c3b2e9a1f5d6c8b4a7e3d2f1c9b8a7d6f5e4c3b2a1d',
      tx_hash: '0x1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z',
      block_number: 12345678,
      chain: 'Base',
      entry_count: 247,
      status: 'confirmed',
      created_at: '2024-01-15T12:00:00Z',
      confirmed_at: '2024-01-15T12:02:30Z',
    },
    {
      id: 'anchor_2',
      merkle_root: '0x3e7a9c2f8d1b6e4a7c9f2d5b8e1a4c7f9d2b5e8a1c4f7d9b2e5',
      tx_hash: '0x9z8y7x6w5v4u3t2s1r0q9p8o7n6m5l4k3j2i1h0g9f8e7d6c5b4a',
      block_number: 12345679,
      chain: 'Polygon',
      entry_count: 189,
      status: 'confirmed',
      created_at: '2024-01-15T11:00:00Z',
      confirmed_at: '2024-01-15T11:01:45Z',
    },
    {
      id: 'anchor_3',
      merkle_root: '0x7b9d2f4e6a8c1d3f5b7e9a2c4d6f8b1d3e5a7c9f2b4d6e8a1c3',
      tx_hash: '0x5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b',
      block_number: 12345680,
      chain: 'Base',
      entry_count: 312,
      status: 'pending',
      created_at: '2024-01-15T13:00:00Z',
    },
  ])

  const [entries, setEntries] = useState<LedgerEntry[]>([
    {
      id: 'entry_1',
      entry_hash: '0xabc123def456',
      agent_id: 'agent_001',
      transaction_id: 'tx_12345',
      amount: 50.00,
      timestamp: '2024-01-15T12:00:00Z',
      anchor_id: 'anchor_1',
    },
    {
      id: 'entry_2',
      entry_hash: '0x789ghi012jkl',
      agent_id: 'agent_002',
      transaction_id: 'tx_12346',
      amount: 250.00,
      timestamp: '2024-01-15T11:55:00Z',
      anchor_id: 'anchor_1',
    },
    {
      id: 'entry_3',
      entry_hash: '0x345mno678pqr',
      agent_id: 'agent_003',
      transaction_id: 'tx_12347',
      amount: 1500.00,
      timestamp: '2024-01-15T11:50:00Z',
      anchor_id: 'anchor_2',
    },
  ])

  const [selectedEntry, setSelectedEntry] = useState<string | null>(null)
  const [verificationResult, setVerificationResult] = useState<MerkleProof | null>(null)
  const [isVerifying, setIsVerifying] = useState(false)

  const handleVerifyAnchor = (anchorId: string) => {
    // Simulate verification API call
    setIsVerifying(true)
    setTimeout(() => {
      console.log(`Verifying anchor ${anchorId}`)
      setIsVerifying(false)
      // In real implementation, this would update the anchor status from the API
    }, 1500)
  }

  const handleVerifyEntry = (entryId: string) => {
    const entry = entries.find(e => e.id === entryId)
    if (!entry || !entry.anchor_id) return

    setSelectedEntry(entryId)
    setIsVerifying(true)

    // Simulate Merkle proof verification
    setTimeout(() => {
      const anchor = anchors.find(a => a.id === entry.anchor_id)
      setVerificationResult({
        entry_hash: entry.entry_hash,
        merkle_root: anchor?.merkle_root || '',
        proof: [
          '0x1a2b3c4d',
          '0x5e6f7g8h',
          '0x9i0j1k2l',
        ],
        is_valid: true,
      })
      setIsVerifying(false)
    }, 1000)
  }

  const handleTriggerAnchor = () => {
    // Simulate creating a new anchor
    const newAnchor: AuditAnchor = {
      id: `anchor_${anchors.length + 1}`,
      merkle_root: `0x${Math.random().toString(16).substring(2, 50)}`,
      tx_hash: `0x${Math.random().toString(16).substring(2, 66)}`,
      block_number: 12345680 + anchors.length,
      chain: 'Base',
      entry_count: Math.floor(Math.random() * 300) + 100,
      status: 'pending',
      created_at: new Date().toISOString(),
    }
    setAnchors(prev => [newAnchor, ...prev])
  }

  const getStatusBadge = (status: AuditAnchor['status']) => {
    switch (status) {
      case 'confirmed':
        return <span className="badge badge-success">Confirmed</span>
      case 'pending':
        return <span className="badge badge-warning">Pending</span>
      case 'failed':
        return <span className="badge badge-error">Failed</span>
    }
  }

  const getStatusIcon = (status: AuditAnchor['status']) => {
    switch (status) {
      case 'confirmed':
        return <CheckCircle className="w-5 h-5 text-sardis-400" />
      case 'pending':
        return <Clock className="w-5 h-5 text-yellow-500" />
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-500" />
    }
  }

  const confirmedAnchors = anchors.filter(a => a.status === 'confirmed').length
  const totalEntries = anchors.reduce((sum, a) => sum + a.entry_count, 0)
  const pendingAnchors = anchors.filter(a => a.status === 'pending').length

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Audit Anchors</h1>
          <p className="text-gray-400 mt-1">
            Merkle tree anchors for immutable audit trail verification
          </p>
        </div>
        <button
          onClick={handleTriggerAnchor}
          className="px-4 py-2 bg-sardis-500 text-white hover:bg-sardis-600 transition-colors font-medium flex items-center gap-2"
        >
          <Anchor className="w-4 h-4" />
          Trigger Manual Anchor
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Anchors"
          value={anchors.length}
          change={`${confirmedAnchors} confirmed`}
          changeType="positive"
          icon={<Anchor className="w-6 h-6" />}
        />
        <StatCard
          title="Pending Verification"
          value={pendingAnchors}
          change="On-chain confirmation"
          changeType={pendingAnchors > 0 ? 'neutral' : 'positive'}
          icon={<Clock className="w-6 h-6" />}
        />
        <StatCard
          title="Total Entries"
          value={totalEntries.toLocaleString()}
          change="Anchored on-chain"
          changeType="positive"
          icon={<FileText className="w-6 h-6" />}
        />
        <StatCard
          title="Integrity Score"
          value="100%"
          change="All verifications pass"
          changeType="positive"
          icon={<Shield className="w-6 h-6" />}
        />
      </div>

      {/* Anchor Records */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-white">Anchor Records</h2>
            <p className="text-sm text-gray-400 mt-1">On-chain Merkle tree commitments</p>
          </div>
          <GitBranch className="w-5 h-5 text-sardis-400" />
        </div>

        <div className="space-y-4">
          {anchors.map((anchor) => (
            <div
              key={anchor.id}
              className="p-4 bg-dark-200 border border-dark-100 hover:border-sardis-500/30 transition-all"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  {getStatusIcon(anchor.status)}
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-white">{anchor.id}</span>
                      <span className="text-xs px-2 py-0.5 bg-dark-300 text-gray-400 rounded">
                        {anchor.chain}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500">
                      Block {anchor.block_number.toLocaleString()} • {anchor.entry_count} entries
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusBadge(anchor.status)}
                  <button
                    onClick={() => handleVerifyAnchor(anchor.id)}
                    disabled={isVerifying || anchor.status === 'pending'}
                    className={clsx(
                      'px-3 py-1.5 text-xs font-medium transition-colors',
                      anchor.status === 'confirmed'
                        ? 'bg-sardis-500/10 text-sardis-400 hover:bg-sardis-500/20'
                        : 'bg-dark-300 text-gray-500 cursor-not-allowed'
                    )}
                  >
                    Verify
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-500 text-xs mb-1 flex items-center gap-1">
                    <Hash className="w-3 h-3" />
                    Merkle Root
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="text-xs text-sardis-400 font-mono bg-dark-300 px-2 py-1 rounded">
                      {anchor.merkle_root.substring(0, 20)}...{anchor.merkle_root.substring(anchor.merkle_root.length - 8)}
                    </code>
                  </div>
                </div>

                <div>
                  <p className="text-gray-500 text-xs mb-1 flex items-center gap-1">
                    <ExternalLink className="w-3 h-3" />
                    Transaction Hash
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="text-xs text-blue-400 font-mono bg-dark-300 px-2 py-1 rounded">
                      {anchor.tx_hash.substring(0, 20)}...{anchor.tx_hash.substring(anchor.tx_hash.length - 8)}
                    </code>
                    <a
                      href={`https://basescan.org/tx/${anchor.tx_hash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-400 hover:text-sardis-400 transition-colors"
                    >
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mt-3 pt-3 border-t border-dark-100 text-xs">
                <div>
                  <span className="text-gray-500">Created:</span>{' '}
                  <span className="text-white">{new Date(anchor.created_at).toLocaleString()}</span>
                </div>
                {anchor.confirmed_at && (
                  <div>
                    <span className="text-gray-500">Confirmed:</span>{' '}
                    <span className="text-white">{new Date(anchor.confirmed_at).toLocaleString()}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Entry Verification */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ledger Entries */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white">Ledger Entries</h2>
              <p className="text-sm text-gray-400 mt-1">Verify individual entries</p>
            </div>
            <FileText className="w-5 h-5 text-sardis-400" />
          </div>

          <div className="space-y-3">
            {entries.map((entry) => (
              <div
                key={entry.id}
                className={clsx(
                  'p-3 bg-dark-200 border transition-all cursor-pointer',
                  selectedEntry === entry.id
                    ? 'border-sardis-500/50 bg-sardis-500/5'
                    : 'border-dark-100 hover:border-sardis-500/30'
                )}
                onClick={() => handleVerifyEntry(entry.id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Search className="w-4 h-4 text-gray-400" />
                    <span className="text-xs font-mono text-gray-400">{entry.id}</span>
                  </div>
                  <span className="text-sm font-medium text-sardis-400 mono-numbers">
                    ${entry.amount.toFixed(2)}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-500">Agent:</span>{' '}
                    <span className="text-white">{entry.agent_id}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">TX:</span>{' '}
                    <span className="text-white">{entry.transaction_id}</span>
                  </div>
                </div>

                <div className="mt-2 pt-2 border-t border-dark-100 flex items-center justify-between text-xs">
                  <code className="text-gray-400 font-mono">
                    {entry.entry_hash}
                  </code>
                  {entry.anchor_id && (
                    <span className="px-2 py-0.5 bg-sardis-500/10 text-sardis-400 rounded">
                      Anchored
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Merkle Proof Display */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white">Merkle Proof</h2>
              <p className="text-sm text-gray-400 mt-1">Cryptographic verification</p>
            </div>
            <Shield className="w-5 h-5 text-sardis-400" />
          </div>

          {isVerifying ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sardis-500 mx-auto mb-4" />
                <p className="text-sm text-gray-400">Verifying proof...</p>
              </div>
            </div>
          ) : verificationResult ? (
            <div className="space-y-4">
              <div className={clsx(
                'p-4 border rounded-lg',
                verificationResult.is_valid
                  ? 'bg-sardis-500/10 border-sardis-500/30'
                  : 'bg-red-500/10 border-red-500/30'
              )}>
                <div className="flex items-center gap-2 mb-2">
                  {verificationResult.is_valid ? (
                    <>
                      <CheckCircle className="w-5 h-5 text-sardis-400" />
                      <span className="font-semibold text-sardis-400">Proof Valid</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-5 h-5 text-red-500" />
                      <span className="font-semibold text-red-500">Proof Invalid</span>
                    </>
                  )}
                </div>
                <p className="text-xs text-gray-400">
                  Entry successfully verified against Merkle root
                </p>
              </div>

              <div>
                <p className="text-xs text-gray-500 mb-2">Entry Hash</p>
                <code className="block text-xs text-white font-mono bg-dark-300 px-3 py-2 rounded break-all">
                  {verificationResult.entry_hash}
                </code>
              </div>

              <div>
                <p className="text-xs text-gray-500 mb-2">Merkle Root</p>
                <code className="block text-xs text-sardis-400 font-mono bg-dark-300 px-3 py-2 rounded break-all">
                  {verificationResult.merkle_root}
                </code>
              </div>

              <div>
                <p className="text-xs text-gray-500 mb-2">Proof Path ({verificationResult.proof.length} hashes)</p>
                <div className="space-y-1">
                  {verificationResult.proof.map((hash, index) => (
                    <code
                      key={index}
                      className="block text-xs text-gray-400 font-mono bg-dark-300 px-3 py-2 rounded"
                    >
                      {index + 1}. {hash}
                    </code>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <Search className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-sm text-gray-400">
                  Select an entry to verify its Merkle proof
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
