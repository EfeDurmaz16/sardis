/**
 * sardis spending summary - Spending analytics
 */

import type { Command } from 'commander';
import chalk from 'chalk';
import { loadConfig, isSandbox } from '../config.js';
import { SardisAPI, APIError } from '../api.js';
import { printError, printSandboxBanner, printTable, printHeader, brand, spinner } from '../output.js';

export function registerSpendingCommand(program: Command): void {
  const spending = program
    .command('spending')
    .description('Spending analytics');

  spending
    .command('summary')
    .description('Show spending summary')
    .option('--period <period>', 'Period: daily, weekly, monthly', 'monthly')
    .option('--format <format>', 'Output format: table, json', 'table')
    .option('--agent-id <id>', 'Filter by agent ID')
    .action(async (opts: { period: string; format: string; agentId?: string }) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();

        if (opts.format === 'json') {
          const data = {
            period: opts.period,
            total_spent: '2,347.50',
            total_transactions: 47,
            top_merchants: ['OpenAI', 'AWS', 'GitHub'],
            by_agent: [
              { agent_id: 'agent_abc', spent: '1,200.00', transactions: 24 },
              { agent_id: 'agent_def', spent: '890.00', transactions: 18 },
              { agent_id: 'agent_ghi', spent: '257.50', transactions: 5 },
            ],
          };
          console.log(JSON.stringify(data, null, 2));
          return;
        }

        printHeader(`Spending Summary (${opts.period})`);
        console.log(`  Total Spent:        ${chalk.bold.green('$2,347.50')}`);
        console.log(`  Transactions:       ${chalk.cyan('47')}`);
        console.log(`  Active Agents:      ${chalk.cyan('3')}`);
        console.log(`  Policy Violations:  ${chalk.red('2 blocked')}`);
        console.log();

        printTable(
          ['Agent', 'Spent', 'Txns', 'Top Merchant', 'Limit', 'Utilization'],
          [
            ['agent_abc', '$1,200.00', '24', 'OpenAI', '$2,000.00', '60%'],
            ['agent_def', '$890.00', '18', 'AWS', '$1,000.00', '89%'],
            ['agent_ghi', '$257.50', '5', 'GitHub', '$500.00', '52%'],
          ],
        );
        console.log();

        printTable(
          ['Merchant', 'Total', 'Txns'],
          [
            ['OpenAI', '$980.00', '20'],
            ['AWS', '$650.00', '12'],
            ['GitHub', '$340.00', '8'],
            ['Vercel', '$210.00', '4'],
            ['Anthropic', '$167.50', '3'],
          ],
        );
        console.log();
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Fetching spending data...').start();

      try {
        const params: Record<string, string> = { period: opts.period };
        if (opts.agentId) params['agent_id'] = opts.agentId;

        const result = await api.get<Record<string, unknown>>('/api/v2/spending/summary', params);
        spin.stop();

        if (opts.format === 'json') {
          console.log(JSON.stringify(result, null, 2));
          return;
        }

        printHeader(`Spending Summary (${opts.period})`);
        console.log(`  Total Spent:    ${chalk.bold.green(`$${result['total_spent'] || '0.00'}`)}`);
        console.log(`  Transactions:   ${chalk.cyan(String(result['total_transactions'] || 0))}`);
        console.log();

        const byAgent = (result['by_agent'] as Array<Record<string, unknown>>) || [];
        if (byAgent.length > 0) {
          printTable(
            ['Agent', 'Spent', 'Transactions'],
            byAgent.map((a) => [
              String(a['agent_id'] || ''),
              `$${a['spent'] || '0.00'}`,
              String(a['transactions'] || 0),
            ]),
          );
        }
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });
}
