/**
 * sardis agent create|list|get - Agent management
 */

import type { Command } from 'commander';
import chalk from 'chalk';
import { loadConfig, isSandbox } from '../config.js';
import { SardisAPI, APIError } from '../api.js';
import { printError, printSuccess, printSandboxBanner, printTable, printKeyValue, printHeader, brand, spinner } from '../output.js';

export function registerAgentCommand(program: Command): void {
  const agent = program
    .command('agent')
    .description('Agent management');

  agent
    .command('list')
    .description('List all agents')
    .action(async () => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printTable(
          ['ID', 'Name', 'Status', 'Created'],
          [
            ['agent_abc', 'Shopping Assistant', chalk.green('Active'), '2025-12-01'],
            ['agent_def', 'DevOps Bot', chalk.green('Active'), '2025-12-15'],
            ['agent_ghi', 'Research Agent', chalk.dim('Inactive'), '2026-01-10'],
          ],
        );
        console.log();
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Fetching agents...').start();

      try {
        const result = await api.get<Record<string, unknown>>('/api/v2/agents');
        spin.stop();

        const agents = (result['agents'] as Array<Record<string, unknown>>) || [];

        if (agents.length === 0) {
          console.log(brand.dim('\n  No agents found\n'));
          return;
        }

        printTable(
          ['ID', 'Name', 'Status', 'Created'],
          agents.map((a) => [
            String(a['external_id'] || ''),
            String(a['name'] || ''),
            a['is_active'] ? chalk.green('Active') : chalk.dim('Inactive'),
            String(a['created_at'] || '').slice(0, 10),
          ]),
        );
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });

  agent
    .command('get')
    .description('Get agent details')
    .argument('<agent-id>', 'Agent ID')
    .action(async (agentId: string) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printHeader('Agent Details');
        printKeyValue([
          ['ID', agentId],
          ['Name', 'Shopping Assistant'],
          ['Description', 'Handles procurement and SaaS payments'],
          ['Status', chalk.green('Active')],
          ['Created', '2025-12-01T10:00:00Z'],
        ]);
        console.log();
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Fetching agent...').start();

      try {
        const a = await api.get<Record<string, unknown>>(`/api/v2/agents/${agentId}`);
        spin.stop();

        printHeader('Agent Details');
        printKeyValue([
          ['ID', String(a['external_id'] || agentId)],
          ['Name', String(a['name'] || '')],
          ['Description', String(a['description'] || 'N/A')],
          ['Status', a['is_active'] ? chalk.green('Active') : chalk.dim('Inactive')],
          ['Created', String(a['created_at'] || '')],
        ]);
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });

  agent
    .command('create')
    .description('Create a new agent')
    .requiredOption('--name <name>', 'Agent name')
    .option('--description <text>', 'Agent description')
    .action(async (opts: { name: string; description?: string }) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printSuccess('Agent created successfully');
        console.log();
        printKeyValue([
          ['ID', brand.info('agent_sim_' + Date.now().toString(36))],
          ['Name', opts.name],
        ]);
        console.log();
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Creating agent...').start();

      try {
        const data: Record<string, string> = { name: opts.name };
        if (opts.description) data['description'] = opts.description;

        const result = await api.post<Record<string, unknown>>('/api/v2/agents', data);
        spin.stop();

        printSuccess('Agent created successfully');
        console.log();
        printKeyValue([
          ['ID', brand.info(String(result['external_id'] || ''))],
          ['Name', String(result['name'] || opts.name)],
        ]);
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) printError(err.message);
        else throw err;
      }
    });
}
