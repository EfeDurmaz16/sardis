/**
 * Agent Observability Dashboard - Per-agent financial behavior monitoring
 *
 * Shows transaction history, spending patterns, policy enforcement,
 * trust scores, and budget utilization for individual agents.
 */

import { useState, useEffect } from 'react';
import {
  CheckCircle,
  CurrencyDollar,
  Eye,
  Pulse,
  Shield,
  ShieldCheck,
  ShieldWarning,
  TrendUp,
  Warning,
  XCircle,
} from '@phosphor-icons/react';
const API_BASE = import.meta.env.VITE_API_URL || '';

// ── Demo data ───────────────────────────────────────────────────────────

const DEMO_AGENTS = [
  { agent_id: 'agent_001', name: 'Shopping Agent', status: 'active' },
  { agent_id: 'agent_002', name: 'Travel Booker', status: 'active' },
  { agent_id: 'agent_003', name: 'SaaS Manager', status: 'active' },
  { agent_id: 'agent_004', name: 'Cloud Ops', status: 'frozen' },
  { agent_id: 'agent_005', name: 'Marketing AI', status: 'active' },
];

const DEMO_TRANSACTIONS = [
  { id: 'tx_1', amount: 45.0, recipient: 'OpenAI API', status: 'completed', created_at: '2026-03-15T10:30:00Z', type: 'api_call' },
  { id: 'tx_2', amount: 127.5, recipient: 'AWS', status: 'blocked', created_at: '2026-03-15T09:15:00Z', type: 'cloud' },
  { id: 'tx_3', amount: 19.0, recipient: 'Vercel', status: 'completed', created_at: '2026-03-14T16:45:00Z', type: 'saas' },
  { id: 'tx_4', amount: 350.0, recipient: 'Google Ads', status: 'pending_approval', created_at: '2026-03-14T14:20:00Z', type: 'marketing' },
  { id: 'tx_5', amount: 8.5, recipient: 'Anthropic API', status: 'completed', created_at: '2026-03-14T11:00:00Z', type: 'api_call' },
  { id: 'tx_6', amount: 75.0, recipient: 'Stripe', status: 'completed', created_at: '2026-03-13T18:30:00Z', type: 'saas' },
  { id: 'tx_7', amount: 200.0, recipient: 'Heroku', status: 'completed', created_at: '2026-03-13T09:00:00Z', type: 'cloud' },
  { id: 'tx_8', amount: 500.0, recipient: 'Booking.com', status: 'blocked', created_at: '2026-03-12T15:30:00Z', type: 'travel' },
];

const DEMO_POLICY_CHECKS = [
  { id: 'pc_1', rule: 'Max $100/transaction', result: 'passed', amount: 45.0, timestamp: '2026-03-15T10:30:00Z' },
  { id: 'pc_2', rule: 'Max $100/transaction', result: 'failed', amount: 127.5, reason: 'Amount $127.50 exceeds limit of $100.00', timestamp: '2026-03-15T09:15:00Z' },
  { id: 'pc_3', rule: 'Allowed vendors only', result: 'passed', amount: 19.0, timestamp: '2026-03-14T16:45:00Z' },
  { id: 'pc_4', rule: 'Require approval above $200', result: 'escalated', amount: 350.0, reason: 'Amount above $200 threshold', timestamp: '2026-03-14T14:20:00Z' },
  { id: 'pc_5', rule: 'Daily limit $500', result: 'passed', amount: 8.5, timestamp: '2026-03-14T11:00:00Z' },
  { id: 'pc_6', rule: 'Block travel bookings', result: 'failed', amount: 500.0, reason: 'Category "travel" is blocked', timestamp: '2026-03-12T15:30:00Z' },
];

const DEMO_DAILY_SPEND = [
  { date: '2026-03-09', amount: 120 },
  { date: '2026-03-10', amount: 280 },
  { date: '2026-03-11', amount: 95 },
  { date: '2026-03-12', amount: 445 },
  { date: '2026-03-13', amount: 275 },
  { date: '2026-03-14', amount: 377 },
  { date: '2026-03-15', amount: 172 },
];

const DEMO_TRUST = {
  tier: 'TRUSTED',
  score: 82,
  factors: {
    transaction_history: 90,
    volume_consistency: 75,
    account_age: 85,
    kyc_verified: true,
    reliability: 78,
  },
  daily_limit: 2500,
};

const DEMO_BUDGET = {
  spent: 1764,
  budget: 5000,
  utilization: 35.3,
  remaining: 3236,
  period: 'March 2026',
};

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
  const [agents, setAgents] = useState(DEMO_AGENTS);
  const [selectedAgent, setSelectedAgent] = useState(DEMO_AGENTS[0].agent_id);
  const [transactions, setTransactions] = useState(DEMO_TRANSACTIONS);
  const [policyChecks] = useState(DEMO_POLICY_CHECKS);
  const [dailySpend] = useState(DEMO_DAILY_SPEND);
  const [trust] = useState(DEMO_TRUST);
  const [budget] = useState(DEMO_BUDGET);

  // Attempt to fetch real agents from API
  useEffect(() => {
    if (!API_BASE) return;
    const token = sessionStorage.getItem('sardis_token');
    if (!token) return;

    fetch(`${API_BASE}/api/v2/agents`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.agents?.length) {
          setAgents(data.agents);
          setSelectedAgent(data.agents[0].agent_id);
        }
      })
      .catch(() => {});
  }, []);

  // Attempt to fetch real transactions for selected agent
  useEffect(() => {
    if (!API_BASE || !selectedAgent) return;
    const token = sessionStorage.getItem('sardis_token');
    if (!token) return;

    fetch(`${API_BASE}/api/v2/transactions?agent_id=${selectedAgent}&limit=20`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.transactions?.length) {
          setTransactions(data.transactions);
        }
      })
      .catch(() => {});
  }, [selectedAgent]);

  const totalSpent = dailySpend.reduce((s, d) => s + d.amount, 0);
  const passedChecks = policyChecks.filter((p) => p.result === 'passed').length;
  const failedChecks = policyChecks.filter((p) => p.result === 'failed').length;

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
        <select
          value={selectedAgent}
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
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Spent (7d)', value: `$${totalSpent.toLocaleString()}`, icon: CurrencyDollar, color: '#818CF8' },
          { label: 'Transactions', value: transactions.length.toString(), icon: Pulse, color: '#60A5FA' },
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
              <TrendUp size={16} color="#818CF8" /> Daily Spending (Last 7 Days)
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
            <div className="flex items-center gap-4">
              <ScoreRing score={trust.score} label="Overall" />
              <div className="flex-1 space-y-2">
                <TrustTierBadge tier={trust.tier} />
                <p className="text-xs" style={{ color: '#808080' }}>
                  Daily limit: <span className="text-white">${trust.daily_limit.toLocaleString()}</span>
                </p>
                {trust.factors.kyc_verified && (
                  <p className="text-xs flex items-center gap-1" style={{ color: '#22C55E' }}>
                    <CheckCircle size={12} /> KYC Verified
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Budget Utilization */}
          <div
            className="rounded-xl p-5"
            style={{ background: '#0A0B0D', border: '1px solid rgba(255,255,255,0.07)' }}
          >
            <h3 className="text-sm font-medium text-white flex items-center gap-2 mb-3">
              <CurrencyDollar size={16} color="#F59E0B" /> Budget ({budget.period})
            </h3>
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span style={{ color: '#808080' }}>${budget.spent.toLocaleString()} spent</span>
                <span style={{ color: '#808080' }}>${budget.budget.toLocaleString()} budget</span>
              </div>
              <div className="w-full h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${Math.min(budget.utilization, 100)}%`,
                    background: budget.utilization > 80 ? '#EF4444' : budget.utilization > 60 ? '#F59E0B' : '#22C55E',
                  }}
                />
              </div>
              <p className="text-xs" style={{ color: '#808080' }}>
                {budget.utilization.toFixed(1)}% used &middot; ${budget.remaining.toLocaleString()} remaining
              </p>
            </div>
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
            <Pulse size={16} color="#60A5FA" /> Recent Transactions
          </h3>
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
        </div>

        {/* Policy Enforcement Log */}
        <div
          className="rounded-xl p-5"
          style={{ background: '#0A0B0D', border: '1px solid rgba(255,255,255,0.07)' }}
        >
          <h3 className="text-sm font-medium text-white flex items-center gap-2 mb-4">
            <Shield size={16} color="#F59E0B" /> Policy Enforcement Log
          </h3>
          <div className="space-y-2">
            {policyChecks.map((pc) => (
              <div
                key={pc.id}
                className="py-2 px-3 rounded-lg"
                style={{ background: 'rgba(255,255,255,0.02)' }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {pc.result === 'passed' ? (
                      <CheckCircle size={14} color="#22C55E" />
                    ) : pc.result === 'escalated' ? (
                      <Warning size={14} color="#F59E0B" />
                    ) : (
                      <ShieldWarning size={14} color="#EF4444" />
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
        </div>
      </div>
    </div>
  );
}
