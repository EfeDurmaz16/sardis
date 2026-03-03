import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Command } from 'commander';
import { registerPayCommand } from '../../commands/pay.js';

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

describe('pay command', () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  it('registers on the program', () => {
    const program = new Command();
    registerPayCommand(program);

    const cmd = program.commands.find((c) => c.name() === 'pay');
    expect(cmd).toBeDefined();
    expect(cmd?.description()).toBe('Execute a payment');
  });

  it('requires --vendor and --amount', () => {
    const program = new Command();
    program.exitOverride();
    registerPayCommand(program);

    expect(() => {
      program.parse(['node', 'sardis', 'pay'], { from: 'user' });
    }).toThrow();
  });

  it('runs in sandbox mode with simulated output', async () => {
    const program = new Command();
    registerPayCommand(program);

    await program.parseAsync(['node', 'sardis', 'pay', '--vendor', 'openai', '--amount', '50']);

    const output = consoleSpy.mock.calls.map((c) => String(c[0])).join('\n');
    expect(output).toContain('sandbox');
    expect(output).toContain('Payment executed');
  });
});
