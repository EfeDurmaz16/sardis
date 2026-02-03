/**
 * Cards Resource
 *
 * Virtual card issuance + simulated purchase demo flow.
 */

import { BaseResource } from './base.js';
import type {
  Card,
  CardTransaction,
  IssueCardInput,
  UpdateCardLimitsInput,
  SimulateCardPurchaseInput,
  SimulateCardPurchaseResponse,
  RequestOptions,
} from '../types.js';

export class CardsResource extends BaseResource {
  async issue(input: IssueCardInput, options?: RequestOptions): Promise<Card> {
    return this._post<Card>('/api/v2/cards', input, options);
  }

  async list(
    wallet_id?: string,
    options?: RequestOptions
  ): Promise<Card[]> {
    const params: Record<string, unknown> = {};
    if (wallet_id) params.wallet_id = wallet_id;
    return this._get<Card[]>('/api/v2/cards', params, options);
  }

  async get(card_id: string, options?: RequestOptions): Promise<Card> {
    return this._get<Card>(`/api/v2/cards/${card_id}`, undefined, options);
  }

  async freeze(card_id: string, options?: RequestOptions): Promise<Card> {
    return this._post<Card>(`/api/v2/cards/${card_id}/freeze`, {}, options);
  }

  async unfreeze(card_id: string, options?: RequestOptions): Promise<Card> {
    return this._post<Card>(`/api/v2/cards/${card_id}/unfreeze`, {}, options);
  }

  async cancel(card_id: string, options?: RequestOptions): Promise<void> {
    await this._delete<void>(`/api/v2/cards/${card_id}`, options);
  }

  async updateLimits(
    card_id: string,
    input: UpdateCardLimitsInput,
    options?: RequestOptions
  ): Promise<Card> {
    return this._patch<Card>(`/api/v2/cards/${card_id}/limits`, input, options);
  }

  async transactions(card_id: string, limit: number = 50, options?: RequestOptions): Promise<CardTransaction[]> {
    return this._get<CardTransaction[]>(
      `/api/v2/cards/${card_id}/transactions`,
      { limit },
      options
    );
  }

  async simulatePurchase(
    card_id: string,
    input: SimulateCardPurchaseInput,
    options?: RequestOptions
  ): Promise<SimulateCardPurchaseResponse> {
    return this._post<SimulateCardPurchaseResponse>(
      `/api/v2/cards/${card_id}/simulate-purchase`,
      input,
      options
    );
  }
}

