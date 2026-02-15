export default function DocsBlockchainInfrastructure() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            INFRASTRUCTURE
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Blockchain Infrastructure</h1>
        <p className="text-xl text-muted-foreground">
          How Sardis uses blockchain technology under the hood to provide secure, non-custodial payment infrastructure for AI agents.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Why Blockchain?
        </h2>
        <p className="text-muted-foreground mb-4">
          Sardis uses stablecoins (USDC) as a settlement rail — not as a product feature. Blockchain gives us three things that traditional payment rails can't:
        </p>
        <ul className="space-y-3 text-muted-foreground mb-6">
          <li className="flex items-start gap-2">
            <span className="text-[var(--sardis-orange)] mt-1">→</span>
            <div><strong className="text-foreground">Non-custodial by design</strong> — funds live in smart contract wallets, not our bank account. No trust assumption needed.</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--sardis-orange)] mt-1">→</span>
            <div><strong className="text-foreground">Programmable money</strong> — spending policies are enforced on-chain. Rules can't be bypassed, even by us.</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--sardis-orange)] mt-1">→</span>
            <div><strong className="text-foreground">Real-time settlement</strong> — no T+2 delays. Payments settle in seconds, not days.</div>
          </li>
        </ul>
        <div className="not-prose p-4 border border-[var(--sardis-orange)]/20 bg-[var(--sardis-orange)]/5 mb-6">
          <p className="text-sm text-muted-foreground">
            <strong className="text-foreground">Note:</strong> End users never interact with blockchain directly.
            Sardis abstracts all complexity — your agents pay in dollars, and we handle the infrastructure.
          </p>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Supported Chains
        </h2>
        <p className="text-muted-foreground mb-6">
          Sardis supports multiple L1 and L2 networks for settlement. Chain selection is automatic — we route to the cheapest and fastest available rail.
        </p>

        <div className="not-prose">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 font-mono font-bold text-foreground">Chain</th>
                  <th className="text-left py-3 px-4 font-mono font-bold text-foreground">Type</th>
                  <th className="text-left py-3 px-4 font-mono font-bold text-foreground">Tokens</th>
                  <th className="text-left py-3 px-4 font-mono font-bold text-foreground">Avg. Cost</th>
                  <th className="text-left py-3 px-4 font-mono font-bold text-foreground">Settlement</th>
                </tr>
              </thead>
              <tbody className="text-muted-foreground">
                <tr className="border-b border-border/50">
                  <td className="py-3 px-4 font-mono text-[var(--sardis-orange)]">Base</td>
                  <td className="py-3 px-4">L2 (Optimistic)</td>
                  <td className="py-3 px-4">USDC, EURC</td>
                  <td className="py-3 px-4">~$0.001</td>
                  <td className="py-3 px-4">~2 seconds</td>
                </tr>
                <tr className="border-b border-border/50">
                  <td className="py-3 px-4 font-mono text-[var(--sardis-orange)]">Polygon</td>
                  <td className="py-3 px-4">L2 (PoS)</td>
                  <td className="py-3 px-4">USDC, USDT, EURC</td>
                  <td className="py-3 px-4">~$0.01</td>
                  <td className="py-3 px-4">~2 seconds</td>
                </tr>
                <tr className="border-b border-border/50">
                  <td className="py-3 px-4 font-mono text-[var(--sardis-orange)]">Arbitrum</td>
                  <td className="py-3 px-4">L2 (Optimistic)</td>
                  <td className="py-3 px-4">USDC, USDT</td>
                  <td className="py-3 px-4">~$0.005</td>
                  <td className="py-3 px-4">~1 second</td>
                </tr>
                <tr className="border-b border-border/50">
                  <td className="py-3 px-4 font-mono text-[var(--sardis-orange)]">Optimism</td>
                  <td className="py-3 px-4">L2 (Optimistic)</td>
                  <td className="py-3 px-4">USDC, USDT</td>
                  <td className="py-3 px-4">~$0.005</td>
                  <td className="py-3 px-4">~2 seconds</td>
                </tr>
                <tr className="border-b border-border/50">
                  <td className="py-3 px-4 font-mono text-[var(--sardis-orange)]">Ethereum</td>
                  <td className="py-3 px-4">L1</td>
                  <td className="py-3 px-4">USDC, USDT, PYUSD, EURC</td>
                  <td className="py-3 px-4">~$2-5</td>
                  <td className="py-3 px-4">~12 seconds</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> MPC Custody (Turnkey)
        </h2>
        <p className="text-muted-foreground mb-4">
          Sardis uses Multi-Party Computation (MPC) via <a href="https://www.turnkey.com" target="_blank" rel="noreferrer" className="text-[var(--sardis-orange)] hover:underline">Turnkey</a> for key management. This means:
        </p>
        <ul className="space-y-3 text-muted-foreground mb-6">
          <li className="flex items-start gap-2">
            <span className="text-[var(--sardis-orange)] mt-1">→</span>
            <div><strong className="text-foreground">No single point of failure</strong> — private keys are split across multiple parties. No single entity (including Sardis) can sign transactions alone.</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--sardis-orange)] mt-1">→</span>
            <div><strong className="text-foreground">Non-custodial</strong> — you retain full ownership. Sardis never has access to your funds.</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--sardis-orange)] mt-1">→</span>
            <div><strong className="text-foreground">Agent-compatible</strong> — MPC signing doesn't require 2FA, seed phrases, or hardware wallets. Agents can sign transactions programmatically while maintaining security.</div>
          </li>
        </ul>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Smart Contract Wallets
        </h2>
        <p className="text-muted-foreground mb-4">
          Each agent wallet is backed by a <code className="text-[var(--sardis-orange)]">SardisAgentWallet</code> smart contract deployed via the <code className="text-[var(--sardis-orange)]">SardisWalletFactory</code>.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-6 font-mono text-xs overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`// SardisAgentWallet.sol — Key features
contract SardisAgentWallet {
    // Owner (you) retains full control
    address public owner;

    // Agent can execute within policy bounds
    address public agent;

    // Spending limits enforced on-chain
    uint256 public dailyLimit;
    uint256 public perTransactionLimit;

    // Execute payment (policy-checked)
    function executePayment(
        address token,
        address recipient,
        uint256 amount,
        bytes calldata purpose
    ) external onlyAgent withinLimits(amount) { ... }

    // Owner can update limits anytime
    function updateLimits(uint256 daily, uint256 perTx)
        external onlyOwner { ... }

    // Emergency: owner can freeze wallet instantly
    function freeze() external onlyOwner { ... }
}`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          The wallet factory is deployed on Base Sepolia testnet. Mainnet deployment is planned for the production launch.
        </p>
        <div className="not-prose">
          <a
            href="https://sepolia.basescan.org/address/0x0922f46cbDA32D93691FE8a8bD7271D24E53B3D7"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 border border-border hover:border-[var(--sardis-orange)] transition-colors text-sm font-mono"
          >
            <span className="text-muted-foreground">View on BaseScan:</span>
            <span className="text-[var(--sardis-orange)]">0x0922...3D7</span>
            <span className="text-muted-foreground">→</span>
          </a>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> ERC-4337 Account Abstraction
        </h2>
        <p className="text-muted-foreground mb-4">
          Sardis is integrating ERC-4337 (Account Abstraction) to enable gasless transactions for agents. This means:
        </p>
        <ul className="space-y-3 text-muted-foreground mb-6">
          <li className="flex items-start gap-2">
            <span className="text-[var(--sardis-orange)] mt-1">→</span>
            <div><strong className="text-foreground">No gas tokens needed</strong> — agents don't need ETH/MATIC to pay for transaction fees. Sardis sponsors gas via a paymaster.</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--sardis-orange)] mt-1">→</span>
            <div><strong className="text-foreground">Bundled transactions</strong> — multiple operations can be batched into a single transaction for efficiency.</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--sardis-orange)] mt-1">→</span>
            <div><strong className="text-foreground">Social recovery</strong> — wallet recovery without seed phrases, using guardian-based recovery mechanisms.</div>
          </li>
        </ul>
        <div className="not-prose p-4 border border-yellow-500/20 bg-yellow-500/5">
          <p className="text-sm text-muted-foreground">
            <strong className="text-yellow-500">Coming Soon:</strong> ERC-4337 support is currently in design phase. See the <a href="/docs/roadmap" className="text-[var(--sardis-orange)] hover:underline">Roadmap</a> for timeline.
          </p>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Stablecoins as Payment Rails
        </h2>
        <p className="text-muted-foreground mb-4">
          Sardis uses stablecoins (primarily USDC by Circle) as the settlement layer. Stablecoins are dollar-pegged digital currencies that combine the programmability of blockchain with the stability of fiat currency.
        </p>
        <div className="not-prose grid md:grid-cols-2 gap-4 mb-6">
          <div className="p-4 border border-border">
            <h4 className="font-bold font-display text-foreground mb-2">Why USDC?</h4>
            <ul className="space-y-1 text-sm text-muted-foreground">
              <li>→ Fully backed by US dollar reserves</li>
              <li>→ Regulated by Circle (US-based)</li>
              <li>→ $30B+ in circulation</li>
              <li>→ Native on all supported chains</li>
              <li>→ Instant settlement (no T+2)</li>
            </ul>
          </div>
          <div className="p-4 border border-border">
            <h4 className="font-bold font-display text-foreground mb-2">Fiat On/Off Ramp</h4>
            <ul className="space-y-1 text-sm text-muted-foreground">
              <li>→ Fund wallets from bank accounts (ACH/wire)</li>
              <li>→ Automatic USD → USDC conversion</li>
              <li>→ Withdraw to bank anytime</li>
              <li>→ Users only see dollar amounts</li>
              <li>→ No crypto knowledge required</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Escrow & Settlement
        </h2>
        <p className="text-muted-foreground mb-4">
          The <code className="text-[var(--sardis-orange)]">SardisEscrow</code> contract provides trustless escrow for agent-to-merchant payments:
        </p>
        <ul className="space-y-3 text-muted-foreground">
          <li className="flex items-start gap-2">
            <span className="text-[var(--sardis-orange)] mt-1">→</span>
            <div><strong className="text-foreground">Lock funds</strong> — when an agent initiates a payment, funds are locked in escrow</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--sardis-orange)] mt-1">→</span>
            <div><strong className="text-foreground">Verify delivery</strong> — the merchant confirms delivery or the service is rendered</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--sardis-orange)] mt-1">→</span>
            <div><strong className="text-foreground">Release or refund</strong> — funds are released to the merchant or refunded to the agent</div>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--sardis-orange)] mt-1">→</span>
            <div><strong className="text-foreground">Dispute resolution</strong> — time-locked disputes with owner arbitration</div>
          </li>
        </ul>
      </section>
    </article>
  );
}
