import { describe, it, expect, vi } from 'vitest';
import { governedToolCall } from '../src/governed.js';
import { runGoverned } from '../src/index.js';
import { mockSardis, ctxFor } from './helpers.js';

describe('governedToolCall — gate paths', () => {
  it('executes an allowed (compensatable) action and returns outcome=allow', async () => {
    const exec = vi.fn().mockResolvedValue({ done: true });
    const res = await governedToolCall(
      'sardis_spend',
      { to: 'm', amount: '10' },
      ctxFor(mockSardis().client),
      exec,
    );
    expect(res.status).toBe('executed');
    expect(res.outcome).toBe('allow');
    expect(res.reversibilityClass).toBe('compensatable');
    expect(res.commitHash).toMatch(/^sardis_[0-9a-f]{40}$/);
    expect(res.result).toEqual({ done: true });
    expect(exec).toHaveBeenCalledOnce();
  });

  it('requires_approval above threshold and does NOT execute', async () => {
    const exec = vi.fn().mockResolvedValue({ done: true });
    const res = await governedToolCall(
      'sardis_spend',
      { to: 'm', amount: '5000' },
      ctxFor(mockSardis().client),
      exec,
    );
    expect(res.status).toBe('awaiting_approval');
    expect(res.outcome).toBe('requires_approval');
    expect(res.reversibilityClass).toBe('approval_only');
    expect(res.commitHash).toMatch(/^sardis_[0-9a-f]{40}$/);
    expect(exec).not.toHaveBeenCalled();
  });

  it('blocks an unknown verb (fail-closed) and does NOT execute', async () => {
    const exec = vi.fn();
    const res = await governedToolCall(
      'sardis_unknown',
      {},
      ctxFor(mockSardis().client),
      exec,
    );
    expect(res.status).toBe('blocked');
    expect(res.outcome).toBe('deny');
    expect(res.reversibilityClass).toBe('irreversible_blocked');
    expect(res.commitHash).toBe('');
    expect(exec).not.toHaveBeenCalled();
  });

  it('captures a thrown execute error as blocked/deny', async () => {
    const exec = vi.fn().mockRejectedValue(new Error('backend says no'));
    const res = await governedToolCall(
      'sardis_spend',
      { to: 'm', amount: '10' },
      ctxFor(mockSardis().client),
      exec,
    );
    expect(res.status).toBe('blocked');
    expect(res.outcome).toBe('deny');
    expect(res.error).toBe('backend says no');
  });
});

describe('runGoverned — registry-resolved, fail-closed', () => {
  it('unknown tool name is blocked before any execution', async () => {
    const { client, calls } = mockSardis();
    const res = await runGoverned('sardis_not_a_verb', {}, ctxFor(client));
    expect(res.status).toBe('blocked');
    expect(res.outcome).toBe('deny');
    expect(calls).toHaveLength(0);
  });
});
