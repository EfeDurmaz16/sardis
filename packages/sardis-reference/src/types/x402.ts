/**
 * x402 / ERC-3009 types — EIP-712 TransferWithAuthorization.
 *
 * Mirrors `protocol/x402_erc3009.py`. Amounts/timestamps are integers (and may
 * exceed 2^53 for value), so `bigint` is used for `value`.
 */

export interface ERC3009Authorization {
  fromAddress: string;
  toAddress: string;
  /** Amount in token base units. */
  value: bigint;
  /** Unix seconds — not valid before. */
  validAfter: number;
  /** Unix seconds — not valid after. */
  validBefore: number;
  /** 32-byte nonce as a hex string. */
  nonce: string;
}

export interface Eip712Domain {
  name: string;
  version: string;
  chainId: number;
  verifyingContract: string;
}

export interface X402VerificationResult {
  ok: boolean;
  reason?: string;
}
