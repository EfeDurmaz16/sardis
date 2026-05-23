/**
 * `sardis/wallet` — MPC wallet primitives.
 *
 * Re-exports the `wallets` resource + wallet/balance/transfer types.
 */

export { WalletsResource } from '../resources/wallets.js';
export type {
  Wallet,
  WalletBalance,
  CreateWalletInput,
  SetAddressInput,
  WalletTransferInput,
  WalletTransferResponse,
  TokenLimit,
  MPCProvider,
} from '../types.js';

/** Resolve a wallet's address on a specific chain, or undefined if not set. */
export function walletAddress(
  wallet: { addresses: Record<string, string> },
  chain: string,
): string | undefined {
  return wallet.addresses[chain];
}
