const items = [
  'NON-CUSTODIAL',
  'MPC WALLETS',
  'SPENDING POLICIES',
  'MULTI-CHAIN',
  'AUDIT TRAIL',
  'COMPLIANCE',
  'AP2 PROTOCOL',
  '52 MCP TOOLS',
  'CCTP BRIDGES',
];

export default function Marquee() {
  const renderItems = () =>
    items.map((item, i) => (
      <span key={i}>
        <span
          className="text-[14px] md:text-[16px] font-medium uppercase tracking-[0.2em]"
          style={{ fontFamily: "'Space Grotesk', system-ui, sans-serif", color: 'var(--landing-marquee-text)' }}
        >
          {item}
        </span>
        <span
          className="text-[14px] md:text-[16px] font-medium mx-4"
          style={{ fontFamily: "'Space Grotesk', system-ui, sans-serif", color: 'var(--landing-marquee-text)' }}
        >
          ·
        </span>
      </span>
    ));

  return (
    <>
      <style>{`
        @keyframes marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}</style>
      <div
        className="overflow-hidden py-6 md:py-8 group"
        style={{ borderTop: '1px solid var(--landing-border)', borderBottom: '1px solid var(--landing-border)' }}
      >
        <div
          className="flex whitespace-nowrap"
          style={{ animation: 'marquee 30s linear infinite' }}
          onMouseEnter={(e) => (e.currentTarget.style.animationPlayState = 'paused')}
          onMouseLeave={(e) => (e.currentTarget.style.animationPlayState = 'running')}
        >
          {renderItems()}
          {renderItems()}
        </div>
      </div>
    </>
  );
}
