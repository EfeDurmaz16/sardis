import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Command } from 'commander';
import { registerCardCommand } from '../../commands/card.js';

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

vi.mock('ora', () => ({
  default: () => ({
    start: vi.fn().mockReturnThis(),
    stop: vi.fn(),
    succeed: vi.fn(),
    fail: vi.fn(),
  }),
}));

describe('card command', () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  it('registers card with subcommands', () => {
    const program = new Command();
    registerCardCommand(program);

    const cmd = program.commands.find((c) => c.name() === 'card');
    expect(cmd).toBeDefined();

    const subcommands = cmd?.commands.map((c) => c.name());
    expect(subcommands).toContain('issue');
    expect(subcommands).toContain('list');
    expect(subcommands).toContain('freeze');
    expect(subcommands).toContain('unfreeze');
    expect(subcommands).toContain('cancel');
  });

  it('card list shows sandbox data', async () => {
    const program = new Command();
    registerCardCommand(program);

    await program.parseAsync(['node', 'sardis', 'card', 'list']);

    const output = consoleSpy.mock.calls.map((c) => String(c[0])).join('\n');
    expect(output).toContain('sandbox');
    expect(output).toContain('card_abc123');
  });

  it('card freeze shows sandbox result', async () => {
    const program = new Command();
    registerCardCommand(program);

    await program.parseAsync(['node', 'sardis', 'card', 'freeze', 'card_test123']);

    const output = consoleSpy.mock.calls.map((c) => String(c[0])).join('\n');
    expect(output).toContain('frozen successfully');
  });
});
