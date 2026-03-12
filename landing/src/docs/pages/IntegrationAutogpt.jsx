export default function DocsIntegrationAutogpt() {
  return (
    <article className="prose dark:prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            INTEGRATION
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">AutoGPT Integration</h1>
        <p className="text-xl text-muted-foreground">
          Add Sardis payment blocks to AutoGPT workflows with typed input/output schemas and policy enforcement.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`pip install sardis-autogpt`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          The AutoGPT integration provides three blocks that follow the AutoGPT block pattern —
          Pydantic input/output schemas with a static run() method that yields output models.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Start
        </h2>

        <p className="text-muted-foreground mb-4">
          Import the BLOCKS registry to get all three Sardis blocks, or import individual block
          classes by name.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_autogpt.blocks import BLOCKS, SardisPayBlock, SardisBalanceBlock, SardisPolicyCheckBlock

# BLOCKS is a list of all three block classes
print(BLOCKS)
# [SardisPayBlock, SardisBalanceBlock, SardisPolicyCheckBlock]

# Run a payment block directly
for output in SardisPayBlock.run(SardisPayBlock.input_schema(
    api_key="sk_live_...",
    wallet_id="wallet_abc123",
    amount=50.00,
    merchant="api.openai.com",
    purpose="API credits",
    token="USDC",
)):
    print(output.status)   # "APPROVED" or "BLOCKED"
    print(output.tx_id)    # Transaction ID if approved
    print(output.message)  # Status message`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Available Blocks
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">SardisPayBlock</h3>
        <p className="text-muted-foreground mb-4">
          Execute a policy-controlled payment. Block ID: <code>sardis-pay-block</code>.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Input schema (SardisPayBlockInput)
api_key: str      # Sardis API key (or SARDIS_API_KEY env var)
wallet_id: str    # Wallet ID (or SARDIS_WALLET_ID env var)
amount: float     # Payment amount in USD
merchant: str     # Merchant or recipient identifier
purpose: str      # Reason for payment (default: "Payment")
token: str        # Token to use (default: "USDC")

# Output schema (SardisPayBlockOutput)
status: str       # "APPROVED", "BLOCKED", or "ERROR"
tx_id: str        # Transaction ID if approved (empty if blocked)
message: str      # Status message
amount: float     # Payment amount
merchant: str     # Merchant name`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">SardisBalanceBlock</h3>
        <p className="text-muted-foreground mb-4">
          Check wallet balance and spending limits. Block ID: <code>sardis-balance-block</code>.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Input schema (SardisBalanceBlockInput)
api_key: str      # Sardis API key
wallet_id: str    # Wallet ID
token: str        # Token to check (default: "USDC")

# Output schema (SardisBalanceBlockOutput)
balance: float    # Current wallet balance
remaining: float  # Remaining spending limit
token: str        # Token type`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">SardisPolicyCheckBlock</h3>
        <p className="text-muted-foreground mb-4">
          Pre-check whether a payment would pass spending policy. Block ID: <code>sardis-policy-check-block</code>.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Input schema (SardisPolicyCheckBlockInput)
api_key: str      # Sardis API key
wallet_id: str    # Wallet ID
amount: float     # Amount to check
merchant: str     # Merchant to check

# Output schema (SardisPolicyCheckBlockOutput)
allowed: bool     # Whether the payment would be allowed
reason: str       # Human-readable explanation`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Example: Check-Then-Pay Pattern
        </h2>

        <p className="text-muted-foreground mb-4">
          Use SardisPolicyCheckBlock before SardisPayBlock for safe autonomous payment workflows.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_autogpt.blocks import (
    SardisPayBlock,
    SardisPolicyCheckBlock,
    SardisPayBlockInput,
    SardisPolicyCheckBlockInput,
)

CREDENTIALS = dict(
    api_key="sk_live_...",
    wallet_id="wallet_abc123",
)

merchant = "api.anthropic.com"
amount = 75.00

# 1. Policy check
for check in SardisPolicyCheckBlock.run(SardisPolicyCheckBlockInput(
    **CREDENTIALS,
    amount=amount,
    merchant=merchant,
)):
    if not check.allowed:
        print(f"Payment blocked: {check.reason}")
        break
    else:
        # 2. Execute payment
        for payment in SardisPayBlock.run(SardisPayBlockInput(
            **CREDENTIALS,
            amount=amount,
            merchant=merchant,
            purpose="Claude API credits",
            token="USDC",
        )):
            print(f"Status: {payment.status}")
            if payment.tx_id:
                print(f"Transaction: {payment.tx_id}")`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Registering Blocks with AutoGPT
        </h2>

        <p className="text-muted-foreground mb-4">
          To make the blocks available in the AutoGPT UI, register them in your AutoGPT plugin configuration.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# In your AutoGPT plugin's __init__.py or block registry:
from sardis_autogpt.blocks import BLOCKS

# Register all Sardis blocks
for block_class in BLOCKS:
    print(f"Registering: {block_class.name} ({block_class.id})")
    # AutoGPT.register_block(block_class)  # Follow your AutoGPT plugin API

# Block IDs for reference:
# - sardis-pay-block         (SardisPayBlock)
# - sardis-balance-block     (SardisBalanceBlock)
# - sardis-policy-check-block (SardisPolicyCheckBlock)`}</pre>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Best Practices</h3>
        <ul className="text-muted-foreground text-sm space-y-2 list-disc list-inside">
          <li>Use SARDIS_API_KEY and SARDIS_WALLET_ID env vars to keep credentials out of block inputs</li>
          <li>Chain SardisPolicyCheckBlock before SardisPayBlock in all automated workflows</li>
          <li>Check output.status == "APPROVED" before trusting output.tx_id</li>
          <li>The BLOCKS list makes it easy to register all blocks programmatically in a plugin</li>
          <li>Block inputs accept empty strings for api_key/wallet_id — they fall back to env vars</li>
        </ul>
      </section>
    </article>
  );
}
