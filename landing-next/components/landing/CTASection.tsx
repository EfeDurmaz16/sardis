export default function CTASection() {
  return (
    <section style={{ backgroundColor: "var(--landing-bg)" }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-[120px] md:pt-40 pb-16 md:pb-20 flex flex-col items-center justify-center text-center gap-6">
        <h2
          className="text-[36px] md:text-[48px] tracking-[-0.04em] leading-tight font-bold"
          style={{
            fontFamily: "'Space Grotesk', system-ui, sans-serif",
            color: "var(--landing-text-primary)",
          }}
        >
          Give your agents a wallet.
        </h2>

        <p
          className="text-[16px] leading-[26px] font-light"
          style={{
            fontFamily: "'Inter', sans-serif",
            color: "var(--landing-text-tertiary)",
          }}
        >
          Start building for free. No credit card required.
        </p>

        <div className="pt-3 flex flex-col sm:flex-row gap-3">
          <a
            href="https://dashboard.sardis.sh/signup"
            className="text-white rounded-lg py-3.5 px-9 transition-colors text-center inline-block hover:opacity-90"
            style={{ backgroundColor: "var(--landing-accent)" }}
          >
            <span
              className="text-[15px] font-medium"
              style={{ fontFamily: "'Inter', sans-serif" }}
            >
              Get Started Free
            </span>
          </a>
          <a
            href="mailto:contact@sardis.sh"
            className="rounded-lg py-3.5 px-9 transition-colors text-center inline-block hover:border-[var(--landing-text-muted)] hover:text-[var(--landing-text-primary)]"
            style={{
              border: "1px solid var(--landing-border)",
              color: "var(--landing-text-secondary)",
            }}
          >
            <span
              className="text-[15px] font-medium"
              style={{ fontFamily: "'Inter', sans-serif" }}
            >
              Book a Demo &rarr;
            </span>
          </a>
        </div>
      </div>
    </section>
  );
}
