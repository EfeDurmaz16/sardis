# CrewAI Procurement Team

Multi-agent procurement system with Sardis + CrewAI.

## Agents

- **Vendor Researcher** - Finds and compares vendors
- **Procurement Agent** - Executes purchases with Sardis wallet
- **Spend Auditor** - Reviews transactions for compliance

## Setup

```bash
pip install sardis-crewai crewai crewai-tools
```

## Run

```bash
export SARDIS_API_KEY="sk_..."
export OPENAI_API_KEY="sk-..."
python main.py
```
