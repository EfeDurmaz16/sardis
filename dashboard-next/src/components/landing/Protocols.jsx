const protocols = [
  {
    name: "AP2",
    full: "Agent Payment Protocol",
    org: "Google, PayPal, Visa",
    desc: "Mandate chain verification: Intent, Cart, Payment. The emerging standard for agent commerce.",
    status: "Production",
  },
  {
    name: "TAP",
    full: "Trusted Agent Protocol",
    org: "Open standard",
    desc: "Cryptographic identity verification using Ed25519 and ECDSA-P256 for agent attestation.",
    status: "Production",
  },
  {
    name: "x402",
    full: "HTTP 402 Micropayments",
    org: "Coinbase",
    desc: "Native HTTP micropayments. Pay-per-request for APIs, content, and compute resources.",
    status: "Pilot",
  },
  {
    name: "A2A",
    full: "Agent-to-Agent Protocol",
    org: "Google",
    desc: "Multi-agent communication for collaborative workflows across payment and service boundaries.",
    status: "Partial",
  },
  {
    name: "UCP",
    full: "Universal Commerce Protocol",
    org: "Open standard",
    desc: "Structured checkout flows enabling agents to complete purchases at any merchant endpoint. MCP transport is experimental.",
    status: "Experimental",
  },
];

export default function Protocols() {
  return (
    <section className="w-full" style={{ backgroundColor: 'var(--landing-bg)' }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-[100px] md:pt-[140px]">
        {/* Header */}
        <div className="flex flex-col gap-4 mb-10">
          <span
            className="tracking-widest uppercase"
            style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--landing-blue)' }}
          >
            Protocol Native
          </span>
          <h2
            className="max-w-[520px]"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 600,
              fontSize: 'clamp(30px, 4.2vw, 40px)',
              lineHeight: 'clamp(36px, 5vw, 46px)',
              color: 'var(--landing-text-primary)',
            }}
          >
            Built on open standards.
          </h2>
          <p
            className="max-w-[520px] font-light"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '15px',
              lineHeight: '24px',
              color: 'var(--landing-text-tertiary)',
            }}
          >
            Sardis implements and extends the emerging standards for agentic commerce.
            See each protocol's maturity status below.
          </p>
        </div>

        {/* Protocol list */}
        <div className="flex flex-col gap-2">
          {protocols.map((p) => (
            <div
              key={p.name}
              className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6 rounded-[14px] p-6 sm:p-8"
              style={{
                backgroundColor: 'var(--landing-surface)',
                border: '1px solid var(--landing-border)',
              }}
            >
              {/* Protocol name badge */}
              <div className="flex items-center gap-3 sm:w-[140px] shrink-0">
                <span
                  className="text-[18px] font-bold"
                  style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--landing-text-primary)' }}
                >
                  {p.name}
                </span>
                <span
                  className="text-[9px] px-2 py-0.5 rounded-full font-medium tracking-wider"
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    background: p.status === 'Production' ? 'rgba(34,197,94,0.1)' : p.status === 'Pilot' ? 'rgba(59,130,246,0.1)' : 'rgba(161,161,170,0.1)',
                    color: p.status === 'Production' ? '#22C55E' : p.status === 'Pilot' ? '#3B82F6' : '#A1A1AA',
                    border: `1px solid ${p.status === 'Production' ? 'rgba(34,197,94,0.15)' : p.status === 'Pilot' ? 'rgba(59,130,246,0.15)' : 'rgba(161,161,170,0.15)'}`,
                  }}
                >
                  {p.status.toUpperCase()}
                </span>
              </div>

              {/* Description */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="text-[14px] font-medium"
                    style={{ fontFamily: "'Inter', sans-serif", color: 'var(--landing-text-secondary)' }}
                  >
                    {p.full}
                  </span>
                  <span
                    className="text-[11px]"
                    style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--landing-text-muted)' }}
                  >
                    {p.org}
                  </span>
                </div>
                <p
                  className="text-[13px] font-light"
                  style={{ fontFamily: "'Inter', sans-serif", color: 'var(--landing-text-tertiary)' }}
                >
                  {p.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
