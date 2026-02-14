# Investor Claims Evidence

Last verified: 2026-02-14

## Public Claims Mapping

| Claim | Current Value | Evidence |
|---|---:|---|
| MCP tools | 52 | `packages/sardis-mcp-server/package.json:99` (`mcp.tools` list), validated by `scripts/audit/claims_check.py` |
| Total packages (npm + PyPI) | 19 | `scripts/audit/claims_check.py:40`-`scripts/audit/claims_check.py:49` (14 Python + 4 npm + 1 meta) |
| Test volume | 758 selected / 820 total | `scripts/audit/claims_check.py:52`-`scripts/audit/claims_check.py:74`, command: `python3 scripts/audit/claims_check.py --json` |
| Supported chains (mainnet) | 5 | `packages/sardis-chain/src/sardis_chain/executor.py:121`, `packages/sardis-chain/src/sardis_chain/executor.py:91`, `packages/sardis-chain/src/sardis_chain/executor.py:106`, `packages/sardis-chain/src/sardis_chain/executor.py:136`, `packages/sardis-chain/src/sardis_chain/executor.py:151` |
| Protocol coverage | 5 (AP2, TAP, UCP, A2A, x402) | AP2/TAP/x402 exports in `packages/sardis-protocol/src/sardis_protocol/__init__.py:1`; UCP package in `packages/sardis-ucp/src/sardis_ucp/__init__.py:1`; A2A package in `packages/sardis-a2a/src/sardis_a2a/__init__.py:1` |

## Protocol Test Evidence

- AP2: `tests/test_ap2_chain_audit_integrity.py:1`, `tests/test_ap2_compliance_checks.py:1`
- TAP: `tests/test_tap_signature_validation.py:1`
- UCP: `tests/test_ucp_conformance_harness.py:1`
- A2A: `tests/test_agent_card.py:1`, `tests/test_messages.py:1`
- x402: `tests/test_x402_challenge_response.py:1`, `tests/test_x402_schema_validation.py:1`

## Verification Commands

```bash
python3 scripts/audit/claims_check.py --json
STRICT_MODE=1 bash ./scripts/check_release_readiness.sh
pytest -q tests/test_e2e_full_flow.py -m e2e
```

## Latest Command Output Snapshot

```json
{"mcp_tools":52,"packages":{"python_packages_under_packages":14,"npm_packages_under_packages":4,"root_meta_package":1,"total_packages_claimable":19},"tests_collected":{"selected":758,"total":820,"deselected":62,"ok":1}}
```
