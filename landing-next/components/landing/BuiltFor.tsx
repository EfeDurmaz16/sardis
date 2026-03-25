export default function BuiltFor() {
  return (
    <section
      className="w-full"
      style={{ backgroundColor: "var(--landing-bg)" }}
    >
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-[100px] md:pt-[140px]">
        <div className="flex flex-col gap-3 mb-12">
          <div className="flex items-center gap-3">
            <span
              className="tracking-widest uppercase"
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "12px",
                color: "var(--landing-blue)",
              }}
            >
              BUILT FOR
            </span>
            <span
              className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5"
              style={{
                backgroundColor: "rgba(0, 82, 255, 0.1)",
                border: "1px solid rgba(0, 82, 255, 0.25)",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "10px",
                color: "#0052FF",
              }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ backgroundColor: "#22C55E" }}
              />
              Live on Tempo
            </span>
          </div>
          <h2
            className="max-w-[520px]"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 600,
              fontSize: "clamp(30px, 4.2vw, 40px)",
              lineHeight: "clamp(36px, 5vw, 46px)",
              color: "var(--landing-text-primary)",
            }}
          >
            Teams building agents that handle real money.
          </h2>
        </div>

        <div className="flex flex-col md:flex-row gap-3 md:min-h-[340px] md:items-stretch">
          {/* Card 1 - Agent commerce */}
          <div
            className="flex flex-col justify-between rounded-[14px] p-6 md:p-8 md:flex-[1.2]"
            style={{
              backgroundColor: "var(--landing-surface)",
              border: "1px solid var(--landing-border)",
            }}
          >
            <div className="flex flex-col gap-3">
              <h3
                style={{
                  fontFamily: "'Space Grotesk', sans-serif",
                  fontWeight: 600,
                  fontSize: "22px",
                  lineHeight: "28px",
                  color: "var(--landing-text-primary)",
                }}
              >
                Agent commerce
              </h3>
              <p
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 300,
                  fontSize: "14px",
                  lineHeight: "24px",
                  color: "var(--landing-text-tertiary)",
                }}
              >
                Your AI agents can autonomously pay vendors, renew
                subscriptions, and handle invoices, all within the bounds of
                your policy.
              </p>
            </div>

            <div className="flex gap-2 flex-wrap mt-6">
              {["invoices", "subscriptions", "vendor pay"].map((tag) => (
                <span
                  key={tag}
                  className="rounded-sm py-1 px-2.5"
                  style={{
                    backgroundColor: "var(--landing-border)",
                    border: "1px solid var(--landing-border)",
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: "11px",
                    color: "var(--landing-text-tertiary)",
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>

          {/* Right column */}
          <div className="flex flex-col gap-3 md:flex-1 min-h-0">
            <div
              className="flex flex-col gap-3 flex-1 rounded-[14px] p-6 md:p-8"
              style={{
                backgroundColor: "var(--landing-surface)",
                border: "1px solid var(--landing-border)",
              }}
            >
              <h3
                style={{
                  fontFamily: "'Space Grotesk', sans-serif",
                  fontWeight: 600,
                  fontSize: "22px",
                  lineHeight: "28px",
                  color: "var(--landing-text-primary)",
                }}
              >
                Treasury automation
              </h3>
              <p
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 300,
                  fontSize: "14px",
                  lineHeight: "24px",
                  color: "var(--landing-text-tertiary)",
                }}
              >
                Automate cross-chain fund flows, payroll, and rebalancing with
                policy-enforced agents that report every move.
              </p>
            </div>

            <div
              className="flex flex-col gap-3 flex-1 rounded-[14px] p-6 md:p-8"
              style={{
                backgroundColor: "var(--landing-surface)",
                border: "1px solid var(--landing-border)",
              }}
            >
              <h3
                style={{
                  fontFamily: "'Space Grotesk', sans-serif",
                  fontWeight: 600,
                  fontSize: "22px",
                  lineHeight: "28px",
                  color: "var(--landing-text-primary)",
                }}
              >
                Financial advisors
              </h3>
              <p
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontWeight: 300,
                  fontSize: "14px",
                  lineHeight: "24px",
                  color: "var(--landing-text-tertiary)",
                }}
              >
                Let advisor agents execute trades, rebalance portfolios, or
                handle client disbursements with a full audit trail.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
