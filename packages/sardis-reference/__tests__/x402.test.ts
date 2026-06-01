import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { validateAuthorizationTiming, verifyTimingAndBinding } from '../src/verify/x402.js';
import { eip712Digest } from '../src/verify/eip712.js';
import type { ERC3009Authorization } from '../src/types/x402.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

interface AuthJson {
  fromAddress: string;
  toAddress: string;
  value: string;
  validAfter: number;
  validBefore: number;
  nonce: string;
}

interface X402Vectors {
  network: string;
  now: number;
  signer: string;
  valid: {
    auth: AuthJson;
    signature: string;
    eip712Digest: string;
    recoveredSigner: string;
    expectedPayer: string;
    verify: { ok: boolean; reason: string | null };
  };
  timing: Record<string, { auth: AuthJson; expected: { ok: boolean; reason: string | null } }>;
}

const vec: X402Vectors = JSON.parse(readFileSync(join(__dirname, 'vectors', 'x402.json'), 'utf8'));

function toAuth(j: AuthJson): ERC3009Authorization {
  return {
    fromAddress: j.fromAddress,
    toAddress: j.toAddress,
    value: BigInt(j.value),
    validAfter: j.validAfter,
    validBefore: j.validBefore,
    nonce: j.nonce,
  };
}

function toHex(bytes: Uint8Array): string {
  return '0x' + Buffer.from(bytes).toString('hex');
}

describe('x402 EIP-712 digest — byte-identical to Python eth_account', () => {
  it('TS eip712Digest equals the Python signing digest', () => {
    const auth = toAuth(vec.valid.auth);
    expect(toHex(eip712Digest(auth, vec.network))).toBe(vec.valid.eip712Digest);
  });

  it('rejects an unknown network', () => {
    const auth = toAuth(vec.valid.auth);
    expect(() => eip712Digest(auth, 'dogechain')).toThrow();
  });
});

describe('validateAuthorizationTiming — exact reason parity', () => {
  for (const [name, t] of Object.entries(vec.timing)) {
    it(`${name} → ${t.expected.reason}`, () => {
      const res = validateAuthorizationTiming(toAuth(t.auth), vec.now);
      expect(res.ok).toBe(t.expected.ok);
      expect(res.reason ?? null).toBe(t.expected.reason);
    });
  }

  it('accepts a valid window', () => {
    const res = validateAuthorizationTiming(toAuth(vec.valid.auth), vec.now);
    expect(res.ok).toBe(true);
  });
});

describe('verifyTimingAndBinding — timing + signer binding (recover supplied by caller)', () => {
  it('accepts when recovered signer == from == expectedPayer (matches Python verify)', () => {
    const auth = toAuth(vec.valid.auth);
    const res = verifyTimingAndBinding(auth, vec.valid.recoveredSigner, {
      network: vec.network,
      expectedPayer: vec.valid.expectedPayer,
      now: vec.now,
    });
    expect(res.ok).toBe(vec.valid.verify.ok);
  });

  it('rejects when recovered signer != auth.from', () => {
    const auth = toAuth(vec.valid.auth);
    const res = verifyTimingAndBinding(auth, '0x' + 'ff'.repeat(20), { network: vec.network, now: vec.now });
    expect(res.reason).toBe('signer_mismatch_authorization_from');
  });

  it('rejects when recovered signer != expectedPayer', () => {
    const auth = toAuth(vec.valid.auth);
    const res = verifyTimingAndBinding(auth, vec.valid.recoveredSigner, {
      network: vec.network,
      expectedPayer: '0x' + 'ee'.repeat(20),
      now: vec.now,
    });
    expect(res.reason).toBe('signer_mismatch_payer_address');
  });

  it('rejects on expired timing before checking binding', () => {
    const auth = toAuth(vec.timing.expired!.auth);
    const res = verifyTimingAndBinding(auth, vec.valid.recoveredSigner, { network: vec.network, now: vec.now });
    expect(res.reason).toBe('authorization_expired');
  });
});
