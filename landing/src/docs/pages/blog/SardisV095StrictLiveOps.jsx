import { Link } from 'react-router-dom';
import { ArrowLeft, Calendar, Clock } from 'lucide-react';
import SEO, { createArticleSchema, createBreadcrumbSchema } from '@/components/SEO';

export default function SardisV095StrictLiveOps() {
  return (
    <>
      <SEO
        title="Sardis v0.9.5: Strict Live Mode + Operations Hardening"
        description="Sardis v0.9.5 ships strict live-mode controls: replay/idempotency proof gates, SLO+Pager routing, DR evidence automation, and runtime security-policy preflight visibility."
        path="/docs/blog/sardis-v0-9-5-strict-live-ops-hardening"
        type="article"
        article={{ publishedDate: '2026-02-26' }}
        schemas={[
          createArticleSchema({
            title: 'Sardis v0.9.5: Strict Live Mode + Operations Hardening',
            description: 'Release notes for v0.9.5: strict live mode, idempotency/replay proof gates, SLO alerting, and DR/compliance evidence automation.',
            path: '/docs/blog/sardis-v0-9-5-strict-live-ops-hardening',
            publishedDate: '2026-02-26',
          }),
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Blog', href: '/docs/blog' },
            { name: 'Sardis v0.9.5' },
          ]),
        ]}
      />

      <article className="prose prose-invert max-w-none">
        <div className="not-prose mb-8">
          <Link
            to="/docs/blog"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Blog
          </Link>
        </div>

        <header className="not-prose mb-8">
          <div className="flex items-center gap-3 mb-4">
            <span className="px-2 py-1 text-xs font-mono bg-purple-500/10 border border-purple-500/30 text-purple-500">
              RELEASE
            </span>
            <span className="px-2 py-1 text-xs font-mono bg-[var(--sardis-orange)] text-white">
              FEATURED
            </span>
          </div>
          <h1 className="text-4xl font-bold font-display mb-4">
            Sardis v0.9.5: Strict Live Mode + Operations Hardening
          </h1>
          <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
            <span className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              February 26, 2026
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" />5 min read
            </span>
          </div>
        </header>

        <p className="text-lg text-muted-foreground leading-relaxed">
          v0.9.5 focuses on production discipline: strict live-mode boundaries, deterministic replay protection,
          operations alerting, and verifiable incident evidence artifacts.
        </p>

        <h2>What shipped</h2>
        <ul>
          <li>Strict live-mode guardrails on critical payment execution paths.</li>
          <li>Idempotency and replay-proof release gates for webhook and payment pipelines.</li>
          <li>SLO dashboard and PagerDuty-ready alert routing for production operations.</li>
          <li>DR drill evidence automation with measured RTO/RPO artifact generation.</li>
          <li>Runtime security-policy preflight surfaced directly in dashboard demo flow.</li>
        </ul>

        <h2>Why this matters</h2>
        <p>
          Agentic payments need deterministic controls even under provider outages or adversarial traffic. This release
          raises the default posture from “works” to “provably safe”: deny on ambiguity, preserve evidence, and keep
          operators inside explicit runbooks.
        </p>

        <h2>Operator checks now exposed</h2>
        <ul>
          <li><code>GET /api/v2/checkout/secure/security-policy</code></li>
          <li><code>GET /api/v2/cards/asa/security-policy</code></li>
          <li><code>GET /api/v2/a2a/trust/security-policy</code></li>
          <li><code>GET /api/v2/cards/providers/readiness</code></li>
        </ul>

        <p>
          Combined with secure checkout evidence exports, these endpoints give operators a deterministic control-plane snapshot
          before and after execution.
        </p>

        <div className="not-prose mt-10 p-6 bg-card/50 rounded-lg">
          <h3 className="font-bold font-display mb-3">Release focus</h3>
          <p className="text-sm text-muted-foreground mb-3">
            Next up is live provider certification and PCI boundary finalization (issuer-hosted reveal/iframe or enclave lane).
          </p>
          <div className="text-sm text-muted-foreground">
            See <Link to="/docs/roadmap" className="text-[var(--sardis-orange)] hover:underline">Roadmap</Link> and{' '}
            <Link to="/docs/changelog" className="text-[var(--sardis-orange)] hover:underline">Changelog</Link>.
          </div>
        </div>
      </article>
    </>
  );
}

