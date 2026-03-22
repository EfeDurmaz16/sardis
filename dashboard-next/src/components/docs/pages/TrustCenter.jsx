export default function TrustCenter() {
  return (
    <article className="prose dark:prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            TRUST & SECURITY
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Trust Center</h1>
        <p className="text-xl text-muted-foreground">
          How Sardis protects your agents, your money, and your data.
        </p>
      </div>

      {/* Security Overview */}
      <h2>Security Architecture</h2>

      <h3>Non-Custodial by Design</h3>
      <p>
        Sardis never holds your private keys. All wallet operations use <strong>MPC (Multi-Party Computation)</strong> via
        Turnkey, where key shares are distributed across multiple parties. No single entity — including Sardis — can
        unilaterally sign a transaction.
      </p>

      <h3>Policy-First Execution</h3>
      <p>
        Every payment passes through a <strong>12-check policy pipeline</strong> before any funds move. The pipeline
        is fail-closed: if any check fails or the policy engine is unreachable, the payment is rejected. This includes:
      </p>
      <ul>
        <li>Per-transaction amount limits</li>
        <li>Daily, weekly, and monthly spending caps</li>
        <li>Merchant allowlist/blocklist with MCC code filtering</li>
        <li>Token type restrictions</li>
        <li>Purpose requirement enforcement</li>
        <li>Human approval threshold routing</li>
        <li>Cross-rail deduplication</li>
        <li>Sanctions screening (OFAC/FATF)</li>
      </ul>

      <h3>Authentication & Access Control</h3>
      <ul>
        <li><strong>Passwords:</strong> Argon2id hashing (PBKDF2 fallback with 100K iterations)</li>
        <li><strong>JWT tokens:</strong> HS256 with JTI-based revocation via Redis blacklist</li>
        <li><strong>API keys:</strong> SHA-256 hashed before storage, constant-time validation</li>
        <li><strong>MFA:</strong> TOTP-based (compatible with Google Authenticator, Authy, 1Password)</li>
        <li><strong>Rate limiting:</strong> Per-IP and per-org, Redis-backed with in-memory fallback</li>
        <li><strong>CORS:</strong> Explicit origin allowlist (no wildcards with credentials)</li>
      </ul>

      <h3>Data Protection</h3>
      <ul>
        <li><strong>In transit:</strong> TLS 1.3 with HSTS (1 year, includeSubDomains, preload)</li>
        <li><strong>At rest:</strong> AES-256 encryption via cloud provider (Neon PostgreSQL, GCP)</li>
        <li><strong>Credentials:</strong> Fernet symmetric encryption for delegated tokens</li>
        <li><strong>Logs:</strong> Sensitive data masked (auth headers, API keys, passwords)</li>
        <li><strong>Headers:</strong> CSP, X-Frame-Options DENY, X-Content-Type-Options nosniff</li>
      </ul>

      <h3>Infrastructure Security</h3>
      <ul>
        <li><strong>Deployment:</strong> Cloud Run (GCP) with non-root containers, multi-stage Docker builds</li>
        <li><strong>CI/CD:</strong> Gitleaks secret scanning, Trivy container scanning, Bandit SAST, pip-audit dependency scanning</li>
        <li><strong>Webhooks:</strong> HMAC-SHA256 signatures with 5-minute replay window, SSRF prevention on URLs</li>
        <li><strong>Kill switch:</strong> Multi-scope emergency stop (global, org, agent, rail, chain)</li>
      </ul>

      {/* Compliance */}
      <h2>Compliance Status</h2>

      <div className="not-prose mb-6">
        <table className="w-full text-sm border border-border">
          <thead>
            <tr className="bg-muted/30">
              <th className="text-left p-3 border-b border-border">Framework</th>
              <th className="text-left p-3 border-b border-border">Status</th>
              <th className="text-left p-3 border-b border-border">Details</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['SOC 2 Type II', 'In Progress', 'Preparing with automated compliance platform. Target: Q3 2026.'],
              ['GDPR', 'Compliant', 'Data export, deletion, consent management, DPA available.'],
              ['CCPA', 'Compliant', 'Data access, deletion, opt-out rights supported.'],
              ['PCI DSS', 'Via Partner', 'Card processing handled by Stripe (PCI Level 1 certified).'],
              ['KYC/AML', 'Integrated', 'iDenfy for identity verification, Elliptic for sanctions screening.'],
              ['Travel Rule', 'Enforced', 'FATF R.16 compliance above $3,000 threshold (IVMS101 format).'],
            ].map(([framework, s, details]) => (
              <tr key={framework} className="border-b border-border">
                <td className="p-3 font-medium">{framework}</td>
                <td className="p-3">
                  <span className={`px-2 py-0.5 text-xs rounded ${
                    s === 'Compliant' || s === 'Integrated' || s === 'Enforced' ? 'bg-green-500/10 text-green-500' :
                    s === 'In Progress' ? 'bg-amber-500/10 text-amber-500' :
                    'bg-blue-500/10 text-blue-500'
                  }`}>{s}</span>
                </td>
                <td className="p-3 text-muted-foreground">{details}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Subprocessors */}
      <h2>Subprocessors</h2>
      <p>
        Sardis uses the following third-party service providers to deliver the platform.
        All subprocessors are bound by data processing agreements.
      </p>

      <div className="not-prose mb-6">
        <table className="w-full text-sm border border-border">
          <thead>
            <tr className="bg-muted/30">
              <th className="text-left p-3 border-b border-border">Provider</th>
              <th className="text-left p-3 border-b border-border">Purpose</th>
              <th className="text-left p-3 border-b border-border">Data Processed</th>
              <th className="text-left p-3 border-b border-border">Location</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['Turnkey', 'MPC wallet custody & signing', 'Public keys, transaction data', 'USA'],
              ['iDenfy', 'KYC identity verification', 'Government ID, selfie, name, DOB', 'EU (Lithuania)'],
              ['Elliptic', 'AML/sanctions screening', 'Wallet addresses, transaction hashes', 'UK'],
              ['Stripe', 'Billing, virtual card issuance', 'Payment method, email, plan', 'USA'],
              ['Neon', 'PostgreSQL database hosting', 'All application data', 'USA (AWS us-east-1)'],
              ['Alchemy', 'Blockchain RPC access', 'Transaction data, wallet addresses', 'USA'],
              ['Google Cloud', 'API hosting (Cloud Run)', 'API requests, logs', 'USA (us-east1)'],
              ['Upstash', 'Redis caching', 'Session data, rate limits', 'USA'],
              ['PostHog', 'Product analytics', 'Usage events, anonymized behavior', 'EU'],
            ].map(([provider, purpose, data, location]) => (
              <tr key={provider} className="border-b border-border">
                <td className="p-3 font-medium">{provider}</td>
                <td className="p-3">{purpose}</td>
                <td className="p-3 text-muted-foreground">{data}</td>
                <td className="p-3">{location}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* SLA */}
      <h2>Service Level Agreement</h2>

      <h3>Uptime Target</h3>
      <p>
        Sardis targets <strong>99.9% monthly uptime</strong> for the API (<code>api.sardis.sh</code>)
        and dashboard (<code>dashboard.sardis.sh</code>), excluding scheduled maintenance windows.
      </p>

      <h3>Maintenance Windows</h3>
      <p>
        Scheduled maintenance occurs during low-traffic periods (Sundays 02:00-06:00 UTC) with
        at least 48 hours advance notice via email and status page. Emergency maintenance may
        occur with shorter notice for critical security patches.
      </p>

      <h3>Incident Response</h3>
      <div className="not-prose mb-6">
        <table className="w-full text-sm border border-border">
          <thead>
            <tr className="bg-muted/30">
              <th className="text-left p-3 border-b border-border">Severity</th>
              <th className="text-left p-3 border-b border-border">Description</th>
              <th className="text-left p-3 border-b border-border">Response Time</th>
              <th className="text-left p-3 border-b border-border">Update Cadence</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['P0 — Critical', 'Complete service outage or data breach', '< 30 minutes', 'Every 30 minutes'],
              ['P1 — High', 'Major feature unavailable, payments blocked', '< 2 hours', 'Every 2 hours'],
              ['P2 — Medium', 'Degraded performance, non-critical feature down', '< 8 hours', 'Daily'],
              ['P3 — Low', 'Minor issue, workaround available', '< 24 hours', 'As resolved'],
            ].map(([severity, desc, response, cadence]) => (
              <tr key={severity} className="border-b border-border">
                <td className="p-3 font-medium">{severity}</td>
                <td className="p-3">{desc}</td>
                <td className="p-3">{response}</td>
                <td className="p-3">{cadence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Data Processing */}
      <h2>Data Processing Agreement</h2>
      <p>
        Enterprise customers can request a Data Processing Agreement (DPA) covering GDPR
        requirements. Our standard DPA includes:
      </p>
      <ul>
        <li>Data processing scope and purposes</li>
        <li>Subprocessor list and notification of changes</li>
        <li>Data subject rights handling procedures</li>
        <li>Security measures and breach notification (72-hour window)</li>
        <li>Data deletion upon contract termination</li>
        <li>Audit rights</li>
      </ul>
      <p>
        Contact <a href="mailto:legal@sardis.sh">legal@sardis.sh</a> to request a DPA.
      </p>

      {/* Data Retention */}
      <h2>Data Retention</h2>
      <div className="not-prose mb-6">
        <table className="w-full text-sm border border-border">
          <thead>
            <tr className="bg-muted/30">
              <th className="text-left p-3 border-b border-border">Data Type</th>
              <th className="text-left p-3 border-b border-border">Retention</th>
              <th className="text-left p-3 border-b border-border">Basis</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['Account data', '3 years after deletion', 'Contractual'],
              ['Transaction records', '7 years', 'Regulatory (financial records)'],
              ['KYC documents', '5-7 years', 'AML/CFT regulations'],
              ['API logs', '90 days', 'Operational'],
              ['Analytics events', '12 months', 'Legitimate interest'],
            ].map(([type, retention, basis]) => (
              <tr key={type} className="border-b border-border">
                <td className="p-3">{type}</td>
                <td className="p-3">{retention}</td>
                <td className="p-3 text-muted-foreground">{basis}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Security Contact */}
      <h2>Security Contact</h2>
      <p>
        To report security vulnerabilities or request security documentation:
      </p>
      <ul>
        <li><strong>Security issues:</strong> <a href="mailto:security@sardis.sh">security@sardis.sh</a></li>
        <li><strong>Legal/DPA:</strong> <a href="mailto:legal@sardis.sh">legal@sardis.sh</a></li>
        <li><strong>General support:</strong> <a href="mailto:support@sardis.sh">support@sardis.sh</a></li>
      </ul>
      <p>
        We commit to acknowledging security reports within 24 hours and providing an initial
        assessment within 72 hours.
      </p>
    </article>
  );
}
