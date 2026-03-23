/**
 * Billing Page - Plan management and usage meters
 *
 * Features:
 * - Current plan card with status badge
 * - Usage meters (API calls, transaction volume, agents)
 * - Plan comparison table with upgrade actions
 * - Stripe billing portal integration
 */

import { useState, useEffect } from 'react';
import {
  ArrowSquareOut,
  Buildings,
  CheckCircle,
  CreditCard,
  Lightning,
  TrendUp,
  Users,
  WarningCircle,
} from '@phosphor-icons/react';
import { useAuth } from '../auth/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

// Types
interface BillingPlan {
  plan: string;
  price_monthly_cents: number;
  api_calls_per_month: number | null;
  agents: number | null;
  tx_fee_bps: number;
  monthly_tx_volume_cents: number | null;
}

interface BillingUsage {
  api_calls_used: number;
  api_calls_limit: number | null;
  tx_volume_cents: number;
  tx_volume_limit_cents: number | null;
  agents_used: number;
  agents_limit: number | null;
}

interface BillingAccount {
  plan: string;
  status: string;
  usage: BillingUsage;
  stripe_customer_id: string | null;
  current_period_end: string | null;
}

const PLAN_ORDER = ['free', 'starter', 'growth', 'enterprise'];

const PLAN_LABELS: Record<string, string> = {
  free: 'Free',
  starter: 'Starter',
  growth: 'Growth',
  enterprise: 'Enterprise',
};

const PLAN_SUPPORT: Record<string, string> = {
  free: 'Community',
  starter: 'Email',
  growth: 'Priority',
  enterprise: 'Dedicated SLA',
};

const PLAN_BADGE_COLORS: Record<string, string> = {
  free: 'bg-gray-500/20 text-gray-300 border border-gray-500/30',
  starter: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
  growth: 'bg-sardis-500/20 text-sardis-300 border border-sardis-500/30',
  enterprise: 'bg-purple-500/20 text-purple-300 border border-purple-500/30',
};

const STATUS_BADGE_COLORS: Record<string, string> = {
  active: 'bg-green-500/20 text-green-300 border border-green-500/30',
  past_due: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
  canceled: 'bg-red-500/20 text-red-300 border border-red-500/30',
};

function formatCents(cents: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

function formatNumber(n: number | null): string {
  if (n === null) return 'Unlimited';
  return new Intl.NumberFormat('en-US').format(n);
}

function getBarColor(pct: number): string {
  if (pct > 90) return 'bg-red-500';
  if (pct > 70) return 'bg-amber-500';
  return 'bg-sardis-500';
}

interface UsageMeterProps {
  label: string;
  used: number;
  limit: number | null;
  format?: (v: number) => string;
  icon: React.ReactNode;
}

function UsageMeter({ label, used, limit, format, icon }: UsageMeterProps) {
  const fmt = format ?? ((v: number) => formatNumber(v));
  const pct = limit !== null && limit > 0 ? Math.min((used / limit) * 100, 100) : 0;
  const isUnlimited = limit === null;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="text-sardis-400">{icon}</div>
          <span className="text-sm font-medium text-gray-300">{label}</span>
        </div>
        <span className="text-xs text-gray-500">
          {fmt(used)} / {isUnlimited ? 'Unlimited' : fmt(limit!)}
        </span>
      </div>

      {isUnlimited ? (
        <div className="w-full bg-dark-100 rounded-full h-2">
          <div className="h-2 rounded-full bg-sardis-500" style={{ width: '100%', opacity: 0.3 }} />
        </div>
      ) : (
        <div className="w-full bg-dark-100 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${getBarColor(pct)}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}

      <div className="flex justify-between mt-2">
        <span className="text-xs text-gray-500">
          {isUnlimited ? 'Unlimited' : `${pct.toFixed(1)}% used`}
        </span>
        {!isUnlimited && pct > 90 && (
          <span className="text-xs text-red-400 font-medium">Near limit</span>
        )}
        {!isUnlimited && pct > 70 && pct <= 90 && (
          <span className="text-xs text-amber-400 font-medium">Getting close</span>
        )}
      </div>
    </div>
  );
}

interface PlanColumnProps {
  plan: BillingPlan;
  isCurrent: boolean;
  isPopular: boolean;
  onUpgrade: (plan: string) => void;
  upgrading: string | null;
}

function PlanColumn({ plan, isCurrent, isPopular, onUpgrade, upgrading }: PlanColumnProps) {
  const isEnterprise = plan.plan === 'enterprise';
  const priceLabel =
    plan.price_monthly_cents === 0
      ? 'Free'
      : `${formatCents(plan.price_monthly_cents)}/mo`;

  return (
    <div
      className={`card p-5 flex flex-col relative ${
        isCurrent
          ? 'border-sardis-500/50 bg-sardis-500/5'
          : isPopular
          ? 'border-sardis-500/30'
          : ''
      }`}
    >
      {isPopular && !isCurrent && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="bg-sardis-500 text-dark-400 text-xs font-bold px-3 py-1 rounded-full">
            Most Popular
          </span>
        </div>
      )}

      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1">
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded-full ${PLAN_BADGE_COLORS[plan.plan] || ''}`}
          >
            {PLAN_LABELS[plan.plan] ?? plan.plan}
          </span>
          {isCurrent && (
            <span className="text-xs text-sardis-400 font-medium">Current</span>
          )}
        </div>
        <p className="text-2xl font-bold text-white mt-2">{priceLabel}</p>
      </div>

      <div className="space-y-2 text-sm text-gray-400 flex-1">
        <div className="flex justify-between">
          <span>API calls/mo</span>
          <span className="text-white font-medium">
            {plan.api_calls_per_month === null ? 'Unlimited' : formatNumber(plan.api_calls_per_month)}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Agents</span>
          <span className="text-white font-medium">
            {plan.agents === null ? 'Unlimited' : plan.agents}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Tx fee</span>
          <span className="text-white font-medium">{plan.tx_fee_bps} bps</span>
        </div>
        <div className="flex justify-between">
          <span>Monthly volume</span>
          <span className="text-white font-medium">
            {plan.monthly_tx_volume_cents === null
              ? 'Unlimited'
              : formatCents(plan.monthly_tx_volume_cents)}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Support</span>
          <span className="text-white font-medium">{PLAN_SUPPORT[plan.plan] ?? 'Standard'}</span>
        </div>
      </div>

      <div className="mt-5">
        {isCurrent ? (
          <div className="flex items-center justify-center gap-2 py-2 text-sm text-sardis-400 font-medium">
            <CheckCircle className="w-4 h-4" />
            Current Plan
          </div>
        ) : isEnterprise ? (
          <a
            href="mailto:sales@sardis.sh"
            className="w-full flex items-center justify-center gap-2 py-2 text-sm font-medium bg-dark-200 text-gray-300 hover:bg-dark-100 hover:text-white transition-colors rounded"
          >
            <Buildings className="w-4 h-4" />
            Contact Sales
          </a>
        ) : (
          <button
            onClick={() => onUpgrade(plan.plan)}
            disabled={upgrading !== null}
            className="w-full py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed rounded"
          >
            {upgrading === plan.plan ? 'Redirecting...' : 'Upgrade'}
          </button>
        )}
      </div>
    </div>
  );
}

export default function BillingPage() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [account, setAccount] = useState<BillingAccount | null>(null);
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [billingError, setBillingError] = useState(false);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);

  const authHeaders: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};

  useEffect(() => {
    fetchBillingData();
  }, []);

  async function fetchBillingData() {
    setLoading(true);
    try {
      const [accountRes, plansRes] = await Promise.all([
        fetch(`${API_BASE}/api/v2/billing/account`, { headers: authHeaders }).catch(() => null),
        fetch(`${API_BASE}/api/v2/billing/plans`, { headers: authHeaders }).catch(() => null),
      ]);

      if (accountRes && accountRes.ok) {
        setAccount(await accountRes.json());
      } else {
        setBillingError(true);
      }

      if (plansRes && plansRes.ok) {
        const data = await plansRes.json();
        const sorted = [...(data.plans ?? [])].sort(
          (a: BillingPlan, b: BillingPlan) =>
            PLAN_ORDER.indexOf(a.plan) - PLAN_ORDER.indexOf(b.plan)
        );
        setPlans(sorted);
      }
    } catch {
      setBillingError(true);
    } finally {
      setLoading(false);
    }
  }

  async function handleUpgrade(plan: string) {
    setUpgrading(plan);
    try {
      const res = await fetch(`${API_BASE}/api/v2/billing/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ plan }),
      });
      if (res.ok) {
        const data = await res.json();
        window.open(data.checkout_url, '_blank');
      } else {
        const errData = await res.json().catch(() => ({}));
        const detail = (errData as { detail?: string }).detail || `Upgrade failed (${res.status})`;
        setBillingError(true);
        alert(detail);
      }
    } catch {
      setBillingError(true);
      alert('Network error — could not start checkout. Please try again.');
    } finally {
      setUpgrading(null);
    }
  }

  async function handlePortal() {
    setPortalLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v2/billing/portal`, {
        method: 'POST',
        headers: authHeaders,
      });
      if (res.ok) {
        const data = await res.json();
        window.open(data.portal_url, '_blank');
      }
    } catch {
      // silent
    } finally {
      setPortalLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sardis-500" />
      </div>
    );
  }

  const currentPlan = account?.plan ?? 'free';
  const status = account?.status ?? 'active';
  const usage = account?.usage ?? {
    api_calls_used: 0,
    api_calls_limit: null,
    tx_volume_cents: 0,
    tx_volume_limit_cents: null,
    agents_used: 0,
    agents_limit: null,
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Billing</h1>
        <p className="text-gray-400 mt-1">Manage your plan, usage, and payment details</p>
      </div>

      {billingError && (
        <div className="card p-4 border-amber-500/30 bg-amber-500/5 flex items-center gap-3">
          <WarningCircle className="w-5 h-5 text-amber-400 shrink-0" />
          <p className="text-sm text-amber-300">
            Billing not configured. You are on the Free plan.
          </p>
        </div>
      )}

      {/* Current Plan Card */}
      <div className="card p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <p className="text-sm text-gray-400 mb-2">Current Plan</p>
            <div className="flex items-center gap-3 flex-wrap">
              <span
                className={`text-sm font-semibold px-3 py-1 rounded-full ${
                  PLAN_BADGE_COLORS[currentPlan] ?? PLAN_BADGE_COLORS.free
                }`}
              >
                {PLAN_LABELS[currentPlan] ?? currentPlan}
              </span>
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  STATUS_BADGE_COLORS[status] ?? STATUS_BADGE_COLORS.active
                }`}
              >
                {status.replace('_', ' ')}
              </span>
            </div>
            {account?.current_period_end && (
              <p className="text-xs text-gray-500 mt-2">
                Current period ends{' '}
                {new Date(account.current_period_end).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            )}
          </div>

          <button
            onClick={handlePortal}
            disabled={portalLoading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-dark-200 text-gray-300 hover:bg-dark-100 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-dark-100"
          >
            <CreditCard className="w-4 h-4" />
            {portalLoading ? 'Opening...' : 'Manage Billing'}
            <ArrowSquareOut className="w-3 h-3 opacity-60" />
          </button>
        </div>
      </div>

      {/* Usage Meters */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Usage This Period</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <UsageMeter
            label="API Calls"
            used={usage.api_calls_used}
            limit={usage.api_calls_limit}
            format={formatNumber}
            icon={<Lightning className="w-5 h-5" />}
          />
          <UsageMeter
            label="Transaction Volume"
            used={usage.tx_volume_cents}
            limit={usage.tx_volume_limit_cents}
            format={formatCents}
            icon={<TrendUp className="w-5 h-5" />}
          />
          <UsageMeter
            label="Agents"
            used={usage.agents_used}
            limit={usage.agents_limit}
            format={(v) => String(v)}
            icon={<Users className="w-5 h-5" />}
          />
        </div>
      </div>

      {/* Plan Comparison */}
      {plans.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Plans</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {plans.map((plan) => (
              <PlanColumn
                key={plan.plan}
                plan={plan}
                isCurrent={plan.plan === currentPlan}
                isPopular={plan.plan === 'growth'}
                onUpgrade={handleUpgrade}
                upgrading={upgrading}
              />
            ))}
          </div>
        </div>
      )}

      {/* Fallback plan table when no plans returned from API */}
      {plans.length === 0 && !loading && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Plans</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { plan: 'free', price_monthly_cents: 0, api_calls_per_month: 1000, agents: 1, tx_fee_bps: 50, monthly_tx_volume_cents: 100000 },
              { plan: 'starter', price_monthly_cents: 4900, api_calls_per_month: 50000, agents: 10, tx_fee_bps: 30, monthly_tx_volume_cents: 1000000 },
              { plan: 'growth', price_monthly_cents: 24900, api_calls_per_month: null, agents: null, tx_fee_bps: 20, monthly_tx_volume_cents: null },
              { plan: 'enterprise', price_monthly_cents: 0, api_calls_per_month: null, agents: null, tx_fee_bps: 10, monthly_tx_volume_cents: null },
            ].map((plan) => (
              <PlanColumn
                key={plan.plan}
                plan={plan}
                isCurrent={plan.plan === currentPlan}
                isPopular={plan.plan === 'growth'}
                onUpgrade={handleUpgrade}
                upgrading={upgrading}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
