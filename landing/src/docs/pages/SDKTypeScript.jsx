export default function DocsSDKTypeScript() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-500">SDKS & TOOLS</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">TypeScript SDK</h1>
        <p className="text-xl text-muted-foreground">Type-safe SDK with Zod validation.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-[var(--sardis-orange)]">$ npm install @sardis/sdk</div>
            <div className="text-muted-foreground mt-2"># or with pnpm/yarn</div>
            <div className="text-[var(--sardis-orange)]">$ pnpm add @sardis/sdk</div>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Start
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import { SardisClient } from '@sardis/sdk';

const client = new SardisClient({ apiKey: 'sk_...' });

// Create a wallet
const wallet = await client.wallets.create({
  agentId: 'my-agent',
  chain: 'base',
});

// Execute a payment
const result = await client.payments.execute({
  walletId: wallet.id,
  destination: '0x...',
  amountMinor: 5_000_000,
  token: 'USDC',
});`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Resources
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <thead>
              <tr className="bg-muted/30">
                <th className="px-4 py-2 text-left border-b border-border">Resource</th>
                <th className="px-4 py-2 text-left border-b border-border">Methods</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.wallets</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, get, list, getBalance</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.payments</td><td className="px-4 py-2 border-b border-border text-muted-foreground">execute, executeMandate</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.holds</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, capture, release, get, list</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.transactions</td><td className="px-4 py-2 border-b border-border text-muted-foreground">get, list</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.ucp</td><td className="px-4 py-2 border-b border-border text-muted-foreground">createCheckout, completeCheckout, getOrder</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.a2a</td><td className="px-4 py-2 border-b border-border text-muted-foreground">discoverAgent, sendPaymentRequest</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Error Handling
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import {
  SardisError,
  AuthenticationError,
  PolicyViolationError,
  InsufficientBalanceError,
} from '@sardis/sdk';

try {
  const result = await client.payments.execute({...});
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.log('Invalid API key');
  } else if (error instanceof PolicyViolationError) {
    console.log(\`Blocked: \${error.message}\`);
  } else if (error instanceof InsufficientBalanceError) {
    console.log('Not enough funds');
  }
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> AI Integrations
        </h2>
        <div className="not-prose space-y-4">
          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Vercel AI SDK</h3>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs overflow-x-auto">
              <pre className="text-[var(--sardis-canvas)]">{`import { sardisPaymentTool } from '@sardis/sdk/integrations/vercel-ai';

const result = await generateText({
  model: openai('gpt-4'),
  tools: { executePayment: sardisPaymentTool(client) },
  prompt: 'Pay $5 to OpenAI',
});`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">LangChain</h3>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs overflow-x-auto">
              <pre className="text-[var(--sardis-canvas)]">{`import { SardisPaymentTool } from '@sardis/sdk/integrations/langchain';

const tools = [new SardisPaymentTool(client)];`}</pre>
            </div>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Types
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import type {
  Wallet,
  Payment,
  Hold,
  Transaction,
  CreateWalletInput,
  ExecutePaymentInput,
} from '@sardis/sdk';

const wallet: Wallet = await client.wallets.get('wallet_abc');`}</pre>
          </div>
        </div>
      </section>
    </article>
  );
}
