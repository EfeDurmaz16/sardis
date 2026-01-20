/**
 * Wallets Resource
 * 
 * Manages non-custodial wallets for agents.
 * Wallets never hold funds - they only sign transactions via MPC.
 */

import { BaseResource } from './base.js';
import type {
  Wallet,
  WalletBalance,
  CreateWalletInput,
  SetAddressInput,
} from '../types.js';

export class WalletsResource extends BaseResource {
  /**
   * Create a new non-custodial wallet for an agent.
   * 
   * @param input Wallet creation parameters
   * @returns Created wallet
   */
  async create(input: CreateWalletInput): Promise<Wallet> {
    return this._post<Wallet>('/api/v2/wallets', input);
  }

  /**
   * Get a wallet by ID.
   * 
   * @param walletId Wallet ID
   * @returns Wallet details
   */
  async get(walletId: string): Promise<Wallet> {
    return this._get<Wallet>(`/api/v2/wallets/${walletId}`);
  }

  /**
   * List wallets.
   * 
   * @param agentId Optional agent ID filter
   * @param limit Maximum number of wallets to return
   * @returns List of wallets
   */
  async list(agentId?: string, limit: number = 100): Promise<Wallet[]> {
    const params: Record<string, unknown> = { limit };
    if (agentId) {
      params.agent_id = agentId;
    }
    return this._get<Wallet[]>('/api/v2/wallets', params);
  }

  /**
   * Get wallet balance from chain (non-custodial, read-only).
   * 
   * @param walletId Wallet ID
   * @param chain Chain identifier (e.g., "base", "polygon")
   * @param token Token symbol (e.g., "USDC", "USDT")
   * @returns Wallet balance from chain
   */
  async getBalance(
    walletId: string,
    chain: string = 'base',
    token: string = 'USDC'
  ): Promise<WalletBalance> {
    return this._get<WalletBalance>(`/api/v2/wallets/${walletId}/balance`, {
      chain,
      token,
    });
  }

  /**
   * Get all wallet addresses (chain -> address mapping).
   * 
   * @param walletId Wallet ID
   * @returns Dictionary mapping chain names to addresses
   */
  async getAddresses(walletId: string): Promise<Record<string, string>> {
    return this._get<Record<string, string>>(
      `/api/v2/wallets/${walletId}/addresses`
    );
  }

  /**
   * Set wallet address for a chain.
   * 
   * @param walletId Wallet ID
   * @param input Address information
   * @returns Updated wallet
   */
  async setAddress(
    walletId: string,
    input: SetAddressInput
  ): Promise<Wallet> {
    return this._post<Wallet>(
      `/api/v2/wallets/${walletId}/addresses`,
      input
    );
  }
}
