/**
 * `sardis` — Official TypeScript SDK for Sardis (Payment OS for the Agent Economy).
 *
 * ## Quickstart
 *
 * ```ts
 * import { Sardis } from "sardis";
 *
 * const sardis = new Sardis({ apiKey: process.env.SARDIS_API_KEY! });
 *
 * // Quick send (uses sardis.wallets.transfer under the hood)
 * await sardis.pay({ from: "wallet_abc", to: "merchant_xyz", amount: "25.00" });
 *
 * // Full AP2 mandate flow
 * await sardis.payments.executeMandate({ ...mandate });
 * ```
 */

import { Engine } from './core/engine.js';
import { AbortError } from './core/errors.js';
import type {
  SardisClientOptions,
  RequestOptions,
  PaginationParams,
  PaginatedResponse,
} from './core/types.js';

import {
  PaymentsResource,
  HoldsResource,
  CardsResource,
  PoliciesResource,
  WebhooksResource,
  MarketplaceResource,
  TransactionsResource,
  LedgerResource,
  WalletsResource,
  AgentsResource,
  GroupsResource,
  UCPResource,
  A2AResource,
  TreasuryResource,
  CheckoutResource,
  ApprovalsResource,
  KillSwitchResource,
  EvidenceResource,
  SimulationResource,
  PaymentObjectsResource,
  FundingResource,
  FXResource,
  SubscriptionsV2Resource,
  EscrowResource,
  BatchResource,
  StreamingResource,
  MandateDelegationResource,
  UsageResource,
  FacilityGateResource,
} from './resources/index.js';

import type {
  Token,
  Chain,
  WalletTransferInput,
  WalletTransferResponse,
} from './types.js';

/**
 * Top-level convenience input for {@link Sardis.pay}.
 *
 * Mirrors the Python SDK's `sardis_sdk.resources.pay` shortcut. Internally
 * dispatches to `wallets.transfer`.
 */
export interface PayInput {
  /** Source wallet ID. Required so the call is unambiguous in multi-wallet orgs. */
  from: string;
  /** Destination — wallet ID, on-chain address, or merchant ID. */
  to: string;
  /** Amount in token-decimal units (e.g. `"25.00"` USDC). */
  amount: string;
  /** Token symbol — defaults to USDC. */
  token?: Token;
  /** Chain — defaults to base. */
  chain?: Chain;
  /** Policy context label (e.g. `"aws.amazon.com"`). */
  domain?: string;
  /** Free-form memo recorded in the ledger. */
  memo?: string;
}

/**
 * Main Sardis client. Wraps a single {@link Engine} and namespaces every
 * resource (Stripe-style discoverability).
 */
export class Sardis {
  /** Low-level HTTP engine — exposed for advanced consumers. */
  public readonly engine: Engine;

  /** Payment mandate execution (single + AP2 bundles). */
  public readonly payments: PaymentsResource;
  /** Fund holds — create, capture, void. */
  public readonly holds: HoldsResource;
  /** Virtual card issuance + simulation. */
  public readonly cards: CardsResource;
  /** Natural-language policy parsing + application. */
  public readonly policies: PoliciesResource;
  /** Webhook subscription management. */
  public readonly webhooks: WebhooksResource;
  /** Service marketplace (A2A offers). */
  public readonly marketplace: MarketplaceResource;
  /** Gas estimation + transaction status. */
  public readonly transactions: TransactionsResource;
  /** Ledger query / proof verification. */
  public readonly ledger: LedgerResource;
  /** Non-custodial wallet operations. */
  public readonly wallets: WalletsResource;
  /** Agent identity management. */
  public readonly agents: AgentsResource;
  /** Multi-agent group governance. */
  public readonly groups: GroupsResource;
  /** Universal Commerce Protocol checkout. */
  public readonly ucp: UCPResource;
  /** Agent-to-Agent communication. */
  public readonly a2a: A2AResource;
  /** Treasury accounts + ACH funding. */
  public readonly treasury: TreasuryResource;
  /** Merchant checkout sessions ("Pay with Sardis"). */
  public readonly checkout: CheckoutResource;
  /** Approval queue management. */
  public readonly approvals: ApprovalsResource;
  /** Emergency halt controls. */
  public readonly killSwitch: KillSwitchResource;
  /** Tamper-evident receipts + audit proofs. */
  public readonly evidence: EvidenceResource;
  /** Dry-run payment execution. */
  public readonly simulation: SimulationResource;
  /** Tokenized payment objects (digital checks, vouchers). */
  public readonly paymentObjects: PaymentObjectsResource;
  /** Cell-based liquidity management. */
  public readonly funding: FundingResource;
  /** FX quoting + cross-chain bridging. */
  public readonly fx: FXResource;
  /** Recurring on-chain billing (V2). */
  public readonly subscriptions: SubscriptionsV2Resource;
  /** Protected transactions + dispute resolution. */
  public readonly escrow: EscrowResource;
  /** Batch transfers. */
  public readonly batch: BatchResource;
  /** Streaming payments (open / consume / settle). */
  public readonly streaming: StreamingResource;
  /** AP2 mandate delegation chains. */
  public readonly mandateDelegation: MandateDelegationResource;
  /** Usage-based billing meters. */
  public readonly usage: UsageResource;
  /** Facility Gate — programmable spending facilities (parity with Python SDK). */
  public readonly facilityGate: FacilityGateResource;

  constructor(options: SardisClientOptions) {
    this.engine = new Engine(options);
    this.payments = new PaymentsResource(this.engine);
    this.holds = new HoldsResource(this.engine);
    this.cards = new CardsResource(this.engine);
    this.policies = new PoliciesResource(this.engine);
    this.webhooks = new WebhooksResource(this.engine);
    this.marketplace = new MarketplaceResource(this.engine);
    this.transactions = new TransactionsResource(this.engine);
    this.ledger = new LedgerResource(this.engine);
    this.wallets = new WalletsResource(this.engine);
    this.agents = new AgentsResource(this.engine);
    this.groups = new GroupsResource(this.engine);
    this.ucp = new UCPResource(this.engine);
    this.a2a = new A2AResource(this.engine);
    this.treasury = new TreasuryResource(this.engine);
    this.checkout = new CheckoutResource(this.engine);
    this.approvals = new ApprovalsResource(this.engine);
    this.killSwitch = new KillSwitchResource(this.engine);
    this.evidence = new EvidenceResource(this.engine);
    this.simulation = new SimulationResource(this.engine);
    this.paymentObjects = new PaymentObjectsResource(this.engine);
    this.funding = new FundingResource(this.engine);
    this.fx = new FXResource(this.engine);
    this.subscriptions = new SubscriptionsV2Resource(this.engine);
    this.escrow = new EscrowResource(this.engine);
    this.batch = new BatchResource(this.engine);
    this.streaming = new StreamingResource(this.engine);
    this.mandateDelegation = new MandateDelegationResource(this.engine);
    this.usage = new UsageResource(this.engine);
    this.facilityGate = new FacilityGateResource(this.engine);
  }

  /**
   * Top-level convenience: send a payment. Builds the wallet transfer
   * internally so AI-agent code can stay one line:
   *
   * ```ts
   * await sardis.pay({ from: "wallet_a", to: "merchant_b", amount: "25.00" });
   * ```
   *
   * For mandate-based flows (AP2 Intent → Cart → Payment) use
   * `sardis.payments.executeMandate(...)` directly.
   */
  pay(input: PayInput, options?: RequestOptions): Promise<WalletTransferResponse> {
    const transferInput: WalletTransferInput = {
      destination: input.to,
      amount: input.amount,
      ...(input.token ? { token: input.token } : {}),
      ...(input.chain ? { chain: input.chain } : {}),
      ...(input.domain ? { domain: input.domain } : {}),
      ...(input.memo ? { memo: input.memo } : {}),
    };
    return this.wallets.transfer(input.from, transferInput, options);
  }

  /** Update the API key in-place. */
  setApiKey(apiKey: string): void {
    this.engine.setApiKey(apiKey);
  }

  /** Get the current API key. */
  getApiKey(): string {
    return this.engine.getApiKey();
  }

  /** Health probe. */
  health(options?: RequestOptions): Promise<{ status: string; version?: string }> {
    return this.engine.request<{ status: string; version?: string }>('GET', '/health', options);
  }

  /** Async-iterator pagination helper. */
  paginate<T>(
    fetchPage: (params: PaginationParams) => Promise<PaginatedResponse<T>>,
    options: PaginationParams = {},
  ): AsyncIterableIterator<T> {
    return this.engine.paginate(fetchPage, options);
  }

  /** Collect all paginated results into an array. */
  paginateAll<T>(
    fetchPage: (params: PaginationParams) => Promise<PaginatedResponse<T>>,
    options: PaginationParams = {},
  ): Promise<T[]> {
    return this.engine.paginateAll(fetchPage, options);
  }

  /** Concurrent multi-operation dispatch. */
  async batchExecute<T>(
    operations: Array<{ method: string; path: string; params?: Record<string, unknown>; data?: unknown }>,
    opts: { concurrency?: number; stopOnError?: boolean; signal?: AbortSignal } = {},
  ): Promise<Array<{ success: true; data: T } | { success: false; error: Error }>> {
    const concurrency = opts.concurrency ?? 5;
    const stopOnError = opts.stopOnError ?? false;
    const signal = opts.signal;
    const results: Array<{ success: true; data: T } | { success: false; error: Error }> = [];
    let stopped = false;
    for (let i = 0; i < operations.length && !stopped; i += concurrency) {
      if (signal?.aborted) throw new AbortError();
      const chunk = operations.slice(i, i + concurrency);
      const chunkResults = await Promise.all(
        chunk.map(async (op) => {
          if (stopped) return { success: false as const, error: new AbortError('Batch stopped') };
          try {
            const data = await this.engine.request<T>(op.method as never, op.path, {
              params: op.params,
              data: op.data,
              signal,
            });
            return { success: true as const, data };
          } catch (e) {
            if (e instanceof AbortError && signal?.aborted) throw e;
            if (stopOnError) stopped = true;
            return { success: false as const, error: e as Error };
          }
        }),
      );
      results.push(...chunkResults);
    }
    return results;
  }
}

export default Sardis;

// Engine + types from core
export { Engine } from './core/engine.js';
export type {
  SardisClientOptions,
  RequestOptions,
  RetryConfig,
  TokenRefreshConfig,
  TelemetryConfig,
  HTTPMethod,
  SardisResponse,
  PaginationParams,
  PaginatedResponse,
  RequestInterceptor,
  ResponseInterceptor,
} from './core/types.js';

// Error hierarchy
export {
  SardisError,
  APIError,
  AuthenticationError,
  RateLimitError,
  TimeoutError,
  AbortError,
  NetworkError,
  ValidationError,
  InsufficientBalanceError,
  NotFoundError,
  PolicyViolationError,
  SpendingLimitError,
  BlockchainError,
  SardisErrorCode,
  isSardisError,
  isRetryableError,
} from './core/errors.js';
export type { ErrorDetails } from './core/errors.js';

// Domain types
export * from './types.js';

// Resource classes (for advanced consumers)
export * from './resources/index.js';
