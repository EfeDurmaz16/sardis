const steps = [
  {
    num: '01',
    title: 'Write a spending policy',
    desc: 'Define what your agent can spend, where, and how much. Plain English or code. Sardis enforces it automatically.',
  },
  {
    num: '02',
    title: 'Connect your agent',
    desc: 'Five lines of Python or TypeScript. Your agent gets a wallet, a policy, and the ability to make real payments.',
  },
  {
    num: '03',
    title: 'Watch every transaction',
    desc: 'Every payment is logged, verified, and auditable. You stay in control while your agents move fast.',
  },
];

export default function HowItWorks() {
  return (
    <section className="w-full" style={{ backgroundColor: 'var(--landing-bg)' }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-[100px] md:pt-[140px]">
        {/* Header */}
        <div className="flex flex-col gap-4 mb-14">
          <span
            className="tracking-widest uppercase"
            style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--landing-blue)' }}
          >
            HOW IT WORKS
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
            Set the rules. Let agents pay.
          </h2>
        </div>

        {/* Steps */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {steps.map((step) => (
            <div
              key={step.num}
              className="flex flex-col gap-4 rounded-[14px] p-8"
              style={{
                backgroundColor: 'var(--landing-surface)',
                border: '1px solid var(--landing-border)',
              }}
            >
              <span
                style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '13px', color: 'var(--landing-blue)' }}
              >
                {step.num}
              </span>
              <h3
                style={{
                  fontFamily: "'Space Grotesk', sans-serif",
                  fontWeight: 600,
                  fontSize: '20px',
                  lineHeight: '26px',
                  color: 'var(--landing-text-primary)',
                }}
              >
                {step.title}
              </h3>
              <p
                className="font-light"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: '14px',
                  lineHeight: '24px',
                  color: 'var(--landing-text-tertiary)',
                }}
              >
                {step.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
