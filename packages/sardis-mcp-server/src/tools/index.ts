/**
 * Sardis MCP Server - Tool Registry
 *
 * Aggregates all tool definitions and handlers from domain-specific modules.
 * Total: 50+ tools across 12 modules.
 */

import type { ToolDefinition, ToolHandler } from './types.js';

// Import tool definitions and handlers from each module
import { walletToolDefinitions, walletToolHandlers } from './wallets.js';
import { holdToolDefinitions, holdToolHandlers } from './holds.js';
import { agentToolDefinitions, agentToolHandlers } from './agents.js';
import { paymentToolDefinitions, paymentToolHandlers } from './payments.js';
import { policyToolDefinitions, policyToolHandlers } from './policy.js';
import { cardToolDefinitions, cardToolHandlers } from './cards.js';
import { fiatToolDefinitions, fiatToolHandlers } from './fiat.js';
import { approvalToolDefinitions, approvalToolHandlers } from './approvals.js';
import { spendingToolDefinitions, spendingToolHandlers } from './spending.js';
import { walletManagementToolDefinitions, walletManagementToolHandlers } from './wallet-management.js';
import { sandboxToolDefinitions, sandboxToolHandlers } from './sandbox.js';
import { groupToolDefinitions, groupToolHandlers } from './groups.js';

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
  ...cardToolDefinitions,
  ...fiatToolDefinitions,
  ...approvalToolDefinitions,
  ...spendingToolDefinitions,
  ...walletManagementToolDefinitions,
  ...sandboxToolDefinitions,
  ...groupToolDefinitions,
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
  ...cardToolHandlers,
  ...fiatToolHandlers,
  ...approvalToolHandlers,
  ...spendingToolHandlers,
  ...walletManagementToolHandlers,
  ...sandboxToolHandlers,
  ...groupToolHandlers,
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
  wallet: ['sardis_get_wallet', 'sardis_get_balance', 'sardis_create_wallet', 'sardis_list_wallets'],
  payment: ['sardis_pay', 'sardis_get_transaction', 'sardis_list_transactions'],
  policy: [
    'sardis_check_policy',
    'sardis_validate_limits',
    'sardis_check_compliance',
    'sardis_get_policies',
  ],
  hold: [
    'sardis_create_hold',
    'sardis_capture_hold',
    'sardis_void_hold',
    'sardis_release_hold',
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
  card: [
    'sardis_issue_card',
    'sardis_create_card',
    'sardis_get_card',
    'sardis_list_cards',
    'sardis_freeze_card',
    'sardis_unfreeze_card',
    'sardis_cancel_card',
  ],
  fiat: [
    'sardis_fund_wallet',
    'sardis_withdraw_to_bank',
    'sardis_withdraw',
    'sardis_get_funding_status',
    'sardis_get_withdrawal_status',
    'sardis_list_funding_transactions',
  ],
  approval: [
    'sardis_request_approval',
    'sardis_get_approval_status',
    'sardis_check_approval',
    'sardis_list_pending_approvals',
    'sardis_cancel_approval',
  ],
  sandbox: ['sardis_sandbox_demo'],
  group: [
    'sardis_create_group',
    'sardis_get_group',
    'sardis_list_groups',
    'sardis_add_agent_to_group',
    'sardis_remove_agent_from_group',
    'sardis_get_group_spending',
  ],
  spending: [
    'sardis_get_spending_summary',
    'sardis_get_spending',
    'sardis_get_spending_by_vendor',
    'sardis_get_spending_by_category',
    'sardis_get_spending_trends',
  ],
} as const;

/**
 * Get tools by category
 */
export function getToolsByCategory(category: keyof typeof toolCategories): ToolDefinition[] {
  const toolNames = toolCategories[category];
  return allToolDefinitions.filter((t) => toolNames.includes(t.name as never));
}

/**
 * Get total tool count
 */
export function getToolCount(): number {
  return allToolDefinitions.length;
}

export type ToolRegistryValidationResult = {
  definitionCount: number;
  handlerCount: number;
  isValid: boolean;
  missingHandlersForDefinitions: string[];
  missingDefinitionsForHandlers: string[];
  duplicateDefinitions: string[];
};

/**
 * Validate tool registry consistency between definitions and handlers.
 *
 * This is the authoritative source for all "tool count" claims in docs/CLI.
 */
export function validateToolRegistry(): ToolRegistryValidationResult {
  const definitionNames = allToolDefinitions.map((d) => d.name);
  const definitionSet = new Set(definitionNames);
  const handlerNames = Object.keys(allToolHandlers);
  const handlerSet = new Set(handlerNames);

  const duplicateDefinitions = definitionNames.filter(
    (name, idx) => definitionNames.indexOf(name) !== idx
  );

  const missingHandlersForDefinitions = definitionNames.filter(
    (name) => !handlerSet.has(name)
  );
  const missingDefinitionsForHandlers = handlerNames.filter(
    (name) => !definitionSet.has(name)
  );

  const isValid =
    duplicateDefinitions.length === 0 &&
    missingHandlersForDefinitions.length === 0 &&
    missingDefinitionsForHandlers.length === 0;

  return {
    definitionCount: definitionNames.length,
    handlerCount: handlerNames.length,
    isValid,
    missingHandlersForDefinitions,
    missingDefinitionsForHandlers,
    duplicateDefinitions,
  };
}

export function getValidatedToolCount(): number {
  return validateToolRegistry().definitionCount;
}

/**
 * Get tool summary for documentation
 */
export function getToolSummary(): { category: string; count: number; tools: string[] }[] {
  return Object.entries(toolCategories).map(([category, tools]) => ({
    category,
    count: tools.length,
    tools: [...tools],
  }));
}

/**
 * Get all tool definitions (alias for allToolDefinitions)
 */
export function getAllTools(): ToolDefinition[] {
  return allToolDefinitions;
}

/**
 * Get all tool handlers (alias for allToolHandlers)
 */
export function getAllToolHandlers(): Record<string, ToolHandler> {
  return allToolHandlers;
}
