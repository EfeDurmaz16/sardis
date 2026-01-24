export default function DocsSDKPython() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-500">SDKS & TOOLS</span>
          <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">v0.6</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Python SDK</h1>
        <p className="text-xl text-muted-foreground">
          Full-featured async SDK for Python with unified wallet, fiat rails, and virtual cards.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-muted-foreground"># Core SDK</div>
            <div className="text-[var(--sardis-orange)]">$ pip install sardis-sdk</div>
            <div className="text-muted-foreground mt-3"># With fiat rails support</div>
            <div className="text-[var(--sardis-orange)]">$ pip install sardis-sdk sardis-ramp</div>
            <div className="text-muted-foreground mt-3"># or with uv</div>
            <div className="text-[var(--sardis-orange)]">$ uv add sardis-sdk sardis-ramp</div>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Start
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis import SardisClient

async with SardisClient(api_key="sk_...") as client:
    # Create a wallet
    wallet = await client.wallets.create(
        agent_id="my-agent",
        chain="base",
    )

    # Execute a payment (crypto)
    result = await client.payments.execute({
        "wallet_id": wallet.id,
        "destination": "0x...",
        "amount_minor": 5_000_000,  # $5.00 USDC
        "token": "USDC",
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
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.wallets</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, get, list, get_balance, fund</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.payments</td><td className="px-4 py-2 border-b border-border text-muted-foreground">execute, execute_mandate</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.holds</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, capture, release, get, list</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.transactions</td><td className="px-4 py-2 border-b border-border text-muted-foreground">get, list</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.policies</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, update, validate</td></tr>
              <tr>
                <td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">
                  client.fiat
                  <span className="ml-2 px-1 py-0.5 text-xs bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">NEW</span>
                </td>
                <td className="px-4 py-2 border-b border-border text-muted-foreground">fund, withdraw, get_quote, get_funding_status, link_bank, list_banks, get_kyc_status, initiate_kyc</td>
              </tr>
              <tr>
                <td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">
                  client.cards
                </td>
                <td className="px-4 py-2 border-b border-border text-muted-foreground">create, get, list, freeze, unfreeze, set_limit</td>
              </tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.ucp</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create_checkout, complete_checkout, get_order</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.a2a</td><td className="px-4 py-2 border-b border-border text-muted-foreground">discover_agent, send_payment_request</td></tr>
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
            <pre className="text-[var(--sardis-canvas)]">{`# Get a quote first
quote = await client.fiat.get_quote(
    wallet_id=wallet.id,
    fiat_currency="USD",
    fiat_amount=100_00,  # $100.00 in cents
    direction="on_ramp",
)
print(f"You'll receive {quote.crypto_amount} USDC")

# Fund wallet from bank
funding = await client.fiat.fund(
    wallet_id=wallet.id,
    fiat_amount=100_00,
    fiat_currency="USD",
    payment_method="bank_transfer",
)

# Check funding status
status = await client.fiat.get_funding_status(funding.id)`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Off-Ramp: Wallet to Bank</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Link a bank account first
bank = await client.fiat.link_bank(
    wallet_id=wallet.id,
    account_number="****1234",
    routing_number="021000021",
)

# Withdraw to linked bank (requires KYC)
withdrawal = await client.fiat.withdraw(
    wallet_id=wallet.id,
    bank_account_id=bank.id,
    crypto_amount=50_000_000,  # 50 USDC
    token="USDC",
)`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">KYC Verification</h3>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Check KYC status
kyc = await client.fiat.get_kyc_status(wallet_id=wallet.id)

if kyc.status != "approved":
    # Get verification link
    verification = await client.fiat.initiate_kyc(
        wallet_id=wallet.id,
        redirect_url="https://myapp.com/kyc-complete",
    )
    print(f"Complete KYC at: {verification.url}")`}</pre>
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
            <pre className="text-[var(--sardis-canvas)]">{`# Get unified balance (USDC + USD combined)
balance = await client.wallets.get_unified_balance(wallet.id)
print(f"Total: {balance.display}")        # "$500.00"
print(f"USDC: {balance.breakdown.usdc}")  # "400.00"
print(f"USD: {balance.breakdown.usd}")    # "100.00"

# Spend via crypto (uses USDC)
await client.payments.execute(
    wallet_id=wallet.id,
    destination="0x...",
    amount_minor=50_000_000,  # $50 USDC
    token="USDC",
)

# Spend via card (auto-converts USDC → USD at 1:1)
card = await client.cards.create(wallet_id=wallet.id)
# Card payment of $30 → converts 30 USDC to USD instantly`}</pre>
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
            <pre className="text-[var(--sardis-canvas)]">{`# Create a virtual card
card = await client.cards.create(
    wallet_id=wallet.id,
    spending_limit=10000,  # $100.00 limit
    merchant_allowlist=["openai.com", "anthropic.com"],
)

print(f"Card number: {card.pan}")
print(f"Expiry: {card.exp_month}/{card.exp_year}")

# Card payment auto-converts USDC → USD (1:1, no slippage)
# $50 purchase = 50 USDC converted instantly`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Error Handling
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis.errors import (
    SardisError,
    AuthenticationError,
    PolicyViolationError,
    InsufficientBalanceError,
    KYCRequiredError,
)

try:
    result = await client.fiat.withdraw(...)
except AuthenticationError:
    print("Invalid API key")
except PolicyViolationError as e:
    print(f"Blocked by policy: {e.message}")
except InsufficientBalanceError:
    print("Not enough funds")
except KYCRequiredError as e:
    print(f"KYC required: {e.verification_url}")
except SardisError as e:
    print(f"API error: {e.code}")`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> AI Integrations
        </h2>
        <div className="not-prose space-y-4">
          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">LangChain</h3>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs overflow-x-auto">
              <pre className="text-[var(--sardis-canvas)]">{`from sardis.integrations.langchain import SardisToolkit

toolkit = SardisToolkit(client)
tools = toolkit.get_tools()  # Returns all payment + fiat tools

agent = create_react_agent(llm, tools)`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">LlamaIndex</h3>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs overflow-x-auto">
              <pre className="text-[var(--sardis-canvas)]">{`from sardis.integrations.llamaindex import SardisTools

tools = SardisTools(client)
agent = OpenAIAgent.from_tools(tools.to_tool_list())`}</pre>
            </div>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Environment Variables
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Set environment variables
export SARDIS_API_KEY="sk_..."
export SARDIS_BASE_URL="https://api.sardis.sh"  # Optional

# Client will use them automatically
client = SardisClient()`}</pre>
          </div>
        </div>
      </section>
    </article>
  );
}
