export default function PressStrip() {
  const protocols = [
    {
      name: 'AP2',
      label: 'Agent Payment Protocol',
      svg: (
        <svg viewBox="0 0 32 32" className="w-6 h-6" fill="none">
          <rect width="32" height="32" rx="6" stroke="currentColor" strokeWidth="1.5" fill="none" />
          <text x="6" y="22" fill="currentColor" fontSize="13" fontWeight="700" fontFamily="'Space Grotesk', sans-serif">AP2</text>
        </svg>
      ),
    },
    {
      name: 'MPP',
      label: 'Model Payment Protocol',
      svg: (
        <svg viewBox="0 0 32 32" className="w-6 h-6" fill="none">
          <rect width="32" height="32" rx="6" stroke="currentColor" strokeWidth="1.5" fill="none" />
          <text x="2" y="22" fill="currentColor" fontSize="11" fontWeight="700" fontFamily="'Space Grotesk', sans-serif">MPP</text>
        </svg>
      ),
    },
    {
      name: 'x402',
      label: 'HTTP 402 Payments',
      svg: (
        <svg viewBox="0 0 32 32" className="w-6 h-6" fill="none">
          <rect width="32" height="32" rx="6" stroke="currentColor" strokeWidth="1.5" fill="none" />
          <text x="3" y="22" fill="currentColor" fontSize="10" fontWeight="700" fontFamily="'JetBrains Mono', monospace">402</text>
        </svg>
      ),
    },
    {
      name: 'MCP',
      label: 'Model Context Protocol',
      svg: (
        <svg viewBox="0 0 32 32" className="w-6 h-6" fill="none">
          <rect width="32" height="32" rx="6" stroke="currentColor" strokeWidth="1.5" fill="none" />
          <text x="2" y="22" fill="currentColor" fontSize="11" fontWeight="700" fontFamily="'Space Grotesk', sans-serif">MCP</text>
        </svg>
      ),
    },
  ];

  return (
    <div
      className="w-full py-5"
      style={{ backgroundColor: 'var(--landing-bg)' }}
    >
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20">
        <div className="flex flex-wrap items-center justify-center gap-3 md:gap-6">
          <span
            className="text-[11px] md:text-[12px] font-light tracking-wide uppercase"
            style={{ fontFamily: "'Inter', system-ui, sans-serif", color: 'var(--landing-text-ghost)' }}
          >
            Integrated with
          </span>
          {protocols.map((p) => (
            <div
              key={p.name}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors duration-200"
              style={{
                border: '1px solid var(--landing-border)',
                color: 'var(--landing-text-muted)',
              }}
              title={p.label}
            >
              {p.svg}
              <span
                className="text-[12px] font-medium hidden sm:inline"
                style={{ fontFamily: "'Inter', sans-serif" }}
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
