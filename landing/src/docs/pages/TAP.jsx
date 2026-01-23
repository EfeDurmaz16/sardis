export default function DocsTAP() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-500">PROTOCOLS</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">TAP Protocol</h1>
        <p className="text-xl text-muted-foreground">Trust Anchor Protocol - Cryptographic identity verification for agents.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Supported Algorithms
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <thead>
              <tr className="bg-muted/30">
                <th className="px-4 py-2 text-left border-b border-border">Algorithm</th>
                <th className="px-4 py-2 text-left border-b border-border">Use Case</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">Ed25519</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Fast signatures, agent identity</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">ECDSA-P256</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Web compatibility, hardware security</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">secp256k1</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Ethereum compatibility</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Agent Identity
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`{
  "agent_id": "agent_abc123",
  "public_key": "0x04...",
  "algorithm": "Ed25519",
  "attestations": [
    {
      "issuer": "sardis.sh",
      "type": "verified_agent",
      "issued_at": "2026-01-01T00:00:00Z"
    }
  ]
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Verification
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis import SardisClient

async with SardisClient(api_key="sk_...") as client:
    # Verify agent identity
    result = await client.tap.verify_identity(
        agent_id="agent_abc123",
        signature="0x...",
        message="payment_request_123",
    )

    if result.verified:
        print(f"Agent verified: {result.attestations}")
    else:
        print(f"Verification failed: {result.reason}")`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Attestation Types
        </h2>
        <div className="not-prose space-y-2 text-sm">
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">✓</span>
            <span className="font-mono text-[var(--sardis-orange)]">verified_agent</span>
            <span className="text-muted-foreground">- Basic identity verification</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">✓</span>
            <span className="font-mono text-[var(--sardis-orange)]">kyc_verified</span>
            <span className="text-muted-foreground">- KYC/AML compliance</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">✓</span>
            <span className="font-mono text-[var(--sardis-orange)]">merchant</span>
            <span className="text-muted-foreground">- Verified merchant status</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">✓</span>
            <span className="font-mono text-[var(--sardis-orange)]">trusted_platform</span>
            <span className="text-muted-foreground">- Platform-level trust</span>
          </div>
        </div>
      </section>
    </article>
  );
}
