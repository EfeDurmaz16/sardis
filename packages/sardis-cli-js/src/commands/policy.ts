/**
 * sardis policy check|set|list - Spending policy management
 */

import type { Command } from 'commander';
import chalk from 'chalk';
import { loadConfig, isSandbox } from '../config.js';
import { SardisAPI, APIError } from '../api.js';
import { printError, printSuccess, printSandboxBanner, printTable, printKeyValue, printHeader, brand, spinner } from '../output.js';

export function registerPolicyCommand(program: Command): void {
  const policy = program
    .command('policy')
    .description('Spending policy management');

  policy
    .command('check')
    .description('Check if a payment would be allowed by policy')
    .requiredOption('--agent <agent-id>', 'Agent ID')
    .requiredOption('--amount <number>', 'Transaction amount', parseFloat)
    .option('--to <address>', 'Destination address')
    .option('--token <token>', 'Token', 'USDC')
    .action(async (opts: { agent: string; amount: number; to?: string; token: string }) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printHeader('Policy Check Result');

        const allowed = opts.amount <= 500;
        console.log(allowed
          ? `  ${chalk.bold.green('ALLOWED')}`
          : `  ${chalk.bold.red('DENIED')}`);

        if (!allowed) {
          console.log(`  Reason: Amount $${opts.amount.toFixed(2)} exceeds per-transaction limit of $500.00`);
        }

        console.log(`\n  ${chalk.green('Checks Passed (3):')}`);
        console.log(`    ${chalk.green('+')} Agent is active`);
        console.log(`    ${chalk.green('+')} Token USDC is allowed`);
        console.log(`    ${chalk.green('+')} Destination not blocked`);

        if (!allowed) {
          console.log(`\n  ${chalk.red('Checks Failed (1):')}`);
          console.log(`    ${chalk.red('-')} Per-transaction limit exceeded`);
        }
        console.log();
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Checking policy...').start();

      try {
        const payload: Record<string, unknown> = {
          agent_id: opts.agent,
          amount: opts.amount,
          token: opts.token,
        };
        if (opts.to) payload['destination'] = opts.to;

        const result = await api.post<Record<string, unknown>>('/api/v2/policies/check', payload);
        spin.stop();

        printHeader('Policy Check Result');

        const allowed = result['allowed'] as boolean;
        console.log(allowed
          ? `  ${chalk.bold.green('ALLOWED')}`
          : `  ${chalk.bold.red('DENIED')}`);

        if (result['reason']) {
          console.log(`  Reason: ${result['reason']}`);
        }

        const passed = (result['checks_passed'] as string[]) || [];
        const failed = (result['checks_failed'] as string[]) || [];

        if (passed.length > 0) {
          console.log(`\n  ${chalk.green(`Checks Passed (${passed.length}):`)}`);
          for (const c of passed) console.log(`    ${chalk.green('+')} ${c}`);
        }
        if (failed.length > 0) {
          console.log(`\n  ${chalk.red(`Checks Failed (${failed.length}):`)}`);
          for (const c of failed) console.log(`    ${chalk.red('-')} ${c}`);
        }
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });

  policy
    .command('set')
    .description('Set or update an agent spending policy')
    .requiredOption('--agent <agent-id>', 'Agent ID')
    .option('--max-per-tx <amount>', 'Maximum per transaction', parseFloat)
    .option('--max-total <amount>', 'Maximum total spend', parseFloat)
    .option('--allowed-destinations <addrs>', 'Comma-separated allowed destinations')
    .option('--policy <text>', 'Natural language policy description')
    .action(async (opts: {
      agent: string;
      maxPerTx?: number;
      maxTotal?: number;
      allowedDestinations?: string;
      policy?: string;
    }) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printSuccess('Policy applied successfully');
        console.log();
        const pairs: Array<[string, string]> = [['Agent', opts.agent]];
        if (opts.maxPerTx !== undefined) pairs.push(['Max Per TX', `$${opts.maxPerTx.toFixed(2)}`]);
        if (opts.maxTotal !== undefined) pairs.push(['Max Total', `$${opts.maxTotal.toFixed(2)}`]);
        if (opts.allowedDestinations) pairs.push(['Allowed Dests', opts.allowedDestinations]);
        if (opts.policy) pairs.push(['Policy', opts.policy]);
        printKeyValue(pairs);
        console.log();
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Applying policy...').start();

      try {
        const payload: Record<string, unknown> = { agent_id: opts.agent };
        if (opts.maxPerTx !== undefined) payload['max_per_tx'] = opts.maxPerTx;
        if (opts.maxTotal !== undefined) payload['max_total'] = opts.maxTotal;
        if (opts.allowedDestinations) {
          payload['allowed_destinations'] = opts.allowedDestinations.split(',').map((d) => d.trim()).filter(Boolean);
        }
        if (opts.policy) payload['policy'] = opts.policy;

        const result = await api.post<Record<string, unknown>>('/api/v2/policies/apply', payload);
        spin.stop();

        printSuccess('Policy applied successfully');
        console.log();
        printKeyValue([
          ['Agent', opts.agent],
          ['Policy ID', String(result['policy_id'] || 'N/A')],
        ]);
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });

  policy
    .command('list')
    .description('List policies for an agent')
    .requiredOption('--agent <agent-id>', 'Agent ID')
    .action(async (opts: { agent: string }) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printTable(
          ['Policy ID', 'Agent', 'Per-TX Limit', 'Total Limit', 'Destinations', 'Status'],
          [
            ['pol_abc123', opts.agent, '$500.00', '$5,000.00', 'Any', chalk.green('Active')],
          ],
        );
        console.log();
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Fetching policies...').start();

      try {
        const result = await api.get<Record<string, unknown>>(`/api/v2/policies/${opts.agent}`);
        spin.stop();

        const policies = (result['policies'] as Array<Record<string, unknown>>)
          || (result['policy_id'] ? [result] : []);

        if (policies.length === 0) {
          console.log(brand.dim('\n  No policies found for this agent\n'));
          return;
        }

        printTable(
          ['Policy ID', 'Agent', 'Per-TX Limit', 'Total Limit', 'Destinations', 'Status'],
          policies.map((p) => {
            const dests = (p['allowed_destinations'] as string[]) || [];
            const status = String(p['status'] || 'active');
            return [
              String(p['policy_id'] || ''),
              String(p['agent_id'] || opts.agent),
              p['max_per_tx'] != null ? `$${p['max_per_tx']}` : 'Unlimited',
              p['max_total'] != null ? `$${p['max_total']}` : 'Unlimited',
              dests.length > 0 ? dests.join(', ') : 'Any',
              status === 'active' ? chalk.green('Active') : chalk.dim(status),
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
