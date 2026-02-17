import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock, Share2 } from "lucide-react";
import SEO, { createArticleSchema, createBreadcrumbSchema } from '@/components/SEO';

export default function MCPIntegration() {
  return (
    <>
      <SEO
        title="MCP Integration: Zero-Code AI Payments in Claude"
        description="Add Sardis payment capabilities to Claude Desktop in under 5 minutes using the MCP server. No code required — configure wallets, execute payments, and manage spending policies through natural conversation."
        path="/docs/blog/mcp-integration"
        type="article"
        article={{ publishedDate: '2025-01-08' }}
        schemas={[
          createArticleSchema({
            title: 'MCP Integration: Zero-Code AI Payments in Claude',
            description: 'Add Sardis payment capabilities to Claude Desktop in under 5 minutes using the MCP server. No code required — configure wallets, execute payments, and manage spending policies through natural conversation.',
            path: '/docs/blog/mcp-integration',
            publishedDate: '2025-01-08',
          }),
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Blog', href: '/docs/blog' },
            { name: 'MCP Integration' },
          ]),
        ]}
      />
    <article className="prose prose-invert max-w-none">
      {/* Back link */}
      <div className="not-prose mb-8">
        <Link
          to="/docs/blog"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Blog
        </Link>
      </div>

      {/* Header */}
      <header className="not-prose mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="px-2 py-1 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">
            TUTORIAL
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">
          MCP Integration: Zero-Code AI Payments in Claude
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            January 8, 2025
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />3 min read
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="prose prose-invert max-w-none">
        <p className="lead text-xl text-muted-foreground">
          With our new Model Context Protocol server, you can add payment
          capabilities to Claude Desktop without writing a single line of code.
          Here's how to get started in under 5 minutes.
        </p>

        <h2>What is MCP?</h2>
        <p>
          Model Context Protocol (MCP) is Anthropic's standard for connecting AI
          assistants to external tools and data sources. Think of it as a plugin
          system for Claude - you can extend its capabilities by adding MCP
          servers.
        </p>
        <p>
          Sardis provides an MCP server that gives Claude the ability to check
          wallet balances, review transaction history, and make payments - all
          within the bounds of your configured policy.
        </p>

        <h2>Prerequisites</h2>
        <ul>
          <li>Claude Desktop installed (macOS or Windows)</li>
          <li>Node.js 18 or higher</li>
          <li>A Sardis account (free tier available)</li>
        </ul>

        <h2>Step 1: Install the MCP Server</h2>
        <p>
          The fastest way to get started is using npx, which downloads and runs
          our server automatically:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border">
          <div className="text-emerald-400">$ npx @sardis/mcp-server start</div>
        </div>

        <p>
          On first run, this will prompt you to log in to your Sardis account
          and configure your wallet.
        </p>

        <h2>Step 2: Configure Claude Desktop</h2>
        <p>
          Open your Claude Desktop configuration file. On macOS, it's located
          at:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border">
          <code>~/Library/Application Support/Claude/claude_desktop_config.json</code>
        </div>

        <p>Add the Sardis server to your configuration:</p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"]
    }
  }
}`}
          </pre>
        </div>

        <h2>Step 3: Restart Claude Desktop</h2>
        <p>
          After saving the configuration, restart Claude Desktop. You should see
          the Sardis tools available in the tools menu (the hammer icon).
        </p>

        <h2>Step 4: Test It Out</h2>
        <p>Try asking Claude:</p>
        <ul>
          <li>"What's my Sardis wallet balance?"</li>
          <li>"Show me my recent transactions"</li>
          <li>"Can you pay $5 to test@example.com?"</li>
        </ul>

        <p>
          Claude will use the Sardis MCP tools to check your balance, review
          history, and (if your policy allows) execute payments.
        </p>

        <h2>Setting Up Policies</h2>
        <p>
          By default, the MCP server runs with conservative policies. You can
          customize these in the Sardis dashboard or by passing a policy file:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border">
          <div className="text-emerald-400">
            $ npx @sardis/mcp-server start --policy ./my-policy.json
          </div>
        </div>

        <p>Example policy file:</p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`{
  "maxPerTransaction": 25,
  "dailyLimit": 100,
  "requireConfirmation": true,
  "allowedCategories": ["subscriptions", "tools"]
}`}
          </pre>
        </div>

        <h2>Available Tools</h2>
        <p>The Sardis MCP server exposes the following tools to Claude:</p>

        <div className="not-prose border border-border mb-6">
          <div className="border-b border-border p-4">
            <div className="font-mono text-sm text-[var(--sardis-orange)]">
              sardis_get_balance
            </div>
            <div className="text-muted-foreground text-sm mt-1">
              Returns current wallet balance in USDC
            </div>
          </div>
          <div className="border-b border-border p-4">
            <div className="font-mono text-sm text-[var(--sardis-orange)]">
              sardis_list_transactions
            </div>
            <div className="text-muted-foreground text-sm mt-1">
              Lists recent transactions with amount, vendor, and status
            </div>
          </div>
          <div className="border-b border-border p-4">
            <div className="font-mono text-sm text-[var(--sardis-orange)]">
              sardis_pay
            </div>
            <div className="text-muted-foreground text-sm mt-1">
              Initiates a payment (subject to policy approval)
            </div>
          </div>
          <div className="p-4">
            <div className="font-mono text-sm text-[var(--sardis-orange)]">
              sardis_get_policy
            </div>
            <div className="text-muted-foreground text-sm mt-1">
              Returns current policy configuration
            </div>
          </div>
        </div>

        <h2>Security Considerations</h2>
        <p>
          The MCP server never has direct access to your private keys. All
          transactions are signed using MPC (Multi-Party Computation), where
          Sardis holds one key share and you hold another. This means:
        </p>
        <ul>
          <li>Sardis cannot move funds without your approval</li>
          <li>
            The MCP server cannot exceed policy limits even if compromised
          </li>
          <li>All transactions are logged and auditable</li>
        </ul>

        <h2>Next Steps</h2>
        <p>
          Now that you have Sardis working with Claude, check out our other
          tutorials on setting up custom policies and integrating with your
          existing workflows.
        </p>
      </div>

      {/* Footer */}
      <footer className="not-prose mt-12 pt-8 border-t border-border">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground font-mono">
            Written by the Sardis Developer Relations Team
          </div>
          <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors">
            <Share2 className="w-4 h-4" />
            Share
          </button>
        </div>
      </footer>
    </article>
    </>
  );
}
