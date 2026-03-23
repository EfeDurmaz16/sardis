/**
 * Escrow Resource
 *
 * Manages escrow holds and disputes for protected transactions.
 * Funds are held in escrow until delivery is confirmed or a dispute
 * is resolved, ensuring safe agent-to-agent commerce.
 */

import { BaseResource } from './base.js';
import type {
  EscrowHold,
  EscrowDispute,
  CreateEscrowHoldInput,
  ConfirmDeliveryInput,
  FileDisputeInput,
  SubmitEvidenceInput,
  ResolveDisputeInput,
  RequestOptions,
} from '../types.js';

export class EscrowResource extends BaseResource {
  /**
   * Create an escrow hold.
   *
   * Locks funds in escrow between a buyer and seller until delivery
   * is confirmed or the hold expires.
   *
   * @param params - Escrow hold creation parameters
   * @param options - Request options (signal, timeout)
   * @returns The created escrow hold
   */
  async createHold(
    params: CreateEscrowHoldInput,
    options?: RequestOptions
  ): Promise<EscrowHold> {
    return this._post<EscrowHold>('/api/v2/escrow/holds', params, options);
  }

  /**
   * Confirm delivery on an escrow hold.
   *
   * Releases the escrowed funds to the seller after the buyer
   * confirms receipt of goods or services.
   *
   * @param holdId - Escrow hold ID
   * @param params - Optional delivery confirmation details
   * @param options - Request options (signal, timeout)
   * @returns The updated escrow hold
   */
  async confirmDelivery(
    holdId: string,
    params?: ConfirmDeliveryInput,
    options?: RequestOptions
  ): Promise<EscrowHold> {
    return this._post<EscrowHold>(
      `/api/v2/escrow/holds/${holdId}/confirm`,
      params ?? {},
      options
    );
  }

  /**
   * File a dispute on an escrow hold.
   *
   * Initiates the dispute resolution process, preventing automatic
   * release of funds until the dispute is resolved.
   *
   * @param holdId - Escrow hold ID
   * @param params - Dispute filing parameters
   * @param options - Request options (signal, timeout)
   * @returns The created dispute
   */
  async fileDispute(
    holdId: string,
    params: FileDisputeInput,
    options?: RequestOptions
  ): Promise<EscrowDispute> {
    return this._post<EscrowDispute>(
      `/api/v2/escrow/holds/${holdId}/dispute`,
      params,
      options
    );
  }

  /**
   * Submit evidence for an escrow dispute.
   *
   * Adds supporting evidence (receipts, screenshots, logs) to an
   * active dispute for review.
   *
   * @param disputeId - Dispute ID
   * @param params - Evidence submission parameters
   * @param options - Request options (signal, timeout)
   * @returns The updated dispute
   */
  async submitEvidence(
    disputeId: string,
    params: SubmitEvidenceInput,
    options?: RequestOptions
  ): Promise<EscrowDispute> {
    return this._post<EscrowDispute>(
      `/api/v2/escrow/disputes/${disputeId}/evidence`,
      params,
      options
    );
  }

  /**
   * Resolve an escrow dispute.
   *
   * Settles the dispute by distributing the escrowed funds according
   * to the resolution outcome (buyer wins, seller wins, or split).
   *
   * @param disputeId - Dispute ID
   * @param params - Resolution parameters
   * @param options - Request options (signal, timeout)
   * @returns The resolved dispute
   */
  async resolveDispute(
    disputeId: string,
    params: ResolveDisputeInput,
    options?: RequestOptions
  ): Promise<EscrowDispute> {
    return this._post<EscrowDispute>(
      `/api/v2/escrow/disputes/${disputeId}/resolve`,
      params,
      options
    );
  }

  /**
   * Get a dispute by ID.
   *
   * @param disputeId - Dispute ID
   * @param options - Request options (signal, timeout)
   * @returns The dispute
   */
  async getDispute(disputeId: string, options?: RequestOptions): Promise<EscrowDispute> {
    return this._get<EscrowDispute>(
      `/api/v2/escrow/disputes/${disputeId}`,
      undefined,
      options
    );
  }
}
