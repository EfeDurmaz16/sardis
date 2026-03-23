/**
 * Payment Objects Resource
 *
 * Tokenized payment objects (digital checks, vouchers, payment tokens)
 * that can be minted, presented, and verified on-chain.
 */

import { BaseResource } from './base.js';
import type {
  PaymentObject,
  MintPaymentObjectInput,
  PresentPaymentObjectInput,
  VerifyPaymentObjectInput,
  ListPaymentObjectsParams,
  RequestOptions,
} from '../types.js';

export class PaymentObjectsResource extends BaseResource {
  /**
   * Mint a new payment object.
   *
   * Creates a tokenized payment object backed by funds in the issuer's wallet.
   *
   * @param params - Minting parameters
   * @param options - Request options (signal, timeout)
   * @returns The minted payment object
   */
  async mint(params: MintPaymentObjectInput, options?: RequestOptions): Promise<PaymentObject> {
    return this._post<PaymentObject>('/api/v2/payment-objects', params, options);
  }

  /**
   * Present a payment object to a recipient.
   *
   * Transfers ownership intent of a payment object to a specific recipient.
   *
   * @param objectId - Payment object ID
   * @param params - Presentation parameters
   * @param options - Request options (signal, timeout)
   * @returns The updated payment object
   */
  async present(
    objectId: string,
    params: PresentPaymentObjectInput,
    options?: RequestOptions
  ): Promise<PaymentObject> {
    return this._post<PaymentObject>(
      `/api/v2/payment-objects/${objectId}/present`,
      params,
      options
    );
  }

  /**
   * Verify a payment object.
   *
   * Validates the authenticity and availability of a payment object.
   *
   * @param objectId - Payment object ID
   * @param params - Verification parameters
   * @param options - Request options (signal, timeout)
   * @returns The verified payment object
   */
  async verify(
    objectId: string,
    params: VerifyPaymentObjectInput,
    options?: RequestOptions
  ): Promise<PaymentObject> {
    return this._post<PaymentObject>(
      `/api/v2/payment-objects/${objectId}/verify`,
      params,
      options
    );
  }

  /**
   * Get a payment object by ID.
   *
   * @param objectId - Payment object ID
   * @param options - Request options (signal, timeout)
   * @returns The payment object
   */
  async get(objectId: string, options?: RequestOptions): Promise<PaymentObject> {
    return this._get<PaymentObject>(`/api/v2/payment-objects/${objectId}`, undefined, options);
  }

  /**
   * List payment objects.
   *
   * @param params - Optional filter and pagination parameters
   * @param options - Request options (signal, timeout)
   * @returns List of payment objects
   */
  async list(params?: ListPaymentObjectsParams, options?: RequestOptions): Promise<PaymentObject[]> {
    const response = await this._get<{ payment_objects: PaymentObject[] } | PaymentObject[]>(
      '/api/v2/payment-objects',
      params as Record<string, unknown>,
      options
    );

    if (Array.isArray(response)) {
      return response;
    }
    return response.payment_objects || [];
  }
}
