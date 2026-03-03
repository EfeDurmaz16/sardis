/**
 * sardis wallet create|list - Wallet management
 */

import type { Command } from 'commander';
import chalk from 'chalk';
import { loadConfig, isSandbox } from '../config.js';
import { SardisAPI, APIError } from '../api.js';
import { printError, printSuccess, printSandboxBanner, printTable, printKeyValue, printHeader, brand, spinner } from '../output.js';

export function registerWalletCommand(program: Command): void {
  const wallet = program
    .command('wallet')
    .description('Wallet management');

  wallet
    .command('list')
    .description('List all wallets')
    .option('--agent <agent-id>', 'Filter by agent ID')
    .action(async (opts: { agent?: string }) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printTable(
          ['ID', 'Agent', 'Balance', 'Currency', 'Status'],
          [
            ['wal_sim_demo01', 'agent_abc', '1,250.00', 'USDC', chalk.green('Active')],
            ['wal_sim_demo02', 'agent_def', '3,400.00', 'USDC', chalk.green('Active')],
            ['wal_sim_demo03', 'agent_ghi', '0.00', 'EURC', chalk.dim('Inactive')],
          ],
        );
        console.log();
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Fetching wallets...').start();

      try {
        const params: Record<string, string> = {};
        if (opts.agent) params['agent_id'] = opts.agent;

        const result = await api.get<Record<string, unknown>>('/api/v2/wallets', params);
        spin.stop();

        const wallets = (result['wallets'] as Array<Record<string, unknown>>) || [];

        if (wallets.length === 0) {
          console.log(brand.dim('\n  No wallets found\n'));
          return;
        }

        printTable(
          ['ID', 'Agent', 'Balance', 'Currency', 'Status'],
          wallets.map((w) => [
            String(w['wallet_id'] || ''),
            String(w['agent_id'] || ''),
            String(w['balance'] || '0.00'),
            String(w['currency'] || 'USDC'),
            w['is_active'] ? chalk.green('Active') : chalk.dim('Inactive'),
          ]),
        );
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) {
          printError(err.message);
        } else {
          throw err;
        }
      }
    });

  wallet
    .command('create')
    .description('Create a new wallet')
    .requiredOption('--agent <agent-id>', 'Agent ID')
    .option('--currency <currency>', 'Currency', 'USDC')
    .action(async (opts: { agent: string; currency: string }) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printSuccess('Wallet created successfully');
        console.log();
        printKeyValue([
          ['ID', brand.info('wal_sim_' + Date.now().toString(36))],
          ['Agent', opts.agent],
          ['Currency', opts.currency],
        ]);
        console.log();
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Creating wallet...').start();

      try {
        const result = await api.post<Record<string, unknown>>('/api/v2/wallets', {
          agent_id: opts.agent,
          currency: opts.currency,
        });
        spin.stop();

        printSuccess('Wallet created successfully');
        console.log();
        printKeyValue([
          ['ID', brand.info(String(result['wallet_id'] || ''))],
          ['Agent', String(result['agent_id'] || opts.agent)],
          ['Currency', String(result['currency'] || opts.currency)],
        ]);
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) {
          printError(err.message);
        } else {
          throw err;
        }
      }
    });
}
