const protocols = [
  { name: "AP2", label: "Agent Payment Protocol" },
  { name: "MPP", label: "Model Payment Protocol" },
  { name: "x402", label: "HTTP 402 Payments" },
  { name: "MCP", label: "Model Context Protocol" },
];

export default function PressStrip() {
  return (
    <div className="w-full py-5" style={{ backgroundColor: "var(--landing-bg)" }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20">
        <div className="flex flex-wrap items-center justify-center gap-3 md:gap-6">
          <span
            className="text-[11px] md:text-[12px] font-light tracking-wide uppercase"
            style={{
              fontFamily: "'Inter', system-ui, sans-serif",
              color: "var(--landing-text-ghost)",
            }}
          >
            Integrated with
          </span>
          {protocols.map((p) => (
            <div
              key={p.name}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors duration-200"
              style={{
                border: "1px solid var(--landing-border)",
                color: "var(--landing-text-muted)",
              }}
              title={p.label}
            >
              <span
                className="text-[12px] font-bold"
                style={{ fontFamily: "'Space Grotesk', sans-serif" }}
              >
                {p.name}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
