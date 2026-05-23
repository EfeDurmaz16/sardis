/**
 * @sardis/ai-sdk — DEPRECATED.
 *
 * This package is now a thin re-export shim over `sardis/ai-sdk`. New
 * code should `npm install sardis` and `import { createSardis } from
 * "sardis/ai-sdk"`.
 *
 * Migration:
 *
 * ```diff
 * - import { createSardisTools } from "@sardis/ai-sdk";
 * + import { createSardis } from "sardis/ai-sdk";
 * - const tools = createSardisTools({ apiKey, walletId });
 * + const sardis = createSardis({ apiKey, walletId });
 * + // then pass sardis.tools to generateText
 * ```
 *
 * Run `npx sardis-migrate` to apply this codemod automatically.
 *
 * This shim will be removed after one minor cycle (target: sardis@2.1).
 */

let warned = false;
function emitDeprecationWarning(): void {
  if (warned) return;
  warned = true;
  const msg =
    '[@sardis/ai-sdk] DEPRECATED — use `sardis/ai-sdk` instead. Run `npx sardis-migrate` to upgrade. See https://sardis.sh/docs/ts-migration';
  if (typeof process !== 'undefined' && process.emitWarning) {
    process.emitWarning(msg, 'DeprecationWarning');
  } else if (typeof console !== 'undefined') {
    console.warn(msg);
  }
}

emitDeprecationWarning();

// Re-export the new factory + provider shape.
export {
  createSardis,
  sardisProvider,
  PayInputSchema,
  HoldCreateSchema,
  HoldCaptureSchema,
  HoldVoidSchema,
  BalanceSchema,
  PolicyCheckSchema,
} from 'sardis/ai-sdk';
export type {
  CreateSardisOptions,
  TransactionEvent,
  SardisProvider as SardisProviderType,
  AISDKTool,
  PayInputT,
  HoldCreateT,
  HoldCaptureT,
  HoldVoidT,
  BalanceT,
  PolicyCheckT,
} from 'sardis/ai-sdk';

// Backwards-compat: the v1 `createSardisTools(opts)` returned a tool map
// directly. v2 returns a provider with `.tools`. Map the old API onto the
// new factory.
import { createSardis as _createSardis } from 'sardis/ai-sdk';

/** @deprecated Use `createSardis(opts).tools` from `sardis/ai-sdk`. */
export function createSardisTools(opts: Parameters<typeof _createSardis>[0]) {
  return _createSardis(opts).tools;
}

/** @deprecated Use `createSardis(...)` from `sardis/ai-sdk`. */
export class SardisProvider {
  private readonly _provider: ReturnType<typeof _createSardis>;
  public readonly tools: ReturnType<typeof _createSardis>['tools'];
  public readonly systemPrompt: string;
  constructor(opts: Parameters<typeof _createSardis>[0]) {
    this._provider = _createSardis(opts);
    this.tools = this._provider.tools;
    this.systemPrompt = this._provider.systemPrompt;
  }
  pay(input: Parameters<ReturnType<typeof _createSardis>['pay']>[0]) {
    return this._provider.pay(input);
  }
  balance(input?: Parameters<ReturnType<typeof _createSardis>['balance']>[0]) {
    return this._provider.balance(input);
  }
}
