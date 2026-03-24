export default function DocsErrorReference() {
  const errors = [
    {
      code: 'PolicyViolationError',
      http: '403 Forbidden',
      description: 'The transaction was blocked by the wallet spending policy.',
      causes: [
        'Amount exceeds per-transaction, daily, or monthly limit',
        'Merchant or category is on the block list',
        'Transaction attempted outside allowed time window',
      ],
      resolution: [
        'Check the wallet policy with GET /api/v2/wallets/{id}',
        'Lower the transaction amount or update the policy',
        'Add the merchant to the allowlist if appropriate',
      ],
    },
    {
      code: 'ComplianceDenied',
      http: '403 Forbidden',
      description: 'The transaction was blocked by compliance screening (KYA, sanctions, or AML).',
      causes: [
        'Recipient address flagged by sanctions screening (Elliptic)',
        'Agent trust score below minimum threshold',
        'KYA verification incomplete or expired',
      ],
      resolution: [
        'Check the agent trust score with GET /api/v2/wallets/{id}/trust-score',
        'Complete KYA verification if pending',
        'Contact support if you believe this is a false positive',
      ],
    },
    {
      code: 'InsufficientFunds',
      http: '402 Payment Required',
      description: 'The wallet does not have enough balance to cover the transaction.',
      causes: [
        'Wallet balance is lower than the requested amount',
        'Balance is locked by an existing hold',
        'Gas fees are not covered',
      ],
      resolution: [
        'Check balance with GET /api/v2/wallets/{id}/balances',
        'Fund the wallet with the required token',
        'Release any unnecessary holds',
      ],
    },
    {
      code: 'NoRoute',
      http: '422 Unprocessable Entity',
      description: 'No valid route found to execute the transaction on the specified chain.',
      causes: [
        'The token is not supported on the specified chain',
        'The chain is not configured or temporarily unavailable',
        'RPC endpoint is unreachable',
      ],
      resolution: [
        'Check supported chains and tokens in the documentation',
        'Verify the chain parameter is correct (e.g., "base" not "Base")',
        'Try a different chain that supports your token',
      ],
    },
    {
      code: 'AllAdaptersExhausted',
      http: '502 Bad Gateway',
      description: 'All chain adapters failed to execute the transaction.',
      causes: [
        'All RPC providers are down or rate-limited',
        'Network congestion causing timeouts',
        'Smart contract execution reverted on all attempts',
      ],
      resolution: [
        'Retry after a short delay (the system retries automatically up to 3 times)',
        'Check network status at status.sardis.sh',
        'If persistent, contact support with the request_id from the error response',
      ],
    },
  ];

  return (
    <article className="prose dark:prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-red-500/10 border border-red-500/30 text-red-500">
            REFERENCE
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Error Codes</h1>
        <p className="text-xl text-muted-foreground">
          Reference for error codes returned by the Sardis API, with causes and resolution steps.
        </p>
      </div>

      <section className="mb-8">
        <p className="text-muted-foreground mb-4">
          All API errors include a <code className="text-[var(--sardis-orange)]">request_id</code> field
          that can be provided to support for debugging.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`{
  "error": {
    "type": "policy_violation",
    "message": "Daily limit of $500 exceeded",
    "details": { ... },
    "request_id": "req_abc123"
  }
}`}</pre>
          </div>
        </div>
      </section>

      {errors.map((err) => (
        <section key={err.code} className="mb-12">
          <h2 className="text-2xl font-bold font-display mb-2 flex items-center gap-3">
            <span className="text-[var(--sardis-orange)]">#</span> {err.code}
          </h2>
          <p className="text-sm font-mono text-muted-foreground mb-4">{err.http}</p>
          <p className="text-muted-foreground mb-4">{err.description}</p>

          <h3 className="text-lg font-bold font-display mb-2">Common Causes</h3>
          <ul className="text-muted-foreground text-sm space-y-1 list-disc list-inside mb-4">
            {err.causes.map((cause, i) => (
              <li key={i}>{cause}</li>
            ))}
          </ul>

          <h3 className="text-lg font-bold font-display mb-2">Resolution</h3>
          <ul className="text-muted-foreground text-sm space-y-1 list-disc list-inside">
            {err.resolution.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ul>
        </section>
      ))}
    </article>
  );
}
