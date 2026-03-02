const integrations = [
  {
    name: "Claude / MCP",
    tools: "52 tools",
    desc: "Native Model Context Protocol server. One command to give Claude payment capabilities.",
    icons: ["/icons/integrations/claude.svg", "/icons/integrations/mcp.svg"],
  },
  {
    name: "OpenAI / GPT",
    tools: "Strict JSON",
    desc: "Function calling with strict JSON schema validation. Drop-in for any GPT-based agent.",
    icons: ["/icons/integrations/openai-2.svg"],
  },
  {
    name: "Google Gemini / ADK",
    tools: "Native adapters",
    desc: "FunctionDeclaration adapters for the Agent Development Kit. First-class Gemini support.",
    icons: ["/icons/integrations/gemini.svg"],
  },
  {
    name: "LangChain / CrewAI",
    tools: "Native tools",
    desc: "Tool integrations for LangChain agents and CrewAI multi-agent orchestration workflows.",
    icons: ["/icons/integrations/langchain.svg", "/icons/integrations/crewai.svg"],
  },
  {
    name: "Vercel AI SDK",
    tools: "TypeScript-first",
    desc: "TypeScript-first integration for the Vercel AI SDK. Streaming-compatible tool definitions.",
    icons: ["/icons/integrations/vercel.svg"],
  },
  {
    name: "OpenClaw",
    tools: "Skill",
    desc: "Available as an OpenClaw skill — the fastest way to give any agent financial powers. send_payment, create_card, set_policy.",
    icons: ["/icons/integrations/openclaw.svg"],
  },
  {
    name: "REST API",
    tools: "8 endpoints",
    desc: "OpenAPI 3.0 spec. If your framework speaks HTTP, it works with Sardis.",
    icons: null,
    fallbackIcon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M8 10l-3 2 3 2M16 10l3 2-3 2M13 8l-2 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
];

export default function Integrations() {
  return (
    <section className="w-full" style={{ backgroundColor: 'var(--landing-bg)' }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-[100px] md:pt-[140px]">
        {/* Header */}
        <div className="flex flex-col gap-4 mb-10">
          <span
            className="tracking-widest uppercase"
            style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--landing-blue)' }}
          >
            Works Everywhere
          </span>
          <h2
            className="max-w-[520px]"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 600,
              fontSize: 'clamp(30px, 4.2vw, 40px)',
              lineHeight: 'clamp(36px, 5vw, 46px)',
              color: 'var(--landing-text-primary)',
            }}
          >
            One payment layer. Every AI platform.
          </h2>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {integrations.map((item) => (
            <div
              key={item.name}
              className="flex flex-col gap-4 rounded-[14px] p-8"
              style={{
                backgroundColor: 'var(--landing-surface)',
                border: '1px solid var(--landing-border)',
              }}
            >
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  {item.icons ? (
                    item.icons.map((icon, idx) => (
                      <div
                        key={idx}
                        className="w-10 h-10 rounded-lg flex items-center justify-center overflow-hidden"
                        style={{
                          backgroundColor: 'var(--landing-code-bg)',
                          border: '1px solid var(--landing-border)',
                        }}
                      >
                        <img
                          src={icon}
                          alt=""
                          width={22}
                          height={22}
                          loading="lazy"
                        />
                      </div>
                    ))
                  ) : (
                    <div
                      className="w-10 h-10 rounded-lg flex items-center justify-center overflow-hidden"
                      style={{
                        backgroundColor: 'var(--landing-code-bg)',
                        border: '1px solid var(--landing-border)',
                        color: 'var(--landing-text-tertiary)',
                      }}
                    >
                      {item.fallbackIcon}
                    </div>
                  )}
                </div>
                <div>
                  <h3
                    className="text-[15px] font-semibold"
                    style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--landing-text-primary)' }}
                  >
                    {item.name}
                  </h3>
                  <span
                    className="text-[11px]"
                    style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--landing-text-muted)' }}
                  >
                    {item.tools}
                  </span>
                </div>
              </div>
              <p
                className="text-[13px] font-light leading-[21px]"
                style={{ fontFamily: "'Inter', sans-serif", color: 'var(--landing-text-tertiary)' }}
              >
                {item.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
