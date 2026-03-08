# PR: Add Sardis provider documentation

## Target Repo
`langchain-ai/langchain`

## Branch
`docs/add-sardis-provider`

## Files
- `docs/docs/integrations/providers/sardis.mdx`

## PR Title
docs: add Sardis provider integration page

## PR Body

## Summary
- Adds Sardis as a community integration provider
- Sardis enables AI agents to make policy-controlled payments through non-custodial MPC wallets
- The `sardis-langchain` package is published on [PyPI](https://pypi.org/project/sardis-langchain/)

## What is Sardis?
Sardis is the Payment OS for the Agent Economy — infrastructure enabling AI agents to make real financial transactions safely. It provides:
- Non-custodial MPC wallets (Turnkey)
- Natural language spending policies
- Multi-chain stablecoin payments (USDC/USDT on Base, Polygon, Ethereum, Arbitrum, Optimism)
- Full audit trail

## Tools provided
- `SardisPaymentTool` — Execute policy-controlled payments
- `SardisBalanceTool` — Check balance and spending limits
- `SardisPolicyCheckTool` — Pre-check payment policy compliance

## Links
- Website: https://sardis.sh
- Docs: https://sardis.sh/docs
- PyPI: https://pypi.org/project/sardis-langchain/
- GitHub: https://github.com/EfeDurmaz16/sardis
