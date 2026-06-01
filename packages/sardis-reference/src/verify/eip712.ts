/**
 * EIP-712 digest for ERC-3009 TransferWithAuthorization — mirrors the domain
 * binding in `protocol/x402_erc3009.py` (`_USDC_EIP712_DOMAINS`,
 * `TRANSFER_WITH_AUTHORIZATION_TYPE`).
 *
 * Produces the 32-byte EIP-712 signing digest:
 *   keccak256( 0x1901 || domainSeparator || hashStruct(message) )
 * using @noble/hashes keccak_256 and a tiny self-contained struct encoder. No
 * viem/ethers. The secp256k1 recover step is intentionally NOT bundled here
 * (it needs @noble/curves, a 3rd dependency pending founder sign-off) — callers
 * supply a recovered signer to `verifyTimingAndBinding` in x402.ts.
 */
import { keccak_256 } from '@noble/hashes/sha3.js';
import type { ERC3009Authorization, Eip712Domain } from '../types/x402.js';

/** Static USDC EIP-712 domains, keyed by Sardis network id. Mirrors Python. */
export const USDC_EIP712_DOMAINS: Record<string, Eip712Domain> = {
  base: { name: 'USD Coin', version: '2', chainId: 8453, verifyingContract: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' },
  base_sepolia: { name: 'USDC', version: '2', chainId: 84532, verifyingContract: '0x036CbD53842c5426634e7929541eC2318f3dCF7e' },
  ethereum: { name: 'USD Coin', version: '2', chainId: 1, verifyingContract: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48' },
  polygon: { name: 'USD Coin', version: '2', chainId: 137, verifyingContract: '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359' },
  arbitrum: { name: 'USD Coin', version: '2', chainId: 42161, verifyingContract: '0xaf88d065e77c8cC2239327C5EDb3A432268e5831' },
  optimism: { name: 'USD Coin', version: '2', chainId: 10, verifyingContract: '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85' },
};

export class X402VerificationError extends Error {}

export function resolveEip712Domain(network: string): Eip712Domain {
  const d = USDC_EIP712_DOMAINS[(network || '').trim().toLowerCase()];
  if (!d) {
    throw new X402VerificationError(`unsupported_network_for_eip3009:${network}`);
  }
  return d;
}

const ENCODER = new TextEncoder();

function concat(...parts: Uint8Array[]): Uint8Array {
  const len = parts.reduce((n, p) => n + p.length, 0);
  const out = new Uint8Array(len);
  let off = 0;
  for (const p of parts) {
    out.set(p, off);
    off += p.length;
  }
  return out;
}

/** Big-endian 32-byte encoding of a non-negative bigint (uint256). */
export function uint256(value: bigint): Uint8Array {
  if (value < 0n) throw new X402VerificationError('uint256_must_be_non_negative');
  const out = new Uint8Array(32);
  let v = value;
  for (let i = 31; i >= 0 && v > 0n; i--) {
    out[i] = Number(v & 0xffn);
    v >>= 8n;
  }
  return out;
}

/** 20-byte address left-padded to 32 bytes (mirrors `_address_to_bytes32`). */
export function addressToBytes32(address: string): Uint8Array {
  let a = address.toLowerCase();
  if (a.startsWith('0x')) a = a.slice(2);
  if (a.length !== 40) {
    throw new X402VerificationError(`invalid_address_length: expected 20 bytes, got ${a.length / 2}`);
  }
  const out = new Uint8Array(32);
  for (let i = 0; i < 20; i++) {
    out[12 + i] = parseInt(a.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

/** Hex string → exactly 32 bytes, left-padded (mirrors `_hex_to_bytes32`). */
export function hexToBytes32(hexString: string): Uint8Array {
  let h = hexString.toLowerCase();
  if (h.startsWith('0x')) h = h.slice(2);
  if (h.length % 2 !== 0) h = '0' + h;
  const raw = new Uint8Array(h.length / 2);
  for (let i = 0; i < raw.length; i++) {
    raw[i] = parseInt(h.slice(i * 2, i * 2 + 2), 16);
  }
  if (raw.length > 32) {
    throw new X402VerificationError(`hex_too_long: expected max 32 bytes, got ${raw.length}`);
  }
  const out = new Uint8Array(32);
  out.set(raw, 32 - raw.length);
  return out;
}

const TRANSFER_TYPEHASH = keccak_256(
  ENCODER.encode(
    'TransferWithAuthorization(address from,address to,uint256 value,uint256 validAfter,uint256 validBefore,bytes32 nonce)',
  ),
);

const DOMAIN_TYPEHASH = keccak_256(
  ENCODER.encode('EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)'),
);

function domainSeparator(domain: Eip712Domain): Uint8Array {
  return keccak_256(
    concat(
      DOMAIN_TYPEHASH,
      keccak_256(ENCODER.encode(domain.name)),
      keccak_256(ENCODER.encode(domain.version)),
      uint256(BigInt(domain.chainId)),
      addressToBytes32(domain.verifyingContract),
    ),
  );
}

function hashStruct(auth: ERC3009Authorization): Uint8Array {
  return keccak_256(
    concat(
      TRANSFER_TYPEHASH,
      addressToBytes32(auth.fromAddress),
      addressToBytes32(auth.toAddress),
      uint256(auth.value),
      uint256(BigInt(auth.validAfter)),
      uint256(BigInt(auth.validBefore)),
      hexToBytes32(auth.nonce),
    ),
  );
}

/** The 32-byte EIP-712 digest a signer commits to for this authorization. */
export function eip712Digest(auth: ERC3009Authorization, network: string): Uint8Array {
  const domain = resolveEip712Domain(network);
  return keccak_256(concat(new Uint8Array([0x19, 0x01]), domainSeparator(domain), hashStruct(auth)));
}
