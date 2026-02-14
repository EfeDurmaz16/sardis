export default function DocsSDKPython() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-500">SDKS & TOOLS</span>
          <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">v0.3.3</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Python SDK</h1>
        <p className="text-xl text-muted-foreground">
          Official Python client for Sardis API with sync/async resources.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-muted-foreground"># Production SDK package</div>
            <div className="text-[var(--sardis-orange)]">$ pip install sardis-sdk</div>
            <div className="text-muted-foreground mt-3"># Meta package (includes convenience APIs)</div>
            <div className="text-[var(--sardis-orange)]">$ pip install sardis</div>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Start (Async)
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from decimal import Decimal
from sardis_sdk import AsyncSardisClient

async with AsyncSardisClient(api_key="sk_...") as client:
    wallet = await client.wallets.create(
        agent_id="agent_123",
        currency="USDC",
        chain="base",
        limit_per_tx=Decimal("100.00"),
        limit_total=Decimal("1000.00"),
    )

    balance = await client.wallets.get_balance(wallet.wallet_id, chain="base", token="USDC")

    transfer = await client.wallets.transfer(
        wallet.wallet_id,
        destination="0x...",
        amount=Decimal("25.00"),
        token="USDC",
        chain="base",
        domain="openai.com",
        memo="API credits",
    )

    print(balance.balance, transfer.tx_hash)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> AP2 Payment Execution
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`result = await client.payments.execute_mandate({
    "mandate_id": "mnd_123",
    "issuer": "agent_123",
    "subject": "agent_123",
    "destination": "0x...",
    "amount_minor": 5_000_000,
    "token": "USDC",
    "chain": "base",
    "expires_at": 1_900_000_000,
})`}</pre>
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
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.wallets</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, get, list, get_balance, get_addresses, set_address, update, transfer</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.payments</td><td className="px-4 py-2 border-b border-border text-muted-foreground">execute_mandate, execute_ap2, execute_ap2_bundle</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.holds</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, get, capture, void, list_by_wallet, list_active</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.cards</td><td className="px-4 py-2 border-b border-border text-muted-foreground">issue, list, get, freeze, unfreeze, cancel, update_limits, transactions, simulate_purchase</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.policies</td><td className="px-4 py-2 border-b border-border text-muted-foreground">parse, preview, apply, get, check, examples</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.agents</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, get, list, list_page, update, delete</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.groups</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, get, list, update, delete, add_agent, remove_agent, get_spending</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.transactions</td><td className="px-4 py-2 border-b border-border text-muted-foreground">list_chains, estimate_gas, get_status, list_tokens</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.webhooks</td><td className="px-4 py-2 border-b border-border text-muted-foreground">list_event_types, create, list, get, update, delete, test, list_deliveries, rotate_secret</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.marketplace</td><td className="px-4 py-2 border-b border-border text-muted-foreground">list_categories, create_service, list_services, get_service, search_services, create_offer, list_offers, accept_offer, reject_offer, complete_offer, create_review</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.ledger</td><td className="px-4 py-2 border-b border-border text-muted-foreground">list_entries, get_entry, verify_entry</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Environment Variables
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`export SARDIS_API_KEY="sk_..."

import os
from sardis_sdk import SardisClient

with SardisClient(api_key=os.environ["SARDIS_API_KEY"]) as client:
    wallets = client.wallets.list(limit=10)`}</pre>
          </div>
        </div>
      </section>
    </article>
  );
}
