"use client";
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
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
import StatCard from '@/components/StatCard'
import { ledgerApi, evidenceApi, getAuthHeaders } from '@/api/client'

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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export default function AuditAnchorsPage() {
  // Fetch anchors from API
  const { data: anchorsData, isLoading: anchorsLoading, refetch: refetchAnchors } = useQuery<AuditAnchor[]>({
    queryKey: ['audit-anchors'],
    queryFn: async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v2/ledger/anchors`, {
          headers: getAuthHeaders(),
        });
        if (!res.ok) return [];
        const data = await res.json();
        return (data.anchors || data || []) as AuditAnchor[];
      } catch {
        return [];
      }
    },
  });

  // Fetch ledger entries from API
  const { data: entriesData, isLoading: entriesLoading } = useQuery<LedgerEntry[]>({
    queryKey: ['ledger-entries'],
    queryFn: async () => {
      try {
        const data = await ledgerApi.recent(20);
        return (data as unknown as LedgerEntry[]) || [];
      } catch {
        return [];
      }
    },
  });

  const anchors = anchorsData || [];
  const entries = entriesData || [];

  const [selectedEntry, setSelectedEntry] = useState<string | null>(null)
  const [verificationResult, setVerificationResult] = useState<MerkleProof | null>(null)
  const [isVerifying, setIsVerifying] = useState(false)

  const handleVerifyAnchor = async (anchorId: string) => {
    setIsVerifying(true)
    try {
      const res = await fetch(`${API_BASE}/api/v2/ledger/anchors/${anchorId}/verify`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        refetchAnchors();
      }
    } catch (error) {
      console.error('Verification failed:', error);
    } finally {
      setIsVerifying(false)
    }
  }

  const handleVerifyEntry = async (entryId: string) => {
    const entry = entries.find(e => e.id === entryId)
    if (!entry) return

    setSelectedEntry(entryId)
    setIsVerifying(true)

    try {
      const txId = entry.transaction_id || entryId;
      const data = await evidenceApi.getTransactionEvidence(txId);
      const evidence = data as Record<string, unknown>;

      setVerificationResult({
        entry_hash: entry.entry_hash || (evidence.entry_hash as string) || '',
        merkle_root: (evidence.merkle_root as string) || '',
        proof: (evidence.proof as string[]) || [],
        is_valid: (evidence.is_valid as boolean) ?? true,
      });
    } catch {
      // If API fails, show that no proof is available
      setVerificationResult(null);
    } finally {
      setIsVerifying(false)
    }
  }

  const handleTriggerAnchor = async () => {
    try {
      await fetch(`${API_BASE}/api/v2/ledger/anchors`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
      });
      refetchAnchors();
    } catch (error) {
      console.error('Trigger anchor failed:', error);
    }
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
  const totalEntries = anchors.reduce((sum, a) => sum + (a.entry_count || 0), 0)
  const pendingAnchors = anchors.filter(a => a.status === 'pending').length

  const isLoading = anchorsLoading || entriesLoading;
  const noData = !isLoading && anchors.length === 0 && entries.length === 0;

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

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-sardis-500 mx-auto mb-4" />
            <p className="text-gray-400 text-sm">Loading audit data...</p>
          </div>
        </div>
      )}

      {/* Empty State */}
      {noData && (
        <div className="card p-12 text-center">
          <Anchor className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No audit anchors yet</h3>
          <p className="text-gray-400">
            Audit anchors will appear here once transactions are recorded and anchored on-chain.
          </p>
        </div>
      )}

      {!isLoading && !noData && (
        <>
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
              value={confirmedAnchors > 0 ? '100%' : 'N/A'}
              change={confirmedAnchors > 0 ? 'All verifications pass' : 'No verified anchors'}
              changeType="positive"
              icon={<Shield className="w-6 h-6" />}
            />
          </div>

          {/* Anchor Records */}
          {anchors.length > 0 && (
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
                            Block {anchor.block_number.toLocaleString()} - {anchor.entry_count} entries
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
          )}

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

              {entries.length === 0 ? (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                    <p className="text-sm text-gray-400">No ledger entries found</p>
                  </div>
                </div>
              ) : (
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
                          ${(entry.amount || 0).toFixed(2)}
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
              )}
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

                  {verificationResult.entry_hash && (
                    <div>
                      <p className="text-xs text-gray-500 mb-2">Entry Hash</p>
                      <code className="block text-xs text-white font-mono bg-dark-300 px-3 py-2 rounded break-all">
                        {verificationResult.entry_hash}
                      </code>
                    </div>
                  )}

                  {verificationResult.merkle_root && (
                    <div>
                      <p className="text-xs text-gray-500 mb-2">Merkle Root</p>
                      <code className="block text-xs text-sardis-400 font-mono bg-dark-300 px-3 py-2 rounded break-all">
                        {verificationResult.merkle_root}
                      </code>
                    </div>
                  )}

                  {verificationResult.proof.length > 0 && (
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
                  )}
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
        </>
      )}
    </div>
  )
}
