/**
 * Tests for MarketplaceResource
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';

const BASE_URL = 'https://api.sardis.sh';

const mockService = {
  id: 'svc_123',
  name: 'Test Service',
  description: 'A test service',
  category: 'SaaS',
  price: '50.00',
  provider_id: 'agent_001',
};

const mockOffer = {
  id: 'offer_123',
  service_id: 'svc_123',
  consumer_id: 'agent_002',
  status: 'pending',
  price: '50.00',
};

describe('MarketplaceResource', () => {
  let client: SardisClient;

  beforeEach(() => {
    client = new SardisClient({
      apiKey: 'test-key',
      baseUrl: BASE_URL,
    });
  });

  describe('Categories', () => {
    it('should list categories', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/marketplace/categories`, () => {
          return HttpResponse.json({ categories: ['SaaS', 'DevTools', 'Cloud'] });
        })
      );

      const categories = await client.marketplace.listCategories();
      expect(categories).toContain('SaaS');
      expect(categories).toContain('DevTools');
    });

    it('should return empty array when no categories', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/marketplace/categories`, () => {
          return HttpResponse.json({ categories: [] });
        })
      );

      const categories = await client.marketplace.listCategories();
      expect(categories).toHaveLength(0);
    });

    it('should handle missing categories field', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/marketplace/categories`, () => {
          return HttpResponse.json({});
        })
      );

      const categories = await client.marketplace.listCategories();
      expect(categories).toHaveLength(0);
    });
  });

  describe('Services', () => {
    it('should list services', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/marketplace/services`, () => {
          return HttpResponse.json({ services: [mockService] });
        })
      );

      const services = await client.marketplace.listServices();
      expect(services).toHaveLength(1);
      expect(services[0].name).toBe('Test Service');
    });

    it('should list services with filters', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/marketplace/services`, ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get('category')).toBe('SaaS');
          expect(url.searchParams.get('limit')).toBe('10');
          return HttpResponse.json({ services: [mockService] });
        })
      );

      const services = await client.marketplace.listServices({
        category: 'SaaS',
        limit: 10,
      });
      expect(services).toHaveLength(1);
    });

    it('should get a service by ID', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/marketplace/services/:id`, ({ params }) => {
          return HttpResponse.json({ ...mockService, id: params.id });
        })
      );

      const service = await client.marketplace.getService('svc_123');
      expect(service.id).toBe('svc_123');
    });

    it('should create a service', async () => {
      server.use(
        http.post(`${BASE_URL}/api/v2/marketplace/services`, async ({ request }) => {
          const body = await request.json() as any;
          expect(body.name).toBe('Test Service');
          expect(body.category).toBe('SaaS');
          return HttpResponse.json(mockService);
        })
      );

      const service = await client.marketplace.createService({
        name: 'Test Service',
        description: 'A test service',
        category: 'SaaS',
        price: '50.00',
      });
      expect(service.id).toBe('svc_123');
    });

    it('should search services', async () => {
      server.use(
        http.post(`${BASE_URL}/api/v2/marketplace/services/search`, async ({ request }) => {
          const body = await request.json() as any;
          expect(body.query).toBe('test');
          return HttpResponse.json({ services: [mockService] });
        })
      );

      const services = await client.marketplace.searchServices({
        query: 'test',
        category: 'SaaS',
      });
      expect(services).toHaveLength(1);
    });

    it('should return empty array for search with no results', async () => {
      server.use(
        http.post(`${BASE_URL}/api/v2/marketplace/services/search`, () => {
          return HttpResponse.json({ services: [] });
        })
      );

      const services = await client.marketplace.searchServices({ query: 'nonexistent' });
      expect(services).toHaveLength(0);
    });
  });

  describe('Offers', () => {
    it('should list offers', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/marketplace/offers`, () => {
          return HttpResponse.json({ offers: [mockOffer] });
        })
      );

      const offers = await client.marketplace.listOffers();
      expect(offers).toHaveLength(1);
    });

    it('should list offers with status filter', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/marketplace/offers`, ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get('status')).toBe('pending');
          return HttpResponse.json({ offers: [mockOffer] });
        })
      );

      const offers = await client.marketplace.listOffers({ status: 'pending' });
      expect(offers).toHaveLength(1);
    });

    it('should create an offer', async () => {
      server.use(
        http.post(`${BASE_URL}/api/v2/marketplace/offers`, async ({ request }) => {
          const body = await request.json() as any;
          expect(body.service_id).toBe('svc_123');
          return HttpResponse.json(mockOffer);
        })
      );

      const offer = await client.marketplace.createOffer({
        service_id: 'svc_123',
        price: '50.00',
      });
      expect(offer.id).toBe('offer_123');
    });

    it('should accept an offer', async () => {
      server.use(
        http.post(`${BASE_URL}/api/v2/marketplace/offers/:id/accept`, ({ params }) => {
          expect(params.id).toBe('offer_123');
          return HttpResponse.json({ ...mockOffer, status: 'accepted' });
        })
      );

      const offer = await client.marketplace.acceptOffer('offer_123');
      expect(offer.status).toBe('accepted');
    });

    it('should reject an offer', async () => {
      server.use(
        http.post(`${BASE_URL}/api/v2/marketplace/offers/:id/reject`, ({ params }) => {
          expect(params.id).toBe('offer_123');
          return HttpResponse.json({ ...mockOffer, status: 'rejected' });
        })
      );

      const offer = await client.marketplace.rejectOffer('offer_123');
      expect(offer.status).toBe('rejected');
    });

    it('should complete an offer', async () => {
      server.use(
        http.post(`${BASE_URL}/api/v2/marketplace/offers/:id/complete`, ({ params }) => {
          expect(params.id).toBe('offer_123');
          return HttpResponse.json({ ...mockOffer, status: 'completed' });
        })
      );

      const offer = await client.marketplace.completeOffer('offer_123');
      expect(offer.status).toBe('completed');
    });
  });

  describe('Reviews', () => {
    it('should create a review', async () => {
      server.use(
        http.post(`${BASE_URL}/api/v2/marketplace/offers/:id/review`, async ({ params, request }) => {
          expect(params.id).toBe('offer_123');
          const body = await request.json() as any;
          expect(body.rating).toBe(5);
          expect(body.comment).toBe('Great service!');
          return HttpResponse.json({
            id: 'review_123',
            offer_id: 'offer_123',
            rating: 5,
            comment: 'Great service!',
          });
        })
      );

      const review = await client.marketplace.createReview('offer_123', 5, 'Great service!');
      expect(review.rating).toBe(5);
    });

    it('should create a review without comment', async () => {
      server.use(
        http.post(`${BASE_URL}/api/v2/marketplace/offers/:id/review`, async ({ request }) => {
          const body = await request.json() as any;
          expect(body.rating).toBe(4);
          expect(body.comment).toBeUndefined();
          return HttpResponse.json({
            id: 'review_124',
            offer_id: 'offer_123',
            rating: 4,
          });
        })
      );

      const review = await client.marketplace.createReview('offer_123', 4);
      expect(review.rating).toBe(4);
    });
  });
});
