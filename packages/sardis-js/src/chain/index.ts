/**
 * `sardis/chain` — chain + token enums and gas/explorer helpers.
 *
 * Pure data: no on-chain client dep. Use the Sardis client for any
 * actual chain interaction.
 */

export type { Chain, Token, ChainInfo, GasEstimate, TransactionStatus } from '../types.js';

/** Map of chain id to display name. */
export const CHAIN_NAMES: Record<string, string> = {
  base: 'Base',
  base_sepolia: 'Base Sepolia',
  polygon: 'Polygon',
  polygon_amoy: 'Polygon Amoy',
  ethereum: 'Ethereum',
  ethereum_sepolia: 'Ethereum Sepolia',
  arbitrum: 'Arbitrum One',
  arbitrum_sepolia: 'Arbitrum Sepolia',
  optimism: 'Optimism',
  optimism_sepolia: 'Optimism Sepolia',
};

/** Map of chain id to numeric chain id (EIP-155). */
export const CHAIN_IDS: Record<string, number> = {
  base: 8453,
  base_sepolia: 84532,
  polygon: 137,
  polygon_amoy: 80002,
  ethereum: 1,
  ethereum_sepolia: 11155111,
  arbitrum: 42161,
  arbitrum_sepolia: 421614,
  optimism: 10,
  optimism_sepolia: 11155420,
};

const EXPLORER_BASE: Record<string, string> = {
  base: 'https://basescan.org',
  base_sepolia: 'https://sepolia.basescan.org',
  polygon: 'https://polygonscan.com',
  polygon_amoy: 'https://amoy.polygonscan.com',
  ethereum: 'https://etherscan.io',
  ethereum_sepolia: 'https://sepolia.etherscan.io',
  arbitrum: 'https://arbiscan.io',
  arbitrum_sepolia: 'https://sepolia.arbiscan.io',
  optimism: 'https://optimistic.etherscan.io',
  optimism_sepolia: 'https://sepolia-optimism.etherscan.io',
};

/** Build a block-explorer URL for a tx hash on the given chain. */
export function explorerTxUrl(chain: string, txHash: string): string | undefined {
  const base = EXPLORER_BASE[chain];
  return base ? `${base}/tx/${txHash}` : undefined;
}

/** Build a block-explorer URL for an address on the given chain. */
export function explorerAddressUrl(chain: string, address: string): string | undefined {
  const base = EXPLORER_BASE[chain];
  return base ? `${base}/address/${address}` : undefined;
}
