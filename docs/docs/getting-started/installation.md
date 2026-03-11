# Installation

## Python Packages

### Core SDK
```bash
pip install sardis-sdk
```

### Framework Integrations

Install only the integrations you need:

```bash
# OpenAI function calling
pip install sardis-openai

# LangChain tools
pip install sardis-langchain

# CrewAI tools + agents
pip install sardis-crewai

# Google ADK / Gemini
pip install sardis-adk

# Claude / Anthropic
pip install sardis-agent-sdk

# OpenClaw skill
pip install sardis-openclaw
```

### CLI
```bash
pip install sardis-cli
sardis --version
```

## TypeScript Packages

### Core SDK
```bash
npm install @sardis/sdk
```

### Framework Integrations

```bash
# Vercel AI SDK
npm install @sardis/ai-sdk

# MCP Server (Claude Desktop, Cursor, Windsurf)
npm install @sardis/mcp-server
```

## Environment Variables

```bash
# Required
export SARDIS_API_KEY="sk_..."

# Optional - for full functionality
export DATABASE_URL="postgresql://..."
export TURNKEY_API_KEY="..."
export STRIPE_SECRET_KEY="..."
```

## Verify Installation

```bash
sardis status
```

Or in Python:
```python
import sardis_sdk
print(sardis_sdk.__version__)  # 0.4.0
```
