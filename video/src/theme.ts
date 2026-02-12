// Sardis Brand Design System — matches dashboard + landing page exactly
// Colors from dashboard/src/index.css and landing/src/index.css
export const colors = {
  bg: '#0f0e0c',
  surface: '#141312',
  cardBg: '#1f1e1c',
  border: '#2f2e2c',
  borderHover: '#3f3e3c',
  orange: '#ff4f00',
  orangeLight: '#ff7a3d',
  orangeGlow: 'rgba(255, 79, 0, 0.4)',
  orangeSubtle: 'rgba(255, 79, 0, 0.08)',
  orangeBg: 'rgba(255, 79, 0, 0.1)',
  green: '#10b981',
  greenGlow: 'rgba(16, 185, 129, 0.3)',
  greenBg: 'rgba(16, 185, 129, 0.1)',
  red: '#ef4444',
  redGlow: 'rgba(239, 68, 68, 0.3)',
  redBg: 'rgba(239, 68, 68, 0.1)',
  yellow: '#f59e0b',
  yellowBg: 'rgba(245, 158, 11, 0.1)',
  blue: '#3b82f6',
  blueBg: 'rgba(59, 130, 246, 0.1)',
  purple: '#8b5cf6',
  white: '#ffffff',
  textPrimary: '#f2f0e9',
  textSecondary: '#94a3b8',
  textMuted: '#64748b',
  base: '#0052FF',
  polygon: '#8247E5',
  arbitrum: '#28A0F0',
  optimism: '#FF0420',
  ethereum: '#627EEA',
} as const;

// Fonts: Cabinet Grotesk ≈ Space Grotesk, Satoshi ≈ Inter, Geist Mono ≈ JetBrains Mono
export const fonts = {
  display: "'Space Grotesk', 'Cabinet Grotesk', system-ui, sans-serif",
  body: "'Inter', 'Satoshi', system-ui, sans-serif",
  mono: "'JetBrains Mono', 'Geist Mono', monospace",
} as const;

export const FPS = 60;
