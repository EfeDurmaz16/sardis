# Smart Contract Formal Audit Plan

## Goal
- Complete third-party formal smart-contract audit before Enterprise GA.
- Gate production release in strict mode until audit status is `completed`.

## Scope
- Contracts:
  - `contracts/src/SardisEscrow.sol`
  - `contracts/src/SardisSmartAccount.sol`
  - `contracts/src/SardisWalletFactory.sol`
- Chains:
  - `base-sepolia` (staging)
  - `base-mainnet` (production target)
- Focus:
  - Access control and governance
  - Escrow safety invariants
  - Upgrade/ownership and timelock paths
  - Reentrancy, replay, and signature validation

## Deliverables
- Signed audit report PDF (public or private URL).
- Machine-verifiable checksum (`sha256`) for the report artifact.
- Findings list with severity and remediation status.
- Re-test letter after remediations (if required by auditor).

## Candidate Firms
- Trail of Bits
- OpenZeppelin
- Spearbit / Cantina

## Process
1. Freeze scoped contracts and tag release candidate.
2. Submit code + threat model + invariants to audit firm.
3. Track findings in remediation issue set.
4. Patch, re-test, and produce final report + checksum.
5. Store the signed report, checksum, and latest status in the private compliance archive.
6. Keep the public contract test gate green with `bash scripts/release/contracts_strict_check.sh`.

## Release Gate
- Public OSS: contract formatting, build, and test gates must pass.
- Private production release: signed third-party audit evidence must be complete before Enterprise GA.
