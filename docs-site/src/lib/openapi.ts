import { createOpenAPI } from 'fumadocs-openapi/server';

export const openapi = createOpenAPI({
  // The OpenAPI spec will be loaded from the Sardis API
  // For local dev, use a local copy; for production, fetch from API
  proxyUrl: '/api/openapi-proxy',
});
