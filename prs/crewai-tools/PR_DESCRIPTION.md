# PR: Add SardisPaymentTool

## Target Repo
`crewAIInc/crewAI-tools`

## Branch
`feat/add-sardis-payment-tool`

## Files
- `crewai_tools/tools/sardis_payment_tool/__init__.py`
- `crewai_tools/tools/sardis_payment_tool/sardis_payment_tool.py`

## PR Title
feat: add SardisPaymentTool for policy-controlled payments

## PR Body

## Summary
- Adds `SardisPaymentTool` for policy-controlled payments from CrewAI agents
- Backed by the `sardis` package on [PyPI](https://pypi.org/project/sardis/)
- Also available as standalone `sardis-crewai` package with additional tools

## Tool
`SardisPaymentTool` enables CrewAI agents to:
- Execute stablecoin payments with spending policy guardrails
- Support USDC/USDT on Base, Polygon, Ethereum, Arbitrum, Optimism
- Enforce per-agent spending limits, merchant restrictions, and category rules

## Usage
```python
from crewai_tools import SardisPaymentTool

tool = SardisPaymentTool()
# or with explicit credentials:
tool = SardisPaymentTool(api_key="sk_...", wallet_id="wal_...")
```

For the full toolkit (pay + balance + policy check), use `sardis-crewai`:
```python
pip install sardis-crewai
from sardis_crewai import create_sardis_toolkit
tools = create_sardis_toolkit()
```

## Links
- Website: https://sardis.sh
- sardis-crewai: https://pypi.org/project/sardis-crewai/
- GitHub: https://github.com/EfeDurmaz16/sardis
