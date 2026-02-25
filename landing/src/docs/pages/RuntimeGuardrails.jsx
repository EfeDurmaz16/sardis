import SEO, { createBreadcrumbSchema } from '@/components/SEO';

export default function DocsRuntimeGuardrails() {
  return (
    <>
      <SEO
        title="Runtime Guardrails"
        description="Operational runtime guardrails for Sardis payment execution: PAN lane quorum, Lithic ASA fail-closed controls, and wallet-aware A2A trust enforcement."
        path="/docs/runtime-guardrails"
        schemas={[
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Runtime Guardrails' },
          ]),
        ]}
      />
      <article className="prose prose-invert max-w-none">
        <div className="not-prose mb-8">
          <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
            <span className="px-2 py-1 bg-red-500/10 border border-red-500/30 text-red-500">SECURITY</span>
            <span>Runtime Control Plane</span>
          </div>
          <h1 className="text-4xl font-bold font-display mb-4">Runtime Guardrails</h1>
          <p className="text-xl text-muted-foreground">
            Production runtime controls that keep agentic payments deterministic, auditable, and fail-closed.
          </p>
        </div>

        <section id="pan-lane-quorum" className="mb-12 scroll-mt-24">
          <h2 className="text-2xl font-bold font-display mb-3">PAN Lane Quorum</h2>
          <p className="text-muted-foreground mb-3">
            Sensitive card actions are protected with quorum approval. Sardis requires distinct reviewers for PAN-lane
            execution, and blocks execution when quorum requirements are not met.
          </p>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li>Fail-closed when reviewer count or reviewer uniqueness is insufficient.</li>
            <li>Approval evidence is stored in audit trail with actor and timestamp metadata.</li>
            <li>High-risk actions can be gated behind stricter thresholds without changing agent prompts.</li>
          </ul>
        </section>

        <section id="asa-fail-closed" className="mb-12 scroll-mt-24">
          <h2 className="text-2xl font-bold font-display mb-3">ASA Fail-Closed</h2>
          <p className="text-muted-foreground mb-3">
            Lithic ASA authorization checks default to deny whenever control-plane dependencies fail (lookup,
            subscription matching, or policy context retrieval).
          </p>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li>Issuer authorization stream errors return deterministic deny, not soft-allow.</li>
            <li>Denied decisions are logged for post-incident forensics and replay analysis.</li>
            <li>Operational posture is exposed through runtime security-policy endpoints for admins.</li>
          </ul>
        </section>

        <section id="wallet-aware-a2a-trust" className="scroll-mt-24">
          <h2 className="text-2xl font-bold font-display mb-3">Wallet-Aware A2A Trust</h2>
          <p className="text-muted-foreground mb-3">
            Multi-agent payment orchestration uses trust relations that are aware of wallet ownership and organization
            boundaries to prevent cross-tenant execution drift.
          </p>
          <ul className="list-disc pl-6 text-muted-foreground space-y-2">
            <li>Trust graph mutations are protected by approval and audit controls.</li>
            <li>Broadcast targets are derived from trusted peers and filtered by wallet visibility.</li>
            <li>Untrusted or cross-organization peers are excluded from payment fan-out paths.</li>
          </ul>
        </section>
      </article>
    </>
  )
}
