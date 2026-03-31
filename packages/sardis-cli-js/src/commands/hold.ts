/**
 * sardis hold create|capture|void|list - Hold (pre-authorization) management
 */

import type { Command } from 'commander';
import chalk from 'chalk';
import { loadConfig, isSandbox } from '../config.js';
import { SardisAPI, APIError } from '../api.js';
import { printError, printSuccess, printSandboxBanner, printTable, printKeyValue, printHeader, brand, spinner } from '../output.js';

export function registerHoldCommand(program: Command): void {
  const hold = program
    .command('hold')
    .description('Hold (pre-authorization) management');

  hold
    .command('create')
    .description('Create a hold (pre-authorization)')
    .requiredOption('--wallet <wallet-id>', 'Wallet ID')
    .requiredOption('--amount <number>', 'Hold amount', parseFloat)
    .option('--token <token>', 'Token', 'USDC')
    .option('--merchant <id>', 'Merchant ID')
    .option('--purpose <text>', 'Hold purpose')
    .option('--hours <number>', 'Expiration hours', parseInt, 24)
    .action(async (opts: {
      wallet: string;
      amount: number;
      token: string;
      merchant?: string;
      purpose?: string;
      hours: number;
    }) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printError('Cannot create holds in sandbox mode. Run `sardis login` to connect your API key.');
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Creating hold...').start();

      try {
        const data: Record<string, unknown> = {
          wallet_id: opts.wallet,
          amount: opts.amount.toFixed(2),
          token: opts.token,
          expiration_hours: opts.hours,
        };
        if (opts.merchant) data['merchant_id'] = opts.merchant;
        if (opts.purpose) data['purpose'] = opts.purpose;

        const result = await api.post<Record<string, unknown>>('/api/v2/holds', data);
        spin.stop();

        printSuccess('Hold created successfully');
        console.log();
        printKeyValue([
          ['Hold ID', brand.info(String(result['hold_id'] || ''))],
          ['Amount', `${result['amount'] || opts.amount.toFixed(2)} ${result['token'] || opts.token}`],
          ['Expires', String(result['expires_at'] || '')],
        ]);
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });

  hold
    .command('capture')
    .description('Capture a hold')
    .argument('<hold-id>', 'Hold ID to capture')
    .option('--amount <number>', 'Capture amount (defaults to full hold)', parseFloat)
    .action(async (holdId: string, opts: { amount?: number }) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printError('Cannot capture holds in sandbox mode. Run `sardis login` to connect your API key.');
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Capturing hold...').start();

      try {
        const data: Record<string, string> = {};
        if (opts.amount !== undefined) data['amount'] = opts.amount.toFixed(2);

        const result = await api.post<Record<string, unknown>>(`/api/v2/holds/${holdId}/capture`, data);
        spin.stop();

        printSuccess('Hold captured successfully');
        console.log();
        printKeyValue([
          ['Hold ID', holdId],
          ['Captured', String(result['captured_amount'] || '')],
          ['Status', chalk.green(String(result['status'] || 'captured'))],
        ]);
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });

  hold
    .command('void')
    .description('Void a hold')
    .argument('<hold-id>', 'Hold ID to void')
    .action(async (holdId: string) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printError('Cannot void holds in sandbox mode. Run `sardis login` to connect your API key.');
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Voiding hold...').start();

      try {
        const result = await api.post<Record<string, unknown>>(`/api/v2/holds/${holdId}/void`);
        spin.stop();

        printSuccess('Hold voided successfully');
        console.log();
        printKeyValue([
          ['Hold ID', holdId],
          ['Status', chalk.dim(String(result['status'] || 'voided'))],
        ]);
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });

  hold
    .command('list')
    .description('List holds')
    .option('--wallet <wallet-id>', 'Filter by wallet ID')
    .action(async (opts: { wallet?: string }) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        console.log(brand.dim('\n  No real holds available in sandbox mode.'));
        console.log(brand.dim('  Run `sardis login` to connect your API key and list real holds.\n'));
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Fetching holds...').start();

      try {
        const path = opts.wallet ? `/api/v2/holds/wallet/${opts.wallet}` : '/api/v2/holds';
        const result = await api.get<Record<string, unknown>>(path);
        spin.stop();

        const holds = (result['holds'] as Array<Record<string, unknown>>) || [];

        if (holds.length === 0) {
          console.log(brand.dim('\n  No holds found\n'));
          return;
        }

        printTable(
          ['Hold ID', 'Wallet', 'Amount', 'Status', 'Expires'],
          holds.map((h) => {
            const status = String(h['status'] || '');
            const statusDisplay = status === 'active' ? chalk.cyan(status)
              : status === 'captured' ? chalk.green(status)
              : chalk.dim(status);
            return [
              String(h['hold_id'] || '').slice(0, 16) + '...',
              String(h['wallet_id'] || '').slice(0, 16) + '...',
              `${h['amount'] || '0.00'} ${h['token'] || 'USDC'}`,
              statusDisplay,
              String(h['expires_at'] || '').slice(0, 16),
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
}
