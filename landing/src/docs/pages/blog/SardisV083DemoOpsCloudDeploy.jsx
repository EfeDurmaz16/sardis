import { Link } from 'react-router-dom';
import { ArrowLeft, Calendar, Clock } from 'lucide-react';

export default function SardisV083DemoOpsCloudDeploy() {
  return (
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
          Sardis v0.8.3: Demo Ops + Cloud Deployment (Cloud Run & AWS)
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            February 8, 2026
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />6 min read
          </span>
        </div>
      </header>

      <p className="text-lg text-muted-foreground leading-relaxed">
        v0.8.3 focuses on one thing: making demos and staging environments reliable under
        real operating conditions. We added deployment automation for both Google Cloud Run
        and AWS App Runner, tightened live-mode operator UX in <code>/demo</code>, and documented
        the exact frontend-to-backend integration contract.
      </p>

      <h2>What Shipped</h2>

      <ul>
        <li>
          <strong>Cloud Run deploy automation</strong> - staging script now handles artifact build/push,
          service deploy, env wiring, health checks, and post-deploy bootstrap guidance.
        </li>
        <li>
          <strong>AWS App Runner deploy automation</strong> - ECR build/push and service create/update flow
          with runtime env injection.
        </li>
        <li>
          <strong>Frontend live-mode runbook</strong> - explicit mapping for
          <code> SARDIS_API_URL</code>, <code>SARDIS_API_KEY</code>, and <code>DEMO_OPERATOR_PASSWORD</code>.
        </li>
        <li>
          <strong>Demo reliability upgrades</strong> - clearer live lock messaging and persistent
          transaction history across refreshes.
        </li>
      </ul>

      <h2>Why This Matters for GTM</h2>

      <p>
        Design partners and investors do not test code in ideal conditions. They test links,
        flows, and operator handoffs. v0.8.3 reduces demo failure risk by making deployment and
        live-mode setup deterministic and repeatable.
      </p>

      <ul>
        <li>Faster path from local staging to shared demo URL</li>
        <li>Lower chance of live-mode lockouts during walkthroughs</li>
        <li>Clear fallback from live mode to simulated mode without breaking the narrative</li>
      </ul>

      <h2>Operator Checklist (Condensed)</h2>

      <ol>
        <li>Deploy API to Cloud Run (recommended) or App Runner</li>
        <li>Bootstrap API key via auth bootstrap endpoint</li>
        <li>Set landing env vars server-side only</li>
        <li>Run blocked and approved scenarios in <code>/demo</code> live mode</li>
      </ol>

      <p>
        See
        {' '}
        <Link to="/docs/deployment" className="text-[var(--sardis-orange)]">
          Deployment Guide
        </Link>
        {' '}
        and
        {' '}
        <Link to="/docs/changelog" className="text-[var(--sardis-orange)]">
          Changelog
        </Link>
        {' '}
        for full commands and environment mappings.
      </p>

      <div className="not-prose mt-12 pt-6 border-t border-border">
        <Link
          to="/docs/roadmap"
          className="inline-flex items-center gap-2 text-sm text-[var(--sardis-orange)] hover:underline"
        >
          View roadmap updates →
        </Link>
      </div>
    </article>
  );
}
