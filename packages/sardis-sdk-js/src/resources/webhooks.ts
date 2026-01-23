/**
 * Webhooks resource
 */

import { BaseResource } from './base.js';
import type { Webhook, WebhookDelivery, CreateWebhookInput, UpdateWebhookInput } from '../types.js';

export class WebhooksResource extends BaseResource {
  /**
   * List all available webhook event types
   */
  async listEventTypes(): Promise<string[]> {
    const response = await this._get<{ event_types: string[] }>('/api/v2/webhooks/event-types');
    return response.event_types || [];
  }

  /**
   * Create a webhook subscription
   */
  async create(input: CreateWebhookInput): Promise<Webhook> {
    return this._post<Webhook>('/api/v2/webhooks', input);
  }

  /**
   * List all webhook subscriptions
   */
  async list(): Promise<Webhook[]> {
    const response = await this._get<{ webhooks: Webhook[] }>('/api/v2/webhooks');
    return response.webhooks || [];
  }

  /**
   * Get a webhook subscription by ID
   *
   * @param webhookId - The webhook ID
   * @returns The webhook object
   */
  async get(webhookId: string): Promise<Webhook> {
    return this._get<Webhook>(`/api/v2/webhooks/${webhookId}`);
  }

  /**
   * Get a webhook subscription by ID
   *
   * @deprecated Use `get(webhookId)` instead. This method will be removed in v1.0.0.
   * @param webhookId - The webhook ID
   * @returns The webhook object
   */
  async getById(webhookId: string): Promise<Webhook> {
    return this.get(webhookId);
  }

  /**
   * Update a webhook subscription
   */
  async update(webhookId: string, input: UpdateWebhookInput): Promise<Webhook> {
    return this._patch<Webhook>(`/api/v2/webhooks/${webhookId}`, input);
  }

  /**
   * Delete a webhook subscription
   */
  async delete(webhookId: string): Promise<void> {
    await this._delete(`/api/v2/webhooks/${webhookId}`);
  }

  /**
   * Send a test event to a webhook
   */
  async test(webhookId: string): Promise<WebhookDelivery> {
    return this._post<WebhookDelivery>(`/api/v2/webhooks/${webhookId}/test`, {});
  }

  /**
   * List delivery attempts for a webhook
   */
  async listDeliveries(webhookId: string, limit: number = 50): Promise<WebhookDelivery[]> {
    const response = await this._get<{ deliveries: WebhookDelivery[] }>(
      `/api/v2/webhooks/${webhookId}/deliveries`,
      { limit }
    );
    return response.deliveries || [];
  }

  /**
   * Rotate the webhook signing secret
   */
  async rotateSecret(webhookId: string): Promise<{ secret: string }> {
    return this._post<{ secret: string }>(`/api/v2/webhooks/${webhookId}/rotate-secret`, {});
  }
}
