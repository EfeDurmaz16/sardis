export default function DocsWebhooks() {
  return (
    <article className="prose dark:prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-500">
            CORE FEATURES
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Webhooks</h1>
        <p className="text-xl text-muted-foreground">
          Receive real-time notifications when events occur in your Sardis account.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Setup
        </h2>

        <p className="text-muted-foreground mb-4">
          Register a webhook endpoint to receive event notifications. Your endpoint must be a publicly accessible HTTPS URL.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`curl -X POST https://api.sardis.sh/api/v2/webhooks \\
  -H "X-API-Key: sk_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://your-app.com/sardis-webhook",
    "events": ["payment.completed", "payment.failed", "wallet.frozen"],
    "secret": "<your-webhook-signing-secret>"
  }'`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          The <code className="text-[var(--sardis-orange)]">secret</code> is used to sign webhook payloads so you can verify
          they came from Sardis. Store it securely — it is only shown once at creation time.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Event Types
        </h2>

        <div className="not-prose mb-6 overflow-x-auto">
          <table className="w-full text-sm border border-border">
            <thead>
              <tr className="bg-muted/50">
                <th className="text-left p-3 border-b border-border font-mono">Event</th>
                <th className="text-left p-3 border-b border-border">Description</th>
              </tr>
            </thead>
            <tbody className="font-mono text-xs">
              <tr><td className="p-3 border-b border-border">payment.completed</td><td className="p-3 border-b border-border text-muted-foreground">Payment executed and confirmed on-chain</td></tr>
              <tr><td className="p-3 border-b border-border">payment.failed</td><td className="p-3 border-b border-border text-muted-foreground">Payment failed (insufficient funds, chain error)</td></tr>
              <tr><td className="p-3 border-b border-border">payment.pending</td><td className="p-3 border-b border-border text-muted-foreground">Payment submitted, awaiting confirmation</td></tr>
              <tr><td className="p-3 border-b border-border">wallet.created</td><td className="p-3 border-b border-border text-muted-foreground">New wallet provisioned</td></tr>
              <tr><td className="p-3 border-b border-border">wallet.frozen</td><td className="p-3 border-b border-border text-muted-foreground">Wallet frozen due to policy or manual action</td></tr>
              <tr><td className="p-3 border-b border-border">wallet.unfrozen</td><td className="p-3 border-b border-border text-muted-foreground">Wallet unfrozen and active again</td></tr>
              <tr><td className="p-3 border-b border-border">policy.violated</td><td className="p-3 border-b border-border text-muted-foreground">Spending policy violation detected</td></tr>
              <tr><td className="p-3 border-b border-border">hold.created</td><td className="p-3 border-b border-border text-muted-foreground">Pre-authorization hold placed</td></tr>
              <tr><td className="p-3 border-b border-border">hold.captured</td><td className="p-3 border-b border-border text-muted-foreground">Hold captured (payment completed)</td></tr>
              <tr><td className="p-3 border-b border-border">hold.voided</td><td className="p-3 border-b border-border text-muted-foreground">Hold voided (cancelled)</td></tr>
              <tr><td className="p-3 border-b border-border">compliance.flagged</td><td className="p-3 border-b border-border text-muted-foreground">Transaction flagged by compliance screening</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Payload Schema
        </h2>

        <p className="text-muted-foreground mb-4">
          All webhook payloads follow this structure:
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`{
  "event_id": "evt_abc123def456",
  "type": "payment.completed",
  "created_at": "2026-03-24T10:30:00Z",
  "data": {
    "payment_id": "pay_xyz789",
    "wallet_id": "wallet_abc123",
    "amount": "50.00",
    "token": "USDC",
    "chain": "base",
    "tx_hash": "0xabcdef...",
    "status": "success"
  }
}`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          The <code className="text-[var(--sardis-orange)]">event_id</code> is unique per delivery and can be used
          for idempotent processing. The <code className="text-[var(--sardis-orange)]">data</code> field varies by event type.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Signature Verification
        </h2>

        <p className="text-muted-foreground mb-4">
          Every webhook delivery includes an <code className="text-[var(--sardis-orange)]">X-Sardis-Signature</code> header
          containing an HMAC-SHA256 signature. Always verify signatures before processing events.
        </p>

        <h3 className="text-lg font-bold font-display mb-3">Python</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import hashlib
import hmac

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

# In your webhook handler:
@app.post("/sardis-webhook")
async def handle_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Sardis-Signature", "")

    if not verify_webhook(body, signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = json.loads(body)
    # Process event...
    return {"ok": True}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">TypeScript</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import { createHmac, timingSafeEqual } from 'crypto';

function verifyWebhook(payload: string, signature: string, secret: string): boolean {
  const expected = 'sha256=' + createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  return timingSafeEqual(Buffer.from(expected), Buffer.from(signature));
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Retry Behavior
        </h2>

        <p className="text-muted-foreground mb-4">
          If your endpoint returns a non-2xx status code or times out, Sardis retries with exponential backoff:
        </p>

        <div className="not-prose mb-6 overflow-x-auto">
          <table className="w-full text-sm border border-border">
            <thead>
              <tr className="bg-muted/50">
                <th className="text-left p-3 border-b border-border font-mono">Attempt</th>
                <th className="text-left p-3 border-b border-border">Delay</th>
              </tr>
            </thead>
            <tbody className="font-mono text-xs">
              <tr><td className="p-3 border-b border-border">1st retry</td><td className="p-3 border-b border-border text-muted-foreground">1 minute</td></tr>
              <tr><td className="p-3 border-b border-border">2nd retry</td><td className="p-3 border-b border-border text-muted-foreground">5 minutes</td></tr>
              <tr><td className="p-3 border-b border-border">3rd retry</td><td className="p-3 border-b border-border text-muted-foreground">30 minutes</td></tr>
              <tr><td className="p-3 border-b border-border">4th retry</td><td className="p-3 border-b border-border text-muted-foreground">2 hours</td></tr>
              <tr><td className="p-3 border-b border-border">5th retry (final)</td><td className="p-3 border-b border-border text-muted-foreground">24 hours</td></tr>
            </tbody>
          </table>
        </div>

        <p className="text-muted-foreground mb-4">
          After 5 failed attempts, the delivery is marked as failed. You can view delivery history
          and manually retry from the dashboard or via the API.
        </p>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Best Practices</h3>
        <ul className="text-muted-foreground text-sm space-y-2 list-disc list-inside">
          <li>Always verify the <code className="text-[var(--sardis-orange)]">X-Sardis-Signature</code> header before processing events</li>
          <li>Use the <code className="text-[var(--sardis-orange)]">event_id</code> field for idempotent processing — you may receive the same event more than once</li>
          <li>Return a 200 response quickly, then process the event asynchronously</li>
          <li>Store your webhook secret in an environment variable, never in code</li>
          <li>Use HTTPS endpoints only — HTTP is rejected in production</li>
        </ul>
      </section>
    </article>
  );
}
