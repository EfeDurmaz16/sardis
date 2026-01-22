import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Easing,
} from 'remotion';
import React from 'react';

// Styles
const styles = {
  container: {
    backgroundColor: '#0a0a0f',
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  centered: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
  },
  gradientText: {
    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
};

// Scene 1: The Problem (0-10s, frames 0-300)
const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [0, 30, 270, 300], [0, 1, 1, 0], {
    extrapolateRight: 'clamp',
  });

  const glitchOffset = Math.sin(frame * 0.5) * (frame < 200 ? 2 : 0);

  return (
    <AbsoluteFill style={{ ...styles.container, ...styles.centered, opacity }}>
      <h1
        style={{
          fontSize: 80,
          fontWeight: 700,
          color: 'white',
          textAlign: 'center',
          transform: `translateX(${glitchOffset}px)`,
          textShadow: frame % 10 < 3 ? '2px 0 #ff0040, -2px 0 #00ff88' : 'none',
        }}
      >
        Agents can code,
      </h1>
      <h1
        style={{
          fontSize: 80,
          fontWeight: 700,
          color: '#ef4444',
          textAlign: 'center',
          marginTop: 20,
          transform: `translateX(${-glitchOffset}px)`,
        }}
      >
        but they can't pay.
      </h1>

      {/* Blinking cursor */}
      <div
        style={{
          marginTop: 60,
          fontFamily: 'monospace',
          fontSize: 24,
          color: '#6366f1',
          opacity: Math.sin(frame * 0.2) > 0 ? 1 : 0,
        }}
      >
        █
      </div>
    </AbsoluteFill>
  );
};

// Scene 2: The Connection - MCP (10-30s, frames 300-900)
const MCPScene: React.FC = () => {
  const frame = useCurrentFrame();
  const localFrame = frame;

  const terminalOpacity = interpolate(localFrame, [0, 30], [0, 1], {
    extrapolateRight: 'clamp',
  });

  const typedChars = Math.floor(localFrame / 3);
  const command = 'npx @sardis/mcp-server start';
  const typedCommand = command.slice(0, typedChars);

  const connectedOpacity = interpolate(localFrame, [180, 210], [0, 1], {
    extrapolateRight: 'clamp',
  });

  const scaleIn = spring({
    frame: localFrame - 180,
    fps: 30,
    config: { damping: 15 },
  });

  return (
    <AbsoluteFill style={{ ...styles.container, padding: 100 }}>
      {/* Terminal Window */}
      <div
        style={{
          opacity: terminalOpacity,
          backgroundColor: '#1a1a2e',
          borderRadius: 16,
          border: '1px solid rgba(255,255,255,0.1)',
          overflow: 'hidden',
          maxWidth: 1000,
          margin: '0 auto',
        }}
      >
        {/* Terminal Header */}
        <div
          style={{
            padding: '12px 20px',
            backgroundColor: 'rgba(255,255,255,0.05)',
            display: 'flex',
            gap: 8,
          }}
        >
          <div style={{ width: 12, height: 12, borderRadius: 6, backgroundColor: '#ff5f57' }} />
          <div style={{ width: 12, height: 12, borderRadius: 6, backgroundColor: '#ffbd2e' }} />
          <div style={{ width: 12, height: 12, borderRadius: 6, backgroundColor: '#28c840' }} />
        </div>

        {/* Terminal Content */}
        <div style={{ padding: 30, fontFamily: 'JetBrains Mono, monospace', fontSize: 22 }}>
          <div style={{ color: '#10b981', marginBottom: 10 }}>
            $ {typedCommand}
            <span style={{ opacity: Math.sin(frame * 0.2) > 0 ? 1 : 0 }}>█</span>
          </div>

          {localFrame > 90 && (
            <div style={{ color: '#64748b', marginTop: 20 }}>
              <div>🚀 Starting Sardis MCP Server v1.0.0...</div>
            </div>
          )}

          {localFrame > 120 && (
            <div style={{ color: '#64748b' }}>
              <div>📋 Tools: sardis_pay, sardis_check_policy, sardis_get_balance</div>
            </div>
          )}

          {localFrame > 150 && (
            <div style={{ color: '#10b981', marginTop: 10 }}>
              <div>✅ Server ready. Connected to Claude Desktop.</div>
            </div>
          )}
        </div>
      </div>

      {/* Connected Badge */}
      <div
        style={{
          opacity: connectedOpacity,
          transform: `scale(${scaleIn})`,
          position: 'absolute',
          bottom: 150,
          left: '50%',
          marginLeft: -150,
          backgroundColor: 'rgba(16, 185, 129, 0.2)',
          border: '2px solid #10b981',
          borderRadius: 100,
          padding: '20px 50px',
          display: 'flex',
          alignItems: 'center',
          gap: 15,
        }}
      >
        <div
          style={{
            width: 16,
            height: 16,
            borderRadius: 8,
            backgroundColor: '#10b981',
            boxShadow: '0 0 20px #10b981',
          }}
        />
        <span style={{ color: '#10b981', fontSize: 28, fontWeight: 600 }}>CONNECTED</span>
      </div>
    </AbsoluteFill>
  );
};

// Scene 3: The Prevention (30-50s, frames 900-1500)
const PreventionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const localFrame = frame;

  const splitProgress = interpolate(localFrame, [0, 60], [0, 1], {
    extrapolateRight: 'clamp',
  });

  const blockedOpacity = interpolate(localFrame, [180, 210], [0, 1], {
    extrapolateRight: 'clamp',
  });

  const shake = localFrame > 180 && localFrame < 240 ? Math.sin(localFrame * 2) * 5 : 0;

  return (
    <AbsoluteFill style={{ ...styles.container }}>
      {/* Split Screen Container */}
      <div style={{ display: 'flex', height: '100%' }}>
        {/* Left: Agent Terminal */}
        <div
          style={{
            flex: 1,
            padding: 60,
            borderRight: '1px solid rgba(255,255,255,0.1)',
            transform: `translateX(${shake}px)`,
          }}
        >
          <div style={{ color: '#8b5cf6', fontSize: 18, fontWeight: 600, marginBottom: 20 }}>
            AI AGENT
          </div>

          <div
            style={{
              backgroundColor: '#1a1a2e',
              borderRadius: 12,
              padding: 30,
              fontFamily: 'monospace',
              fontSize: 20,
            }}
          >
            <div style={{ color: '#64748b', marginBottom: 15 }}>
              {'>'} Executing purchase task...
            </div>

            {localFrame > 60 && (
              <div style={{ color: '#6366f1' }}>
                {'>'} sardis.pay("Amazon", $500, "Gift Card")
              </div>
            )}

            {localFrame > 180 && (
              <div style={{ color: '#ef4444', marginTop: 20, fontWeight: 600 }}>
                ❌ Error 403: POLICY_VIOLATION
              </div>
            )}
          </div>
        </div>

        {/* Right: Policy Engine */}
        <div style={{ flex: 1, padding: 60 }}>
          <div style={{ color: '#6366f1', fontSize: 18, fontWeight: 600, marginBottom: 20 }}>
            SARDIS POLICY ENGINE
          </div>

          <div
            style={{
              backgroundColor: '#1a1a2e',
              borderRadius: 12,
              padding: 30,
              fontSize: 18,
            }}
          >
            {localFrame > 30 && (
              <div style={{ color: '#64748b', marginBottom: 10 }}>
                [14:32:01] Request: Amazon ($500)
              </div>
            )}

            {localFrame > 90 && (
              <div style={{ color: '#64748b', marginBottom: 10 }}>
                [14:32:01] Merchant: amazon.com
              </div>
            )}

            {localFrame > 120 && (
              <div style={{ color: '#64748b', marginBottom: 10 }}>
                [14:32:01] Running policy check...
              </div>
            )}

            {localFrame > 150 && (
              <div style={{ color: '#64748b', marginBottom: 10 }}>
                [14:32:02] Category: Retail/Gift Cards
              </div>
            )}

            {localFrame > 180 && (
              <>
                <div style={{ color: '#ef4444', fontWeight: 700, marginTop: 20 }}>
                  ❌ BLOCKED
                </div>
                <div style={{ color: '#fca5a5', marginTop: 10 }}>
                  Reason: Merchant not in allowlist
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* BLOCKED Overlay */}
      {localFrame > 180 && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            opacity: blockedOpacity,
          }}
        >
          <div
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.9)',
              color: 'white',
              fontSize: 64,
              fontWeight: 800,
              padding: '30px 80px',
              borderRadius: 16,
              boxShadow: '0 0 100px rgba(239, 68, 68, 0.5)',
            }}
          >
            BLOCKED
          </div>
          <div
            style={{
              textAlign: 'center',
              color: 'white',
              fontSize: 24,
              marginTop: 20,
            }}
          >
            Financial Hallucination PREVENTED
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

// Scene 4: The Solution (50-60s, frames 1500-1800)
const SolutionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const localFrame = frame;

  const logoScale = spring({
    frame: localFrame - 200,
    fps: 30,
    config: { damping: 12 },
  });

  const successOpacity = interpolate(localFrame, [120, 150], [0, 1], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{ ...styles.container, ...styles.centered }}>
      {localFrame < 200 ? (
        // Success state
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              color: '#64748b',
              fontSize: 24,
              marginBottom: 30,
            }}
          >
            Policy updated: "Allow OpenAI up to $50"
          </div>

          <div
            style={{
              backgroundColor: '#1a1a2e',
              borderRadius: 16,
              padding: 40,
              maxWidth: 600,
            }}
          >
            <div style={{ fontFamily: 'monospace', fontSize: 22, color: '#6366f1' }}>
              {'>'} sardis.pay("OpenAI", $20, "API Credits")
            </div>

            {localFrame > 60 && (
              <div style={{ marginTop: 30, opacity: successOpacity }}>
                <div style={{ color: '#10b981', fontSize: 32, fontWeight: 700 }}>
                  ✓ APPROVED
                </div>
                <div style={{ color: '#64748b', marginTop: 15, fontSize: 18 }}>
                  Card: 4242 **** **** 9999
                </div>
                <div style={{ color: '#64748b', fontSize: 18 }}>
                  Transaction ID: tx_0x8a2f...c91e
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        // Logo reveal
        <div
          style={{
            textAlign: 'center',
            transform: `scale(${logoScale})`,
          }}
        >
          {/* Logo */}
          <div
            style={{
              width: 120,
              height: 120,
              borderRadius: 30,
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 40px',
              boxShadow: '0 0 100px rgba(99, 102, 241, 0.5)',
            }}
          >
            <span style={{ color: 'white', fontSize: 64, fontWeight: 800 }}>S</span>
          </div>

          <h1
            style={{
              fontSize: 72,
              fontWeight: 700,
              ...styles.gradientText,
            }}
          >
            Sardis
          </h1>

          <p style={{ color: '#64748b', fontSize: 28, marginTop: 20 }}>
            The Payment OS for the Agent Economy
          </p>

          <div
            style={{
              marginTop: 50,
              padding: '20px 50px',
              backgroundColor: 'rgba(255,255,255,0.05)',
              borderRadius: 12,
              display: 'inline-block',
            }}
          >
            <span style={{ color: 'white', fontSize: 32, fontWeight: 500 }}>sardis.sh</span>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

// Main Demo Composition
export const SardisDemo: React.FC = () => {
  return (
    <AbsoluteFill style={styles.container}>
      {/* Scene 1: The Problem (0-10s) */}
      <Sequence from={0} durationInFrames={300}>
        <ProblemScene />
      </Sequence>

      {/* Scene 2: MCP Connection (10-30s) */}
      <Sequence from={300} durationInFrames={600}>
        <MCPScene />
      </Sequence>

      {/* Scene 3: The Prevention (30-50s) */}
      <Sequence from={900} durationInFrames={600}>
        <PreventionScene />
      </Sequence>

      {/* Scene 4: The Solution (50-60s) */}
      <Sequence from={1500} durationInFrames={300}>
        <SolutionScene />
      </Sequence>
    </AbsoluteFill>
  );
};
