# LangChain Payment Agent

AI agent that makes payments using Sardis + LangChain.

## Setup

```bash
pip install sardis-langchain langchain langchain-openai
```

## Run

```bash
export SARDIS_API_KEY="sk_..."
export OPENAI_API_KEY="sk-..."
python main.py
```

## What it does

1. Creates a Sardis wallet with spending policy
2. Sets up LangChain tools (pay, check balance, check policy)
3. Agent checks balance, validates policy, and executes payment
