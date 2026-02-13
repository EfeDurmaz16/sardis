export default function DocsSDKTypeScript() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-500">SDKS & TOOLS</span>
          <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">v0.3.4</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">TypeScript SDK</h1>
        <p className="text-xl text-muted-foreground">
          Type-safe SDK with Zod validation, unified wallet, fiat rails, and virtual cards.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-muted-foreground"># Core SDK</div>
            <div className="text-[var(--sardis-orange)]">$ npm install @sardis/sdk</div>
            <div className="text-muted-foreground mt-3"># With fiat rails support</div>
            <div className="text-[var(--sardis-orange)]">$ npm install @sardis/sdk @sardis/ramp</div>
            <div className="text-muted-foreground mt-3"># or with pnpm</div>
            <div className="text-[var(--sardis-orange)]">$ pnpm add @sardis/sdk @sardis/ramp</div>
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

// Execute a payment (crypto)
const result = await client.payments.execute({
  walletId: wallet.id,
  destination: '0x...',
  amountMinor: 5_000_000, // $5.00 USDC
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
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.policies</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, update, validate</td></tr>
              <tr>
                <td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">
                  client.fiat
                  <span className="ml-2 px-1 py-0.5 text-xs bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">NEW</span>
                </td>
                <td className="px-4 py-2 border-b border-border text-muted-foreground">fund, withdraw, getQuote, getFundingStatus, linkBank, listBanks, getKycStatus, initiateKyc</td>
              </tr>
              <tr>
                <td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.cards</td>
                <td className="px-4 py-2 border-b border-border text-muted-foreground">create, get, list, freeze, unfreeze, setLimit</td>
              </tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.ucp</td><td className="px-4 py-2 border-b border-border text-muted-foreground">createCheckout, completeCheckout, getOrder</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.a2a</td><td className="px-4 py-2 border-b border-border text-muted-foreground">discoverAgent, sendPaymentRequest</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Fiat Rails
          <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">NEW</span>
        </h2>
        <p className="text-muted-foreground mb-4">
          Fund wallets from bank accounts (on-ramp) and withdraw back to fiat (off-ramp).
        </p>

        <h3 className="text-lg font-bold font-display mb-3">On-Ramp: Bank to Wallet</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`// Get a quote first
const quote = await client.fiat.getQuote({
  walletId: wallet.id,
  fiatCurrency: 'USD',
  fiatAmount: 10000, // $100.00 in cents
  direction: 'on_ramp',
});
console.log(\`You'll receive \${quote.cryptoAmount} USDC\`);

// Fund wallet from bank
const funding = await client.fiat.fund({
  walletId: wallet.id,
  fiatAmount: 10000,
  fiatCurrency: 'USD',
  paymentMethod: 'bank_transfer',
});

// Check funding status
const status = await client.fiat.getFundingStatus(funding.id);`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Off-Ramp: Wallet to Bank</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`// Link a bank account first
const bank = await client.fiat.linkBank({
  walletId: wallet.id,
  accountNumber: '****1234',
  routingNumber: '021000021',
});

// Withdraw to linked bank (requires KYC)
const withdrawal = await client.fiat.withdraw({
  walletId: wallet.id,
  bankAccountId: bank.id,
  cryptoAmount: 50_000_000, // 50 USDC
  token: 'USDC',
});`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">KYC Verification</h3>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`// Check KYC status
const kyc = await client.fiat.getKycStatus(wallet.id);

if (kyc.status !== 'approved') {
  // Get verification link
  const verification = await client.fiat.initiateKyc({
    walletId: wallet.id,
    redirectUrl: 'https://myapp.com/kyc-complete',
  });
  console.log(\`Complete KYC at: \${verification.url}\`);
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Unified Balance
          <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">NEW</span>
        </h2>
        <p className="text-muted-foreground mb-4">
          USDC and USD are treated as equivalent (1:1). Deposit either, spend both ways.
        </p>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`// Get unified balance (USDC + USD combined)
const balance = await client.wallets.getUnifiedBalance(wallet.id);
console.log(\`Total: \${balance.display}\`);       // "$500.00"
console.log(\`USDC: \${balance.breakdown.usdc}\`);  // "400.00"
console.log(\`USD: \${balance.breakdown.usd}\`);    // "100.00"

// Spend via crypto (uses USDC)
await client.payments.execute({
  walletId: wallet.id,
  destination: '0x...',
  amountMinor: 50_000_000, // $50 USDC
  token: 'USDC',
});

// Spend via card (auto-converts USDC → USD at 1:1)
const card = await client.cards.create({ walletId: wallet.id });
// Card payment of $30 → converts 30 USDC to USD instantly`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Virtual Cards
        </h2>
        <p className="text-muted-foreground mb-4">
          Create virtual cards funded by your unified balance. USDC auto-converts to USD at 1:1 when you swipe.
        </p>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`// Create a virtual card
const card = await client.cards.create({
  walletId: wallet.id,
  spendingLimit: 10000, // $100.00 limit
  merchantAllowlist: ['openai.com', 'anthropic.com'],
});

console.log(\`Card number: \${card.pan}\`);
console.log(\`Expiry: \${card.expMonth}/\${card.expYear}\`);

// Card payment auto-converts USDC → USD (1:1, no slippage)
// $50 purchase = 50 USDC converted instantly`}</pre>
          </div>
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
  KYCRequiredError,
} from '@sardis/sdk';

try {
  const result = await client.fiat.withdraw({...});
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.log('Invalid API key');
  } else if (error instanceof PolicyViolationError) {
    console.log(\`Blocked: \${error.message}\`);
  } else if (error instanceof InsufficientBalanceError) {
    console.log('Not enough funds');
  } else if (error instanceof KYCRequiredError) {
    console.log(\`KYC required: \${error.verificationUrl}\`);
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
              <pre className="text-[var(--sardis-canvas)]">{`import { sardisTools } from '@sardis/sdk/integrations/vercel-ai';

const result = await generateText({
  model: openai('gpt-4'),
  tools: sardisTools(client), // Includes all payment + fiat tools
  prompt: 'Pay $5 to OpenAI using my virtual card',
});`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">LangChain.js</h3>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs overflow-x-auto">
              <pre className="text-[var(--sardis-canvas)]">{`import { SardisToolkit } from '@sardis/sdk/integrations/langchain';

const toolkit = new SardisToolkit(client);
const tools = toolkit.getTools();

const agent = await createOpenAIFunctionsAgent({
  llm: model,
  tools,
  prompt,
});`}</pre>
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
  VirtualCard,
  FundingQuote,
  BankAccount,
  KYCStatus,
  CreateWalletInput,
  ExecutePaymentInput,
  FundWalletInput,
  WithdrawInput,
} from '@sardis/sdk';

const wallet: Wallet = await client.wallets.get('wallet_abc');
const quote: FundingQuote = await client.fiat.getQuote({...});`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Environment Variables
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`// Set environment variables
// SARDIS_API_KEY=sk_...
// SARDIS_BASE_URL=https://sardis.sh/api/v2 (optional)

// Client will use them automatically
const client = new SardisClient();`}</pre>
          </div>
        </div>
      </section>
    </article>
  );
}
