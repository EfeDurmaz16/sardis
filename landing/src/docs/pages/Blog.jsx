import { Link } from 'react-router-dom';
import { Calendar, Clock, ArrowRight } from 'lucide-react';

const posts = [
  {
    title: 'Fiat Rails: Bridging Traditional Banking to Agent Wallets',
    excerpt: 'The crypto rails for agent payments are ready. But the real world runs on dollars. Today we announce Fiat Rails — a complete on/off ramp solution that bridges traditional banking to agent wallets with full policy enforcement.',
    date: '2026-01-24',
    readTime: '8 min read',
    category: 'Feature',
    featured: true,
    slug: 'fiat-rails',
  },
  {
    title: 'Why Sardis: The Policy Firewall for Agent Payments',
    excerpt: 'We analyzed the competitive landscape and built Sardis to fill a critical gap: natural language policy enforcement with non-custodial security. See how we compare to Locus, Payman, and Skyfire.',
    date: '2026-01-24',
    readTime: '7 min read',
    category: 'Technical',
    featured: true,
    slug: 'why-sardis',
  },
  {
    title: 'Sardis v0.5: UCP and A2A Protocol Support',
    excerpt: 'Today we release Sardis v0.5 with full support for UCP (Universal Commerce Protocol) and A2A (Agent-to-Agent) protocol. Now your agents can participate in the broader AI agent economy with standardized checkout flows and multi-agent communication.',
    date: '2026-01-24',
    readTime: '6 min read',
    category: 'Release',
    featured: true,
    slug: 'sardis-v0-5-protocols',
  },
  {
    title: 'Understanding AP2: The Industry Standard for Agent Payments',
    excerpt: 'AP2 (Agent Payment Protocol) is the Google, PayPal, Mastercard, and Visa consortium standard. Learn how the Intent → Cart → Payment mandate chain provides cryptographic proof of authorization for every transaction.',
    date: '2026-01-20',
    readTime: '8 min read',
    category: 'Technical',
    featured: true,
    slug: 'understanding-ap2',
  },
  {
    title: 'MCP Server: 36+ Tools for AI Payments',
    excerpt: 'Our MCP server has expanded from 4 tools to 36+. From checkout sessions to agent discovery, learn how to add comprehensive payment capabilities to Claude Desktop and Cursor without writing code.',
    date: '2026-01-18',
    readTime: '5 min read',
    category: 'Tutorial',
    featured: false,
    slug: 'mcp-36-tools',
  },
  {
    title: 'Introducing Sardis: Secure Payments for AI Agents',
    excerpt: 'Today we announce Sardis, a stablecoin execution layer designed specifically for AI agents. Learn how MPC wallets and policy enforcement enable autonomous financial operations while preventing hallucination-driven spending.',
    date: '2025-01-15',
    readTime: '5 min read',
    category: 'Announcement',
    featured: false,
    slug: 'introducing-sardis',
  },
  {
    title: 'Financial Hallucination Prevention: Why AI Needs Guardrails',
    excerpt: 'AI agents can hallucinate facts, and they can hallucinate financial transactions. We explore the risks of unconstrained AI spending and how cryptographic policy enforcement provides the solution.',
    date: '2025-01-10',
    readTime: '8 min read',
    category: 'Security',
    featured: false,
    slug: 'financial-hallucination-prevention',
  },
  {
    title: 'MCP Integration: Zero-Code AI Payments in Claude',
    excerpt: 'With our new Model Context Protocol server, you can add payment capabilities to Claude Desktop without writing a single line of code. Here\'s how to get started in under 5 minutes.',
    date: '2025-01-08',
    readTime: '3 min read',
    category: 'Tutorial',
    featured: false,
    slug: 'mcp-integration',
  },
  {
    title: 'Understanding MPC Wallets for Agent Security',
    excerpt: 'Multi-Party Computation wallets distribute key shares across parties, ensuring no single entity can move funds. Learn how this technology secures AI agent transactions at the cryptographic level.',
    date: '2025-01-05',
    readTime: '10 min read',
    category: 'Technical',
    featured: false,
    slug: 'mpc-wallets',
  },
  {
    title: 'Policy Engine Deep Dive: Configuring Spending Rules',
    excerpt: 'Explore the full capabilities of the Sardis policy engine. From simple spending limits to complex vendor allowlists and time-based rules, learn how to configure exactly what your agents can spend.',
    date: '2024-12-28',
    readTime: '12 min read',
    category: 'Technical',
    featured: false,
    slug: 'policy-engine-deep-dive',
  },
];

const categoryColors = {
  Announcement: 'bg-[var(--sardis-orange)]/10 border-[var(--sardis-orange)]/30 text-[var(--sardis-orange)]',
  Security: 'bg-red-500/10 border-red-500/30 text-red-500',
  Tutorial: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500',
  Technical: 'bg-blue-500/10 border-blue-500/30 text-blue-500',
  Release: 'bg-purple-500/10 border-purple-500/30 text-purple-500',
  Feature: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500',
};

function BlogCard({ post, featured = false }) {
  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (featured) {
    return (
      <Link to={`/docs/blog/${post.slug}`} className="block">
        <article className="group border border-border p-6 hover:border-[var(--sardis-orange)]/50 transition-colors">
          <div className="flex items-center gap-3 mb-4">
            <span className={`px-2 py-1 text-xs font-mono border ${categoryColors[post.category]}`}>
              {post.category.toUpperCase()}
            </span>
            {post.featured && (
              <span className="px-2 py-1 text-xs font-mono bg-[var(--sardis-orange)] text-white">
                FEATURED
              </span>
            )}
          </div>

          <h3 className="text-xl font-bold font-display mb-3 group-hover:text-[var(--sardis-orange)] transition-colors">
            {post.title}
          </h3>

          <p className="text-muted-foreground text-sm mb-4 leading-relaxed">
            {post.excerpt}
          </p>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4 text-xs text-muted-foreground font-mono">
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {formatDate(post.date)}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {post.readTime}
              </span>
            </div>

            <span className="flex items-center gap-1 text-sm text-[var(--sardis-orange)] font-medium group-hover:gap-2 transition-all">
              Read <ArrowRight className="w-4 h-4" />
            </span>
          </div>
        </article>
      </Link>
    );
  }

  return (
    <Link to={`/docs/blog/${post.slug}`} className="block">
      <article className="group border border-border p-4 hover:border-[var(--sardis-orange)]/50 transition-colors">
        <div className="flex items-center gap-2 mb-2">
          <span className={`px-2 py-0.5 text-xs font-mono border ${categoryColors[post.category]}`}>
            {post.category.toUpperCase()}
          </span>
        </div>

        <h3 className="font-bold font-display mb-2 group-hover:text-[var(--sardis-orange)] transition-colors">
          {post.title}
        </h3>

        <p className="text-muted-foreground text-sm mb-3 line-clamp-2">
          {post.excerpt}
        </p>

        <div className="flex items-center gap-3 text-xs text-muted-foreground font-mono">
          <span>{formatDate(post.date)}</span>
          <span>{post.readTime}</span>
        </div>
      </article>
    </Link>
  );
}

export default function DocsBlog() {
  const featuredPosts = posts.filter(p => p.featured);
  const regularPosts = posts.filter(p => !p.featured);

  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-500">
            BLOG
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Blog</h1>
        <p className="text-xl text-muted-foreground">
          Updates, tutorials, and deep dives from the Sardis team.
        </p>
      </div>

      {/* Featured Posts */}
      <section className="not-prose mb-12">
        <h2 className="text-xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Featured
        </h2>
        <div className="grid gap-6 md:grid-cols-2">
          {featuredPosts.map((post, idx) => (
            <BlogCard key={idx} post={post} featured />
          ))}
        </div>
      </section>

      {/* All Posts */}
      <section className="not-prose mb-12">
        <h2 className="text-xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> All Posts
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          {regularPosts.map((post, idx) => (
            <BlogCard key={idx} post={post} />
          ))}
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/20">
        <h3 className="font-bold font-display mb-2">Subscribe to Updates</h3>
        <p className="text-muted-foreground text-sm mb-4">
          Get notified when we publish new articles and release updates.
        </p>
        <form className="flex gap-2">
          <input
            type="email"
            placeholder="Enter your email"
            className="flex-1 px-4 py-2 bg-background border border-border text-sm font-mono focus:outline-none focus:border-[var(--sardis-orange)]"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-[var(--sardis-orange)] text-white font-medium text-sm hover:bg-[var(--sardis-orange)]/90 transition-colors"
          >
            Subscribe
          </button>
        </form>
      </section>
    </article>
  );
}
