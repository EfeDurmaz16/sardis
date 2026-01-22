import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Sequence,
  spring,
} from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";

// ============================================================================
// SARDIS YC DEMO VIDEO
// The Payment OS for AI Agents
// ============================================================================

// Color Palette
const colors = {
  bg: "#09090b",
  bgLight: "#18181b",
  primary: "#6366f1",
  secondary: "#8b5cf6",
  success: "#22c55e",
  error: "#ef4444",
  text: "#fafafa",
  textMuted: "#71717a",
  border: "rgba(255,255,255,0.1)",
};

interface Props {
  shortVersion?: boolean;
}

// ============================================================================
// SCENE 1: INTRO - "The Payment OS for AI Agents"
// ============================================================================
const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, fps], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [0, fps], [50, 0], { extrapolateRight: "clamp" });

  const subtitleOpacity = interpolate(frame, [fps * 0.5, fps * 1.5], [0, 1], { extrapolateRight: "clamp" });

  const badgeScale = spring({ frame: frame - fps * 2, fps, config: { damping: 12 } });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      {/* Background gradient */}
      <div
        style={{
          position: "absolute",
          top: "20%",
          left: "30%",
          width: 600,
          height: 600,
          background: `radial-gradient(circle, ${colors.primary}30 0%, transparent 70%)`,
          filter: "blur(100px)",
        }}
      />

      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        {/* Logo */}
        <div
          style={{
            width: 80,
            height: 80,
            background: `linear-gradient(135deg, ${colors.primary}, ${colors.secondary})`,
            borderRadius: 20,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 40,
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
          }}
        >
          <span style={{ fontSize: 40, fontWeight: "bold", color: "white" }}>S</span>
        </div>

        {/* Title */}
        <h1
          style={{
            fontSize: 90,
            fontWeight: 800,
            color: colors.text,
            margin: 0,
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
            letterSpacing: "-0.02em",
          }}
        >
          Sardis
        </h1>

        {/* Subtitle */}
        <p
          style={{
            fontSize: 36,
            color: colors.textMuted,
            marginTop: 20,
            opacity: subtitleOpacity,
          }}
        >
          The Payment OS for AI Agents
        </p>

        {/* Badge */}
        <div
          style={{
            marginTop: 60,
            padding: "12px 28px",
            background: `${colors.success}15`,
            border: `1px solid ${colors.success}40`,
            borderRadius: 100,
            transform: `scale(${badgeScale})`,
          }}
        >
          <span style={{ color: colors.success, fontSize: 18, fontWeight: 600 }}>
            Live on Testnet
          </span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ============================================================================
// SCENE 2: THE PROBLEM - Agents are "Read-Only"
// ============================================================================
const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const terminalOpacity = interpolate(frame, [0, fps * 0.5], [0, 1], { extrapolateRight: "clamp" });
  const line1 = interpolate(frame, [fps * 0.5, fps * 1], [0, 1], { extrapolateRight: "clamp" });
  const line2 = interpolate(frame, [fps * 1, fps * 1.5], [0, 1], { extrapolateRight: "clamp" });
  const line3 = interpolate(frame, [fps * 1.5, fps * 2], [0, 1], { extrapolateRight: "clamp" });
  const errorLine = interpolate(frame, [fps * 2.5, fps * 3], [0, 1], { extrapolateRight: "clamp" });
  const blockedBadge = spring({ frame: frame - fps * 3.5, fps, config: { damping: 10 } });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      {/* Title */}
      <div style={{ position: "absolute", top: 80, left: 100 }}>
        <h2 style={{ fontSize: 48, color: colors.text, margin: 0, fontWeight: 700 }}>
          The Problem
        </h2>
        <p style={{ fontSize: 24, color: colors.textMuted, marginTop: 10 }}>
          AI agents are stuck in "read-only" mode
        </p>
      </div>

      {/* Terminal Window */}
      <div
        style={{
          position: "absolute",
          top: 220,
          left: 100,
          right: 100,
          background: colors.bgLight,
          borderRadius: 16,
          border: `1px solid ${colors.border}`,
          overflow: "hidden",
          opacity: terminalOpacity,
        }}
      >
        {/* Title bar */}
        <div
          style={{
            padding: "12px 16px",
            background: "rgba(255,255,255,0.03)",
            borderBottom: `1px solid ${colors.border}`,
            display: "flex",
            gap: 8,
          }}
        >
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#ef4444" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#f59e0b" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#22c55e" }} />
        </div>

        {/* Terminal content */}
        <div style={{ padding: 30, fontFamily: "monospace", fontSize: 22, lineHeight: 2 }}>
          <div style={{ color: colors.success, opacity: line1 }}>
            $ agent plan trip --budget 500
          </div>
          <div style={{ color: colors.textMuted, opacity: line1 }}>
            {">"} Planning itinerary... Done.
          </div>
          <div style={{ color: colors.success, opacity: line2, marginTop: 10 }}>
            $ agent book flights
          </div>
          <div style={{ color: colors.textMuted, opacity: line2 }}>
            {">"} Selecting best option... UA445 selected.
          </div>
          <div style={{ color: colors.textMuted, opacity: line3 }}>
            {">"} Entering payment details...
          </div>

          {/* Error */}
          <div
            style={{
              marginTop: 20,
              padding: 16,
              background: `${colors.error}10`,
              border: `1px solid ${colors.error}30`,
              borderRadius: 8,
              opacity: errorLine,
            }}
          >
            <div style={{ color: colors.error, fontWeight: 600 }}>
              ERROR: 2FA Required
            </div>
            <div style={{ color: colors.error, opacity: 0.7 }}>
              Please enter the code sent to +1 (555) ***-****
            </div>
            <div style={{ color: colors.error, opacity: 0.7, marginTop: 8 }}>
              {">"} Timeout. Booking failed.
            </div>
          </div>
        </div>
      </div>

      {/* BLOCKED badge */}
      <div
        style={{
          position: "absolute",
          bottom: 150,
          right: 150,
          background: colors.error,
          color: "white",
          padding: "16px 32px",
          borderRadius: 12,
          fontSize: 24,
          fontWeight: 700,
          transform: `scale(${blockedBadge}) rotate(-3deg)`,
          boxShadow: "0 10px 40px rgba(239,68,68,0.4)",
        }}
      >
        EXECUTION BLOCKED
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// SCENE 3: THE SOLUTION - Sardis Policy Engine
// ============================================================================
const SolutionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, fps * 0.5], [0, 1], { extrapolateRight: "clamp" });

  const card1 = spring({ frame: frame - fps * 0.5, fps, config: { damping: 12 } });
  const card2 = spring({ frame: frame - fps * 0.8, fps, config: { damping: 12 } });
  const card3 = spring({ frame: frame - fps * 1.1, fps, config: { damping: 12 } });

  const features = [
    {
      icon: "W",
      title: "Agent Wallets",
      desc: "Non-custodial MPC wallets with their own financial identity",
      color: colors.primary,
    },
    {
      icon: "P",
      title: "Policy Engine",
      desc: "Natural language spending rules that prevent financial hallucinations",
      color: colors.secondary,
    },
    {
      icon: "$",
      title: "Programmable Rails",
      desc: "Instant settlement via USDC + virtual cards for fiat merchants",
      color: colors.success,
    },
  ];

  const scales = [card1, card2, card3];

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 100,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: titleOpacity,
        }}
      >
        <h2 style={{ fontSize: 64, color: colors.text, margin: 0, fontWeight: 700 }}>
          The Solution
        </h2>
        <p style={{ fontSize: 28, color: colors.textMuted, marginTop: 16 }}>
          Banking for Bots - built for the agent economy
        </p>
      </div>

      {/* Feature Cards */}
      <div
        style={{
          position: "absolute",
          top: 320,
          left: 100,
          right: 100,
          display: "flex",
          gap: 40,
        }}
      >
        {features.map((feature, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              background: colors.bgLight,
              borderRadius: 20,
              padding: 40,
              border: `1px solid ${colors.border}`,
              transform: `scale(${scales[i]})`,
            }}
          >
            <div
              style={{
                width: 70,
                height: 70,
                background: `${feature.color}20`,
                borderRadius: 16,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: 24,
              }}
            >
              <span style={{ fontSize: 32, color: feature.color, fontWeight: 700 }}>
                {feature.icon}
              </span>
            </div>
            <h3 style={{ fontSize: 28, color: colors.text, margin: 0, fontWeight: 600 }}>
              {feature.title}
            </h3>
            <p style={{ fontSize: 20, color: colors.textMuted, marginTop: 12, lineHeight: 1.5 }}>
              {feature.desc}
            </p>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// SCENE 4: LIVE DEMO - Policy Engine in Action
// ============================================================================
const DemoScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animation timeline
  const showClaudeRequest = frame > fps * 0.5;
  const showPolicyCheck = frame > fps * 2;
  const showBlocked = frame > fps * 3.5;
  const showPolicyUpdate = frame > fps * 5;
  const showNewRequest = frame > fps * 7;
  const showApproved = frame > fps * 8.5;
  const showPaymentSuccess = frame > fps * 10;

  const blockedPulse = Math.sin(frame * 0.2) * 0.1 + 1;
  const successPulse = Math.sin(frame * 0.15) * 0.05 + 1;

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      {/* Title */}
      <div style={{ position: "absolute", top: 50, left: 100 }}>
        <h2 style={{ fontSize: 40, color: colors.text, margin: 0, fontWeight: 700 }}>
          Live Demo: Policy Engine
        </h2>
      </div>

      {/* Two-panel layout */}
      <div
        style={{
          position: "absolute",
          top: 140,
          left: 80,
          right: 80,
          bottom: 80,
          display: "flex",
          gap: 30,
        }}
      >
        {/* Left: Agent Terminal */}
        <div
          style={{
            flex: 1,
            background: "#000",
            borderRadius: 16,
            border: `1px solid ${colors.border}`,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "10px 16px",
              background: "rgba(255,255,255,0.03)",
              borderBottom: `1px solid ${colors.border}`,
              fontSize: 14,
              color: colors.textMuted,
              display: "flex",
              justifyContent: "space-between",
            }}
          >
            <span>Claude Desktop + MCP</span>
            <span style={{ color: colors.success }}>Connected</span>
          </div>
          <div style={{ padding: 24, fontFamily: "monospace", fontSize: 18, lineHeight: 1.8 }}>
            {showClaudeRequest && (
              <div>
                <span style={{ color: colors.primary }}>claude</span>
                <span style={{ color: colors.textMuted }}> {">"} </span>
                <span style={{ color: colors.text }}>
                  Buy a $500 Amazon gift card for rewards
                </span>
              </div>
            )}
            {showBlocked && (
              <div style={{ marginTop: 16, color: colors.error }}>
                Error 403: Policy Violation
                <br />
                <span style={{ opacity: 0.7 }}>Reason: Gift cards not in allowed categories</span>
              </div>
            )}
            {showNewRequest && (
              <div style={{ marginTop: 24 }}>
                <span style={{ color: colors.primary }}>claude</span>
                <span style={{ color: colors.textMuted }}> {">"} </span>
                <span style={{ color: colors.text }}>
                  Buy OpenAI API credits ($20)
                </span>
              </div>
            )}
            {showPaymentSuccess && (
              <div style={{ marginTop: 16, color: colors.success }}>
                Payment executed successfully
                <br />
                <span style={{ opacity: 0.7 }}>
                  Virtual Card: 4242 **** **** 9999
                </span>
                <br />
                <span style={{ opacity: 0.7 }}>
                  Tx: 0x7a3f...8d2e
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Policy Engine Dashboard */}
        <div
          style={{
            flex: 1,
            background: colors.bgLight,
            borderRadius: 16,
            border: `1px solid ${colors.border}`,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "10px 16px",
              background: "rgba(255,255,255,0.03)",
              borderBottom: `1px solid ${colors.border}`,
              fontSize: 14,
              color: colors.textMuted,
            }}
          >
            Sardis Policy Engine (CFO)
          </div>
          <div style={{ padding: 24, fontSize: 16, lineHeight: 1.8 }}>
            {showPolicyCheck && (
              <div>
                <div style={{ color: colors.textMuted, fontSize: 14, marginBottom: 8 }}>
                  [Incoming Request]
                </div>
                <div style={{ color: colors.text }}>
                  Amount: <strong>$500</strong> | Category: Gift Cards
                </div>
                <div style={{ color: colors.textMuted, marginTop: 8 }}>
                  Checking policy rules...
                </div>
              </div>
            )}
            {showBlocked && (
              <div
                style={{
                  marginTop: 16,
                  padding: 16,
                  background: `${colors.error}15`,
                  border: `1px solid ${colors.error}30`,
                  borderRadius: 8,
                  transform: `scale(${blockedPulse})`,
                }}
              >
                <div style={{ color: colors.error, fontWeight: 700, fontSize: 20 }}>
                  BLOCKED
                </div>
                <div style={{ color: colors.error, opacity: 0.8, marginTop: 4 }}>
                  Rule: "Only allow SaaS & DevTools"
                </div>
              </div>
            )}
            {showPolicyUpdate && (
              <div style={{ marginTop: 24 }}>
                <div style={{ color: colors.secondary, fontSize: 14 }}>
                  [Policy Updated via Natural Language]
                </div>
                <div
                  style={{
                    marginTop: 8,
                    padding: 12,
                    background: `${colors.secondary}10`,
                    borderRadius: 8,
                    fontStyle: "italic",
                    color: colors.text,
                  }}
                >
                  "Allow SaaS payments up to $100/day"
                </div>
              </div>
            )}
            {showApproved && (
              <div
                style={{
                  marginTop: 16,
                  padding: 16,
                  background: `${colors.success}15`,
                  border: `1px solid ${colors.success}30`,
                  borderRadius: 8,
                  transform: `scale(${successPulse})`,
                }}
              >
                <div style={{ color: colors.success, fontWeight: 700, fontSize: 20 }}>
                  APPROVED
                </div>
                <div style={{ color: colors.success, opacity: 0.8, marginTop: 4 }}>
                  MPC Signing... Transaction submitted
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// SCENE 5: CTA - Get Early Access
// ============================================================================
const CTAScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, fps], [0, 1], { extrapolateRight: "clamp" });
  const buttonScale = spring({ frame: frame - fps * 1.5, fps, config: { damping: 10 } });
  const urlOpacity = interpolate(frame, [fps * 2, fps * 2.5], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      {/* Background gradient */}
      <div
        style={{
          position: "absolute",
          top: "30%",
          left: "40%",
          width: 500,
          height: 500,
          background: `radial-gradient(circle, ${colors.primary}40 0%, transparent 70%)`,
          filter: "blur(120px)",
        }}
      />

      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <h1
          style={{
            fontSize: 72,
            fontWeight: 800,
            color: colors.text,
            textAlign: "center",
            opacity: titleOpacity,
            margin: 0,
          }}
        >
          Give Your Agent
          <br />
          <span
            style={{
              background: `linear-gradient(135deg, ${colors.primary}, ${colors.secondary})`,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            Financial Superpowers
          </span>
        </h1>

        <div
          style={{
            marginTop: 60,
            padding: "20px 48px",
            background: `linear-gradient(135deg, ${colors.primary}, ${colors.secondary})`,
            borderRadius: 100,
            transform: `scale(${buttonScale})`,
            boxShadow: `0 20px 60px ${colors.primary}50`,
          }}
        >
          <span style={{ fontSize: 28, fontWeight: 700, color: "white" }}>
            Get Early Access
          </span>
        </div>

        <p
          style={{
            marginTop: 40,
            fontSize: 24,
            color: colors.textMuted,
            opacity: urlOpacity,
          }}
        >
          sardis.dev
        </p>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ============================================================================
// MAIN COMPOSITION
// ============================================================================
export const SardisDemoVideo: React.FC<Props> = ({ shortVersion = false }) => {
  const { fps } = useVideoConfig();

  // Scene durations (in seconds)
  const introLength = 4 * fps;
  const problemLength = 5 * fps;
  const solutionLength = 5 * fps;
  const demoLength = 12 * fps;
  const ctaLength = 4 * fps;

  const transitionDuration = 15; // frames

  return (
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={introLength}>
        <IntroScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: transitionDuration })}
      />

      <TransitionSeries.Sequence durationInFrames={problemLength}>
        <ProblemScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={slide({ direction: "from-right" })}
        timing={linearTiming({ durationInFrames: transitionDuration })}
      />

      <TransitionSeries.Sequence durationInFrames={solutionLength}>
        <SolutionScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: transitionDuration })}
      />

      <TransitionSeries.Sequence durationInFrames={demoLength}>
        <DemoScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: transitionDuration })}
      />

      <TransitionSeries.Sequence durationInFrames={ctaLength}>
        <CTAScene />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
