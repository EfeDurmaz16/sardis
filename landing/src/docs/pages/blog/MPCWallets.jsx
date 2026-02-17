import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock, Share2 } from "lucide-react";
import SEO, { createArticleSchema, createBreadcrumbSchema } from '@/components/SEO';

export default function MPCWallets() {
  return (
    <>
      <SEO
        title="Understanding MPC Wallets for Agent Security"
        description="Multi-Party Computation wallets distribute key shares so no single entity can move funds. Learn how Sardis uses threshold ECDSA to provide non-custodial, policy-enforced wallets for AI agents."
        path="/docs/blog/mpc-wallets"
        type="article"
        article={{ publishedDate: '2025-01-05' }}
        schemas={[
          createArticleSchema({
            title: 'Understanding MPC Wallets for Agent Security',
            description: 'Multi-Party Computation wallets distribute key shares so no single entity can move funds. Learn how Sardis uses threshold ECDSA to provide non-custodial, policy-enforced wallets for AI agents.',
            path: '/docs/blog/mpc-wallets',
            publishedDate: '2025-01-05',
          }),
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Blog', href: '/docs/blog' },
            { name: 'MPC Wallets' },
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
          <span className="px-2 py-1 text-xs font-mono bg-blue-500/10 border border-blue-500/30 text-blue-500">
            TECHNICAL
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">
          Understanding MPC Wallets for Agent Security
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            January 5, 2025
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            10 min read
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="prose prose-invert max-w-none">
        <p className="lead text-xl text-muted-foreground">
          Multi-Party Computation wallets distribute key shares across parties,
          ensuring no single entity can move funds. Learn how this technology
          secures AI agent transactions at the cryptographic level.
        </p>

        <h2>The Problem with Traditional Wallets</h2>
        <p>
          Traditional cryptocurrency wallets rely on a single private key. If
          you have the key, you can move the funds. Full stop. This creates two
          problems for AI agents:
        </p>
        <ol>
          <li>
            <strong>Single point of failure:</strong> If the agent's key is
            compromised, all funds are at risk
          </li>
          <li>
            <strong>No spending controls:</strong> Whoever holds the key has
            unlimited authority - there's no way to enforce policies at the
            cryptographic level
          </li>
        </ol>
        <p>
          You could try to solve this with smart contracts, but that adds
          complexity and gas costs to every transaction. MPC offers a cleaner
          solution.
        </p>

        <h2>What is Multi-Party Computation?</h2>
        <p>
          Multi-Party Computation (MPC) is a cryptographic technique that allows
          multiple parties to jointly compute a function while keeping their
          inputs private. In the context of wallets, this means:
        </p>
        <ul>
          <li>The private key is split into multiple "shares"</li>
          <li>Each party holds one share</li>
          <li>
            To sign a transaction, parties collaborate without ever revealing
            their shares
          </li>
          <li>
            No single party ever has access to the complete private key
          </li>
        </ul>

        <h2>How Sardis Uses MPC</h2>
        <p>
          In Sardis, every agent wallet uses a 2-of-2 MPC scheme. Here's how the
          shares are distributed:
        </p>

        <div className="not-prose border border-border p-6 mb-6">
          <div className="grid md:grid-cols-2 gap-6">
            <div className="border border-border p-4">
              <div className="font-mono text-sm text-[var(--sardis-orange)] mb-2">
                SHARE 1: YOUR AGENT
              </div>
              <div className="text-muted-foreground text-sm">
                Held locally by your agent or in your secure infrastructure.
                This share can initiate transactions but cannot complete them
                alone.
              </div>
            </div>
            <div className="border border-border p-4">
              <div className="font-mono text-sm text-[var(--sardis-orange)] mb-2">
                SHARE 2: SARDIS POLICY ENGINE
              </div>
              <div className="text-muted-foreground text-sm">
                Held by Sardis. Will only co-sign transactions that pass your
                policy checks. Acts as a programmable guardian.
              </div>
            </div>
          </div>
        </div>

        <h2>The Transaction Flow</h2>
        <p>When your agent wants to make a payment, here's what happens:</p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border">
          <div className="text-muted-foreground mb-2">
            1. Agent requests payment: $50 to vendor.com
          </div>
          <div className="text-muted-foreground mb-2">
            2. Agent's share creates partial signature
          </div>
          <div className="text-muted-foreground mb-2">
            3. Request sent to Sardis Policy Engine
          </div>
          <div className="text-muted-foreground mb-2">
            4. Policy Engine checks:
          </div>
          <div className="text-emerald-400 ml-4 mb-1">
            ✓ Amount under $100 limit
          </div>
          <div className="text-emerald-400 ml-4 mb-1">
            ✓ Vendor in allowlist
          </div>
          <div className="text-emerald-400 ml-4 mb-1">
            ✓ Daily limit not exceeded
          </div>
          <div className="text-muted-foreground mb-2">
            5. Policy Engine co-signs with Share 2
          </div>
          <div className="text-muted-foreground mb-2">
            6. Complete signature submitted to blockchain
          </div>
          <div className="text-emerald-400">7. Transaction confirmed</div>
        </div>

        <h2>Security Properties</h2>

        <h3>Non-Custodial</h3>
        <p>
          Sardis never has full control over your funds. We only hold one share
          of the key - we cannot move funds without your agent's participation.
          This is fundamentally different from custodial solutions where a third
          party holds your keys.
        </p>

        <h3>Tamper-Proof Policy Enforcement</h3>
        <p>
          Because the policy engine controls a required key share, policies
          cannot be bypassed. Even if an agent is compromised or behaves
          unexpectedly, it cannot exceed the limits you've set.
        </p>

        <h3>No Single Point of Failure</h3>
        <p>
          If Sardis is compromised, attackers only get one key share -
          insufficient to move funds. If your agent is compromised, same
          situation. Both parties would need to be compromised simultaneously.
        </p>

        <h3>Audit Trail</h3>
        <p>
          Every signing request is logged with full context: what the agent was
          trying to do, why it needed the funds, and whether the policy allowed
          it. This creates a complete audit trail for compliance and debugging.
        </p>

        <h2>Comparison with Alternatives</h2>

        <div className="not-prose border border-border mb-6 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/20">
                <th className="text-left p-3 font-mono">Feature</th>
                <th className="text-left p-3 font-mono">Single-Key</th>
                <th className="text-left p-3 font-mono">Multisig</th>
                <th className="text-left p-3 font-mono">MPC</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3">Non-custodial</td>
                <td className="p-3 text-emerald-400">Yes</td>
                <td className="p-3 text-emerald-400">Yes</td>
                <td className="p-3 text-emerald-400">Yes</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3">Policy enforcement</td>
                <td className="p-3 text-red-400">No</td>
                <td className="p-3 text-yellow-400">Limited</td>
                <td className="p-3 text-emerald-400">Yes</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3">Gas efficient</td>
                <td className="p-3 text-emerald-400">Yes</td>
                <td className="p-3 text-red-400">No</td>
                <td className="p-3 text-emerald-400">Yes</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3">Chain agnostic</td>
                <td className="p-3 text-emerald-400">Yes</td>
                <td className="p-3 text-red-400">No</td>
                <td className="p-3 text-emerald-400">Yes</td>
              </tr>
              <tr>
                <td className="p-3">Key rotation</td>
                <td className="p-3 text-red-400">Hard</td>
                <td className="p-3 text-yellow-400">Moderate</td>
                <td className="p-3 text-emerald-400">Easy</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2>Technical Deep Dive: Threshold Signatures</h2>
        <p>
          Under the hood, Sardis uses threshold ECDSA signatures based on the
          GG20 protocol. Here's a simplified view of the math:
        </p>
        <ol>
          <li>
            During wallet creation, a trusted dealer generates the private key
            and splits it into shares using Shamir's Secret Sharing
          </li>
          <li>
            Shares are distributed to parties (in our case: your agent and
            Sardis)
          </li>
          <li>
            During signing, parties engage in a multi-round protocol to produce
            a valid ECDSA signature
          </li>
          <li>
            The resulting signature is indistinguishable from a normal single-
            key signature - the blockchain never knows MPC was used
          </li>
        </ol>

        <h2>Key Rotation and Recovery</h2>
        <p>
          One advantage of MPC is easy key rotation. Without changing the wallet
          address, we can refresh the key shares. This allows:
        </p>
        <ul>
          <li>
            Regular rotation as a security best practice
          </li>
          <li>
            Rotation after suspected compromise
          </li>
          <li>
            Recovery if one party loses their share (through a secure recovery
            process)
          </li>
        </ul>

        <h2>Getting Started</h2>
        <p>
          Every Sardis wallet uses MPC by default - no extra configuration
          needed. When you create a wallet through our SDK or dashboard, the MPC
          setup happens automatically. Your agent receives its key share, and
          you can start transacting immediately.
        </p>
      </div>

      {/* Footer */}
      <footer className="not-prose mt-12 pt-8 border-t border-border">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground font-mono">
            Written by the Sardis Cryptography Team
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
