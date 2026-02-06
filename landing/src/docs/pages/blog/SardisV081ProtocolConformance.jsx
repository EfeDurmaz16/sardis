import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock } from "lucide-react";

export default function SardisV081ProtocolConformance() {
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
          Sardis v0.8.1: Protocol Conformance Hardening for AP2/TAP
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            February 6, 2026
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />7 min read
          </span>
        </div>
      </header>

      <p className="text-lg text-muted-foreground leading-relaxed">
        v0.8.1 is a protocol-hardening release focused on correctness over breadth. We tightened AP2 payment
        semantics, strengthened TAP validation paths, and added a source-mapped conformance baseline so engineering
        decisions stay anchored to canonical AP2, TAP, UCP, and x402 references.
      </p>

      <h2>What Changed</h2>

      <ul>
        <li>
          <strong>AP2 payment semantics hardened</strong> &mdash; payment mandates now include explicit
          <code>ai_agent_presence</code> and <code>transaction_modality</code> signals
          (<code>human_present</code> or <code>human_not_present</code>) and are enforced in verification.
        </li>
        <li>
          <strong>TAP header checks tightened</strong> &mdash; signature input validation now rejects unsupported
          message signature algorithms by default.
        </li>
        <li>
          <strong>Linked object signature hooks added</strong> &mdash; <code>agenticConsumer</code> and
          <code>agenticPaymentContainer</code> validation supports canonical signature-base building and
          optional verification hooks.
        </li>
        <li>
          <strong>Conformance evidence improved</strong> &mdash; new tests cover invalid alg, nonce mismatch,
          and signature-failure paths for TAP and modality guardrails for AP2.
        </li>
      </ul>

      <h2>Why This Release Matters</h2>

      <p>
        Before scaling integrations, protocol interpretation drift is one of the highest engineering risks.
        v0.8.1 reduces this risk by making protocol assumptions explicit in code and test gates.
      </p>

      <ul>
        <li>Lower interoperability risk across AP2/TAP counterparties</li>
        <li>Better auditability of policy and protocol decisions</li>
        <li>Stronger defaults for pre-prod design partner environments</li>
      </ul>

      <h2>Source Mapping and Governance</h2>

      <p>
        We now maintain a protocol source map that links canonical references to concrete enforcement points
        in code and tests. This keeps conformance work reviewable and repeatable over time.
      </p>

      <p>
        See:
        {" "}
        <Link to="/docs/changelog" className="text-[var(--sardis-orange)]">
          Changelog
        </Link>
        {" "}
        and the release docs for implementation details.
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

