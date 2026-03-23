/**
 * Spending Mandate Management — Create, view, and manage spending mandates
 *
 * The core UI for Sardis's differentiating feature: machine-readable
 * spending permissions for AI agents.
 */

import { useState } from 'react';
import {
  Shield,
  Plus,
  Loader2,
  CheckCircle,
  XCircle,
  PauseCircle,
  Clock,
  DollarSign,
  ChevronDown,
  ChevronRight,
  Ban,
  Play,
  Pause,
} from 'lucide-react';
import clsx from 'clsx';
import { useMandates, useMandateTransitions, useCreateMandate, useMandateAction } from '../hooks/useApi';

// ── Types ─────────────────────────────────────────────────────────────

interface Mandate {
  id: string;
  org_id: string;
  agent_id: string | null;
  purpose_scope: string | null;
  merchant_scope: Record<string, unknown> | null;
  amount_per_tx: string | null;
  amount_daily: string | null;
  amount_monthly: string | null;
  amount_total: string | null;
  currency: string;
  spent_total: string;
  allowed_rails: string[];
  approval_threshold: string | null;
  approval_mode: string;
  status: string;
  version: number;
  expires_at: string | null;
  created_at: string;
}

// ── Status Badge ──────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; icon: typeof CheckCircle }> = {
    active: { bg: 'bg-green-500/10', text: 'text-green-500', icon: CheckCircle },
    draft: { bg: 'bg-gray-500/10', text: 'text-gray-400', icon: Clock },
    suspended: { bg: 'bg-yellow-500/10', text: 'text-yellow-500', icon: PauseCircle },
    revoked: { bg: 'bg-red-500/10', text: 'text-red-500', icon: XCircle },
    expired: { bg: 'bg-gray-500/10', text: 'text-gray-500', icon: Clock },
    consumed: { bg: 'bg-blue-500/10', text: 'text-blue-400', icon: DollarSign },
  };
  const c = config[status] || config.draft;
  const Icon = c.icon;
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium capitalize', c.bg, c.text)}>
      <Icon size={12} />
      {status}
    </span>
  );
}

// ── Budget Bar ────────────────────────────────────────────────────────

function BudgetBar({ spent, total }: { spent: string; total: string | null }) {
  if (!total) return <span className="text-xs text-gray-500">No limit</span>;
  const s = parseFloat(spent);
  const t = parseFloat(total);
  const pct = t > 0 ? Math.min(100, (s / t) * 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-400">${s.toFixed(2)} spent</span>
        <span className="text-gray-500">${t.toFixed(2)} total</span>
      </div>
      <div className="w-full h-1.5 rounded-full bg-dark-100">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${pct}%`,
            background: pct > 80 ? '#EF4444' : pct > 60 ? '#F59E0B' : '#22C55E',
          }}
        />
      </div>
    </div>
  );
}

// ── Create Mandate Form ───────────────────────────────────────────────

function CreateMandateForm({ onCreated }: { onCreated: () => void }) {
  const createMandate = useCreateMandate();
  const [purpose, setPurpose] = useState('');
  const [perTx, setPerTx] = useState('100');
  const [daily, setDaily] = useState('');
  const [monthly, setMonthly] = useState('');
  const [total, setTotal] = useState('');
  const [merchants, setMerchants] = useState('');
  const [approvalThreshold, setApprovalThreshold] = useState('');
  const [approvalMode, setApprovalMode] = useState('auto');
  const [rails, setRails] = useState(['card', 'usdc', 'bank']);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const body: Record<string, unknown> = {
      purpose_scope: purpose || undefined,
      amount_per_tx: perTx ? parseFloat(perTx) : undefined,
      amount_daily: daily ? parseFloat(daily) : undefined,
      amount_monthly: monthly ? parseFloat(monthly) : undefined,
      amount_total: total ? parseFloat(total) : undefined,
      allowed_rails: rails,
      approval_mode: approvalMode,
      approval_threshold: approvalThreshold ? parseFloat(approvalThreshold) : undefined,
    };

    if (merchants.trim()) {
      body.merchant_scope = {
        allowed: merchants.split(',').map(m => m.trim()).filter(Boolean),
      };
    }

    try {
      await createMandate.mutateAsync(body as Parameters<typeof createMandate.mutateAsync>[0]);
      onCreated();
      setPurpose(''); setPerTx('100'); setDaily(''); setMonthly(''); setTotal('');
      setMerchants(''); setApprovalThreshold(''); setApprovalMode('auto');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create mandate');
    }
  };

  const isLoading = createMandate.isPending;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">{error}</div>}

      <div>
        <label className="block text-xs font-medium text-gray-400 mb-1">Purpose</label>
        <input value={purpose} onChange={e => setPurpose(e.target.value)} placeholder="e.g., Cloud infrastructure and API calls"
          className="w-full px-3 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white text-sm focus:border-sardis-500/50" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">Per Transaction ($)</label>
          <input type="number" value={perTx} onChange={e => setPerTx(e.target.value)} placeholder="100"
            className="w-full px-3 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white text-sm focus:border-sardis-500/50" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">Daily ($)</label>
          <input type="number" value={daily} onChange={e => setDaily(e.target.value)} placeholder="Optional"
            className="w-full px-3 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white text-sm focus:border-sardis-500/50" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">Monthly ($)</label>
          <input type="number" value={monthly} onChange={e => setMonthly(e.target.value)} placeholder="Optional"
            className="w-full px-3 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white text-sm focus:border-sardis-500/50" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">Total Budget ($)</label>
          <input type="number" value={total} onChange={e => setTotal(e.target.value)} placeholder="Optional"
            className="w-full px-3 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white text-sm focus:border-sardis-500/50" />
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-400 mb-1">Allowed Merchants (comma-separated, empty = all)</label>
        <input value={merchants} onChange={e => setMerchants(e.target.value)} placeholder="openai.com, anthropic.com, aws.amazon.com"
          className="w-full px-3 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white text-sm focus:border-sardis-500/50" />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">Approval Mode</label>
          <select value={approvalMode} onChange={e => setApprovalMode(e.target.value)}
            className="w-full px-3 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white text-sm focus:border-sardis-500/50">
            <option value="auto">Auto-approve all</option>
            <option value="threshold">Approve below threshold</option>
            <option value="always_human">Always require human</option>
          </select>
        </div>
        {approvalMode === 'threshold' && (
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1">Approval Threshold ($)</label>
            <input type="number" value={approvalThreshold} onChange={e => setApprovalThreshold(e.target.value)} placeholder="500"
              className="w-full px-3 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white text-sm focus:border-sardis-500/50" />
          </div>
        )}
      </div>

      <button type="submit" disabled={isLoading}
        className="w-full py-2.5 bg-sardis-500 text-dark-400 font-bold rounded-lg hover:bg-sardis-400 transition-colors disabled:opacity-50 text-sm">
        {isLoading ? 'Creating...' : 'Create Mandate'}
      </button>
    </form>
  );
}

// ── Transition History (lazy-loaded per mandate) ─────────────────────

function TransitionHistory({ mandateId }: { mandateId: string }) {
  const { data: transitions, isLoading } = useMandateTransitions(mandateId);

  if (isLoading) return <Loader2 size={14} className="text-gray-500 animate-spin" />;

  if (!transitions || transitions.length === 0) {
    return <p className="text-xs text-gray-500">No transitions yet</p>;
  }

  return (
    <div className="space-y-2">
      {transitions.map(t => (
        <div key={t.id} className="text-xs">
          <span className="text-gray-500">{new Date(t.created_at).toLocaleString()}</span>
          <span className="text-gray-400 mx-1">&middot;</span>
          <span className="text-white">{t.from_status} → {t.to_status}</span>
          {t.reason && <span className="text-gray-500 ml-1">({t.reason})</span>}
        </div>
      ))}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────

export default function MandatesPage() {
  const { data: mandates = [], isLoading: loading, isError } = useMandates();
  const mandateAction = useMandateAction();
  const [showCreate, setShowCreate] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleAction = async (mandateId: string, action: string, reason?: string) => {
    await mandateAction.mutateAsync({ mandateId, action, reason });
  };

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const actionLoading = mandateAction.isPending ? mandateAction.variables?.mandateId ?? null : null;

  const activeMandates = mandates.filter(m => m.status === 'active').length;
  const totalBudget = mandates.reduce((s, m) => s + (m.amount_total ? parseFloat(m.amount_total) : 0), 0);
  const totalSpent = mandates.reduce((s, m) => s + parseFloat(m.spent_total || '0'), 0);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display flex items-center gap-3">
            <Shield className="w-8 h-8 text-sardis-400" />
            Spending Mandates
          </h1>
          <p className="text-gray-400 mt-1">Machine-readable payment permissions for your AI agents</p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors text-sm"
        >
          <Plus size={16} />
          New Mandate
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-4">
          <p className="text-sm text-gray-400">Active Mandates</p>
          <p className="text-2xl font-bold text-green-500">{activeMandates}</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Total Budget</p>
          <p className="text-2xl font-bold text-white mono-numbers">${totalBudget.toFixed(2)}</p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Total Spent</p>
          <p className="text-2xl font-bold text-sardis-400 mono-numbers">${totalSpent.toFixed(2)}</p>
        </div>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Plus size={18} className="text-sardis-400" /> Create Spending Mandate
          </h2>
          <CreateMandateForm
            onCreated={() => { setShowCreate(false); }}
          />
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="card p-12 text-center">
          <Loader2 className="w-8 h-8 text-sardis-500 mx-auto mb-4 animate-spin" />
          <p className="text-gray-400">Loading mandates...</p>
        </div>
      )}

      {/* Error */}
      {isError && !loading && (
        <div className="card p-6 border-red-500/30">
          <p className="text-red-400 text-sm">Failed to load mandates</p>
        </div>
      )}

      {/* Mandate List */}
      {!loading && !isError && mandates.length === 0 && (
        <div className="card p-12 text-center">
          <Shield className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 mb-2">No spending mandates yet</p>
          <p className="text-sm text-gray-500">Create your first mandate to control how your AI agents spend money.</p>
        </div>
      )}

      {!loading && mandates.length > 0 && (
        <div className="space-y-3">
          {mandates.map((m) => (
            <div key={m.id} className="card overflow-hidden">
              {/* Mandate Row */}
              <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-dark-200/30 transition-colors"
                onClick={() => toggleExpand(m.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpand(m.id); } }}
                aria-expanded={expandedId === m.id}
              >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  {expandedId === m.id ? <ChevronDown size={16} className="text-gray-500 shrink-0" /> : <ChevronRight size={16} className="text-gray-500 shrink-0" />}
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono text-white">{m.id}</span>
                      <StatusBadge status={m.status} />
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5 truncate">
                      {m.purpose_scope || 'No purpose defined'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-6 shrink-0">
                  <div className="text-right w-32">
                    <BudgetBar spent={m.spent_total} total={m.amount_total} />
                  </div>

                  <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                    {m.status === 'active' && (
                      <>
                        <button onClick={() => handleAction(m.id, 'suspend')} disabled={actionLoading === m.id}
                          className="p-1.5 text-yellow-500 hover:bg-yellow-500/10 rounded transition-colors" title="Suspend">
                          <Pause size={14} />
                        </button>
                        <button onClick={() => handleAction(m.id, 'revoke', 'Revoked from dashboard')} disabled={actionLoading === m.id}
                          className="p-1.5 text-red-500 hover:bg-red-500/10 rounded transition-colors" title="Revoke">
                          <Ban size={14} />
                        </button>
                      </>
                    )}
                    {m.status === 'suspended' && (
                      <>
                        <button onClick={() => handleAction(m.id, 'resume')} disabled={actionLoading === m.id}
                          className="p-1.5 text-green-500 hover:bg-green-500/10 rounded transition-colors" title="Resume">
                          <Play size={14} />
                        </button>
                        <button onClick={() => handleAction(m.id, 'revoke', 'Revoked from dashboard')} disabled={actionLoading === m.id}
                          className="p-1.5 text-red-500 hover:bg-red-500/10 rounded transition-colors" title="Revoke">
                          <Ban size={14} />
                        </button>
                      </>
                    )}
                    {m.status === 'draft' && (
                      <button onClick={() => handleAction(m.id, 'activate')} disabled={actionLoading === m.id}
                        className="p-1.5 text-green-500 hover:bg-green-500/10 rounded transition-colors" title="Activate">
                        <Play size={14} />
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Expanded Detail */}
              {expandedId === m.id && (
                <div className="border-t border-dark-100 p-4 bg-dark-300/30">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Limits */}
                    <div>
                      <h4 className="text-xs font-medium text-gray-400 uppercase mb-2">Amount Limits</h4>
                      <div className="space-y-1.5 text-sm">
                        {m.amount_per_tx && <div className="flex justify-between"><span className="text-gray-500">Per transaction</span><span className="text-white">${m.amount_per_tx}</span></div>}
                        {m.amount_daily && <div className="flex justify-between"><span className="text-gray-500">Daily</span><span className="text-white">${m.amount_daily}</span></div>}
                        {m.amount_monthly && <div className="flex justify-between"><span className="text-gray-500">Monthly</span><span className="text-white">${m.amount_monthly}</span></div>}
                        {m.amount_total && <div className="flex justify-between"><span className="text-gray-500">Total budget</span><span className="text-white">${m.amount_total}</span></div>}
                        <div className="flex justify-between"><span className="text-gray-500">Spent</span><span className="text-sardis-400">${m.spent_total}</span></div>
                      </div>
                    </div>

                    {/* Scope */}
                    <div>
                      <h4 className="text-xs font-medium text-gray-400 uppercase mb-2">Scope & Controls</h4>
                      <div className="space-y-1.5 text-sm">
                        <div className="flex justify-between"><span className="text-gray-500">Rails</span><span className="text-white">{m.allowed_rails.join(', ')}</span></div>
                        <div className="flex justify-between"><span className="text-gray-500">Approval</span><span className="text-white capitalize">{m.approval_mode}</span></div>
                        {m.approval_threshold && <div className="flex justify-between"><span className="text-gray-500">Threshold</span><span className="text-white">${m.approval_threshold}</span></div>}
                        {m.expires_at && <div className="flex justify-between"><span className="text-gray-500">Expires</span><span className="text-white">{new Date(m.expires_at).toLocaleDateString()}</span></div>}
                        {m.merchant_scope && (m.merchant_scope as any).allowed && (
                          <div>
                            <span className="text-gray-500">Allowed merchants:</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {((m.merchant_scope as any).allowed as string[]).map((merchant: string) => (
                                <span key={merchant} className="text-xs px-1.5 py-0.5 bg-dark-100 rounded text-gray-300">{merchant}</span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* History */}
                    <div>
                      <h4 className="text-xs font-medium text-gray-400 uppercase mb-2">State History</h4>
                      <TransitionHistory mandateId={m.id} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
