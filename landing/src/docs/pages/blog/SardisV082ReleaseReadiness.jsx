import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock } from "lucide-react";

export default function SardisV082ReleaseReadiness() {
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
          Sardis v0.8.2: Release Readiness Hardening for MCP + SDKs
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            February 6, 2026
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />6 min read
          </span>
        </div>
      </header>

      <p className="text-lg text-muted-foreground leading-relaxed">
        v0.8.2 is an engineering-readiness release focused on reproducible checks and safer
        pre-prod execution. We hardened release scripts, isolated protocol conformance lanes,
        and made local validation clearer when npm or network access is constrained.
      </p>

      <h2>What Changed</h2>

      <ul>
        <li>
          <strong>Deterministic JS bootstrap preflight</strong> - <code>bootstrap:js</code> now checks
          node/pnpm versions, DNS resolution, and npm registry reachability before install.
        </li>
        <li>
          <strong>Live-chain conformance gate added</strong> - <code>check:live-chain</code> validates
          Turnkey + testnet integrations and supports strict fail-closed mode.
        </li>
        <li>
          <strong>Protocol lane isolation fixed</strong> - root conformance and package-level UCP tests now
          run without pytest import collisions.
        </li>
        <li>
          <strong>Conformance reporting hardened</strong> - report generation now works even without
          pytest JSON plugins, with summary-based pass/fail extraction.
        </li>
      </ul>

      <h2>Why This Release Matters</h2>

      <p>
        Design partner programs fail when local and CI outcomes diverge. v0.8.2 reduces that risk by
        making release checks explicit, deterministic, and transparent under both normal and constrained
        environments.
      </p>

      <ul>
        <li>Faster diagnosis when local npm execution is blocked by DNS/network policy</li>
        <li>Safer progression from protocol conformance to real integration checks</li>
        <li>Clearer release gating semantics for staging and design-partner readiness</li>
      </ul>

      <h2>Current Validation Baseline</h2>

      <ul>
        <li>Protocol conformance: <strong>191 passed / 0 failed / 0 skipped</strong></li>
        <li>Python SDK suite: <strong>251 passed / 4 skipped</strong></li>
        <li>A2A + UCP package suites: <strong>98 + 53 passed</strong></li>
      </ul>

      <p>
        See the
        {" "}
        <Link to="/docs/changelog" className="text-[var(--sardis-orange)]">
          Changelog
        </Link>
        {" "}
        and roadmap for the next hardening steps.
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
