/**
 * Sardis API Client for MCP Server
 *
 * Handles all API communication with the Sardis backend.
 */

import { getConfig } from './config.js';

/**
 * Make an API request to Sardis
 */
export async function apiRequest<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const config = getConfig();
  const url = `${config.apiUrl}${path.startsWith('/') ? path : '/' + path}`;
  const paymentIdentity = process.env.SARDIS_PAYMENT_IDENTITY;

  const response = await fetch(url, {
    method,
    headers: {
      'X-API-Key': config.apiKey,
      'Content-Type': 'application/json',
      'User-Agent': 'sardis-mcp-server/0.1.0',
      ...(paymentIdentity ? { 'X-Sardis-Payment-Identity': paymentIdentity } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API error ${response.status}: ${errorBody}`);
  }

  return response.json() as Promise<T>;
}

/**
 * Generate unique mandate ID
 *
 * SECURITY: Uses crypto.randomUUID() for cryptographically secure IDs.
 * Math.random() is not suitable for security-relevant identifiers.
 */
export function generateMandateId(): string {
  const id = (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID().replace(/-/g, '').substring(0, 16)
    : Array.from(
        (typeof crypto !== 'undefined' && crypto.getRandomValues)
          ? crypto.getRandomValues(new Uint8Array(8))
          : new Uint8Array(8).map(() => Math.floor(Math.random() * 256)),
      ).map((b) => b.toString(16).padStart(2, '0')).join('');
  return `mnd_${id}`;
}

/**
 * Create SHA-256 hash for audit
 *
 * SECURITY: The fallback now uses Node.js crypto module instead of a
 * predictable timestamp string. Audit hashes must provide collision
 * resistance for financial integrity.
 */
export async function createAuditHash(data: string): Promise<string> {
  if (typeof crypto !== 'undefined' && crypto.subtle) {
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(data);
    const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
  }
  // Fallback: use Node.js crypto (always available in Node environments)
  try {
    const { createHash } = await import('node:crypto');
    return createHash('sha256').update(data).digest('hex');
  } catch {
    // SECURITY: Refuse to produce a fake hash — fail-closed.
    throw new Error(
      'No cryptographic hash function available. '
      + 'Audit integrity cannot be guaranteed without SHA-256.'
    );
  }
}
