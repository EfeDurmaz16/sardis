/**
 * sardis card issue|list|freeze|unfreeze|cancel - Virtual card management
 */

import type { Command } from 'commander';
import chalk from 'chalk';
import { loadConfig, isSandbox } from '../config.js';
import { SardisAPI, APIError } from '../api.js';
import { printError, printSuccess, printSandboxBanner, printTable, printKeyValue, printHeader, brand, spinner } from '../output.js';

export function registerCardCommand(program: Command): void {
  const card = program
    .command('card')
    .description('Virtual card management');

  card
    .command('issue')
    .description('Issue a virtual card for an agent')
    .requiredOption('--agent-id <id>', 'Agent to issue card for')
    .option('--limit <amount>', 'Monthly spending limit', parseFloat, 500)
    .option('--currency <currency>', 'Card currency', 'USD')
    .action(async (opts: { agentId: string; limit: number; currency: string }) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        const spin = spinner('Issuing virtual card...').start();
        await new Promise((r) => setTimeout(r, 600));
        spin.stop();

        printSuccess('Virtual card issued');
        console.log();
        printKeyValue([
          ['Card ID', brand.info('card_sim_' + Date.now().toString(36))],
          ['Agent', opts.agentId],
          ['Number', brand.dim('4242 **** **** 1234')],
          ['Limit', brand.success(`$${opts.limit.toFixed(2)}/month`)],
          ['Currency', opts.currency],
          ['Status', chalk.green('active')],
          ['Provider', 'Stripe Issuing'],
        ]);
        console.log();
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Issuing virtual card...').start();

      try {
        const result = await api.post<Record<string, unknown>>('/api/v2/cards', {
          agent_id: opts.agentId,
          spending_limit: opts.limit,
          currency: opts.currency,
        });
        spin.stop();

        printSuccess('Virtual card issued');
        console.log();
        printKeyValue([
          ['Card ID', brand.info(String(result['card_id'] || ''))],
          ['Agent', opts.agentId],
          ['Last 4', String(result['last4'] || '')],
          ['Limit', brand.success(`$${opts.limit.toFixed(2)}/month`)],
          ['Status', chalk.green(String(result['status'] || 'active'))],
        ]);
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });

  card
    .command('list')
    .description('List virtual cards')
    .option('--status <status>', 'Filter by status (active, frozen, cancelled)')
    .action(async (opts: { status?: string }) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printTable(
          ['Card ID', 'Agent', 'Last 4', 'Limit', 'Spent', 'Status', 'Provider'],
          [
            ['card_abc123', 'agent_abc', '1234', '$500.00', '$127.50', chalk.green('active'), 'Stripe'],
            ['card_def456', 'agent_def', '5678', '$1,000.00', '$890.00', chalk.green('active'), 'Stripe'],
            ['card_ghi789', 'agent_ghi', '9012', '$200.00', '$200.00', chalk.red('frozen'), 'Stripe'],
          ],
        );
        console.log();
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Fetching cards...').start();

      try {
        const params: Record<string, string> = {};
        if (opts.status) params['status'] = opts.status;

        const result = await api.get<Record<string, unknown>>('/api/v2/cards', params);
        spin.stop();

        const cards = (result['cards'] as Array<Record<string, unknown>>) || [];

        if (cards.length === 0) {
          console.log(brand.dim('\n  No cards found\n'));
          return;
        }

        printTable(
          ['Card ID', 'Agent', 'Last 4', 'Limit', 'Spent', 'Status', 'Provider'],
          cards.map((c) => {
            const status = String(c['status'] || '');
            const statusDisplay = status === 'active' ? chalk.green(status)
              : status === 'frozen' ? chalk.red(status)
              : chalk.dim(status);
            return [
              String(c['card_id'] || ''),
              String(c['agent_id'] || ''),
              String(c['last4'] || ''),
              `$${c['spending_limit'] || '0.00'}`,
              `$${c['spent'] || '0.00'}`,
              statusDisplay,
              String(c['provider'] || 'Stripe'),
            ];
          }),
        );
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });

  card
    .command('freeze')
    .description('Freeze a virtual card (temporarily disable)')
    .argument('<card-id>', 'Card ID to freeze')
    .action(async (cardId: string) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printSuccess(`Card ${cardId} frozen successfully`);
        console.log(brand.dim("  Use 'sardis card unfreeze' to re-enable\n"));
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Freezing card...').start();

      try {
        await api.post(`/api/v2/cards/${cardId}/freeze`);
        spin.stop();
        printSuccess(`Card ${cardId} frozen successfully`);
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });

  card
    .command('unfreeze')
    .description('Unfreeze a virtual card')
    .argument('<card-id>', 'Card ID to unfreeze')
    .action(async (cardId: string) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printSuccess(`Card ${cardId} is now active`);
        console.log();
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Unfreezing card...').start();

      try {
        await api.post(`/api/v2/cards/${cardId}/unfreeze`);
        spin.stop();
        printSuccess(`Card ${cardId} is now active`);
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });

  card
    .command('cancel')
    .description('Cancel a virtual card (permanent)')
    .argument('<card-id>', 'Card ID to cancel')
    .action(async (cardId: string) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printSuccess(`Card ${cardId} cancelled permanently`);
        console.log();
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Cancelling card...').start();

      try {
        await api.delete(`/api/v2/cards/${cardId}`);
        spin.stop();
        printSuccess(`Card ${cardId} cancelled permanently`);
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });
}
