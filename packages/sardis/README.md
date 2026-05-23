# sardis

> 🚧 sardis 2.0 is under active migration from 34 separate packages.
> Track progress in `project-directions/sardis-python-sdk-redesign.md`.
> For stable v1.x packages, see https://pypi.org/project/sardis-sdk/.

Payment OS for the Agent Economy — Python SDK, CLI, and runtime primitives.

## Install

```bash
pip install sardis                              # core SDK + CLI
pip install sardis[langchain]                   # + LangChain adapter
pip install sardis[crewai,openai-agents,a2a]    # multiple integrations
pip install sardis[all]                         # everything
```

## Main client

```python
from sardis import Sardis

client = Sardis(api_key="sk_live_...")
wallet = client.wallets.create(name="agent-1", chain="base")
result = client.payments.execute_mandate(mandate)
```

Async-native counterpart:

```python
from sardis import AsyncSardis

async with AsyncSardis(api_key="sk_live_...") as client:
    wallet = await client.wallets.create(name="agent-1", chain="base")
```
