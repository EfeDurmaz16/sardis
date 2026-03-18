const stats = [
  { number: '50K+', label: 'SDK Installs', meta: '50,000+ downloads on PyPI and npm' },
  { number: '52', label: 'MCP Tools', meta: '52 tools for Claude Desktop integration' },
  { number: '12', label: 'Policy Checks', meta: '12-check enforcement pipeline on every transaction' },
  { number: '6', label: 'Chains Supported', meta: 'Base, Ethereum, Polygon, Arbitrum, Optimism, and more' },
];

export default function StatsSection() {
  return (
    <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 py-20 md:py-28 flex flex-col items-center gap-0">
      <div className="max-w-7xl w-full h-px" style={{ backgroundColor: 'var(--landing-border)' }} />
      <div className="w-full max-w-7xl py-20 md:py-28">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-4">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center" title={stat.meta}>
              <div
                className="text-[48px] md:text-[56px] leading-tight font-bold tracking-[-0.04em]"
                style={{ fontFamily: "'Space Grotesk', system-ui, sans-serif", color: 'var(--landing-text-primary)' }}
                aria-label={stat.meta}
              >
                {stat.number}
              </div>
              <div
                className="text-[13px] leading-[18px] mt-2"
                style={{ fontFamily: "'Inter', system-ui, sans-serif", color: 'var(--landing-text-muted)' }}
              >
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="max-w-7xl w-full h-px" style={{ backgroundColor: 'var(--landing-border)' }} />
    </div>
  );
}
