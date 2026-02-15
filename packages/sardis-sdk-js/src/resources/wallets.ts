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
  WalletTransferInput,
  WalletTransferResponse,
  RequestOptions,
} from '../types.js';

export class WalletsResource extends BaseResource {
  private _normalize(wallet: Wallet): Wallet {
    // Provide backwards-compatible alias: id := wallet_id
    if (!wallet.id) {
      (wallet as unknown as { id: string }).id = wallet.wallet_id;
    }
    return wallet;
  }

  /**
   * Create a new non-custodial wallet for an agent.
   *
   * @param input Wallet creation parameters
   * @param options Request options (signal, timeout)
   * @returns Created wallet
   */
  async create(input: CreateWalletInput, options?: RequestOptions): Promise<Wallet> {
    const wallet = await this._post<Wallet>('/api/v2/wallets', input, options);
    return this._normalize(wallet);
  }

  /**
   * Get a wallet by ID.
   *
   * @param walletId Wallet ID
   * @param options Request options (signal, timeout)
   * @returns Wallet details
   */
  async get(walletId: string, options?: RequestOptions): Promise<Wallet> {
    const wallet = await this._get<Wallet>(`/api/v2/wallets/${walletId}`, undefined, options);
    return this._normalize(wallet);
  }

  /**
   * List wallets.
   *
   * @param agentId Optional agent ID filter
   * @param limit Maximum number of wallets to return
   * @param options Request options (signal, timeout)
   * @returns List of wallets
   */
  async list(agentId?: string, limit: number = 100, options?: RequestOptions): Promise<Wallet[]> {
    const params: Record<string, unknown> = { limit };
    if (agentId) {
      params.agent_id = agentId;
    }
    const response = await this._get<{ wallets: Wallet[] } | Wallet[]>(
      '/api/v2/wallets',
      params,
      options
    );

    // Handle both array and object response formats
    if (Array.isArray(response)) {
      return response.map((w) => this._normalize(w));
    }
    return (response.wallets || []).map((w) => this._normalize(w));
  }

  /**
   * Get wallet balance from chain (non-custodial, read-only).
   *
   * @param walletId Wallet ID
   * @param chain Chain identifier (e.g., "base", "polygon")
   * @param token Token symbol (e.g., "USDC", "USDT")
   * @param options Request options (signal, timeout)
   * @returns Wallet balance from chain
   */
  async getBalance(
    walletId: string,
    chain: string = 'base',
    token: string = 'USDC',
    options?: RequestOptions
  ): Promise<WalletBalance> {
    return this._get<WalletBalance>(`/api/v2/wallets/${walletId}/balance`, {
      chain,
      token,
    }, options);
  }

  /**
   * Get all wallet addresses (chain -> address mapping).
   *
   * @param walletId Wallet ID
   * @param options Request options (signal, timeout)
   * @returns Dictionary mapping chain names to addresses
   */
  async getAddresses(walletId: string, options?: RequestOptions): Promise<Record<string, string>> {
    return this._get<Record<string, string>>(
      `/api/v2/wallets/${walletId}/addresses`,
      undefined,
      options
    );
  }

  /**
   * Set wallet address for a chain.
   *
   * @param walletId Wallet ID
   * @param input Address information
   * @param options Request options (signal, timeout)
   * @returns Updated wallet
   */
  async setAddress(
    walletId: string,
    input: SetAddressInput,
    options?: RequestOptions
  ): Promise<Wallet> {
    const wallet = await this._post<Wallet>(
      `/api/v2/wallets/${walletId}/addresses`,
      input,
      options
    );
    return this._normalize(wallet);
  }

  /**
   * Transfer stablecoins from a wallet (agent is sender).
   *
   * This endpoint is intended to be called by an agent process using an API key.
   * Sardis enforces policy + compliance and signs via the agent MPC wallet.
   */
  async transfer(
    walletId: string,
    input: WalletTransferInput,
    options?: RequestOptions
  ): Promise<WalletTransferResponse> {
    return this._post<WalletTransferResponse>(
      `/api/v2/wallets/${walletId}/transfer`,
      input,
      options
    );
  }

  async upgradeSmartAccount(
    walletId: string,
    input: {
      smart_account_address: string;
      entrypoint_address?: string;
      paymaster_enabled?: boolean;
      bundler_profile?: string;
    },
    options?: RequestOptions
  ): Promise<Wallet> {
    const wallet = await this._post<Wallet>(
      `/api/v2/wallets/${walletId}/upgrade-smart-account`,
      input,
      options
    );
    return this._normalize(wallet);
  }
}
