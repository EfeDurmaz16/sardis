import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock, Share2 } from "lucide-react";

export default function PolicyEngineDeepDive() {
  return (
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
          <span className="px-2 py-1 text-xs font-mono bg-blue-500/10 border border-blue-500/30 text-blue-500">
            TECHNICAL
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">
          Policy Engine Deep Dive: Configuring Spending Rules
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            December 28, 2024
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            12 min read
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="prose prose-invert max-w-none">
        <p className="lead text-xl text-muted-foreground">
          Explore the full capabilities of the Sardis policy engine. From simple
          spending limits to complex vendor allowlists and time-based rules,
          learn how to configure exactly what your agents can spend.
        </p>

        <h2>Why Policies Matter</h2>
        <p>
          Giving AI agents the ability to spend money is powerful - and
          dangerous. Without proper controls, an agent could:
        </p>
        <ul>
          <li>Overspend on a single transaction</li>
          <li>Make purchases from untrusted vendors</li>
          <li>Exceed your intended budget over time</li>
          <li>Make purchases outside business hours or contexts</li>
        </ul>
        <p>
          The Sardis policy engine lets you define precise rules that are
          enforced cryptographically. Your agent literally cannot exceed these
          limits - it's not just a suggestion, it's a cryptographic guarantee.
        </p>

        <h2>Policy Basics</h2>
        <p>
          A policy is a JSON object that defines what transactions are allowed.
          Here's the simplest possible policy:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`{
  "maxPerTransaction": 100
}`}
          </pre>
        </div>

        <p>
          This policy allows any transaction up to $100. Simple, but probably
          too permissive for production.
        </p>

        <h2>Spending Limits</h2>
        <p>
          You can set limits at multiple levels:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`{
  "maxPerTransaction": 50,      // Max $50 per transaction
  "dailyLimit": 500,            // Max $500 per day
  "weeklyLimit": 2000,          // Max $2000 per week
  "monthlyLimit": 5000          // Max $5000 per month
}`}
          </pre>
        </div>

        <p>
          All limits are cumulative. A transaction that would exceed any limit
          is rejected.
        </p>

        <h2>Vendor Allowlists</h2>
        <p>
          Restrict transactions to specific vendors:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`{
  "maxPerTransaction": 100,
  "allowedVendors": [
    "github.com",
    "aws.amazon.com",
    "openai.com",
    "anthropic.com"
  ]
}`}
          </pre>
        </div>

        <p>
          With this policy, your agent can only pay vendors in the allowlist.
          Any other vendor is automatically rejected.
        </p>

        <h3>Wildcard Patterns</h3>
        <p>
          You can use wildcards to allow entire domains:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`{
  "allowedVendors": [
    "*.amazonaws.com",    // All AWS services
    "api.*.com",          // Any api.X.com domain
    "github.com"          // Exact match
  ]
}`}
          </pre>
        </div>

        <h2>Category-Based Rules</h2>
        <p>
          Instead of listing specific vendors, you can allow categories:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`{
  "maxPerTransaction": 200,
  "allowedCategories": [
    "cloud_infrastructure",
    "developer_tools",
    "saas_subscriptions"
  ],
  "blockedCategories": [
    "gambling",
    "adult_content",
    "cryptocurrency_exchanges"
  ]
}`}
          </pre>
        </div>

        <p>
          Categories are determined by our vendor classification system. You can
          also combine categories with explicit vendor lists.
        </p>

        <h2>Time-Based Rules</h2>
        <p>
          Restrict when transactions can occur:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`{
  "maxPerTransaction": 100,
  "timeRestrictions": {
    "allowedDays": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "allowedHours": {
      "start": "09:00",
      "end": "18:00",
      "timezone": "America/New_York"
    }
  }
}`}
          </pre>
        </div>

        <p>
          This policy only allows transactions during business hours on
          weekdays. Perfect for agents that shouldn't be spending overnight.
        </p>

        <h2>Velocity Controls</h2>
        <p>
          Detect and prevent unusual spending patterns:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`{
  "maxPerTransaction": 100,
  "velocityRules": {
    "maxTransactionsPerHour": 10,
    "maxTransactionsPerDay": 50,
    "maxUniqueVendorsPerDay": 5,
    "cooldownAfterRejection": "5m"
  }
}`}
          </pre>
        </div>

        <p>
          Velocity rules help detect compromised agents or unusual behavior.
          After a rejection, the agent must wait before trying again.
        </p>

        <h2>Conditional Rules</h2>
        <p>
          Apply different limits based on conditions:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`{
  "rules": [
    {
      "condition": {
        "vendor": "aws.amazon.com",
        "category": "cloud_infrastructure"
      },
      "limits": {
        "maxPerTransaction": 500,
        "dailyLimit": 2000
      }
    },
    {
      "condition": {
        "category": "saas_subscriptions"
      },
      "limits": {
        "maxPerTransaction": 50,
        "dailyLimit": 200
      }
    }
  ],
  "defaultLimits": {
    "maxPerTransaction": 25,
    "dailyLimit": 100
  }
}`}
          </pre>
        </div>

        <p>
          Rules are evaluated in order. The first matching rule applies. If no
          rule matches, default limits are used.
        </p>

        <h2>Approval Workflows</h2>
        <p>
          Require human approval for certain transactions:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`{
  "maxPerTransaction": 1000,
  "approvalRequired": {
    "threshold": 100,              // Require approval over $100
    "vendors": ["newvendor.com"],  // Always require for new vendors
    "categories": ["high_risk"],   // Always require for risky categories
    "approvers": ["admin@company.com"],
    "timeout": "24h"               // Auto-reject if not approved
  }
}`}
          </pre>
        </div>

        <p>
          When approval is required, the transaction is held pending until an
          approver confirms or rejects it.
        </p>

        <h2>Reason Requirements</h2>
        <p>
          Force agents to explain their purchases:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`{
  "maxPerTransaction": 100,
  "requireReason": true,
  "reasonMinLength": 20,
  "flaggedReasonPatterns": [
    "testing",
    "just because",
    "no reason"
  ]
}`}
          </pre>
        </div>

        <p>
          With this policy, every transaction must include a reason. Short or
          suspicious reasons are flagged for review.
        </p>

        <h2>Complete Example</h2>
        <p>
          Here's a production-ready policy for a development team's AI agent:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`{
  "name": "dev-team-agent-policy",
  "version": "1.0.0",

  "rules": [
    {
      "name": "aws-infrastructure",
      "condition": { "vendor": "*.amazonaws.com" },
      "limits": {
        "maxPerTransaction": 500,
        "dailyLimit": 2000
      }
    },
    {
      "name": "developer-subscriptions",
      "condition": {
        "vendors": ["github.com", "jetbrains.com", "figma.com"]
      },
      "limits": {
        "maxPerTransaction": 100,
        "monthlyLimit": 500
      }
    }
  ],

  "defaultLimits": {
    "maxPerTransaction": 25,
    "dailyLimit": 100,
    "monthlyLimit": 500
  },

  "blockedCategories": ["gambling", "adult_content"],

  "velocityRules": {
    "maxTransactionsPerHour": 5,
    "maxUniqueVendorsPerDay": 3
  },

  "timeRestrictions": {
    "allowedDays": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "allowedHours": { "start": "08:00", "end": "20:00", "timezone": "UTC" }
  },

  "requireReason": true,

  "approvalRequired": {
    "threshold": 200,
    "approvers": ["finance@company.com"]
  }
}`}
          </pre>
        </div>

        <h2>Policy Versioning</h2>
        <p>
          Policies can be versioned and updated without changing wallets:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`// Update policy via SDK
await wallet.updatePolicy({
  version: "1.1.0",
  changes: {
    maxPerTransaction: 75  // Increased from 50
  }
});

// Or via CLI
sardis policy update --wallet wallet_xxx --file new-policy.json`}
          </pre>
        </div>

        <p>
          Policy changes take effect immediately. Old versions are kept for
          audit purposes.
        </p>

        <h2>Testing Policies</h2>
        <p>
          Use our policy simulator to test before deploying:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`import { PolicySimulator } from '@sardis/sdk';

const simulator = new PolicySimulator(myPolicy);

// Test transactions
simulator.test({ amount: 50, vendor: 'github.com' });
// -> ALLOWED

simulator.test({ amount: 500, vendor: 'unknown.com' });
// -> REJECTED: exceeds maxPerTransaction, vendor not allowed`}
          </pre>
        </div>

        <h2>Best Practices</h2>
        <ol>
          <li>
            <strong>Start strict, loosen over time.</strong> Begin with tight
            limits and expand as you build confidence.
          </li>
          <li>
            <strong>Use allowlists over blocklists.</strong> It's safer to
            approve specific vendors than to try blocking bad ones.
          </li>
          <li>
            <strong>Always require reasons.</strong> Even if you don't review
            them, they create an audit trail.
          </li>
          <li>
            <strong>Set velocity limits.</strong> Even with good per-transaction
            limits, runaway agents can do damage through volume.
          </li>
          <li>
            <strong>Review and update regularly.</strong> As your agent's use
            cases evolve, so should your policies.
          </li>
        </ol>
      </div>

      {/* Footer */}
      <footer className="not-prose mt-12 pt-8 border-t border-border">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground font-mono">
            Written by the Sardis Platform Team
          </div>
          <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors">
            <Share2 className="w-4 h-4" />
            Share
          </button>
        </div>
      </footer>
    </article>
  );
}
