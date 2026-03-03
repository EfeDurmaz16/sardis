#!/usr/bin/env node

/**
 * Sardis CLI - The Payment OS for the Agent Economy
 *
 * Usage:
 *   sardis status              Show config & auth status
 *   sardis login               Set API key
 *   sardis pay                 Execute a payment
 *   sardis balance             Check wallet balance
 *   sardis wallet create|list  Manage wallets
 *   sardis card issue|list|... Virtual card management
 *   sardis hold create|...     Hold (pre-auth) management
 *   sardis policy check|set|.. Spending policies
 *   sardis agent create|list   Agent management
 *   sardis spending summary    Analytics
 *   sardis init                Interactive setup
 *   sardis demo                Guided walkthrough
 */

import { Command } from 'commander';
import { CLI_VERSION } from './version.js';

import { registerStatusCommand } from './commands/status.js';
import { registerLoginCommand } from './commands/login.js';
import { registerBalanceCommand } from './commands/balance.js';
import { registerPayCommand } from './commands/pay.js';
import { registerWalletCommand } from './commands/wallet.js';
import { registerAgentCommand } from './commands/agent.js';
import { registerCardCommand } from './commands/card.js';
import { registerHoldCommand } from './commands/hold.js';
import { registerPolicyCommand } from './commands/policy.js';
import { registerSpendingCommand } from './commands/spending.js';
import { registerInitCommand } from './commands/init.js';
import { registerDemoCommand } from './commands/demo.js';

const program = new Command();

program
  .name('sardis')
  .description('Sardis CLI - The Payment OS for the Agent Economy')
  .version(CLI_VERSION, '-v, --version');

// Register all commands
registerStatusCommand(program);
registerLoginCommand(program);
registerBalanceCommand(program);
registerPayCommand(program);
registerWalletCommand(program);
registerAgentCommand(program);
registerCardCommand(program);
registerHoldCommand(program);
registerPolicyCommand(program);
registerSpendingCommand(program);
registerInitCommand(program);
registerDemoCommand(program);

program.parseAsync(process.argv).catch((err: Error) => {
  console.error(`Error: ${err.message}`);
  process.exitCode = 1;
});
