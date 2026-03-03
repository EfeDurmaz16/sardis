/**
 * CLI Configuration
 *
 * Loads/saves ~/.sardis/config.json with env var overrides.
 * Compatible with the Python CLI's config format (snake_case keys).
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

export interface CLIConfig {
  api_key: string;
  api_base_url: string;
  default_chain: string;
  default_token: string;
  mode: 'live' | 'sandbox';
  agent_id: string;
  wallet_id: string;
}

const CONFIG_DIR = join(homedir(), '.sardis');
const CONFIG_FILE = join(CONFIG_DIR, 'config.json');

const DEFAULTS: CLIConfig = {
  api_key: '',
  api_base_url: 'https://api.sardis.sh',
  default_chain: 'base',
  default_token: 'USDC',
  mode: 'sandbox',
  agent_id: '',
  wallet_id: '',
};

/**
 * Read raw config from disk
 */
function readConfigFile(): Partial<CLIConfig> {
  try {
    if (!existsSync(CONFIG_FILE)) return {};
    const raw = readFileSync(CONFIG_FILE, 'utf-8');
    return JSON.parse(raw) as Partial<CLIConfig>;
  } catch {
    return {};
  }
}

/**
 * Load config with env var overrides
 */
export function loadConfig(): CLIConfig {
  const file = readConfigFile();

  return {
    api_key: process.env['SARDIS_API_KEY'] || file.api_key || DEFAULTS.api_key,
    api_base_url: (process.env['SARDIS_API_URL'] || file.api_base_url || DEFAULTS.api_base_url).replace(/\/$/, ''),
    default_chain: process.env['SARDIS_CHAIN'] || file.default_chain || DEFAULTS.default_chain,
    default_token: process.env['SARDIS_TOKEN'] || file.default_token || DEFAULTS.default_token,
    mode: (process.env['SARDIS_MODE'] as CLIConfig['mode']) || file.mode || DEFAULTS.mode,
    agent_id: process.env['SARDIS_AGENT_ID'] || file.agent_id || DEFAULTS.agent_id,
    wallet_id: process.env['SARDIS_WALLET_ID'] || file.wallet_id || DEFAULTS.wallet_id,
  };
}

/**
 * Save config to disk (merges with existing)
 */
export function saveConfig(updates: Partial<CLIConfig>): void {
  const existing = readConfigFile();
  const merged = { ...existing, ...updates };

  if (!existsSync(CONFIG_DIR)) {
    mkdirSync(CONFIG_DIR, { recursive: true });
  }

  writeFileSync(CONFIG_FILE, JSON.stringify(merged, null, 2) + '\n', 'utf-8');
}

/**
 * Clear credentials from config
 */
export function clearCredentials(): void {
  const existing = readConfigFile();
  delete existing.api_key;
  delete existing.agent_id;
  delete existing.wallet_id;

  if (!existsSync(CONFIG_DIR)) {
    mkdirSync(CONFIG_DIR, { recursive: true });
  }

  writeFileSync(CONFIG_FILE, JSON.stringify(existing, null, 2) + '\n', 'utf-8');
}

/**
 * Check if running in sandbox mode (no API key configured)
 */
export function isSandbox(config: CLIConfig): boolean {
  return !config.api_key || config.mode === 'sandbox';
}

export function getConfigPath(): string {
  return CONFIG_FILE;
}
