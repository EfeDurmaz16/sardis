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

  // x402 Configuration
  x402Enabled: boolean;
  x402MaxCost: number;
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
    apiUrl: (process.env.SARDIS_API_URL || 'https://api.sardis.sh').replace(/\/$/, ''),
    walletId: process.env.SARDIS_WALLET_ID || '',
    agentId: process.env.SARDIS_AGENT_ID || '',
    chain: process.env.SARDIS_CHAIN || 'base_sepolia',
    // Default to live: simulated mode must be an explicit opt-in
    // (SARDIS_MODE=simulated). This prevents silently degrading real
    // payments/cards into fakes when the API key is missing.
    mode: (process.env.SARDIS_MODE || 'live') as 'live' | 'simulated',

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

    // x402 configuration
    x402Enabled: process.env.SARDIS_X402_ENABLED === 'true',
    x402MaxCost: parseInt(process.env.SARDIS_X402_MAX_COST || '100', 10),
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
 * Error thrown when a tool is invoked in live mode without an API key.
 *
 * In live mode we must NEVER silently fall back to simulated/fake results —
 * doing so makes hallucinated payments and cards look real. We hard-fail
 * instead so the caller fixes their configuration.
 */
export class LiveModeMisconfiguredError extends Error {
  constructor(operation?: string) {
    const scope = operation ? ` for "${operation}"` : '';
    super(
      `SARDIS_MODE=live${scope} but SARDIS_API_KEY is not set. `
      + 'Refusing to return a fake result. '
      + 'Set SARDIS_API_KEY to execute real operations, or set '
      + 'SARDIS_MODE=simulated to explicitly opt in to simulated data.'
    );
    this.name = 'LiveModeMisconfiguredError';
  }
}

/**
 * Decide whether a tool should produce simulated data.
 *
 * Rules (trust-first):
 * - mode === 'simulated' -> simulate (explicit opt-in, no key required).
 * - mode === 'live' + apiKey present -> do NOT simulate (call the real API).
 * - mode === 'live' + no apiKey -> THROW. Never silently fake a live result.
 *
 * @param operation Optional label used in the error message for clarity.
 */
export function shouldSimulate(
  config: Pick<MCPConfig, 'apiKey' | 'mode'> = getConfig(),
  operation?: string
): boolean {
  if (config.mode === 'simulated') {
    return true;
  }
  // mode === 'live'
  if (!config.apiKey) {
    throw new LiveModeMisconfiguredError(operation);
  }
  return false;
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
