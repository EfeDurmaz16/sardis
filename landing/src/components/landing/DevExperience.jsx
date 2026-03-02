import { useState } from 'react';

function CodeLine({ children }) {
  return (
    <div className="leading-[1.7]">{children}</div>
  );
}

// Code syntax highlighting colors: editor theme colors, kept hardcoded
function K({ children }) {
  return <span className="text-[#C586C0]">{children}</span>;
}

function S({ children }) {
  return <span className="text-[#CE9178]">{children}</span>;
}

function F({ children }) {
  return <span className="text-[#DCDCAA]">{children}</span>;
}

function P({ children }) {
  return <span className="text-[#808080]">{children}</span>;
}

function T({ children }) {
  return <span className="text-[#D4D4D4]">{children}</span>;
}

export default function DevExperience() {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText('pip install sardis');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-[100px] md:pt-[140px]">
      <div className="flex flex-col md:flex-row gap-12 md:gap-16 lg:gap-24 items-center">
        {/* Left column */}
        <div className="w-full md:w-auto md:shrink-0 md:max-w-[460px] flex flex-col gap-6">
          <div
            className="text-[12px] uppercase tracking-widest"
            style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--landing-blue)' }}
          >
            DEVELOPER EXPERIENCE
          </div>

          <h2
            className="text-[30px] leading-[36px] md:text-[40px] md:leading-[46px] font-semibold"
            style={{ fontFamily: "'Space Grotesk', system-ui, sans-serif", color: 'var(--landing-text-primary)' }}
          >
            Five lines of code.
          </h2>

          <p
            className="text-[14px] leading-[24px] font-light"
            style={{ fontFamily: "'Inter', system-ui, sans-serif", color: 'var(--landing-text-tertiary)' }}
          >
            From install to first payment in under a minute. Our Python and TypeScript SDKs make agent payments feel native.
          </p>

          {/* Install command */}
          <div
            className="rounded-lg py-3 px-4 flex flex-row items-center justify-between gap-4"
            style={{
              backgroundColor: 'var(--landing-surface)',
              border: '1px solid var(--landing-border)',
            }}
          >
            <code
              className="text-[13px]"
              style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--landing-text-secondary)' }}
            >
              pip install sardis
            </code>
            <button
              onClick={handleCopy}
              className="text-[12px] transition-colors duration-150 shrink-0"
              style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--landing-text-muted)' }}
              onMouseEnter={(e) => e.currentTarget.style.color = 'var(--landing-text-primary)'}
              onMouseLeave={(e) => e.currentTarget.style.color = 'var(--landing-text-muted)'}
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
        </div>

        {/* Right column: code block (always dark for editor feel) */}
        <div
          className="w-full flex-1 min-h-[280px] rounded-[14px] overflow-hidden"
          style={{
            backgroundColor: '#1E1E2E',
            border: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          {/* Title bar */}
          <div
            className="py-3 px-4 flex items-center justify-between"
            style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}
          >
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-md" style={{ backgroundColor: 'rgba(255,255,255,0.12)' }} />
              <div className="w-3 h-3 rounded-md" style={{ backgroundColor: 'rgba(255,255,255,0.12)' }} />
              <div className="w-3 h-3 rounded-md" style={{ backgroundColor: 'rgba(255,255,255,0.12)' }} />
            </div>
            <span
              className="text-[12px]"
              style={{ fontFamily: "'JetBrains Mono', monospace", color: 'rgba(255,255,255,0.35)' }}
            >
              main.py
            </span>
          </div>

          {/* Code content */}
          <div className="p-5 overflow-x-auto">
            <pre
              className="text-[13px] leading-[1.7]"
              style={{ fontFamily: "'JetBrains Mono', monospace" }}
            >
              <CodeLine>
                <K>from</K>
                <T> sardis </T>
                <K>import</K>
                <T> Sardis</T>
              </CodeLine>
              <CodeLine>
                <T>&nbsp;</T>
              </CodeLine>
              <CodeLine>
                <T>client </T>
                <P>= </P>
                <F>Sardis</F>
                <P>(</P>
                <T>api_key</T>
                <P>=</P>
                <S>"sk_..."</S>
                <P>)</P>
              </CodeLine>
              <CodeLine>
                <T>wallet </T>
                <P>= </P>
                <T>client</T>
                <P>.</P>
                <T>wallets</T>
                <P>.</P>
                <F>create</F>
                <P>(</P>
              </CodeLine>
              <CodeLine>
                <T>{'    '}policy</T>
                <P>=</P>
                <S>"Max $500/day on SaaS tools"</S>
              </CodeLine>
              <CodeLine>
                <P>)</P>
              </CodeLine>
              <CodeLine>
                <T>wallet</T>
                <P>.</P>
                <F>pay</F>
                <P>(</P>
                <T>to</T>
                <P>=</P>
                <S>"vendor.eth"</S>
                <P>, </P>
                <T>amount</T>
                <P>=</P>
                <T>99</T>
                <P>, </P>
                <T>token</T>
                <P>=</P>
                <S>"USDC"</S>
                <P>)</P>
              </CodeLine>
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
