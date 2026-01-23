/**
 * MCP Server Configuration
 *
 * Loads configuration from environment variables with sensible defaults.
 * Supports both live and simulated modes for development.
 */

export interface MCPConfig {
  // API Configuration
  apiKey: string;
  apiUrl: string;

  // Wallet Configuration
  walletId: string;
  agentId: string;

  // Chain Configuration
  chain: string;
  mode: 'live' | 'simulated';

  // Policy Configuration (configurable instead of hardcoded)
  policyBlockedVendors: string[];
  policyAllowedVendors: string[];
  fetchAgentPolicy: boolean;
  requireExplicitApproval: boolean;
}

/**
 * Load configuration from environment variables
 */
export function loadConfig(): MCPConfig {
  // Parse comma-separated vendor lists from environment
  const parseVendorList = (envVar: string | undefined, defaults: string[]): string[] => {
    if (!envVar) return defaults;
    return envVar.split(',').map((v) => v.trim().toLowerCase()).filter(Boolean);
  };

  // Default blocked vendors (can be overridden)
  const defaultBlockedVendors = ['amazon', 'ebay', 'aliexpress', 'wish'];

  // Default allowed SaaS vendors (can be overridden)
  const defaultAllowedVendors = [
    'openai', 'anthropic', 'aws', 'gcp', 'azure', 'vercel',
    'supabase', 'stripe', 'github', 'netlify', 'cloudflare',
    'mongodb', 'redis', 'postgresql', 'datadog', 'sentry',
  ];

  return {
    apiKey: process.env.SARDIS_API_KEY || '',
    apiUrl: (process.env.SARDIS_API_URL || 'https://api.sardis.network').replace(/\/$/, ''),
    walletId: process.env.SARDIS_WALLET_ID || '',
    agentId: process.env.SARDIS_AGENT_ID || '',
    chain: process.env.SARDIS_CHAIN || 'base_sepolia',
    mode: (process.env.SARDIS_MODE || 'simulated') as 'live' | 'simulated',

    // Policy configuration from environment
    policyBlockedVendors: parseVendorList(
      process.env.SARDIS_POLICY_BLOCKED_VENDORS,
      defaultBlockedVendors
    ),
    policyAllowedVendors: parseVendorList(
      process.env.SARDIS_POLICY_ALLOWED_VENDORS,
      defaultAllowedVendors
    ),
    fetchAgentPolicy: process.env.SARDIS_FETCH_AGENT_POLICY === 'true',
    requireExplicitApproval: process.env.SARDIS_REQUIRE_EXPLICIT_APPROVAL === 'true',
  };
}

// Global config instance
let _config: MCPConfig | null = null;

/**
 * Get the global configuration instance
 */
export function getConfig(): MCPConfig {
  if (!_config) {
    _config = loadConfig();
  }
  return _config;
}

/**
 * Reset configuration (for testing)
 */
export function resetConfig(): void {
  _config = null;
}

/**
 * Get blocked vendors list
 */
export function getBlockedVendors(): string[] {
  return getConfig().policyBlockedVendors;
}

/**
 * Get allowed vendors list
 */
export function getAllowedVendors(): string[] {
  return getConfig().policyAllowedVendors;
}

/**
 * Check if vendor is blocked
 */
export function isVendorBlocked(vendor: string): boolean {
  const normalized = vendor.toLowerCase().trim();
  return getBlockedVendors().some((b) => normalized.includes(b));
}

/**
 * Check if vendor is explicitly allowed
 */
export function isVendorAllowed(vendor: string): boolean {
  const normalized = vendor.toLowerCase().trim();
  return getAllowedVendors().some((a) => normalized.includes(a));
}
