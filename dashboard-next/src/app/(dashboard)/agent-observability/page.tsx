"use client";
/**
 * Agent Observability Dashboard - Per-agent financial behavior monitoring
 *
 * Shows transaction history, spending patterns, policy enforcement,
 * trust scores, and budget utilization for individual agents.
 */

import { useState, useMemo } from 'react';
import {
  Activity,
  TrendingUp,
  Shield,
  ShieldCheck,
  ShieldAlert,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Eye,
} from 'lucide-react';
import { useAgents, useTransactions, useAgentTransactions, usePolicyDecisions } from '@/hooks/useApi';

// ── Helpers ─────────────────────────────────────────────────────────────

function formatTime(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; text: string; label: string }> = {
    completed: { bg: 'rgba(34,197,94,0.15)', text: '#22C55E', label: 'Completed' },
    blocked: { bg: 'rgba(239,68,68,0.15)', text: '#EF4444', label: 'Blocked' },
    pending_approval: { bg: 'rgba(245,158,11,0.15)', text: '#F59E0B', label: 'Pending' },
    passed: { bg: 'rgba(34,197,94,0.15)', text: '#22C55E', label: 'Passed' },
    failed: { bg: 'rgba(239,68,68,0.15)', text: '#EF4444', label: 'Denied' },
    escalated: { bg: 'rgba(245,158,11,0.15)', text: '#F59E0B', label: 'Escalated' },
    allow: { bg: 'rgba(34,197,94,0.15)', text: '#22C55E', label: 'Passed' },
    deny: { bg: 'rgba(239,68,68,0.15)', text: '#EF4444', label: 'Denied' },
  };
  const s = styles[status] || { bg: 'rgba(100,100,100,0.15)', text: '#888', label: status };
  return (
    <span
      className="px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ background: s.bg, color: s.text }}
    >
      {s.label}
    </span>
  );
}

// ── Trust Tier Badge ────────────────────────────────────────────────────

function TrustTierBadge({ tier }: { tier: string }) {
  const config: Record<string, { color: string; bg: string; icon: typeof ShieldCheck }> = {
    NEW: { color: '#94A3B8', bg: 'rgba(148,163,184,0.15)', icon: Shield },
    BASIC: { color: '#60A5FA', bg: 'rgba(96,165,250,0.15)', icon: Shield },
    TRUSTED: { color: '#22C55E', bg: 'rgba(34,197,94,0.15)', icon: ShieldCheck },
    VERIFIED: { color: '#818CF8', bg: 'rgba(129,140,248,0.15)', icon: ShieldCheck },
  };
  const c = config[tier] || config.NEW;
  const Icon = c.icon;
  return (
    <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full" style={{ background: c.bg }}>
      <Icon size={14} color={c.color} />
      <span className="text-xs font-semibold" style={{ color: c.color }}>{tier}</span>
    </div>
  );
}

// ── Simple Bar Chart ────────────────────────────────────────────────────

function SpendChart({ data }: { data: { date: string; amount: number }[] }) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
        No spending data
      </div>
    );
  }
  const max = Math.max(...data.map(d => d.amount), 1);
  return (
    <div className="flex items-end gap-1.5 h-32">
      {data.map((d) => (
        <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
          <div
            className="w-full rounded-sm transition-all"
            style={{
              height: `${(d.amount / max) * 100}%`,
              minHeight: 4,
              background: 'linear-gradient(to top, #4F46E5, #818CF8)',
            }}
            title={`${d.date}: $${d.amount}`}
          />
          <span className="text-[10px]" style={{ color: '#505460' }}>
            {new Date(d.date).getDate()}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Score Ring ───────────────────────────────────────────────────────────

function ScoreRing({ score, label }: { score: number; label: string }) {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 80 ? '#22C55E' : score >= 50 ? '#F59E0B' : '#EF4444';
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="84" height="84" viewBox="0 0 84 84">
        <circle cx="42" cy="42" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
        <circle
          cx="42" cy="42" r={radius} fill="none" stroke={color} strokeWidth="6"
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round" transform="rotate(-90 42 42)"
        />
        <text x="42" y="46" textAnchor="middle" fill="#F5F5F5" fontSize="18" fontWeight="600">{score}</text>
      </svg>
      <span className="text-[11px]" style={{ color: '#808080' }}>{label}</span>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────

export default function AgentObservability() {
  const { data: agents = [], isLoading: agentsLoading } = useAgents();
  const [selectedAgent, setSelectedAgent] = useState<string>('');

  // Auto-select the first agent once loaded
  const effectiveAgent = selectedAgent || (agents.length > 0 ? agents[0].agent_id : '');

  // Fetch transactions for selected agent
  const { data: agentTransactions = [], isLoading: txLoading } = useAgentTransactions(effectiveAgent);

  // Fetch policy decisions for selected agent
  const { data: policyDecisions, isLoading: policiesLoading } = usePolicyDecisions(effectiveAgent, { limit: 20 });

  // Derive policy checks from API data
  const policyChecks = useMemo(() => {
    if (!policyDecisions || !Array.isArray(policyDecisions)) return [];
    return (policyDecisions as Record<string, unknown>[]).map((d, i) => ({
      id: (d.id as string) || `pc_${i}`,
      rule: (d.rule as string) || (d.policy_rule as string) || 'Policy Check',
      result: (d.result as string) || (d.decision as string) || 'passed',
      amount: Number(d.amount || 0),
      reason: (d.reason as string) || undefined,
      timestamp: (d.timestamp as string) || (d.created_at as string) || new Date().toISOString(),
    }));
  }, [policyDecisions]);

  // Build daily spending data from transactions
  const dailySpend = useMemo(() => {
    const txs = agentTransactions as Array<Record<string, unknown>>;
    if (!txs.length) return [];

    const byDate: Record<string, number> = {};
    const now = new Date();
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      byDate[d.toISOString().slice(0, 10)] = 0;
    }

    txs.forEach((tx) => {
      const date = (tx.created_at as string || '').slice(0, 10);
      if (date in byDate) {
        byDate[date] += Number(tx.amount || 0);
      }
    });

    return Object.entries(byDate).map(([date, amount]) => ({ date, amount }));
  }, [agentTransactions]);

  const totalSpent = dailySpend.reduce((s, d) => s + d.amount, 0);
  const passedChecks = policyChecks.filter((p) => p.result === 'passed' || p.result === 'allow').length;
  const failedChecks = policyChecks.filter((p) => p.result === 'failed' || p.result === 'deny').length;

  const isLoading = agentsLoading;
  const noData = !agentsLoading && agents.length === 0;

  // Derive transactions as a typed array
  const transactions = (agentTransactions as Array<Record<string, unknown>>).map((tx, i) => ({
    id: (tx.id as string) || (tx.tx_id as string) || `tx_${i}`,
    amount: Number(tx.amount || 0),
    recipient: (tx.recipient as string) || (tx.merchant_name as string) || (tx.destination as string) || 'Unknown',
    status: (tx.status as string) || 'completed',
    created_at: (tx.created_at as string) || new Date().toISOString(),
    type: (tx.type as string) || 'payment',
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Eye size={24} /> Agent Observability
          </h1>
          <p className="text-sm text-gray-400 mt-1">Per-agent financial behavior monitoring</p>
        </div>

        {/* Agent Selector */}
        {agents.length > 0 && (
          <select
            value={effectiveAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className="rounded-lg px-4 py-2 text-sm"
            style={{
              background: '#0A0B0D',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#E0E0E0',
            }}
          >
            {agents.map((a) => (
              <option key={a.agent_id} value={a.agent_id}>
                {a.name || a.agent_id} {a.status === 'frozen' ? '(frozen)' : ''}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-sardis-500 mx-auto mb-4"></div>
            <p className="text-gray-400 text-sm">Loading agents...</p>
          </div>
        </div>
      )}

      {/* Empty state */}
      {noData && (
        <div className="card p-12 text-center">
          <Eye className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No agents yet</h3>
          <p className="text-gray-400">
            Create an agent to start monitoring its financial behavior.
          </p>
        </div>
      )}

      {!isLoading && !noData && (
        <>
          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Total Spent (7d)', value: `$${totalSpent.toLocaleString()}`, icon: DollarSign, color: '#818CF8' },
              { label: 'Transactions', value: transactions.length.toString(), icon: Activity, color: '#60A5FA' },
              { label: 'Policy Passed', value: passedChecks.toString(), icon: CheckCircle, color: '#22C55E' },
              { label: 'Policy Denied', value: failedChecks.toString(), icon: XCircle, color: '#EF4444' },
            ].map((stat) => (
              <div
                key={stat.label}
                className="rounded-xl p-4"
                style={{ background: '#0A0B0D', border: '1px solid rgba(255,255,255,0.07)' }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <stat.icon size={16} color={stat.color} />
                  <span className="text-xs" style={{ color: '#808080' }}>{stat.label}</span>
                </div>
                <span className="text-xl font-bold text-white">{stat.value}</span>
              </div>
            ))}
          </div>

          {/* Main Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Spending Chart (2 cols) */}
            <div
              className="lg:col-span-2 rounded-xl p-5"
              style={{ background: '#0A0B0D', border: '1px solid rgba(255,255,255,0.07)' }}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-white flex items-center gap-2">
                  <TrendingUp size={16} color="#818CF8" /> Daily Spending (Last 7 Days)
                </h3>
              </div>
              <SpendChart data={dailySpend} />
            </div>

            {/* Trust Score & Budget (1 col) */}
            <div className="space-y-4">
              {/* Trust Score */}
              <div
                className="rounded-xl p-5"
                style={{ background: '#0A0B0D', border: '1px solid rgba(255,255,255,0.07)' }}
              >
                <h3 className="text-sm font-medium text-white flex items-center gap-2 mb-4">
                  <ShieldCheck size={16} color="#22C55E" /> Trust Score
                </h3>
                {transactions.length > 0 ? (
                  <div className="flex items-center gap-4">
                    <ScoreRing
                      score={Math.min(Math.round((passedChecks / Math.max(passedChecks + failedChecks, 1)) * 100), 100)}
                      label="Overall"
                    />
                    <div className="flex-1 space-y-2">
                      <TrustTierBadge tier={failedChecks === 0 && passedChecks > 5 ? 'TRUSTED' : passedChecks > 0 ? 'BASIC' : 'NEW'} />
                      <p className="text-xs" style={{ color: '#808080' }}>
                        {passedChecks} checks passed, {failedChecks} denied
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <p className="text-xs text-gray-500">No trust data yet</p>
                  </div>
                )}
              </div>

              {/* Budget Utilization */}
              <div
                className="rounded-xl p-5"
                style={{ background: '#0A0B0D', border: '1px solid rgba(255,255,255,0.07)' }}
              >
                <h3 className="text-sm font-medium text-white flex items-center gap-2 mb-3">
                  <DollarSign size={16} color="#F59E0B" /> Spending Summary
                </h3>
                {transactions.length > 0 ? (
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span style={{ color: '#808080' }}>{transactions.length} transactions</span>
                      <span style={{ color: '#808080' }}>${totalSpent.toLocaleString()} total</span>
                    </div>
                    <div className="w-full h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
                      <div
                        className="h-full rounded-full transition-all bg-sardis-500"
                        style={{ width: `${Math.min(100, (transactions.filter(t => t.status === 'completed').length / Math.max(transactions.length, 1)) * 100)}%` }}
                      />
                    </div>
                    <p className="text-xs" style={{ color: '#808080' }}>
                      {transactions.filter(t => t.status === 'completed').length} completed
                    </p>
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <p className="text-xs text-gray-500">No transactions yet</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Bottom Grid: Transactions + Policy Checks */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent Transactions */}
            <div
              className="rounded-xl p-5"
              style={{ background: '#0A0B0D', border: '1px solid rgba(255,255,255,0.07)' }}
            >
              <h3 className="text-sm font-medium text-white flex items-center gap-2 mb-4">
                <Activity size={16} color="#60A5FA" /> Recent Transactions
              </h3>
              {txLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-sardis-500"></div>
                </div>
              ) : transactions.length === 0 ? (
                <div className="text-center py-8 text-gray-500 text-sm">
                  No transactions for this agent
                </div>
              ) : (
                <div className="space-y-2">
                  {transactions.slice(0, 6).map((tx) => (
                    <div
                      key={tx.id}
                      className="flex items-center justify-between py-2 px-3 rounded-lg"
                      style={{ background: 'rgba(255,255,255,0.02)' }}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-white truncate">{tx.recipient}</span>
                          <StatusBadge status={tx.status} />
                        </div>
                        <span className="text-xs" style={{ color: '#505460' }}>{formatTime(tx.created_at)}</span>
                      </div>
                      <span className="text-sm font-medium text-white ml-3">
                        ${tx.amount.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Policy Enforcement Log */}
            <div
              className="rounded-xl p-5"
              style={{ background: '#0A0B0D', border: '1px solid rgba(255,255,255,0.07)' }}
            >
              <h3 className="text-sm font-medium text-white flex items-center gap-2 mb-4">
                <Shield size={16} color="#F59E0B" /> Policy Enforcement Log
              </h3>
              {policiesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-sardis-500"></div>
                </div>
              ) : policyChecks.length === 0 ? (
                <div className="text-center py-8 text-gray-500 text-sm">
                  No policy checks recorded
                </div>
              ) : (
                <div className="space-y-2">
                  {policyChecks.map((pc) => (
                    <div
                      key={pc.id}
                      className="py-2 px-3 rounded-lg"
                      style={{ background: 'rgba(255,255,255,0.02)' }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {(pc.result === 'passed' || pc.result === 'allow') ? (
                            <CheckCircle size={14} color="#22C55E" />
                          ) : pc.result === 'escalated' ? (
                            <AlertTriangle size={14} color="#F59E0B" />
                          ) : (
                            <ShieldAlert size={14} color="#EF4444" />
                          )}
                          <span className="text-sm text-white">{pc.rule}</span>
                        </div>
                        <StatusBadge status={pc.result} />
                      </div>
                      {pc.reason && (
                        <p className="text-xs mt-1 ml-5" style={{ color: '#808080' }}>{pc.reason}</p>
                      )}
                      <p className="text-xs mt-0.5 ml-5" style={{ color: '#505460' }}>
                        ${pc.amount.toFixed(2)} &middot; {formatTime(pc.timestamp)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
