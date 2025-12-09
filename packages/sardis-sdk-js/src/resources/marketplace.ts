/**
 * Marketplace resource
 */

import { BaseResource } from './base.js';
import type {
  Service,
  ServiceOffer,
  ServiceReview,
  ServiceCategory,
  OfferStatus,
  CreateServiceInput,
  CreateOfferInput,
  SearchServicesInput,
} from '../types.js';

export class MarketplaceResource extends BaseResource {
  // ==================== Categories ====================

  /**
   * List all service categories
   */
  async listCategories(): Promise<string[]> {
    const response = await this._get<{ categories: string[] }>('/api/v2/marketplace/categories');
    return response.categories || [];
  }

  // ==================== Services ====================

  /**
   * Create a new service listing
   */
  async createService(input: CreateServiceInput): Promise<Service> {
    return this._post<Service>('/api/v2/marketplace/services', input);
  }

  /**
   * List services in the marketplace
   */
  async listServices(options?: {
    category?: ServiceCategory;
    limit?: number;
    offset?: number;
  }): Promise<Service[]> {
    const response = await this._get<{ services: Service[] }>('/api/v2/marketplace/services', options);
    return response.services || [];
  }

  /**
   * Get a service by ID
   */
  async getService(serviceId: string): Promise<Service> {
    return this._get<Service>(`/api/v2/marketplace/services/${serviceId}`);
  }

  /**
   * Search for services
   */
  async searchServices(input: SearchServicesInput): Promise<Service[]> {
    const response = await this._post<{ services: Service[] }>(
      '/api/v2/marketplace/services/search',
      input
    );
    return response.services || [];
  }

  // ==================== Offers ====================

  /**
   * Create an offer for a service
   */
  async createOffer(input: CreateOfferInput): Promise<ServiceOffer> {
    return this._post<ServiceOffer>('/api/v2/marketplace/offers', input);
  }

  /**
   * List offers
   */
  async listOffers(options?: {
    status?: OfferStatus;
    as_provider?: boolean;
    as_consumer?: boolean;
  }): Promise<ServiceOffer[]> {
    const response = await this._get<{ offers: ServiceOffer[] }>('/api/v2/marketplace/offers', options);
    return response.offers || [];
  }

  /**
   * Accept an offer (as provider)
   */
  async acceptOffer(offerId: string): Promise<ServiceOffer> {
    return this._post<ServiceOffer>(`/api/v2/marketplace/offers/${offerId}/accept`, {});
  }

  /**
   * Reject an offer (as provider)
   */
  async rejectOffer(offerId: string): Promise<ServiceOffer> {
    return this._post<ServiceOffer>(`/api/v2/marketplace/offers/${offerId}/reject`, {});
  }

  /**
   * Mark an offer as completed
   */
  async completeOffer(offerId: string): Promise<ServiceOffer> {
    return this._post<ServiceOffer>(`/api/v2/marketplace/offers/${offerId}/complete`, {});
  }

  // ==================== Reviews ====================

  /**
   * Create a review for a completed offer
   */
  async createReview(offerId: string, rating: number, comment?: string): Promise<ServiceReview> {
    return this._post<ServiceReview>(`/api/v2/marketplace/offers/${offerId}/review`, {
      rating,
      comment,
    });
  }
}
