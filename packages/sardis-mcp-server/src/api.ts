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

  const response = await fetch(url, {
    method,
    headers: {
      'X-API-Key': config.apiKey,
      'Content-Type': 'application/json',
      'User-Agent': 'sardis-mcp-server/0.1.0',
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
 */
export function generateMandateId(): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 10);
  return `mnd_${timestamp}${random}`;
}

/**
 * Create SHA-256 hash for audit
 */
export async function createAuditHash(data: string): Promise<string> {
  if (typeof crypto !== 'undefined' && crypto.subtle) {
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(data);
    const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
  }
  // Fallback for environments without crypto.subtle
  return `hash_${Date.now().toString(16)}`;
}
