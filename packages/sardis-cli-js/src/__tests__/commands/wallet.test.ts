import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Command } from 'commander';
import { registerWalletCommand } from '../../commands/wallet.js';

vi.mock('../../config.js', () => ({
  loadConfig: vi.fn(() => ({
    api_key: '',
    api_base_url: 'https://api.sardis.sh',
    default_chain: 'base',
    default_token: 'USDC',
    mode: 'sandbox',
    agent_id: '',
    wallet_id: '',
  })),
  isSandbox: vi.fn(() => true),
}));

describe('wallet command', () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  it('registers wallet with subcommands', () => {
    const program = new Command();
    registerWalletCommand(program);

    const cmd = program.commands.find((c) => c.name() === 'wallet');
    expect(cmd).toBeDefined();

    const subcommands = cmd?.commands.map((c) => c.name());
    expect(subcommands).toContain('list');
    expect(subcommands).toContain('create');
  });

  it('wallet list shows sandbox data', async () => {
    const program = new Command();
    registerWalletCommand(program);

    await program.parseAsync(['node', 'sardis', 'wallet', 'list']);

    const output = consoleSpy.mock.calls.map((c) => String(c[0])).join('\n');
    expect(output).toContain('sandbox');
    expect(output).toContain('wal_sim_demo01');
  });

  it('wallet create shows sandbox result', async () => {
    const program = new Command();
    registerWalletCommand(program);

    await program.parseAsync(['node', 'sardis', 'wallet', 'create', '--agent', 'test_agent']);

    const output = consoleSpy.mock.calls.map((c) => String(c[0])).join('\n');
    expect(output).toContain('sandbox');
    expect(output).toContain('Wallet created');
  });
});
