import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Blog",
  description:
    "News, insights, and technical deep dives on AI agent payments, spending policies, and the agent economy.",
  alternates: { canonical: "https://www.sardis.sh/blog" },
};

const posts = [
  {
    slug: "why-agents-need-wallets",
    title: "Why AI Agents Need Their Own Wallets",
    excerpt:
      "Shared corporate cards were built for humans. AI agents need programmable, policy-controlled wallets with per-agent visibility and cryptographic audit trails.",
    date: "2026-03-20",
    category: "Product",
  },
  {
    slug: "natural-language-policies",
    title: "Natural Language Spending Policies: How They Work",
    excerpt:
      "A deep dive into Sardis's 12-check enforcement pipeline. From plain English rules to deterministic execution with signed attestation envelopes.",
    date: "2026-03-15",
    category: "Technical",
  },
  {
    slug: "ap2-protocol-explained",
    title: "AP2: The Agent Payment Protocol Explained",
    excerpt:
      "Google, PayPal, Visa, and Mastercard are building the standard for agent commerce. Here's how Sardis implements AP2 with full mandate chain verification.",
    date: "2026-03-10",
    category: "Ecosystem",
  },
  {
    slug: "mcp-server-52-tools",
    title: "52 MCP Tools: Giving Claude Financial Superpowers",
    excerpt:
      "Our Model Context Protocol server gives Claude Desktop full access to wallets, payments, treasury management, and compliance -- all within policy bounds.",
    date: "2026-03-05",
    category: "Integration",
  },
  {
    slug: "kill-switch-design",
    title: "Designing the Kill Switch: 5 Scopes of Control",
    excerpt:
      "How we built instant financial freeze capabilities across global, organization, agent, rail, and chain scopes with sub-second propagation.",
    date: "2026-02-28",
    category: "Technical",
  },
  {
    slug: "spending-mandates-architecture",
    title: "Spending Mandates: Delegating Financial Authority to Agents",
    excerpt:
      "The hard part is not access to money -- it is controlling authority over money. How spending mandates create a trust chain from human to agent.",
    date: "2026-02-20",
    category: "Product",
  },
];

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function BlogPage() {
  return (
    <div
      className="min-h-screen"
      style={{ backgroundColor: "var(--landing-bg)" }}
    >
      {/* Hero */}
      <section className="pt-20 pb-12">
        <div className="max-w-4xl mx-auto px-5">
          <p
            className="text-xs font-semibold uppercase tracking-widest mb-4"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              color: "var(--landing-blue)",
            }}
          >
            BLOG
          </p>
          <h1
            className="text-4xl md:text-5xl font-bold tracking-[-0.04em] mb-4"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              color: "var(--landing-text-primary)",
            }}
          >
            Insights & Updates
          </h1>
          <p
            className="text-base max-w-2xl"
            style={{
              fontFamily: "'Inter', sans-serif",
              color: "var(--landing-text-tertiary)",
            }}
          >
            Technical deep dives, product updates, and ecosystem analysis from
            the Sardis team.
          </p>
        </div>
      </section>

      {/* Posts */}
      <section className="pb-20">
        <div className="max-w-4xl mx-auto px-5">
          <div className="flex flex-col gap-4">
            {posts.map((post) => (
              <Link
                key={post.slug}
                href={`/docs/blog/${post.slug}`}
                className="block rounded-[14px] p-6 md:p-8 transition-colors hover:border-[var(--landing-accent)]"
                style={{
                  backgroundColor: "var(--landing-surface)",
                  border: "1px solid var(--landing-border)",
                }}
              >
                <div className="flex items-center gap-3 mb-3">
                  <span
                    className="text-[11px] uppercase tracking-wider font-medium px-2 py-0.5 rounded"
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      background: "rgba(59,130,246,0.1)",
                      color: "#3B82F6",
                      border: "1px solid rgba(59,130,246,0.15)",
                    }}
                  >
                    {post.category}
                  </span>
                  <span
                    className="text-[12px]"
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      color: "var(--landing-text-ghost)",
                    }}
                  >
                    {formatDate(post.date)}
                  </span>
                </div>
                <h2
                  className="font-semibold mb-2"
                  style={{
                    fontFamily: "'Space Grotesk', sans-serif",
                    fontSize: "20px",
                    lineHeight: "28px",
                    color: "var(--landing-text-primary)",
                  }}
                >
                  {post.title}
                </h2>
                <p
                  className="text-[14px] font-light leading-[22px]"
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    color: "var(--landing-text-tertiary)",
                  }}
                >
                  {post.excerpt}
                </p>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
