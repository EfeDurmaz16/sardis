export default function ProblemCards() {
  const cards = [
    {
      icon: (
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <circle cx="14" cy="14" r="10" stroke="#EF4444" strokeWidth="1.2" fill="none" opacity="0.6" />
          <path d="M14 10v5" stroke="#EF4444" strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="14" cy="18.5" r="0.75" fill="#EF4444" />
        </svg>
      ),
      title: "Runaway Spending",
      desc: "An agent stuck in a retry loop made 47,000 API calls in 6 hours. $1,410 burned before anyone noticed.",
      stat: "$1,410",
      statLabel: "burned in 6 hours",
    },
    {
      icon: (
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <circle cx="14" cy="14" r="10" stroke="#EF4444" strokeWidth="1.2" fill="none" opacity="0.6" />
          <path d="M10 10l8 8M18 10l-8 8" stroke="#EF4444" strokeWidth="1.2" strokeLinecap="round" />
        </svg>
      ),
      title: "Blocked at Checkout",
      desc: "Payment rails were built to block non-humans. 2FA, OTPs, CAPTCHAs — your agent hits a wall every time it tries to pay.",
      stat: "100%",
      statLabel: "of agents blocked",
    },
    {
      icon: (
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <circle cx="14" cy="14" r="10" stroke="#EF4444" strokeWidth="1.2" fill="none" opacity="0.6" />
          <path d="M11 14h6M14 11v6" stroke="#EF4444" strokeWidth="1.2" strokeLinecap="round" />
        </svg>
      ),
      title: "No Visibility",
      desc: "73% of teams have no real-time cost tracking for autonomous agents. Cost overruns average 340% above estimates.",
      stat: "340%",
      statLabel: "average cost overrun",
    },
  ];

  return (
    <div className="w-full">
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-[100px] md:pt-[140px]">
        <div className="flex flex-col gap-12">
          {/* Header */}
          <div className="flex flex-col max-w-[560px] gap-3.5">
            <div
              className="text-[12px] leading-[14px] tracking-widest uppercase"
              style={{ fontFamily: "'JetBrains Mono', system-ui, sans-serif", color: '#EF4444' }}
            >
              The Problem
            </div>
            <div
              className="text-[30px] leading-[36px] md:text-[40px] md:leading-[46px] tracking-[-0.03em] font-semibold"
              style={{ fontFamily: "'Space Grotesk', system-ui, sans-serif", color: 'var(--landing-text-primary)' }}
            >
              What happens when agents spend without guardrails.
            </div>
          </div>

          {/* Cards */}
          <div className="flex flex-col md:flex-row gap-3">
            {cards.map((card, i) => (
              <div
                key={i}
                className="flex flex-col w-full md:grow md:shrink md:basis-0 rounded-[14px] gap-3.5 p-8"
                style={{
                  backgroundColor: 'var(--landing-surface)',
                  border: '1px solid var(--landing-border)',
                }}
              >
                <div>{card.icon}</div>
                <div
                  className="text-[18px] leading-[24px] font-semibold"
                  style={{ fontFamily: "'Space Grotesk', system-ui, sans-serif", color: 'var(--landing-text-primary)' }}
                >
                  {card.title}
                </div>
                <div
                  className="text-[14px] leading-6 font-light"
                  style={{ fontFamily: "'Inter', system-ui, sans-serif", color: 'var(--landing-text-tertiary)' }}
                >
                  {card.desc}
                </div>
                <div className="mt-auto pt-3" style={{ borderTop: '1px solid var(--landing-border)' }}>
                  <span
                    className="text-[24px] font-bold"
                    style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#EF4444' }}
                  >
                    {card.stat}
                  </span>
                  <span
                    className="text-[12px] ml-2"
                    style={{ fontFamily: "'Inter', sans-serif", color: 'var(--landing-text-muted)' }}
                  >
                    {card.statLabel}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Terminal horror story */}
          <div
            className="rounded-[14px] p-6 overflow-hidden"
            style={{
              backgroundColor: '#0D0F14',
              border: '1px solid var(--landing-border)',
            }}
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: '#EF4444' }} />
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: '#F59E0B' }} />
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: '#22C55E' }} />
              <span
                className="ml-2 text-[11px]"
                style={{ fontFamily: "'JetBrains Mono', monospace", color: '#505460' }}
              >
                agent-terminal
              </span>
            </div>
            <pre
              className="text-[12px] leading-[20px] overflow-x-auto"
              style={{ fontFamily: "'JetBrains Mono', monospace" }}
            >
              <code>
                <span style={{ color: '#808080' }}>$</span>{' '}
                <span style={{ color: '#A0A0AA' }}>agent plan trip --budget 500</span>{'\n'}
                <span style={{ color: '#22C55E' }}>&gt; Planning itinerary... Done.</span>{'\n'}
                <span style={{ color: '#808080' }}>$</span>{' '}
                <span style={{ color: '#A0A0AA' }}>agent book flights</span>{'\n'}
                <span style={{ color: '#22C55E' }}>&gt; Selecting best flight... UA445 selected.</span>{'\n'}
                <span style={{ color: '#22C55E' }}>&gt; Entering payment details...</span>{'\n'}
                <span style={{ color: '#EF4444' }}>ERROR: 2FA Required. Please enter the code sent to +1 (555) ***-****</span>{'\n'}
                <span style={{ color: '#EF4444' }}>&gt; Timeout. Booking failed.</span>{'\n'}
                <span style={{ color: '#EF4444', fontWeight: 600 }}>EXECUTION BLOCKED</span>
              </code>
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
