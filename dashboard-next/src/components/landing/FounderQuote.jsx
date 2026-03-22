export default function FounderQuote() {
  return (
    <section className="w-full" style={{ backgroundColor: 'var(--landing-bg)' }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-[100px] md:pt-[140px]">
        <div
          className="rounded-[14px] p-10 md:p-14 flex flex-col items-center text-center"
          style={{
            backgroundColor: 'var(--landing-surface)',
            border: '1px solid var(--landing-border)',
          }}
        >
          {/* Quote mark */}
          <svg width="40" height="32" viewBox="0 0 40 32" fill="none" className="mb-6" style={{ opacity: 0.15 }}>
            <path
              d="M0 20.8C0 12.267 5.333 5.333 16 0l2.133 4.267C12.267 7.467 9.6 11.733 9.067 16H16v16H0V20.8zM24 20.8C24 12.267 29.333 5.333 40 0l2.133 4.267C36.267 7.467 33.6 11.733 33.067 16H40v16H24V20.8z"
              fill="var(--landing-text-primary)"
            />
          </svg>

          <blockquote
            className="max-w-[640px] mb-8"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 'clamp(17px, 2.2vw, 22px)',
              lineHeight: 'clamp(28px, 3.2vw, 36px)',
              fontWeight: 300,
              color: 'var(--landing-text-secondary)',
              fontStyle: 'italic',
            }}
          >
            I hit this wall myself while building AI agents for the past 18 months.
            I'm building Sardis to solve the execution gap I faced as an engineer.
          </blockquote>

          <div className="flex flex-col items-center gap-1">
            <span
              className="text-[15px] font-medium"
              style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--landing-text-primary)' }}
            >
              Efe Baran Durmaz
            </span>
            <span
              className="text-[12px]"
              style={{ fontFamily: "'Inter', sans-serif", color: 'var(--landing-text-muted)' }}
            >
              Founder & AI Architect
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
