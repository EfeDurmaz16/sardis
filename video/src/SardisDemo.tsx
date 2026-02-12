import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import React from 'react';
import { colors, fonts, FPS } from './theme';

// ─── HELPERS ────────────────────────────────────────────────────────

const cl = {
  extrapolateLeft: 'clamp' as const,
  extrapolateRight: 'clamp' as const,
};

const fi = (f: number, start: number, dur = 30) =>
  interpolate(f, [start, start + dur], [0, 1], cl);

const su = (f: number, start: number, dur = 30, d = 20) =>
  interpolate(f, [start, start + dur], [d, 0], cl);

const ctr: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
};

// ─── SYNTAX TOKENS ──────────────────────────────────────────────────

const syn = {
  kw: '#ff4f00',
  str: '#10b981',
  fn: '#f59e0b',
  cls: '#ff7a3d',
  nm: '#f2f0e9',
  num: '#3b82f6',
  op: '#94a3b8',
};

type Tk = { t: string; c: string };
const K = (s: string): Tk => ({ t: s, c: syn.kw });
const ST = (s: string): Tk => ({ t: s, c: syn.str });
const N = (s: string): Tk => ({ t: s, c: syn.nm });
const FN = (s: string): Tk => ({ t: s, c: syn.fn });
const CLS = (s: string): Tk => ({ t: s, c: syn.cls });
const NU = (s: string): Tk => ({ t: s, c: syn.num });
const O = (s: string): Tk => ({ t: s, c: syn.op });

const renderTk = (tks: Tk[]) =>
  tks.map((tk, i) => (
    <span key={i} style={{ color: tk.c }}>
      {tk.t}
    </span>
  ));

const Blink: React.FC<{ frame: number; color?: string }> = ({
  frame,
  color = colors.orange,
}) => (
  <span style={{ color, opacity: Math.sin(frame * 0.15) > 0 ? 1 : 0.15 }}>
    _
  </span>
);

// ─── SVG ICONS ──────────────────────────────────────────────────────

type IP = { s?: number; c?: string };

const ShieldIcon = ({ s = 18, c = colors.orange }: IP) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="square">
    <path d="M12 3L4 7v5c0 5 3.5 8.5 8 10 4.5-1.5 8-5 8-10V7z" />
  </svg>
);

const UsersIcon = ({ s = 18, c = colors.orange }: IP) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="square">
    <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
  </svg>
);

const DollarIcon = ({ s = 18, c = colors.orange }: IP) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="square">
    <line x1="12" y1="1" x2="12" y2="23" />
    <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
  </svg>
);

const ActivityIcon = ({ s = 18, c = colors.orange }: IP) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="square">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
);

const GlobeIcon = ({ s = 18, c = colors.orange }: IP) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="square">
    <circle cx="12" cy="12" r="10" />
    <line x1="2" y1="12" x2="22" y2="12" />
    <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
  </svg>
);

const CheckIcon = ({ s = 18, c = colors.green }: IP) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2.5" strokeLinecap="square">
    <polyline points="4 12 9 17 20 6" />
  </svg>
);

const XIcon = ({ s = 18, c = colors.red }: IP) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2.5" strokeLinecap="square">
    <line x1="6" y1="6" x2="18" y2="18" />
    <line x1="18" y1="6" x2="6" y2="18" />
  </svg>
);

const ZapIcon = ({ s = 18, c = colors.yellow }: IP) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill={c} stroke="none">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10" />
  </svg>
);

const CardIcon = ({ s = 18, c = colors.orange }: IP) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="square">
    <rect x="1" y="4" width="22" height="16" />
    <line x1="1" y1="10" x2="23" y2="10" />
  </svg>
);

const BellIcon = ({ s = 18, c = colors.yellow }: IP) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="square">
    <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
    <path d="M13.73 21a2 2 0 01-3.46 0" />
  </svg>
);

const AlertIcon = ({ s = 18, c = colors.yellow }: IP) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="square">
    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

// ─── SARDIS LOGO ────────────────────────────────────────────────────

const SardisLogo: React.FC<{
  size?: number;
  color?: string;
  scale?: number;
}> = ({ size = 40, color = colors.orange, scale = 1 }) => (
  <svg
    viewBox="0 0 100 100"
    width={size}
    height={size}
    style={{ transform: `scale(${scale})` }}
  >
    <path d="M35 25 H25 V75 H35" stroke={color} strokeWidth="10" fill="none" strokeLinecap="square" />
    <path d="M65 25 H75 V75 H65" stroke={color} strokeWidth="10" fill="none" strokeLinecap="square" />
    <rect x="40" y="40" width="20" height="20" fill={color} />
  </svg>
);

// ─── SHARED UI ──────────────────────────────────────────────────────

const GridBg: React.FC = () => (
  <div
    style={{
      position: 'absolute',
      inset: 0,
      backgroundImage: `linear-gradient(rgba(255,79,0,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,79,0,0.02) 1px, transparent 1px)`,
      backgroundSize: '48px 48px',
    }}
  />
);

const Badge: React.FC<{ label: string; color: string; glow?: string }> = ({
  label,
  color,
  glow,
}) => (
  <div
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      padding: '6px 16px',
      border: `1px solid ${color}`,
      backgroundColor: `${color}15`,
      fontFamily: fonts.mono,
      fontSize: 13,
      fontWeight: 600,
      color,
      letterSpacing: '0.08em',
      boxShadow: glow ? `0 0 20px ${glow}` : 'none',
    }}
  >
    <div style={{ width: 6, height: 6, backgroundColor: color, boxShadow: `0 0 6px ${color}` }} />
    {label}
  </div>
);

// ─── VS CODE THEME ──────────────────────────────────────────────────

const vsc = {
  bg: '#1a1918',
  titleBar: '#141312',
  tab: '#141312',
  tabActive: '#1a1918',
  terminal: '#0f0e0c',
  lineNum: '#4a4a4a',
  border: '#2a2928',
};

// ─── CODE EDITOR COMPONENT ──────────────────────────────────────────

const CodeEditor: React.FC<{
  title: string;
  tab: string;
  lines: { tks: Tk[]; at: number }[];
  term: { text: string; color: string; at: number }[];
  frame: number;
}> = ({ title, tab, lines, term, frame }) => (
  <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: vsc.bg, fontFamily: fonts.mono }}>
    {/* Title bar */}
    <div style={{ height: 36, backgroundColor: vsc.titleBar, borderBottom: `1px solid ${vsc.border}`, display: 'flex', alignItems: 'center', padding: '0 14px', gap: 8 }}>
      <div style={{ display: 'flex', gap: 6 }}>
        <div style={{ width: 10, height: 10, backgroundColor: '#ff5f57' }} />
        <div style={{ width: 10, height: 10, backgroundColor: '#ffbd2e' }} />
        <div style={{ width: 10, height: 10, backgroundColor: '#28c840' }} />
      </div>
      <span style={{ flex: 1, textAlign: 'center', fontSize: 12, color: vsc.lineNum }}>{title}</span>
    </div>

    {/* Tab bar */}
    <div style={{ height: 36, backgroundColor: vsc.tab, borderBottom: `1px solid ${vsc.border}`, display: 'flex', alignItems: 'stretch' }}>
      <div style={{ padding: '0 16px', display: 'flex', alignItems: 'center', backgroundColor: vsc.tabActive, borderTop: `2px solid ${colors.orange}`, borderRight: `1px solid ${vsc.border}` }}>
        <span style={{ fontSize: 12, color: colors.textPrimary }}>{tab}</span>
      </div>
    </div>

    {/* Editor */}
    <div style={{ flex: 1, overflow: 'hidden', padding: '12px 0' }}>
      {lines.map((line, i) => (
        <div key={i} style={{ display: 'flex', height: 24, alignItems: 'center', opacity: fi(frame, line.at, 18), transform: `translateX(${su(frame, line.at, 18, 8)}px)` }}>
          <div style={{ width: 48, textAlign: 'right', paddingRight: 16, fontSize: 13, color: vsc.lineNum }}>{i + 1}</div>
          <div style={{ fontSize: 15, lineHeight: '24px' }}>
            {line.tks.length > 0 ? renderTk(line.tks) : '\u00A0'}
          </div>
        </div>
      ))}
    </div>

    {/* Terminal */}
    <div style={{ borderTop: `1px solid ${vsc.border}`, backgroundColor: vsc.terminal, minHeight: 200 }}>
      <div style={{ height: 28, borderBottom: `1px solid ${vsc.border}`, display: 'flex', alignItems: 'center', padding: '0 12px' }}>
        <span style={{ fontSize: 11, color: colors.textSecondary, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Terminal</span>
      </div>
      <div style={{ padding: '8px 16px' }}>
        {term.map((l, i) => (
          <div key={i} style={{ fontSize: 13, lineHeight: 1.8, color: l.color, opacity: fi(frame, l.at, 12) }}>
            {l.text || '\u00A0'}
          </div>
        ))}
      </div>
    </div>
  </div>
);

// ─── MCP CHAT COMPONENT ────────────────────────────────────────────

type ChatMsg = {
  role: 'user' | 'assistant' | 'tool_call' | 'tool_result' | 'tool_error';
  content: React.ReactNode;
  at: number;
};

const MCPChat: React.FC<{ messages: ChatMsg[]; frame: number }> = ({ messages, frame }) => (
  <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: vsc.bg }}>
    {/* Title bar */}
    <div style={{ height: 36, backgroundColor: vsc.titleBar, borderBottom: `1px solid ${vsc.border}`, display: 'flex', alignItems: 'center', padding: '0 14px', gap: 8 }}>
      <div style={{ display: 'flex', gap: 6 }}>
        <div style={{ width: 10, height: 10, backgroundColor: '#ff5f57' }} />
        <div style={{ width: 10, height: 10, backgroundColor: '#ffbd2e' }} />
        <div style={{ width: 10, height: 10, backgroundColor: '#28c840' }} />
      </div>
      <span style={{ flex: 1, textAlign: 'center', fontSize: 12, color: vsc.lineNum, fontFamily: fonts.mono }}>AI Agent Terminal</span>
    </div>

    {/* MCP badge */}
    <div style={{ padding: '8px 14px', borderBottom: `1px solid ${vsc.border}`, display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 6, height: 6, backgroundColor: colors.green, boxShadow: `0 0 4px ${colors.green}` }} />
      <span style={{ fontSize: 11, color: colors.textSecondary, fontFamily: fonts.mono }}>sardis-mcp-server connected</span>
    </div>

    {/* Messages */}
    <div style={{ flex: 1, padding: '16px 20px', overflow: 'hidden' }}>
      {messages.map((msg, i) => {
        const op = fi(frame, msg.at, 25);
        const y = su(frame, msg.at, 25, 10);

        if (msg.role === 'user') {
          return (
            <div key={i} style={{ opacity: op, transform: `translateY(${y}px)`, display: 'flex', justifyContent: 'flex-end', marginBottom: 14 }}>
              <div style={{ maxWidth: '85%', padding: '10px 14px', backgroundColor: colors.orangeSubtle, border: `1px solid rgba(255,79,0,0.2)`, fontSize: 13, color: colors.textPrimary, fontFamily: fonts.body, lineHeight: 1.5 }}>
                {msg.content}
              </div>
            </div>
          );
        }

        if (msg.role === 'assistant') {
          return (
            <div key={i} style={{ opacity: op, transform: `translateY(${y}px)`, marginBottom: 14 }}>
              <div style={{ maxWidth: '90%', fontSize: 13, color: colors.textSecondary, fontFamily: fonts.body, lineHeight: 1.5 }}>
                {msg.content}
              </div>
            </div>
          );
        }

        if (msg.role === 'tool_call') {
          return (
            <div key={i} style={{ opacity: op, transform: `translateY(${y}px)`, marginBottom: 14, padding: '12px 14px', border: `1px solid ${colors.border}`, backgroundColor: colors.cardBg, fontFamily: fonts.mono, fontSize: 12 }}>
              <div style={{ fontSize: 11, color: colors.orange, fontWeight: 600, marginBottom: 8, letterSpacing: '0.05em' }}>
                sardis.pay
              </div>
              {msg.content}
            </div>
          );
        }

        if (msg.role === 'tool_result') {
          return (
            <div key={i} style={{ opacity: op, transform: `translateY(${y}px)`, marginBottom: 14, padding: '12px 14px', border: `1px solid ${colors.green}`, backgroundColor: colors.greenBg, fontFamily: fonts.mono, fontSize: 12 }}>
              {msg.content}
            </div>
          );
        }

        // tool_error
        return (
          <div key={i} style={{ opacity: op, transform: `translateY(${y}px)`, marginBottom: 14, padding: '12px 14px', border: `1px solid ${colors.red}`, backgroundColor: colors.redBg, fontFamily: fonts.mono, fontSize: 12 }}>
            {msg.content}
          </div>
        );
      })}
    </div>
  </div>
);

// ─── DASHBOARD PANEL (right side of split) ──────────────────────────

type TxEntry = {
  agent: string;
  merchant: string;
  amount: string;
  rail: string;
  railColor: string;
  status?: 'ok' | 'blocked' | 'approved';
  isNew?: boolean;
  at: number;
};

const DashPanel: React.FC<{
  frame: number;
  stats: { label: string; value: string; at: number }[];
  txs: TxEntry[];
  children?: React.ReactNode;
}> = ({ frame, stats, txs, children }) => (
  <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: colors.bg }}>
    {/* Header */}
    <div style={{ padding: '14px 20px', borderBottom: `1px solid ${colors.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', opacity: fi(frame, 20, 20) }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <SardisLogo size={20} />
        <span style={{ fontSize: 15, fontWeight: 700, fontFamily: fonts.display, color: colors.textPrimary }}>Dashboard</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '2px 8px', border: `1px solid ${colors.border}`, backgroundColor: colors.cardBg }}>
        <div style={{ width: 5, height: 5, backgroundColor: colors.green, boxShadow: `0 0 4px ${colors.green}` }} />
        <span style={{ fontSize: 10, color: colors.textMuted, fontFamily: fonts.mono }}>Live</span>
      </div>
    </div>

    {/* Stats */}
    <div style={{ display: 'flex', gap: 10, padding: '14px 20px' }}>
      {stats.map((s, i) => (
        <div key={i} style={{ flex: 1, padding: 12, backgroundColor: colors.cardBg, border: `1px solid ${colors.border}`, opacity: fi(frame, s.at, 20), transform: `translateY(${su(frame, s.at, 20, 10)}px)` }}>
          <div style={{ fontSize: 10, color: colors.textMuted, fontFamily: fonts.mono, marginBottom: 4 }}>{s.label}</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: colors.textPrimary, fontFamily: fonts.mono }}>{s.value}</div>
        </div>
      ))}
    </div>

    {/* Live Feed */}
    <div style={{ flex: 1, padding: '0 20px 14px' }}>
      <div style={{ padding: 14, backgroundColor: colors.cardBg, border: `1px solid ${colors.border}`, height: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: colors.white, fontFamily: fonts.body }}>Live Transaction Feed</span>
          <span style={{ fontSize: 9, color: colors.textMuted, fontFamily: fonts.mono }}>Real-time</span>
        </div>
        {txs.map((tx, i) => {
          const isBlocked = tx.status === 'blocked';
          const isApproved = tx.status === 'approved';
          return (
            <div key={i} style={{
              opacity: fi(frame, tx.at, 20),
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '7px 10px', marginBottom: 3,
              backgroundColor: isBlocked ? colors.redBg : (tx.isNew && frame > tx.at + 30) ? 'rgba(255,79,0,0.06)' : 'rgba(255,255,255,0.02)',
              border: isBlocked ? `1px solid rgba(239,68,68,0.3)` : (tx.isNew && frame > tx.at + 30) ? `1px solid rgba(255,79,0,0.2)` : '1px solid transparent',
            }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 500, color: isBlocked ? colors.red : colors.white, fontFamily: fonts.mono }}>{tx.agent}</div>
                <div style={{ fontSize: 9, color: colors.textMuted, fontFamily: fonts.mono }}>→ {tx.merchant}</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{
                  fontSize: 9, padding: '1px 5px',
                  backgroundColor: isBlocked ? colors.redBg : `${tx.railColor}15`,
                  color: isBlocked ? colors.red : tx.railColor,
                  fontFamily: fonts.mono, fontWeight: 600,
                }}>{isBlocked ? 'BLOCKED' : tx.rail}</span>
                <span style={{ fontSize: 11, fontWeight: 500, color: isBlocked ? colors.red : (isApproved ? colors.green : colors.orange), fontFamily: fonts.mono }}>{tx.amount}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>

    {/* Optional overlay content (notifications, rail labels) */}
    {children}
  </div>
);

// ─── SPLIT LAYOUT ───────────────────────────────────────────────────

const SplitLayout: React.FC<{
  left: React.ReactNode;
  right: React.ReactNode;
  frame: number;
}> = ({ left, right, frame }) => (
  <AbsoluteFill style={{ display: 'flex', flexDirection: 'row', opacity: fi(frame, 0, 15) }}>
    <div style={{ width: '55%', height: '100%', borderRight: `1px solid ${colors.border}` }}>{left}</div>
    <div style={{ width: '45%', height: '100%' }}>{right}</div>
  </AbsoluteFill>
);

// ─── SCENE 1: HOOK (0-4s, 240f) ────────────────────────────────────

const HookScene: React.FC = () => {
  const frame = useCurrentFrame();
  const line1Op = fi(frame, 20, 30);
  const line1Y = su(frame, 20, 30);
  const line2Op = fi(frame, 80, 30);
  const line2Y = su(frame, 80, 30);
  const fadeOut = interpolate(frame, [180, 230], [1, 0], cl);
  const glitch = frame > 80 && frame < 180 ? Math.sin(frame * 0.7) * 2 : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, ...ctr, opacity: fadeOut }}>
      <GridBg />
      <h1 style={{ fontSize: 68, fontWeight: 700, color: colors.textPrimary, fontFamily: fonts.display, textAlign: 'center', opacity: line1Op, transform: `translateY(${line1Y}px)` }}>
        AI agents can reason.
      </h1>
      <h1 style={{
        fontSize: 68, fontWeight: 700, color: colors.red, fontFamily: fonts.display, textAlign: 'center', marginTop: 12,
        opacity: line2Op, transform: `translateY(${line2Y}px) translateX(${glitch}px)`,
        textShadow: frame % 12 < 3 && frame > 80 ? `2px 0 ${colors.red}, -2px 0 ${colors.orange}` : 'none',
      }}>
        They can't be trusted with money.
      </h1>
    </AbsoluteFill>
  );
};

// ─── SCENE 2: SETUP + STABLECOIN (4-22s, 1080f) ────────────────────

const SetupScene: React.FC = () => {
  const frame = useCurrentFrame();

  const codeLines: { tks: Tk[]; at: number }[] = [
    { tks: [K('from'), N(' sardis '), K('import'), N(' '), CLS('Agent'), O(', '), CLS('Policy')], at: 60 },
    { tks: [], at: 60 },
    { tks: [N('agent'), O(' = '), CLS('Agent'), O('('), ST('"procurement-bot"'), O(')')], at: 120 },
    { tks: [N('wallet'), O(' = '), N('agent'), O('.'), FN('create_wallet'), O('('), ST('"USDC"'), O(', '), N('chain'), O('='), ST('"base"'), O(')')], at: 170 },
    { tks: [], at: 200 },
    { tks: [O('# Fund via bank ACH \u2192 USDC on-ramp (Bridge)')], at: 230 },
    { tks: [N('wallet'), O('.'), FN('deposit'), O('('), NU('1000'), O(', '), N('via'), O('='), ST('"bank_ach"'), O(')')], at: 260 },
    { tks: [], at: 290 },
    { tks: [N('policy'), O(' = '), CLS('Policy'), O('(')], at: 320 },
    { tks: [N('    allowed'), O('=['), ST('"openai:*"'), O(', '), ST('"aws:*"'), O('],')], at: 350 },
    { tks: [N('    max_per_tx'), O('='), NU('500'), O(', '), N('approval_above'), O('='), NU('200')], at: 375 },
    { tks: [O(')')], at: 395 },
    { tks: [N('agent'), O('.'), FN('set_policy'), O('('), N('policy'), O(')')], at: 420 },
  ];

  const termLines = [
    { text: '~/sardis $ python setup_agent.py', color: colors.orange, at: 460 },
    { text: '\u2713 Agent created: procurement-bot', color: colors.green, at: 490 },
    { text: '[On-Ramp] ACH \u2192 USDC via Bridge: $1,000.00', color: colors.blue, at: 520 },
    { text: '\u2713 Wallet funded: 1,000 USDC on Base', color: colors.green, at: 550 },
    { text: '\u2713 Policy attached: 2 rules compiled', color: colors.green, at: 575 },
    { text: '', color: colors.textMuted, at: 600 },
    { text: '~/sardis $ sardis pay openai:api 29.99 --purpose "GPT-5.2 API"', color: colors.orange, at: 640 },
    { text: '[TAP] \u2713 Agent identity verified (Ed25519)', color: colors.textMuted, at: 680 },
    { text: '[AP2] \u2713 Mandate chain: Intent \u2192 Cart \u2192 Payment', color: colors.textMuted, at: 710 },
    { text: '[Policy] \u2713 amount $29.99 \u2264 $500 | destination: allowed', color: colors.textSecondary, at: 740 },
    { text: '[Settle] USDC on Base \u2192 0x8a2f...c91e', color: colors.blue, at: 780 },
    { text: '\u2713 Payment confirmed \u2014 $29.99 (2 confirmations)', color: colors.green, at: 820 },
  ];

  const dashStats = [
    { label: 'Volume (24h)', value: '$2,450', at: 60 },
    { label: 'Transactions', value: '47', at: 80 },
    { label: 'Agents', value: '3 online', at: 100 },
  ];

  const dashTxs: TxEntry[] = [
    { agent: 'compute_agent', merchant: 'Lambda GPU', amount: '$45.00', rail: 'USDC', railColor: colors.blue, at: 100 },
    { agent: 'data_buyer', merchant: 'Weather API', amount: '$8.00', rail: 'USDC', railColor: colors.blue, at: 140 },
    { agent: 'procurement-bot', merchant: 'openai:api', amount: '$29.99', rail: 'USDC', railColor: colors.blue, isNew: true, at: 800 },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <SplitLayout
        frame={frame}
        left={
          <CodeEditor
            title="setup_agent.py — sardis-demo"
            tab="setup_agent.py"
            lines={codeLines}
            term={termLines}
            frame={frame}
          />
        }
        right={
          <DashPanel frame={frame} stats={dashStats} txs={dashTxs}>
            {frame > 900 && (
              <div style={{ position: 'absolute', bottom: 24, left: 20, right: 20, opacity: fi(frame, 900, 25) }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px', border: `1px solid ${colors.blue}`, backgroundColor: colors.blueBg }}>
                  <GlobeIcon s={14} c={colors.blue} />
                  <span style={{ fontSize: 11, fontWeight: 600, color: colors.blue, fontFamily: fonts.mono }}>
                    STABLECOIN RAIL · USDC on Base
                  </span>
                </div>
              </div>
            )}
          </DashPanel>
        }
      />
    </AbsoluteFill>
  );
};

// ─── SCENE 3: MCP + FIAT PAYMENT (22-40s, 1080f) ───────────────────

const MCPFiatScene: React.FC = () => {
  const frame = useCurrentFrame();

  const messages: ChatMsg[] = [
    {
      role: 'user',
      content: 'Subscribe procurement-bot to Notion Team plan',
      at: 40,
    },
    {
      role: 'assistant',
      content: "Processing subscription via sardis.pay tool.",
      at: 180,
    },
    {
      role: 'tool_call',
      content: (
        <div style={{ lineHeight: 1.8, color: colors.textSecondary }}>
          <div>agent: <span style={{ color: colors.textPrimary }}>procurement-bot</span></div>
          <div>merchant: <span style={{ color: colors.textPrimary }}>notion:subscription</span></div>
          <div>amount: <span style={{ color: colors.textPrimary }}>$96.00/month</span></div>
          <div>rail: <span style={{ color: colors.purple, fontWeight: 600 }}>fiat</span> <span style={{ color: colors.textMuted }}>{'\u2192'} Virtual Visa</span></div>
        </div>
      ),
      at: 300,
    },
    {
      role: 'tool_result',
      content: (
        <div style={{ lineHeight: 1.8 }}>
          <div style={{ color: colors.textMuted }}>[TAP] {'\u2713'} Identity verified | [AP2] {'\u2713'} Mandate valid</div>
          <div style={{ color: colors.blue }}>[Off-Ramp] USDC {'\u2192'} USD auto-convert via Lithic</div>
          <div style={{ color: colors.green }}>{'\u2713'} Virtual Visa **** 4242 issued</div>
          <div style={{ color: colors.green }}>{'\u2713'} Charged $96.00 to Notion</div>
        </div>
      ),
      at: 520,
    },
    {
      role: 'assistant',
      content: 'Done. USDC auto-converted to USD, virtual card charged. Recurring billing active.',
      at: 720,
    },
  ];

  const dashStats = [
    { label: 'Volume (24h)', value: '$2,480', at: 40 },
    { label: 'Transactions', value: '48', at: 60 },
    { label: 'Agents', value: '3 online', at: 80 },
  ];

  const dashTxs: TxEntry[] = [
    { agent: 'procurement-bot', merchant: 'openai:api', amount: '$29.99', rail: 'USDC', railColor: colors.blue, at: 80 },
    { agent: 'compute_agent', merchant: 'Lambda GPU', amount: '$45.00', rail: 'USDC', railColor: colors.blue, at: 100 },
    { agent: 'procurement-bot', merchant: 'Notion', amount: '$96.00', rail: 'VISA', railColor: colors.purple, isNew: true, at: 520 },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <SplitLayout
        frame={frame}
        left={<MCPChat messages={messages} frame={frame} />}
        right={
          <DashPanel frame={frame} stats={dashStats} txs={dashTxs}>
            {frame > 600 && (
              <div style={{ position: 'absolute', bottom: 24, left: 20, right: 20, opacity: fi(frame, 600, 25) }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px', border: `1px solid ${colors.purple}`, backgroundColor: 'rgba(139,92,246,0.1)' }}>
                  <CardIcon s={14} c={colors.purple} />
                  <span style={{ fontSize: 11, fontWeight: 600, color: colors.purple, fontFamily: fonts.mono }}>
                    FIAT RAIL · Virtual Visa via Lithic
                  </span>
                </div>
              </div>
            )}
          </DashPanel>
        }
      />
    </AbsoluteFill>
  );
};

// ─── SCENE 4: BLOCK + APPROVAL (40-58s, 1080f) ─────────────────────

const BlockScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const approveAt = 680;
  const isApproved = frame >= approveAt;

  const messages: ChatMsg[] = [
    {
      role: 'user',
      content: 'Buy $8,000 in Meta ad credits for marketing-bot',
      at: 40,
    },
    {
      role: 'assistant',
      content: 'Processing via sardis.pay...',
      at: 160,
    },
    {
      role: 'tool_call',
      content: (
        <div style={{ lineHeight: 1.8, color: colors.textSecondary }}>
          <div>agent: <span style={{ color: colors.textPrimary }}>marketing-bot</span></div>
          <div>merchant: <span style={{ color: colors.textPrimary }}>meta:ads</span></div>
          <div>amount: <span style={{ color: colors.textPrimary }}>$8,000.00</span></div>
        </div>
      ),
      at: 250,
    },
    {
      role: 'tool_error',
      content: (
        <div>
          <div style={{ color: colors.red, fontWeight: 600, marginBottom: 6 }}>{'\u2717'} BLOCKED {'\u2014'} Exceeds daily limit ($5,000)</div>
          <div style={{ color: colors.yellow }}>{'\u2192'} Requires human approval</div>
          <div style={{ color: colors.textMuted, marginTop: 4 }}>{'\u2192'} Notification sent to admin@company.com</div>
        </div>
      ),
      at: 400,
    },
    {
      role: 'assistant',
      content: "Payment blocked by spending policy. Approval request sent to admin.",
      at: 530,
    },
    ...(isApproved
      ? [
          {
            role: 'tool_result' as const,
            content: (
              <div style={{ lineHeight: 1.8 }}>
                <div style={{ color: colors.green }}>{'\u2713'} Approved by admin@company.com</div>
                <div style={{ color: colors.green }}>{'\u2713'} Payment processing: $8,000 {'\u2192'} Meta Ads</div>
              </div>
            ),
            at: 780,
          },
          {
            role: 'assistant' as const,
            content: 'Payment approved and processing!' as React.ReactNode,
            at: 900,
          },
        ]
      : []),
  ];

  const dashStats = [
    { label: 'Volume (24h)', value: '$2,576', at: 40 },
    { label: 'Transactions', value: '49', at: 60 },
    { label: 'Agents', value: '3 online', at: 80 },
  ];

  const dashTxs: TxEntry[] = [
    { agent: 'procurement-bot', merchant: 'Notion', amount: '$96.00', rail: 'VISA', railColor: colors.purple, at: 80 },
    { agent: 'procurement-bot', merchant: 'openai:api', amount: '$29.99', rail: 'USDC', railColor: colors.blue, at: 100 },
    {
      agent: 'marketing-bot',
      merchant: 'Meta Ads',
      amount: '$8,000',
      rail: isApproved ? 'USDC' : 'BLOCKED',
      railColor: isApproved ? colors.blue : colors.red,
      status: isApproved ? 'approved' : (frame >= 400 ? 'blocked' : 'ok'),
      isNew: true,
      at: 400,
    },
  ];

  const notifScale = spring({ frame: frame - 480, fps, config: { damping: 12 } });
  const approveScale = spring({ frame: frame - approveAt, fps, config: { damping: 10 } });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <SplitLayout
        frame={frame}
        left={<MCPChat messages={messages} frame={frame} />}
        right={
          <DashPanel frame={frame} stats={dashStats} txs={dashTxs}>
            {/* Approval notification */}
            {frame >= 480 && (
              <div style={{
                position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                backgroundColor: 'rgba(15,14,12,0.7)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                opacity: fi(frame, 480, 20),
                zIndex: 10,
              }}>
              <div style={{
                width: '85%',
                transform: `scale(${notifScale})`,
              }}>
                <div style={{
                  padding: 16,
                  border: `1px solid ${isApproved ? colors.green : colors.yellow}`,
                  backgroundColor: isApproved ? colors.greenBg : colors.yellowBg,
                }}>
                  {/* Header */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                    {isApproved
                      ? <CheckIcon s={16} c={colors.green} />
                      : <BellIcon s={16} c={colors.yellow} />}
                    <span style={{ fontSize: 13, fontWeight: 600, color: isApproved ? colors.green : colors.yellow, fontFamily: fonts.display }}>
                      {isApproved ? 'Approved' : 'Approval Required'}
                    </span>
                  </div>

                  {/* Details */}
                  <div style={{ fontSize: 12, color: colors.textPrimary, fontFamily: fonts.mono, marginBottom: 6 }}>
                    marketing-bot {'\u2192'} Meta Ads {'\u2014'} $8,000
                  </div>
                  {!isApproved && (
                    <div style={{ fontSize: 11, color: colors.textMuted, fontFamily: fonts.mono, marginBottom: 12 }}>
                      Exceeds daily limit ($5,000)
                    </div>
                  )}
                  {isApproved && (
                    <div style={{ fontSize: 11, color: colors.textMuted, fontFamily: fonts.mono, marginBottom: 8 }}>
                      Approved by admin@company.com
                    </div>
                  )}

                  {/* Buttons */}
                  {!isApproved && (
                    <div style={{ display: 'flex', gap: 8 }}>
                      <div style={{
                        padding: '6px 16px',
                        backgroundColor: frame >= approveAt - 60 ? colors.green : colors.orange,
                        color: colors.white,
                        fontFamily: fonts.mono, fontSize: 12, fontWeight: 600,
                        boxShadow: frame >= approveAt - 60 ? `0 0 12px ${colors.greenGlow}` : 'none',
                        transform: `scale(${frame >= approveAt - 30 ? 0.95 : 1})`,
                      }}>
                        Approve
                      </div>
                      <div style={{ padding: '6px 16px', border: `1px solid ${colors.border}`, color: colors.textMuted, fontFamily: fonts.mono, fontSize: 12 }}>
                        Reject
                      </div>
                    </div>
                  )}
                </div>
              </div>
              </div>
            )}
          </DashPanel>
        }
      />
    </AbsoluteFill>
  );
};

// ─── SCENE 5: SUMMARY (58-72s, 840f) ───────────────────────────────

const SummaryScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const totalAmount = Math.floor(interpolate(frame, [30, 120], [0, 2847], cl));
  const stats = [
    { label: '23', desc: 'transactions', icon: <ActivityIcon s={16} c={colors.orange} />, at: 140 },
    { label: '3', desc: 'agents', icon: <UsersIcon s={16} c={colors.orange} />, at: 170 },
    { label: '1', desc: 'blocked', icon: <ShieldIcon s={16} c={colors.red} />, at: 200 },
    { label: '2', desc: 'rails', icon: <ZapIcon s={16} c={colors.yellow} />, at: 230 },
  ];

  const packages = [
    'sardis-core', 'sardis-api', 'sardis-chain', 'sardis-wallet',
    'sardis-protocol', 'sardis-ledger', 'sardis-compliance', 'sardis-cards',
    'sardis-checkout', 'sardis-mcp-server', 'sardis-sdk-python', 'sardis-sdk-js',
    'sardis-cli', 'sardis-contracts',
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, ...ctr }}>
      <GridBg />

      {/* Headline */}
      <div style={{ fontSize: 14, color: colors.textMuted, fontFamily: fonts.mono, letterSpacing: '0.1em', opacity: fi(frame, 20, 20) }}>
        END OF DAY · 17:00
      </div>

      {/* Big counter */}
      <div style={{ fontSize: 80, fontWeight: 800, fontFamily: fonts.display, color: colors.orange, marginTop: 8, opacity: fi(frame, 30, 30) }}>
        ${totalAmount.toLocaleString()}
      </div>
      <div style={{ fontSize: 20, color: colors.textSecondary, fontFamily: fonts.display, opacity: fi(frame, 60, 20) }}>
        processed today
      </div>

      {/* Stats row */}
      <div style={{ display: 'flex', gap: 24, marginTop: 32 }}>
        {stats.map((s, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 8,
            opacity: fi(frame, s.at, 20), transform: `translateY(${su(frame, s.at, 20, 10)}px)`,
          }}>
            {s.icon}
            <span style={{ fontSize: 24, fontWeight: 700, color: colors.textPrimary, fontFamily: fonts.mono }}>{s.label}</span>
            <span style={{ fontSize: 14, color: colors.textMuted, fontFamily: fonts.body }}>{s.desc}</span>
          </div>
        ))}
      </div>

      {/* Dual rail cards */}
      <div style={{ display: 'flex', gap: 20, marginTop: 36 }}>
        {/* Stablecoin */}
        <div style={{
          opacity: fi(frame, 280, 30), transform: `translateY(${su(frame, 280, 30, 15)}px)`,
          width: 340, padding: 20,
          border: `1px solid ${colors.blue}`, backgroundColor: colors.blueBg,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <GlobeIcon s={18} c={colors.blue} />
            <span style={{ fontSize: 15, fontWeight: 700, color: colors.blue, fontFamily: fonts.display }}>STABLECOIN RAIL</span>
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: colors.textPrimary, fontFamily: fonts.mono }}>$1,947</div>
          <div style={{ fontSize: 13, color: colors.textSecondary, fontFamily: fonts.mono, marginTop: 4 }}>18 transactions</div>
          <div style={{ fontSize: 11, color: colors.textMuted, fontFamily: fonts.mono, marginTop: 8 }}>USDC · Base, Polygon, Ethereum</div>
        </div>

        {/* Fiat */}
        <div style={{
          opacity: fi(frame, 340, 30), transform: `translateY(${su(frame, 340, 30, 15)}px)`,
          width: 340, padding: 20,
          border: `1px solid ${colors.purple}`, backgroundColor: 'rgba(139,92,246,0.1)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <CardIcon s={18} c={colors.purple} />
            <span style={{ fontSize: 15, fontWeight: 700, color: colors.purple, fontFamily: fonts.display }}>FIAT RAIL</span>
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: colors.textPrimary, fontFamily: fonts.mono }}>$900</div>
          <div style={{ fontSize: 13, color: colors.textSecondary, fontFamily: fonts.mono, marginTop: 4 }}>5 transactions</div>
          <div style={{ fontSize: 11, color: colors.textMuted, fontFamily: fonts.mono, marginTop: 8 }}>Virtual Visa · Lithic</div>
        </div>
      </div>

      {/* Package badges */}
      <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: 6, maxWidth: 900, justifyContent: 'center', marginTop: 32 }}>
        {packages.map((pkg, i) => {
          const delay = 420 + i * 8;
          const s = spring({ frame: frame - delay, fps, config: { damping: 20 } });
          return (
            <div key={i} style={{
              opacity: fi(frame, delay, 15), transform: `scale(${s})`,
              padding: '4px 10px', border: `1px solid ${colors.border}`, backgroundColor: colors.cardBg,
              fontFamily: fonts.mono, fontSize: 11, color: colors.textMuted,
            }}>
              {pkg}
            </div>
          );
        })}
      </div>

      {/* Protocols */}
      <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
        {[
          { name: 'AP2', org: 'Google + 60 partners', color: '#4285F4', at: 580 },
          { name: 'TAP', org: 'Visa + 10 partners', color: '#1A1F71', at: 620 },
        ].map((p, i) => (
          <div key={i} style={{
            opacity: fi(frame, p.at, 25), transform: `translateY(${su(frame, p.at, 25, 10)}px)`,
            padding: '8px 16px', border: `1px solid ${colors.border}`, backgroundColor: colors.cardBg,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{ fontSize: 14, fontWeight: 800, color: p.color, fontFamily: fonts.mono }}>{p.name}</span>
            <span style={{ fontSize: 10, color: colors.textMuted, fontFamily: fonts.mono }}>{p.org}</span>
          </div>
        ))}
      </div>

      {/* Solo builder */}
      <div style={{ marginTop: 24, opacity: fi(frame, 680, 30), fontSize: 18, color: colors.textPrimary, fontFamily: fonts.display, fontWeight: 600 }}>
        Built solo. <span style={{ color: colors.orange }}>3 months.</span>
      </div>
    </AbsoluteFill>
  );
};

// ─── SCENE 6: CTA (72-90s, 1080f) ──────────────────────────────────

const CTAScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame: frame - 20, fps, config: { damping: 12, stiffness: 80 } });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, ...ctr }}>
      <GridBg />

      {/* Ambient glow */}
      <div style={{
        position: 'absolute', width: 500, height: 500,
        background: `radial-gradient(circle, ${colors.orangeGlow} 0%, transparent 70%)`,
        filter: 'blur(80px)', opacity: 0.4,
      }} />

      {/* Logo */}
      <SardisLogo size={100} scale={logoScale} />

      {/* Name */}
      <h1 style={{
        fontSize: 64, fontWeight: 700, fontFamily: fonts.display, marginTop: 16,
        background: `linear-gradient(135deg, ${colors.orange}, ${colors.orangeLight})`,
        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
        opacity: fi(frame, 60, 30),
      }}>
        Sardis
      </h1>

      {/* Tagline */}
      <p style={{
        fontSize: 22, color: colors.textSecondary, fontFamily: fonts.display, marginTop: 8,
        opacity: fi(frame, 100, 30),
      }}>
        Safe spending infrastructure for AI agents.
      </p>

      {/* Install commands side by side */}
      <div style={{
        display: 'flex', gap: 16, marginTop: 36, opacity: fi(frame, 160, 30),
        transform: `translateY(${su(frame, 160, 30, 10)}px)`,
      }}>
        <div style={{ padding: '10px 20px', backgroundColor: colors.orangeSubtle, border: `1px solid rgba(255,79,0,0.2)` }}>
          <span style={{ fontSize: 14, fontFamily: fonts.mono, color: colors.orange }}>pip install sardis</span>
        </div>
        <div style={{ padding: '10px 20px', backgroundColor: colors.orangeSubtle, border: `1px solid rgba(255,79,0,0.2)` }}>
          <span style={{ fontSize: 14, fontFamily: fonts.mono, color: colors.orange }}>npm install @sardis/sdk</span>
        </div>
      </div>

      {/* URL */}
      <div style={{
        marginTop: 20, opacity: fi(frame, 220, 30),
      }}>
        <span style={{ fontSize: 26, fontWeight: 500, fontFamily: fonts.mono, color: colors.textPrimary }}>
          sardis.sh
        </span>
      </div>
    </AbsoluteFill>
  );
};

// ─── MAIN COMPOSITION ───────────────────────────────────────────────

export const SardisDemo: React.FC = () => {
  const S = {
    setup:   { from: 0,    dur: 1500 },  // 0-25s    SDK + stablecoin payment
    mcp:     { from: 1500, dur: 1380 },  // 25-48s   MCP tool + fiat rail
    block:   { from: 2880, dur: 1200 },  // 48-68s   Block + human approval
    summary: { from: 4080, dur: 840 },   // 68-82s   End-of-day summary
    cta:     { from: 4920, dur: 480 },   // 82-90s   Logo + install + URL
  };

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <Sequence from={S.setup.from} durationInFrames={S.setup.dur}><SetupScene /></Sequence>
      <Sequence from={S.mcp.from} durationInFrames={S.mcp.dur}><MCPFiatScene /></Sequence>
      <Sequence from={S.block.from} durationInFrames={S.block.dur}><BlockScene /></Sequence>
      <Sequence from={S.summary.from} durationInFrames={S.summary.dur}><SummaryScene /></Sequence>
      <Sequence from={S.cta.from} durationInFrames={S.cta.dur}><CTAScene /></Sequence>
    </AbsoluteFill>
  );
};
