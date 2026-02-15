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
          Official TypeScript client for Sardis API with typed resources and validation.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-[var(--sardis-orange)]">$ npm install @sardis/sdk</div>
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

const wallet = await client.wallets.create({
  agent_id: 'agent_123',
  currency: 'USDC',
  limit_per_tx: '100.00',
  limit_total: '1000.00',
});

const balance = await client.wallets.getBalance(wallet.wallet_id, 'base', 'USDC');

const transfer = await client.wallets.transfer(wallet.wallet_id, {
  destination: '0x...',
  amount: '25.00',
  token: 'USDC',
  chain: 'base',
  domain: 'openai.com',
  memo: 'API credits',
});

console.log(balance.balance, transfer.tx_hash);`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> AP2 Payment Execution
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`const result = await client.payments.executeMandate({
  mandate_id: 'mnd_123',
  issuer: 'agent_123',
  subject: 'agent_123',
  destination: '0x...',
  amount_minor: 5_000_000,
  token: 'USDC',
  chain: 'base',
  expires_at: Math.floor(Date.now() / 1000) + 300,
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
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.wallets</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, get, list, getBalance, getAddresses, setAddress, transfer</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.payments</td><td className="px-4 py-2 border-b border-border text-muted-foreground">executeMandate, executeAP2, executeAP2Bundle</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.holds</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, get, getById, capture, void, listByWallet, listActive</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.cards</td><td className="px-4 py-2 border-b border-border text-muted-foreground">issue, list, get, freeze, unfreeze, cancel, updateLimits, transactions, simulatePurchase</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.policies</td><td className="px-4 py-2 border-b border-border text-muted-foreground">parse, preview, apply, get, check, examples</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.agents</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, get, list, update, delete, getWallet, createWallet</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.groups</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, get, list, update, delete, addAgent, removeAgent, getSpending</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.transactions</td><td className="px-4 py-2 border-b border-border text-muted-foreground">listChains, estimateGas, getStatus, listTokens</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.webhooks</td><td className="px-4 py-2 border-b border-border text-muted-foreground">listEventTypes, create, list, get, getById, update, delete, test, listDeliveries, rotateSecret</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.ucp</td><td className="px-4 py-2 border-b border-border text-muted-foreground">createCheckout, getCheckout, updateCheckout, completeCheckout, cancelCheckout, getOrder, listOrders</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.a2a</td><td className="px-4 py-2 border-b border-border text-muted-foreground">discoverAgent, getAgentCard, listAgents, sendPaymentRequest, verifyCredential, sendMessage, listMessages, registerAgent</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.treasury</td><td className="px-4 py-2 border-b border-border text-muted-foreground">syncAccountHolders, listFinancialAccounts, createExternalBankAccount, verifyMicroDeposits, fund, withdraw, getPayment, getBalances</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Treasury Example (ACH)
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`const payment = await client.treasury.fund({
  financial_account_token: 'fa_123',
  external_bank_account_token: 'eba_123',
  amount_minor: 5000, // $50.00
  method: 'ACH_NEXT_DAY',
  sec_code: 'CCD',
});

console.log(payment.payment_token, payment.status);`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Environment Variables
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`// SARDIS_API_KEY=sk_...

const client = new SardisClient({
  apiKey: process.env.SARDIS_API_KEY!,
});`}</pre>
          </div>
        </div>
      </section>
    </article>
  );
}
