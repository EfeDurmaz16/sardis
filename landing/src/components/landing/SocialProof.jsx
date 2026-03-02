export default function SocialProof() {
  const chains = ["Ethereum", "Base", "Polygon", "Arbitrum", "Optimism", "Arc"];

  return (
    <div className="w-full" style={{ borderTop: '1px solid var(--landing-border)', borderBottom: '1px solid var(--landing-border)' }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 py-8">
        <div className="flex flex-wrap items-center justify-center gap-4 md:gap-12">
          <div
            className="text-[12px] md:text-[13px] leading-4 font-light whitespace-nowrap"
            style={{ fontFamily: "'Inter', system-ui, sans-serif", color: 'var(--landing-text-muted)' }}
          >
            Built for teams on
          </div>
          <div className="flex flex-wrap items-center gap-4 md:gap-8">
            {chains.map((chain) => (
              <div
                key={chain}
                className="text-[13px] md:text-[14px] leading-[18px] font-medium"
                style={{ fontFamily: "'Space Grotesk', system-ui, sans-serif", color: 'var(--landing-text-ghost)' }}
              >
                {chain}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
