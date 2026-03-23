# Sardis Protocol v1.0 -- SDK Examples

Usage examples for every major protocol flow in both Python and TypeScript.

---

## Table of Contents

1. [Mint a Payment Object from a Mandate](#1-mint-a-payment-object-from-a-mandate)
2. [Create Funding Commitment and Claim Cells](#2-create-funding-commitment-and-claim-cells)
3. [Get FX Quote and Execute Swap](#3-get-fx-quote-and-execute-swap)
4. [Create Subscription with Dunning](#4-create-subscription-with-dunning)
5. [Full Escrow Flow](#5-full-escrow-flow)
6. [Batch Payment on Tempo](#6-batch-payment-on-tempo)
7. [Streaming Payment](#7-streaming-payment)

---

## 1. Mint a Payment Object from a Mandate

Mint a signed, one-time payment token from an existing spending mandate,
then present it to a merchant and verify.

### Python

```python
import asyncio
from sardis import Sardis

async def mint_and_present():
    client = Sardis(api_key="sk_live_...")

    # Step 1 -- Mint a payment object
    po = await client.payment_objects.mint(
        mandate_id="mandate_abc123",
        merchant_id="merch_xyz789",
        amount="25.00",
        currency="USDC",
        privacy_tier="transparent",
        memo="Invoice #1042",
        expires_in_seconds=3600,
        metadata={"order_id": "ord_001"},
    )
    print(f"Minted: {po.object_id} | Status: {po.status}")
    print(f"Cells claimed: {po.cell_ids}")

    # Step 2 -- Present to the merchant
    presented = await client.payment_objects.present(
        object_id=po.object_id,
        merchant_id="merch_xyz789",
    )
    print(f"Presented: {presented.status}")

    # Step 3 -- Merchant verifies (merchant-side call)
    verified = await client.payment_objects.verify(
        object_id=po.object_id,
        merchant_id="merch_xyz789",
        merchant_signature="0xabc...",
    )
    print(f"Verified: {verified.status}")

    # Step 4 -- Retrieve the payment object
    fetched = await client.payment_objects.get(po.object_id)
    print(f"Current status: {fetched.status}")

    # Step 5 -- List all objects for this mandate
    listing = await client.payment_objects.list(
        mandate_id="mandate_abc123",
        status="verified",
        limit=10,
    )
    print(f"Found {listing.total} verified objects")

asyncio.run(mint_and_present())
```

### TypeScript

```typescript
import { Sardis } from "@sardis/sdk";

const client = new Sardis({ apiKey: "sk_live_..." });

async function mintAndPresent() {
  // Step 1 -- Mint
  const po = await client.paymentObjects.mint({
    mandateId: "mandate_abc123",
    merchantId: "merch_xyz789",
    amount: "25.00",
    currency: "USDC",
    privacyTier: "transparent",
    memo: "Invoice #1042",
    expiresInSeconds: 3600,
    metadata: { orderId: "ord_001" },
  });
  console.log(`Minted: ${po.objectId} | Status: ${po.status}`);
  console.log(`Cells claimed: ${po.cellIds}`);

  // Step 2 -- Present
  const presented = await client.paymentObjects.present(po.objectId, {
    merchantId: "merch_xyz789",
  });
  console.log(`Presented: ${presented.status}`);

  // Step 3 -- Verify (merchant side)
  const verified = await client.paymentObjects.verify(po.objectId, {
    merchantId: "merch_xyz789",
    merchantSignature: "0xabc...",
  });
  console.log(`Verified: ${verified.status}`);

  // Step 4 -- Retrieve
  const fetched = await client.paymentObjects.get(po.objectId);
  console.log(`Current status: ${fetched.status}`);

  // Step 5 -- List
  const listing = await client.paymentObjects.list({
    mandateId: "mandate_abc123",
    status: "verified",
    limit: 10,
  });
  console.log(`Found ${listing.total} verified objects`);
}

mintAndPresent();
```

---

## 2. Create Funding Commitment and Claim Cells

Create a UTXO-style funding commitment, inspect the cells, split a large
cell, and merge small cells together.

### Python

```python
import asyncio
from sardis import Sardis

async def funding_flow():
    client = Sardis(api_key="sk_live_...")

    # Create a commitment with 10 x $100 cells
    commitment = await client.funding.commit(
        vault_ref="0x1234...abcd",
        total_value="1000.00",
        currency="USDC",
        cell_strategy="fixed",
        cell_denomination="100.00",
        settlement_preferences={"chain": "tempo"},
    )
    print(f"Commitment: {commitment.commitment_id}")
    print(f"Cell count: {commitment.cell_count}")

    # List all commitments
    commitments = await client.funding.list_commitments(status="active")
    print(f"Active commitments: {len(commitments)}")

    # List available cells
    cells = await client.funding.list_cells(
        commitment_id=commitment.commitment_id,
        status="available",
    )
    print(f"Available cells: {cells.total}")

    # Split the first cell into two
    first_cell = cells.cells[0]
    split_cells = await client.funding.split_cell(
        cell_id=first_cell.cell_id,
        amounts=["60.00", "40.00"],
    )
    print(f"Split into {len(split_cells)} cells:")
    for c in split_cells:
        print(f"  {c.cell_id}: {c.value} {c.currency}")

    # Merge the two smallest cells back
    merged = await client.funding.merge_cells(
        cell_ids=[split_cells[1].cell_id, cells.cells[1].cell_id],
    )
    print(f"Merged into {merged.cell_id}: {merged.value} {merged.currency}")

asyncio.run(funding_flow())
```

### TypeScript

```typescript
import { Sardis } from "@sardis/sdk";

const client = new Sardis({ apiKey: "sk_live_..." });

async function fundingFlow() {
  // Create commitment
  const commitment = await client.funding.commit({
    vaultRef: "0x1234...abcd",
    totalValue: "1000.00",
    currency: "USDC",
    cellStrategy: "fixed",
    cellDenomination: "100.00",
    settlementPreferences: { chain: "tempo" },
  });
  console.log(`Commitment: ${commitment.commitmentId}`);
  console.log(`Cell count: ${commitment.cellCount}`);

  // List available cells
  const cells = await client.funding.listCells({
    commitmentId: commitment.commitmentId,
    status: "available",
  });
  console.log(`Available cells: ${cells.total}`);

  // Split first cell
  const splitCells = await client.funding.splitCell(cells.cells[0].cellId, {
    amounts: ["60.00", "40.00"],
  });
  console.log(`Split into ${splitCells.length} cells`);

  // Merge two cells
  const merged = await client.funding.mergeCells({
    cellIds: [splitCells[1].cellId, cells.cells[1].cellId],
  });
  console.log(`Merged into ${merged.cellId}: ${merged.value} ${merged.currency}`);
}

fundingFlow();
```

---

## 3. Get FX Quote and Execute Swap

Get a stablecoin FX quote (USDC -> EURC), check rates, and execute the
swap before the 30-second quote window expires.

### Python

```python
import asyncio
from sardis import Sardis

async def fx_swap():
    client = Sardis(api_key="sk_live_...")

    # Check current rates
    rates = await client.fx.rates()
    for pair in rates.rates:
        print(f"{pair['from']} -> {pair['to']}: {pair['rate']}")

    # Get a quote
    quote = await client.fx.quote(
        from_currency="USDC",
        to_currency="EURC",
        from_amount="1000.00",
        chain="tempo",
        slippage_bps=50,
    )
    print(f"Quote {quote.quote_id}: {quote.from_amount} {quote.from_currency}"
          f" -> {quote.to_amount} {quote.to_currency}")
    print(f"Rate: {quote.rate} | Provider: {quote.provider}")
    print(f"Expires at: {quote.expires_at}")

    # Execute before expiry (30-second window)
    result = await client.fx.execute(quote_id=quote.quote_id)
    print(f"Swap status: {result.status}")

asyncio.run(fx_swap())
```

### TypeScript

```typescript
import { Sardis } from "@sardis/sdk";

const client = new Sardis({ apiKey: "sk_live_..." });

async function fxSwap() {
  // Check rates
  const rates = await client.fx.rates();
  for (const pair of rates.rates) {
    console.log(`${pair.from} -> ${pair.to}: ${pair.rate}`);
  }

  // Get a quote
  const quote = await client.fx.quote({
    fromCurrency: "USDC",
    toCurrency: "EURC",
    fromAmount: "1000.00",
    chain: "tempo",
    slippageBps: 50,
  });
  console.log(`Quote ${quote.quoteId}: ${quote.fromAmount} ${quote.fromCurrency}`
    + ` -> ${quote.toAmount} ${quote.toCurrency}`);
  console.log(`Rate: ${quote.rate} | Provider: ${quote.provider}`);

  // Execute within 30-second window
  const result = await client.fx.execute({ quoteId: quote.quoteId });
  console.log(`Swap status: ${result.status}`);
}

fxSwap();
```

---

## 4. Create Subscription with Dunning

Set up a metered subscription, report usage via the usage API, and
read cumulative billing state. The countersignature prevents unauthorized
usage reports.

### Python

```python
import asyncio
import hashlib
import hmac
from sardis import Sardis

COUNTER_SECRET = "meter-signing-secret-from-setup"

async def metered_billing():
    client = Sardis(api_key="sk_live_...")

    # List existing meters for a subscription
    meters = await client.usage.list_meters(subscription_id="sub_abc123")
    print(f"Meters: {meters.total}")

    meter_id = "meter_api_calls"

    # Generate the countersignature
    usage_delta = "150"
    message = f"{meter_id}:{usage_delta}"
    countersig = hmac.new(
        COUNTER_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    # Report usage
    report = await client.usage.report(
        meter_id=meter_id,
        usage_delta=usage_delta,
        countersignature=countersig,
        idempotency_key="report_2026-03-23_batch_01",
    )
    print(f"Reported: delta={report.usage_delta}, "
          f"cumulative={report.cumulative_usage}, "
          f"billable={report.billable_amount}")

    # Read meter state
    meter = await client.usage.get_meter(meter_id)
    print(f"Meter '{meter.name}': "
          f"{meter.cumulative_usage} {meter.unit}s "
          f"= ${meter.billable_amount}")

asyncio.run(metered_billing())
```

### TypeScript

```typescript
import { createHmac } from "crypto";
import { Sardis } from "@sardis/sdk";

const client = new Sardis({ apiKey: "sk_live_..." });
const COUNTER_SECRET = "meter-signing-secret-from-setup";

async function meteredBilling() {
  // List meters
  const meters = await client.usage.listMeters({
    subscriptionId: "sub_abc123",
  });
  console.log(`Meters: ${meters.total}`);

  const meterId = "meter_api_calls";
  const usageDelta = "150";

  // Countersignature (HMAC-SHA256)
  const message = `${meterId}:${usageDelta}`;
  const countersig = createHmac("sha256", COUNTER_SECRET)
    .update(message)
    .digest("hex");

  // Report usage
  const report = await client.usage.report({
    meterId,
    usageDelta,
    countersignature: countersig,
    idempotencyKey: "report_2026-03-23_batch_01",
  });
  console.log(`Reported: delta=${report.usageDelta}, `
    + `cumulative=${report.cumulativeUsage}, `
    + `billable=${report.billableAmount}`);

  // Read meter state
  const meter = await client.usage.getMeter(meterId);
  console.log(`Meter '${meter.name}': `
    + `${meter.cumulativeUsage} ${meter.unit}s `
    + `= $${meter.billableAmount}`);
}

meteredBilling();
```

---

## 5. Full Escrow Flow

Create an escrow hold for a payment object, then either confirm delivery
(happy path) or file a dispute, submit evidence, and resolve.

### Python

```python
import asyncio
from sardis import Sardis

async def escrow_happy_path():
    """Happy path: create escrow, confirm delivery, funds released."""
    client = Sardis(api_key="sk_live_...")

    # Create escrow
    escrow = await client.escrow.create(
        payment_object_id="po_a1b2c3d4e5f6",
        merchant_id="merch_xyz789",
        amount="250.00",
        currency="USDC",
        timelock_hours=72,
        chain="tempo",
        metadata={"order_id": "ord_555"},
    )
    print(f"Escrow created: {escrow.hold_id} | Status: {escrow.status}")
    print(f"Timelock expires: {escrow.timelock_expires_at}")

    # Buyer confirms delivery
    released = await client.escrow.confirm_delivery(
        hold_id=escrow.hold_id,
        evidence={"tracking_number": "1Z999AA10123456784"},
    )
    print(f"Escrow released: {released.status}")
    print(f"Released at: {released.released_at}")


async def escrow_dispute_path():
    """Dispute path: create escrow, file dispute, submit evidence, resolve."""
    client = Sardis(api_key="sk_live_...")

    # Assume escrow already created with hold_id "esc_existing"
    hold_id = "esc_existing"

    # File a dispute
    dispute = await client.escrow.dispute(
        hold_id=hold_id,
        reason="not_delivered",
        description="Item was not delivered within the agreed timeframe.",
    )
    print(f"Dispute filed: {dispute.dispute_id} | Status: {dispute.status}")

    # Payer submits evidence
    evidence = await client.disputes.submit_evidence(
        dispute_id=dispute.dispute_id,
        party="payer",
        evidence_type="screenshot",
        content={"url": "https://example.com/screenshot.png"},
        description="Screenshot showing order status: not shipped",
    )
    print(f"Evidence submitted: {evidence.evidence_id}")

    # Merchant submits counter-evidence
    counter = await client.disputes.submit_evidence(
        dispute_id=dispute.dispute_id,
        party="merchant",
        evidence_type="receipt",
        content={"url": "https://example.com/shipping-receipt.pdf"},
        description="Shipping receipt showing dispatch",
    )
    print(f"Counter-evidence: {counter.evidence_id}")

    # Check dispute state
    current = await client.disputes.get(dispute.dispute_id)
    print(f"Evidence count: {current.evidence_count}")
    print(f"Deadline: {current.evidence_deadline}")

    # Admin resolves: full refund to payer
    resolution = await client.disputes.resolve(
        dispute_id=dispute.dispute_id,
        outcome="resolved_refund",
        payer_amount="250.00",
        merchant_amount="0.00",
        reasoning="Merchant failed to provide proof of delivery within deadline.",
    )
    print(f"Resolution: {resolution.outcome}")
    print(f"Payer receives: {resolution.payer_amount}")

asyncio.run(escrow_happy_path())
asyncio.run(escrow_dispute_path())
```

### TypeScript

```typescript
import { Sardis } from "@sardis/sdk";

const client = new Sardis({ apiKey: "sk_live_..." });

// Happy path
async function escrowHappyPath() {
  const escrow = await client.escrow.create({
    paymentObjectId: "po_a1b2c3d4e5f6",
    merchantId: "merch_xyz789",
    amount: "250.00",
    currency: "USDC",
    timelockHours: 72,
    chain: "tempo",
    metadata: { orderId: "ord_555" },
  });
  console.log(`Escrow: ${escrow.holdId} | Status: ${escrow.status}`);

  // Confirm delivery
  const released = await client.escrow.confirmDelivery(escrow.holdId, {
    evidence: { trackingNumber: "1Z999AA10123456784" },
  });
  console.log(`Released: ${released.status}`);
}

// Dispute path
async function escrowDisputePath() {
  const holdId = "esc_existing";

  // File dispute
  const dispute = await client.escrow.dispute(holdId, {
    reason: "not_delivered",
    description: "Item was not delivered within the agreed timeframe.",
  });
  console.log(`Dispute: ${dispute.disputeId} | Status: ${dispute.status}`);

  // Payer evidence
  const evidence = await client.disputes.submitEvidence(dispute.disputeId, {
    party: "payer",
    evidenceType: "screenshot",
    content: { url: "https://example.com/screenshot.png" },
    description: "Screenshot showing order status: not shipped",
  });
  console.log(`Evidence: ${evidence.evidenceId}`);

  // Resolve
  const resolution = await client.disputes.resolve(dispute.disputeId, {
    outcome: "resolved_refund",
    payerAmount: "250.00",
    merchantAmount: "0.00",
    reasoning: "Merchant failed to provide proof of delivery within deadline.",
  });
  console.log(`Resolution: ${resolution.outcome}`);
  console.log(`Payer receives: ${resolution.payerAmount}`);
}

escrowHappyPath();
escrowDisputePath();
```

---

## 6. Batch Payment on Tempo

Execute multiple transfers in a single atomic transaction using Tempo's
type 0x76 batch instruction. All transfers succeed or all fail.

### Python

```python
import asyncio
from sardis import Sardis

async def batch_payroll():
    client = Sardis(api_key="sk_live_...")

    result = await client.payments.batch(
        transfers=[
            {"to": "0xAlice...", "amount": "2500.00", "token": "USDC", "memo": "March salary"},
            {"to": "0xBob...", "amount": "3000.00", "token": "USDC", "memo": "March salary"},
            {"to": "0xCarol...", "amount": "2800.00", "token": "USDC", "memo": "March salary"},
            {"to": "0xDave...", "amount": "1500.00", "token": "USDC", "memo": "March contractor"},
        ],
        chain="tempo",
        mandate_id="mandate_payroll",
    )

    print(f"Batch tx: {result.tx_hash}")
    print(f"Transfers: {result.transfer_count}")
    print(f"Total: {result.total_amount} USDC")
    print(f"Status: {result.status}")

    for t in result.transfers:
        print(f"  [{t.index}] {t.to}: {t.amount} {t.token} -> {t.status}")

asyncio.run(batch_payroll())
```

### TypeScript

```typescript
import { Sardis } from "@sardis/sdk";

const client = new Sardis({ apiKey: "sk_live_..." });

async function batchPayroll() {
  const result = await client.payments.batch({
    transfers: [
      { to: "0xAlice...", amount: "2500.00", token: "USDC", memo: "March salary" },
      { to: "0xBob...", amount: "3000.00", token: "USDC", memo: "March salary" },
      { to: "0xCarol...", amount: "2800.00", token: "USDC", memo: "March salary" },
      { to: "0xDave...", amount: "1500.00", token: "USDC", memo: "March contractor" },
    ],
    chain: "tempo",
    mandateId: "mandate_payroll",
  });

  console.log(`Batch tx: ${result.txHash}`);
  console.log(`Transfers: ${result.transferCount}`);
  console.log(`Total: ${result.totalAmount} USDC`);
  console.log(`Status: ${result.status}`);

  for (const t of result.transfers) {
    console.log(`  [${t.index}] ${t.to}: ${t.amount} ${t.token} -> ${t.status}`);
  }
}

batchPayroll();
```

---

## 7. Streaming Payment

Open a pay-per-use streaming channel, consume work units (e.g., LLM
tokens), listen for real-time SSE events, and settle on-chain.

### Python

```python
import asyncio
import json
import httpx
from sardis import Sardis

async def streaming_payment():
    client = Sardis(api_key="sk_live_...")

    # Open a stream channel
    stream = await client.payments.stream.open(
        service_address="0xServiceProvider...",
        deposit_amount="10.00",
        token="USDC",
        unit_price="0.0001",  # $0.0001 per token
        max_units=100000,
        duration_hours=1,
    )
    print(f"Stream opened: {stream.stream_id}")
    print(f"Channel: {stream.channel_id}")
    print(f"Deposit: {stream.deposit_amount} USDC")
    print(f"SSE URL: {stream.sse_url}")

    # Start SSE listener in background
    async def listen_events():
        base_url = "https://api.sardis.sh/api/v2"
        async with httpx.AsyncClient() as http:
            async with http.stream(
                "GET",
                f"{base_url}{stream.sse_url}",
                headers={"Authorization": "Bearer sk_live_..."},
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        event = json.loads(line[5:].strip())
                        print(f"  SSE event: {event['type']}", end="")
                        if event["type"] == "payment":
                            print(f" | units={event['units']} "
                                  f"amount={event['amount']} "
                                  f"seq={event['voucher_sequence']}")
                        else:
                            print()

    listener = asyncio.create_task(listen_events())

    # Simulate consuming units (e.g., LLM token generation)
    for batch in range(5):
        result = await client.payments.stream.consume(
            stream_id=stream.stream_id,
            units=200,
            metadata={"batch": batch, "model": "claude-opus-4-20250514"},
        )
        print(f"Consumed batch {batch}: "
              f"{result.units_consumed} units, "
              f"total={result.total_amount}, "
              f"remaining={result.remaining}")
        await asyncio.sleep(0.5)

    # Settle and close
    settled = await client.payments.stream.settle(
        stream_id=stream.stream_id,
    )
    print(f"\nStream settled: {settled.status}")
    print(f"Total consumed: {settled.units_consumed} units = {settled.amount_consumed}")
    print(f"Remaining deposit returned: {settled.remaining}")

    listener.cancel()

asyncio.run(streaming_payment())
```

### TypeScript

```typescript
import { Sardis } from "@sardis/sdk";

const client = new Sardis({ apiKey: "sk_live_..." });

async function streamingPayment() {
  // Open stream
  const stream = await client.payments.stream.open({
    serviceAddress: "0xServiceProvider...",
    depositAmount: "10.00",
    token: "USDC",
    unitPrice: "0.0001",
    maxUnits: 100000,
    durationHours: 1,
  });
  console.log(`Stream: ${stream.streamId}`);
  console.log(`Channel: ${stream.channelId}`);

  // Listen to SSE events
  const baseUrl = "https://api.sardis.sh/api/v2";
  const eventSource = new EventSource(
    `${baseUrl}${stream.sseUrl}`,
    // Note: SSE auth requires a proxy or polyfill that supports headers
  );
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "payment") {
      console.log(`  SSE: units=${data.units} amount=${data.amount} seq=${data.voucher_sequence}`);
    } else {
      console.log(`  SSE: ${data.type}`);
    }
  };

  // Consume units in batches
  for (let batch = 0; batch < 5; batch++) {
    const result = await client.payments.stream.consume(stream.streamId, {
      units: 200,
      metadata: { batch, model: "claude-opus-4-20250514" },
    });
    console.log(`Batch ${batch}: ${result.unitsConsumed} units, `
      + `total=${result.totalAmount}, remaining=${result.remaining}`);
    await new Promise((r) => setTimeout(r, 500));
  }

  // Settle
  const settled = await client.payments.stream.settle(stream.streamId);
  console.log(`\nSettled: ${settled.status}`);
  console.log(`Consumed: ${settled.unitsConsumed} units = ${settled.amountConsumed}`);
  console.log(`Returned: ${settled.remaining}`);

  eventSource.close();
}

streamingPayment();
```

---

## Error Handling

All SDK methods throw typed exceptions. Wrap calls in try/catch for
production use.

### Python

```python
from sardis.exceptions import (
    SardisAPIError,
    SardisNotFoundError,
    SardisConflictError,
    SardisValidationError,
)

try:
    po = await client.payment_objects.mint(
        mandate_id="mandate_expired",
        merchant_id="merch_xyz789",
        amount="25.00",
    )
except SardisNotFoundError:
    print("Mandate does not exist")
except SardisConflictError as e:
    print(f"Mandate state conflict: {e.detail}")
except SardisValidationError as e:
    print(f"Validation failed: {e.detail}")
except SardisAPIError as e:
    print(f"Unexpected API error {e.status_code}: {e.detail}")
```

### TypeScript

```typescript
import {
  SardisAPIError,
  SardisNotFoundError,
  SardisConflictError,
  SardisValidationError,
} from "@sardis/sdk";

try {
  const po = await client.paymentObjects.mint({
    mandateId: "mandate_expired",
    merchantId: "merch_xyz789",
    amount: "25.00",
  });
} catch (e) {
  if (e instanceof SardisNotFoundError) {
    console.error("Mandate does not exist");
  } else if (e instanceof SardisConflictError) {
    console.error(`State conflict: ${e.detail}`);
  } else if (e instanceof SardisValidationError) {
    console.error(`Validation: ${e.detail}`);
  } else if (e instanceof SardisAPIError) {
    console.error(`API error ${e.statusCode}: ${e.detail}`);
  }
}
```

---

## Environment Setup

### Python

```bash
pip install sardis
# or
uv add sardis
```

```python
import os
from sardis import Sardis

client = Sardis(
    api_key=os.environ["SARDIS_API_KEY"],
    base_url="https://api.sardis.sh/api/v2",  # default
)
```

### TypeScript

```bash
npm install @sardis/sdk
# or
pnpm add @sardis/sdk
```

```typescript
import { Sardis } from "@sardis/sdk";

const client = new Sardis({
  apiKey: process.env.SARDIS_API_KEY!,
  baseUrl: "https://api.sardis.sh/api/v2", // default
});
```
