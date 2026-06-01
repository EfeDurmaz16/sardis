#!/usr/bin/env node
/**
 * Generate the cross-impl IDENTITY (issue-side) vector.
 *
 * GITIGNORED-free reproducible tooling (run once; output committed). Produces
 * `__tests__/vectors/identity-issue.json`: a proof MINTED in TS with the
 * deterministic dev seed + a fixed issuedAt, exported as a JWS, plus the
 * published public key. The companion Python check
 * (`verify_identity_vectors.py`) loads this JWS and confirms the Python
 * `AuthorityProof.verify` accepts it — proving TS issue ↔ Python verify parity.
 *
 * Uses the deterministic dev Ed25519 seed only — a test key, never a secret.
 *
 * Usage:  node scripts/gen_identity_vectors.mjs
 */
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

// Import from the built dist (run `pnpm build` first) or from src via tsx.
// We import from src through the TS loader the repo already uses in tests.
const { identity } = await import('../dist/index.js');
const { issueAuthorityProof, publicKeyB64url, devSeed, toJws } = identity;

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, '..', '__tests__', 'vectors');

// Fixed issuedAt in Python isoformat() shape (UTC, +00:00 offset).
const ISSUED = '2026-01-01T12:00:00+00:00';

const proof = issueAuthorityProof({
  proofId: 'poauth_fixed_identity_1',
  actionId: 'act_ts_issue',
  agent: 'agent_b',
  amountMinor: 5_000_000n, // 5 USDC (6 decimals)
  currency: 'USDC',
  counterparty: 'merchant.example',
  policyHash: 'ph_abc',
  mandateHash: 'mh_def',
  spendingMandateId: 'mandate_root',
  amount: '5.0',
  inputs: { rail: 'usdc', chain: 'base', token: 'USDC', category: 'cloud' },
  delegationChain: null,
  issuedAt: ISSUED,
});

const out = {
  description:
    'Proof MINTED in TS (@sardis/reference identity) with the dev seed; Python AuthorityProof.verify must accept it.',
  publicKeyB64u: publicKeyB64url(devSeed()),
  jws: toJws(proof),
  issuedAt: ISSUED,
  expectValid: true,
};

writeFileSync(join(OUT, 'identity-issue.json'), JSON.stringify(out, null, 2) + '\n');
process.stderr.write('wrote __tests__/vectors/identity-issue.json\n');
