# PR: Add Sardis payment tools

## Target Repo
`google/adk-python-community`

## Branch
`feat/add-sardis-payment-tools`

## Files
- `tools/sardis/__init__.py`
- `tools/sardis/sardis_tool.py`
- `tools/sardis/README.md`

## PR Title
feat: add Sardis payment tools for ADK agents

## PR Body

## Summary
- Adds Sardis payment tools for Google ADK agents
- Backed by the `sardis-adk` package on [PyPI](https://pypi.org/project/sardis-adk/)
- Enables ADK agents to make policy-controlled stablecoin payments

## Tools
- `sardis_pay` — Execute payments with policy guardrails
- `sardis_check_balance` — Check wallet balance and limits
- `sardis_check_policy` — Pre-validate payments against policy

## What is Sardis?
Sardis is the Payment OS for the Agent Economy. It provides non-custodial MPC wallets with natural language spending policies, multi-chain stablecoin support, and full audit trails.

## Links
- Website: https://sardis.sh
- PyPI: https://pypi.org/project/sardis-adk/
- GitHub: https://github.com/EfeDurmaz16/sardis
