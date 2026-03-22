import Link from 'next/link';
import { Calendar, Clock, ArrowRight } from 'lucide-react';

const posts = [
  {
    title: 'Who Owns Accountability When an AI Agent Moves Money?',
    excerpt: 'When an AI agent pays the wrong vendor, overspends, or gets exploited — who is responsible? The operator, the model provider, the framework, or the agent itself? We break down the accountability gap and how to close it.',
    date: '2026-03-17',
    readTime: '7 min read',
    category: 'Opinion',
    featured: true,
    slug: 'agent-accountability',
  },
  {
    title: 'How AI Agent Spending Rules Actually Work — A Plain-English Guide',
    excerpt: 'No jargon, no code. A practical guide to how Sardis spending policies control what AI agents can and cannot do with money. Written for finance teams, engineering leads, and skeptical buyers.',
    date: '2026-03-17',
    readTime: '6 min read',
    category: 'Explainer',
    featured: true,
    slug: 'spending-rules-explained',
  },
  {
    title: 'Sardis AI Agent Payments: What It Is and How It Works',
    excerpt: 'A practical guide to Sardis AI payments infrastructure for autonomous agents: deterministic policy enforcement, approval controls, virtual cards, and auditable execution.',
    date: '2026-02-25',
    readTime: '4 min read',
    category: 'Technical',
    featured: true,
    slug: 'sardis-ai-agent-payments',
  },
  {
    title: 'Sardis v0.8.4: Packages Live on npm & PyPI + Security Audit',
    excerpt: 'All 19 Sardis packages are now publicly available on npm and PyPI. This release also includes a comprehensive 54-fix security audit covering auth, crypto, input validation, JWT, and more. The hosted API is in private beta with staging/testnet access.',
    date: '2026-02-08',
    readTime: '5 min read',
    category: 'Release',
    featured: true,
    slug: 'sardis-v0-8-4-packages-live',
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
    title: 'Introducing Sardis: Secure Payments for AI Agents',
    excerpt: 'Today we announce Sardis, a Payment OS designed specifically for AI agents. Learn how MPC wallets and policy enforcement enable autonomous financial operations while preventing hallucination-driven spending.',
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
  Security: 'bg-[var(--landing-red)]/10 border-[var(--landing-red)]/30 text-[var(--landing-red)]',
  Tutorial: 'bg-[var(--landing-green)]/10 border-[var(--landing-green)]/30 text-[var(--landing-green)]',
  Technical: 'bg-[var(--landing-blue)]/10 border-[var(--landing-blue)]/30 text-[var(--landing-blue)]',
  Release: 'bg-[var(--sardis-orange)]/10 border-[var(--sardis-orange)]/30 text-[var(--sardis-orange)]',
  Feature: 'bg-[var(--landing-green)]/10 border-[var(--landing-green)]/30 text-[var(--landing-green)]',
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
      <Link href={`/docs/blog/${post.slug}`} className="block">
        <article className="group bg-card/50 rounded-lg p-7 shadow-sm hover:shadow-md transition-all">
          <div className="flex items-center gap-3 mb-5">
            <span className={`px-2 py-1 text-xs font-mono border ${categoryColors[post.category]}`}>
              {post.category.toUpperCase()}
            </span>
            {post.featured && (
              <span className="px-2 py-1 text-xs font-mono bg-[var(--sardis-orange)] text-white">
                FEATURED
              </span>
            )}
          </div>

          <h3 className="text-xl font-bold font-display mb-4 group-hover:text-[var(--sardis-orange)] transition-colors leading-snug">
            {post.title}
          </h3>

          <p className="text-muted-foreground text-sm mb-5 leading-7">
            {post.excerpt}
          </p>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4 text-xs text-muted-foreground font-mono">
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" />
                {formatDate(post.date)}
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
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
    <Link href={`/docs/blog/${post.slug}`} className="block">
      <article className="group bg-card/50 rounded-lg p-5 shadow-sm hover:shadow-md transition-all">
        <div className="flex items-center gap-2 mb-3">
          <span className={`px-2 py-0.5 text-xs font-mono border ${categoryColors[post.category]}`}>
            {post.category.toUpperCase()}
          </span>
        </div>

        <h3 className="font-bold font-display mb-3 group-hover:text-[var(--sardis-orange)] transition-colors leading-snug">
          {post.title}
        </h3>

        <p className="text-muted-foreground text-sm mb-4 line-clamp-2 leading-relaxed">
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
    <article className="prose dark:prose-invert max-w-none">
      <SEO
        title="Sardis Blog"
        description="Product updates, release notes, and technical guides on Sardis AI agent payments infrastructure."
        path="/docs/blog"
        schemas={[
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Blog' },
          ]),
        ]}
      />
      <div className="not-prose mb-10">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-500">
            BLOG
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Blog</h1>
        <p className="text-xl text-muted-foreground leading-relaxed">
          Updates, tutorials, and deep dives from the Sardis team.
        </p>
      </div>

      {/* Featured Posts */}
      <section className="not-prose mb-14">
        <h2 className="text-xl font-bold font-display mb-6 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Featured
        </h2>
        <div className="grid gap-6 md:grid-cols-2">
          {featuredPosts.map((post, idx) => (
            <BlogCard key={idx} post={post} featured />
          ))}
        </div>
      </section>

      {/* All Posts */}
      <section className="not-prose mb-14">
        <h2 className="text-xl font-bold font-display mb-6 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> All Posts
        </h2>
        <div className="grid gap-5 md:grid-cols-2">
          {regularPosts.map((post, idx) => (
            <BlogCard key={idx} post={post} />
          ))}
        </div>
      </section>

      <section className="not-prose p-7 rounded-lg bg-card/50 shadow-sm">
        <h3 className="font-bold font-display mb-3">Subscribe to Updates</h3>
        <p className="text-muted-foreground text-sm mb-5 leading-relaxed">
          Get notified when we publish new articles and release updates.
        </p>
        <WaitlistForm
          ctaLabel="SUBSCRIBE"
          successTitle="Subscribed"
          successDescription="You're subscribed. We'll email you when we publish new posts and product updates."
        />
      </section>
    </article>
  );
}
