export default function BuiltFor() {
  return (
    <section className="w-full" style={{ backgroundColor: 'var(--landing-bg)' }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-[100px] md:pt-[140px]">
        {/* Header */}
        <div className="flex flex-col gap-3 mb-12">
          <div className="flex items-center gap-3">
            <span
              className="tracking-widest uppercase"
              style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--landing-blue)' }}
            >
              BUILT FOR
            </span>
            <span
              className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5"
              style={{
                backgroundColor: 'rgba(0, 82, 255, 0.1)',
                border: '1px solid rgba(0, 82, 255, 0.25)',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '10px',
                color: '#0052FF',
              }}
            >
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: '#22C55E' }} />
              Live on Base
            </span>
          </div>
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
            Teams building agents that handle real money.
          </h2>
        </div>

        {/* Bento Grid */}
        <div className="flex flex-col md:flex-row gap-3 md:min-h-[340px] md:items-stretch">
          {/* Card 1 - Agent commerce (big left) */}
          <div
            className="flex flex-col justify-between rounded-[14px] p-6 md:p-8 md:flex-[1.2]"
            style={{
              backgroundColor: 'var(--landing-surface)',
              border: '1px solid var(--landing-border)',
            }}
          >
            <div className="flex flex-col gap-3">
              <h3
                style={{
                  fontFamily: "'Space Grotesk', sans-serif",
                  fontWeight: 600,
                  fontSize: '22px',
                  lineHeight: '28px',
                  color: 'var(--landing-text-primary)',
                }}
              >
                Agent commerce
              </h3>
              <p
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 300,
                  fontSize: '14px',
                  lineHeight: '24px',
                  color: 'var(--landing-text-tertiary)',
                }}
              >
                Your AI agents can autonomously pay vendors, renew subscriptions, and handle invoices, all within the bounds of your policy.
              </p>
            </div>
            {/* Visual flow */}
            <div
              className="flex items-center justify-between gap-2 my-6 md:my-0 py-4 px-2"
              style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}
            >
              {[
                { label: 'Agent', color: 'var(--landing-blue)' },
                { label: 'Policy', color: 'var(--landing-text-tertiary)' },
                { label: 'Sign', color: 'var(--landing-text-tertiary)' },
                { label: 'Settle', color: '#22C55E' },
              ].map((step, i) => (
                <div key={step.label} className="contents">
                  <div className="flex flex-col items-center gap-1.5">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center"
                      style={{ border: `1px solid ${step.color}`, color: step.color }}
                    >
                      {i === 0 && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 2a5 5 0 015 5v1a5 5 0 01-10 0V7a5 5 0 015-5zM20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/></svg>}
                      {i === 1 && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>}
                      {i === 2 && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4M10 17l5-5-5-5M13 12H3"/></svg>}
                      {i === 3 && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M20 6L9 17l-5-5"/></svg>}
                    </div>
                    <span style={{ color: step.color }}>{step.label}</span>
                  </div>
                  {i < 3 && (
                    <div className="flex items-center self-center -mt-4">
                      <svg width="20" height="8" viewBox="0 0 20 8" style={{ color: 'var(--landing-text-muted)' }}>
                        <path d="M0 4h16M14 1l3 3-3 3" stroke="currentColor" strokeWidth="1" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Tags */}
            <div className="flex gap-2 flex-wrap">
              {['invoices', 'subscriptions', 'vendor pay'].map((tag) => (
                <span
                  key={tag}
                  className="rounded-sm py-1 px-2.5"
                  style={{
                    backgroundColor: 'var(--landing-border)',
                    border: '1px solid var(--landing-border)',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '11px',
                    color: 'var(--landing-text-tertiary)',
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          {/* Right column */}
          <div className="flex flex-col gap-3 md:flex-1 min-h-0">
            {/* Card 2 - Treasury automation */}
            <div
              className="flex flex-col gap-3 flex-1 rounded-[14px] p-6 md:p-8"
              style={{
                backgroundColor: 'var(--landing-surface)',
                border: '1px solid var(--landing-border)',
              }}
            >
              <h3
                style={{
                  fontFamily: "'Space Grotesk', sans-serif",
                  fontWeight: 600,
                  fontSize: '22px',
                  lineHeight: '28px',
                  color: 'var(--landing-text-primary)',
                }}
              >
                Treasury automation
              </h3>
              <p
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 300,
                  fontSize: '14px',
                  lineHeight: '24px',
                  color: 'var(--landing-text-tertiary)',
                }}
              >
                Automate cross-chain fund flows, payroll, and rebalancing with policy-enforced agents that report every move.
              </p>
            </div>

            {/* Card 3 - Financial advisors */}
            <div
              className="flex flex-col gap-3 flex-1 rounded-[14px] p-6 md:p-8"
              style={{
                backgroundColor: 'var(--landing-surface)',
                border: '1px solid var(--landing-border)',
              }}
            >
              <h3
                style={{
                  fontFamily: "'Space Grotesk', sans-serif",
                  fontWeight: 600,
                  fontSize: '22px',
                  lineHeight: '28px',
                  color: 'var(--landing-text-primary)',
                }}
              >
                Financial advisors
              </h3>
              <p
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 300,
                  fontSize: '14px',
                  lineHeight: '24px',
                  color: 'var(--landing-text-tertiary)',
                }}
              >
                Let advisor agents execute trades, rebalance portfolios, or handle client disbursements with a full audit trail.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
