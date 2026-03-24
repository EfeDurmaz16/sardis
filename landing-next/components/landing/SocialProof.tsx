const partners = [
  { name: "Coinbase", text: "Coinbase", viewBox: "0 0 200 40" },
  { name: "Base", text: "Base", viewBox: "0 0 120 40" },
  { name: "Circle", text: "Circle", viewBox: "0 0 130 40" },
  { name: "Stripe", text: "Stripe", viewBox: "0 0 130 40" },
  { name: "Anthropic MCP", text: "Anthropic MCP", viewBox: "0 0 190 40" },
];

export default function SocialProof() {
  return (
    <div
      className="w-full"
      style={{
        borderTop: "1px solid var(--landing-border)",
        borderBottom: "1px solid var(--landing-border)",
      }}
    >
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 py-8">
        <div className="flex flex-wrap items-center justify-center gap-4 md:gap-12">
          <div
            className="text-[12px] md:text-[13px] leading-4 font-light whitespace-nowrap"
            style={{
              fontFamily: "'Inter', system-ui, sans-serif",
              color: "var(--landing-text-muted)",
            }}
          >
            Trusted by teams building on
          </div>
          <div className="flex flex-wrap items-center gap-6 md:gap-10">
            {partners.map((partner) => (
              <div
                key={partner.name}
                className="transition-opacity duration-200 opacity-40 hover:opacity-80"
                style={{ color: "var(--landing-text-secondary)" }}
                role="img"
                aria-label={partner.name}
              >
                <span
                  className="text-[16px] md:text-[18px] font-semibold"
                  style={{ fontFamily: "'Inter', sans-serif" }}
                >
                  {partner.text}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
