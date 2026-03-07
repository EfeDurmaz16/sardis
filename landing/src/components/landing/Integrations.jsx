const integrations = [
  {
    name: "Claude / MCP",
    tools: "52 tools",
    desc: "Native Model Context Protocol server. One command to give Claude payment capabilities.",
    icons: ["/icons/integrations/claude.svg", "/icons/integrations/mcp.svg"],
  },
  {
    name: "OpenAI / Agents SDK",
    tools: "@function_tool",
    desc: "Function calling with strict JSON schema. Native Agents SDK integration with get_sardis_tools().",
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
    tools: "BaseTool",
    desc: "Tool integrations for LangChain agents and CrewAI multi-agent orchestration. create_sardis_toolkit() for instant setup.",
    icons: ["/icons/integrations/langchain.svg", "/icons/integrations/crewai.svg"],
  },
  {
    name: "Vercel AI SDK",
    tools: "tool()",
    desc: "TypeScript-first integration with streaming-compatible tool definitions. Works with generateText and streamText.",
    icons: ["/icons/integrations/vercel.svg"],
  },
  {
    name: "Browser Use",
    tools: "3 actions",
    desc: "Give browser automation agents payment capabilities. register_sardis_actions() on any controller.",
    icons: null,
    fallbackIcon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="1.5" />
        <path d="M3 9h18M9 3v6" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    ),
  },
  {
    name: "AutoGPT",
    tools: "Block SDK",
    desc: "Official payment blocks for AutoGPT. SardisPayBlock, SardisBalanceBlock with Pydantic I/O schemas.",
    icons: null,
    fallbackIcon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    name: "n8n / Activepieces",
    tools: "Workflow nodes",
    desc: "No-code workflow automation. Send payments, check balances, and enforce policies from visual workflows.",
    icons: null,
    fallbackIcon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <circle cx="6" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="18" cy="6" r="3" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="18" cy="18" r="3" stroke="currentColor" strokeWidth="1.5" />
        <path d="M9 11l6-4M9 13l6 4" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    ),
  },
  {
    name: "REST / ChatGPT",
    tools: "OpenAPI 3.1",
    desc: "OpenAPI spec for ChatGPT Actions, Composio, and any HTTP client. If your framework speaks HTTP, it works with Sardis.",
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
            One payment layer. Every AI framework.
          </h2>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {integrations.map((item, i) => (
            <div
              key={item.name}
              className={`flex flex-col gap-4 rounded-[14px] p-8${i === integrations.length - 1 ? ' xl:col-span-3' : ''}`}
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
                          className="dark:invert"
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
