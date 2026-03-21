interface EnvironmentBadgeProps {
  environment: 'test' | 'live';
}

export function EnvironmentBadge({ environment }: EnvironmentBadgeProps) {
  const isLive = environment === 'live';
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        fontSize: '0.7rem',
        fontWeight: 600,
        padding: '3px 10px',
        borderRadius: '100px',
        letterSpacing: '0.05em',
        background: isLive ? 'var(--success-dim)' : 'var(--warning-dim)',
        color: isLive ? 'var(--success)' : 'var(--warning)',
      }}
    >
      <span
        style={{
          width: '5px',
          height: '5px',
          borderRadius: '50%',
          background: isLive ? 'var(--success)' : 'var(--warning)',
        }}
      />
      {isLive ? 'MAINNET' : 'TESTNET'}
    </span>
  );
}
