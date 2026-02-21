import { Agent, Alert, ApprovalRequest, SpendingPolicy, SpendingSummary, QuickStats } from '../types';

const DEFAULT_BASE_URL = 'https://api.sardis.sh/api/v2';

interface ApiConfig {
  baseUrl: string;
  apiKey: string;
}

class SardisApiClient {
  private config: ApiConfig | null = null;

  configure(config: Partial<ApiConfig> & { apiKey: string }) {
    this.config = {
      baseUrl: config.baseUrl ?? DEFAULT_BASE_URL,
      apiKey: config.apiKey,
    };
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    if (!this.config) {
      throw new Error('API client not configured. Call configure() first.');
    }

    const url = `${this.config.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.config.apiKey}`,
      ...options.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      return response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Agents
  async getAgents(): Promise<Agent[]> {
    return this.request<Agent[]>('/agents');
  }

  async getAgent(agentId: string): Promise<Agent> {
    return this.request<Agent>(`/agents/${agentId}`);
  }

  // Alerts
  async getAlerts(filters?: {
    severity?: 'info' | 'warning' | 'critical';
    agentId?: string;
    unreadOnly?: boolean;
  }): Promise<Alert[]> {
    const params = new URLSearchParams();
    if (filters?.severity) params.append('severity', filters.severity);
    if (filters?.agentId) params.append('agent_id', filters.agentId);
    if (filters?.unreadOnly) params.append('unread_only', 'true');

    const query = params.toString();
    return this.request<Alert[]>(`/alerts${query ? `?${query}` : ''}`);
  }

  async markAlertAsRead(alertId: string): Promise<void> {
    await this.request(`/alerts/${alertId}/read`, {
      method: 'POST',
    });
  }

  async acknowledgeAlert(alertId: string): Promise<void> {
    await this.request(`/alerts/${alertId}/acknowledge`, {
      method: 'POST',
    });
  }

  // Approvals
  async getApprovalRequests(status?: 'pending' | 'approved' | 'rejected'): Promise<ApprovalRequest[]> {
    const params = status ? `?status=${status}` : '';
    return this.request<ApprovalRequest[]>(`/approvals${params}`);
  }

  async approveTransaction(requestId: string, note?: string): Promise<void> {
    await this.request(`/approvals/${requestId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    });
  }

  async rejectTransaction(requestId: string, reason?: string): Promise<void> {
    await this.request(`/approvals/${requestId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  // Policies
  async getPolicies(agentId?: string): Promise<SpendingPolicy[]> {
    const params = agentId ? `?agent_id=${agentId}` : '';
    return this.request<SpendingPolicy[]>(`/policies${params}`);
  }

  async updatePolicy(policyId: string, updates: Partial<SpendingPolicy>): Promise<SpendingPolicy> {
    return this.request<SpendingPolicy>(`/policies/${policyId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  async togglePolicy(policyId: string, enabled: boolean): Promise<void> {
    await this.request(`/policies/${policyId}`, {
      method: 'PATCH',
      body: JSON.stringify({ enabled }),
    });
  }

  // Reports
  async getSpendingSummary(period: '7d' | '30d' | '90d' = '30d'): Promise<SpendingSummary> {
    return this.request<SpendingSummary>(`/reports/spending?period=${period}`);
  }

  async getQuickStats(): Promise<QuickStats> {
    return this.request<QuickStats>('/stats/quick');
  }

  // Export
  async exportReport(period: '7d' | '30d' | '90d', format: 'csv' | 'pdf' = 'csv'): Promise<Blob> {
    if (!this.config) {
      throw new Error('API client not configured');
    }

    const url = `${this.config.baseUrl}/reports/export?period=${period}&format=${format}`;
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${this.config.apiKey}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }

    return response.blob();
  }
}

export const sardisApi = new SardisApiClient();
