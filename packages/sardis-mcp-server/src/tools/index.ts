/**
 * Sardis MCP Server - Tool Registry
 *
 * Aggregates all tool definitions and handlers from domain-specific modules.
 */

import type { ToolDefinition, ToolHandler } from './types.js';

// Import tool definitions and handlers from each module
import { walletToolDefinitions, walletToolHandlers } from './wallets.js';
import { holdToolDefinitions, holdToolHandlers } from './holds.js';
import { agentToolDefinitions, agentToolHandlers } from './agents.js';
import { paymentToolDefinitions, paymentToolHandlers } from './payments.js';
import { policyToolDefinitions, policyToolHandlers } from './policy.js';

// Re-export types
export * from './types.js';

// Re-export domain functions for direct use
export { getWalletInfo, getWalletBalance } from './wallets.js';
export { checkPolicy } from './policy.js';
export { executePayment } from './payments.js';

/**
 * All tool definitions aggregated from modules
 */
export const allToolDefinitions: ToolDefinition[] = [
  ...walletToolDefinitions,
  ...holdToolDefinitions,
  ...agentToolDefinitions,
  ...paymentToolDefinitions,
  ...policyToolDefinitions,
];

/**
 * All tool handlers aggregated from modules
 */
export const allToolHandlers: Record<string, ToolHandler> = {
  ...walletToolHandlers,
  ...holdToolHandlers,
  ...agentToolHandlers,
  ...paymentToolHandlers,
  ...policyToolHandlers,
};

/**
 * Get tool handler by name
 */
export function getToolHandler(name: string): ToolHandler | undefined {
  return allToolHandlers[name];
}

/**
 * Check if a tool exists
 */
export function hasToolHandler(name: string): boolean {
  return name in allToolHandlers;
}

/**
 * Get list of all tool names
 */
export function getAllToolNames(): string[] {
  return Object.keys(allToolHandlers);
}

/**
 * Tool categories for organization
 */
export const toolCategories = {
  wallet: ['sardis_get_wallet', 'sardis_get_balance'],
  payment: ['sardis_pay', 'sardis_get_transaction', 'sardis_list_transactions'],
  policy: ['sardis_check_policy', 'sardis_validate_limits', 'sardis_check_compliance'],
  hold: [
    'sardis_create_hold',
    'sardis_capture_hold',
    'sardis_void_hold',
    'sardis_get_hold',
    'sardis_list_holds',
    'sardis_extend_hold',
  ],
  agent: [
    'sardis_create_agent',
    'sardis_get_agent',
    'sardis_list_agents',
    'sardis_update_agent',
  ],
} as const;

/**
 * Get tools by category
 */
export function getToolsByCategory(category: keyof typeof toolCategories): ToolDefinition[] {
  const toolNames = toolCategories[category];
  return allToolDefinitions.filter((t) => toolNames.includes(t.name as never));
}
