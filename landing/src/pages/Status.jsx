import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';

import '@fontsource/space-grotesk/400.css';
import '@fontsource/space-grotesk/600.css';
import '@fontsource/space-grotesk/700.css';
import '@fontsource/inter/300.css';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'https://api.sardis.sh';
const REFRESH_INTERVAL_MS = 30_000;

// ─── Status Dot ─────────────────────────────────────────────────────────
function StatusDot({ status }) {
  const color =
    status === 'healthy' || status === 'ok'
      ? '#22C55E'
      : status === 'degraded' || status === 'partial'
        ? '#F59E0B'
        : '#EF4444';
  return (
    <span
      className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
      style={{ background: color, boxShadow: `0 0 6px ${color}40` }}
    />
  );
}

// ─── Component Card ─────────────────────────────────────────────────────
function ComponentCard({ name, status, details }) {
  return (
    <div
      className="flex items-center justify-between py-3 px-4 rounded-lg"
      style={{ background: 'rgba(255,255,255,0.02)' }}
    >
      <div className="flex items-center gap-3">
        <StatusDot status={status} />
        <span className="text-sm" style={{ fontFamily: "'Inter', sans-serif", color: '#E0E0E0' }}>
          {name}
        </span>
      </div>
      <span
        className="text-xs capitalize"
        style={{
          fontFamily: "'Inter', sans-serif",
          color:
            status === 'healthy' || status === 'ok'
              ? '#22C55E'
              : status === 'degraded' || status === 'partial'
                ? '#F59E0B'
                : '#EF4444',
        }}
      >
        {status === 'healthy' || status === 'ok' ? 'Operational' : status}
      </span>
    </div>
  );
}

// ─── Section ────────────────────────────────────────────────────────────
function Section({ title, components }) {
  return (
    <div>
      <h3
        className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ fontFamily: "'Inter', sans-serif", color: '#505460' }}
      >
        {title}
      </h3>
      <div
        className="rounded-xl overflow-hidden"
        style={{ background: '#0A0B0D', border: '1px solid rgba(255,255,255,0.07)' }}
      >
        <div className="divide-y" style={{ borderColor: 'rgba(255,255,255,0.04)' }}>
          {components.map((c) => (
            <ComponentCard key={c.name} name={c.name} status={c.status} details={c.details} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Wordmark ───────────────────────────────────────────────────────────
function SardisWordmark() {
  return (
    <Link to="/" className="flex items-center gap-2.5 flex-shrink-0">
      <svg width="34" height="34" viewBox="0 0 28 28" fill="none">
        <path d="M20 5H10a7 7 0 000 14h2" stroke="#F5F5F5" strokeWidth="3" strokeLinecap="round" fill="none" />
        <path d="M8 23h10a7 7 0 000-14h-2" stroke="#F5F5F5" strokeWidth="3" strokeLinecap="round" fill="none" />
      </svg>
      <span className="text-2xl font-bold leading-none" style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#F5F5F5' }}>
        Sardis
      </span>
    </Link>
  );
}

// ─── Main Page ──────────────────────────────────────────────────────────
export default function Status() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState(null);
  const [error, setError] = useState(null);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/health`);
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
        setError(null);
      } else {
        setError(`API returned ${res.status}`);
      }
    } catch (e) {
      setError('Unable to reach API');
    } finally {
      setLoading(false);
      setLastChecked(new Date());
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  // Parse health response into grouped components
  const components = health?.components || {};
  const overallStatus = health?.status || (error ? 'down' : 'unknown');

  const coreInfra = [
    { name: 'Database (PostgreSQL)', status: components.database || 'unknown' },
    { name: 'Cache (Redis)', status: components.cache || components.redis || 'unknown' },
  ];

  const paymentRails = [
    { name: 'Stripe', status: components.stripe || 'unknown' },
    { name: 'Turnkey (MPC)', status: components.turnkey || 'unknown' },
    { name: 'RPC (Base)', status: components.rpc || 'unknown' },
    { name: 'Smart Contracts', status: components.contracts || components.smart_contracts || 'unknown' },
  ];

  const compliance = [
    { name: 'KYC (iDenfy)', status: components.kyc || components.compliance || 'unknown' },
    { name: 'AML (Elliptic)', status: components.aml || components.sanctions || 'unknown' },
  ];

  const operations = [
    { name: 'Webhooks', status: components.webhooks || 'unknown' },
    { name: 'Kill Switch', status: components.kill_switch || 'unknown' },
    { name: 'TAP JWKS', status: components.tap_jwks || 'unknown' },
  ];

  const overallBanner =
    overallStatus === 'healthy'
      ? { text: 'All Systems Operational', color: '#22C55E', bg: 'rgba(34,197,94,0.08)' }
      : overallStatus === 'partial' || overallStatus === 'degraded'
        ? { text: 'Partial System Degradation', color: '#F59E0B', bg: 'rgba(245,158,11,0.08)' }
        : { text: 'System Issues Detected', color: '#EF4444', bg: 'rgba(239,68,68,0.08)' };

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#050506' }}>
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md border-b" style={{ backgroundColor: 'rgba(5,5,6,0.85)', borderBottomColor: 'rgba(255,255,255,0.07)' }}>
        <div className="max-w-[800px] mx-auto px-5">
          <div className="flex items-center justify-between h-16">
            <SardisWordmark />
            <Link to="/" className="text-sm transition-colors" style={{ fontFamily: "'Inter', sans-serif", color: '#808080' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#C0C0C0')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#808080')}
            >
              Back to Sardis
            </Link>
          </div>
        </div>
      </nav>

      <div className="h-16" />

      {/* Header */}
      <section className="pt-16 pb-8 px-5">
        <div className="max-w-[800px] mx-auto">
          <h1 className="text-3xl font-bold mb-2" style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#F5F5F5' }}>
            System Status
          </h1>
          <p className="text-sm" style={{ fontFamily: "'Inter', sans-serif", color: '#808080' }}>
            Real-time health of Sardis infrastructure. Auto-refreshes every 30 seconds.
          </p>
        </div>
      </section>

      {/* Overall Status Banner */}
      <section className="px-5 pb-8">
        <div className="max-w-[800px] mx-auto">
          <div
            className="rounded-xl p-5 flex items-center gap-3"
            style={{ background: overallBanner.bg, border: `1px solid ${overallBanner.color}30` }}
          >
            <StatusDot status={overallStatus === 'healthy' ? 'healthy' : overallStatus === 'partial' ? 'degraded' : 'down'} />
            <span className="text-lg font-semibold" style={{ fontFamily: "'Space Grotesk', sans-serif", color: overallBanner.color }}>
              {loading ? 'Checking...' : overallBanner.text}
            </span>
          </div>
        </div>
      </section>

      {/* Component Groups */}
      {!loading && (
        <section className="px-5 pb-16">
          <div className="max-w-[800px] mx-auto space-y-8">
            <Section title="Core Infrastructure" components={coreInfra} />
            <Section title="Payment Rails" components={paymentRails} />
            <Section title="Compliance" components={compliance} />
            <Section title="Operations" components={operations} />
          </div>
        </section>
      )}

      {/* Last Updated */}
      <section className="px-5 pb-8">
        <div className="max-w-[800px] mx-auto text-center">
          {lastChecked && (
            <p className="text-xs" style={{ fontFamily: "'Inter', sans-serif", color: '#3F3F4A' }}>
              Last checked: {lastChecked.toLocaleTimeString()} &middot; Refreshes every 30s
            </p>
          )}
          {error && (
            <p className="text-xs mt-2" style={{ color: '#EF4444' }}>
              {error}
            </p>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8 text-center" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <p className="text-xs" style={{ fontFamily: "'Inter', sans-serif", color: '#3F3F4A' }}>
          &copy; {new Date().getFullYear()} Sardis. All rights reserved.{' '}
          <Link to="/docs/terms" className="underline" style={{ color: '#505460' }}>Terms</Link>
          {' '}&middot;{' '}
          <Link to="/docs/privacy" className="underline" style={{ color: '#505460' }}>Privacy</Link>
        </p>
      </footer>
    </div>
  );
}
