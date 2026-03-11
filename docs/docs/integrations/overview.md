# Integration Overview

Sardis integrates with all major AI agent frameworks, giving your agents financial capabilities with a single package install.

## Supported Frameworks

| Framework | Package | Language | Tools |
|-----------|---------|----------|-------|
| **OpenAI** | `sardis-openai` | Python | 5 strict-mode functions |
| **LangChain** | `sardis-langchain` | Python | 5 BaseTool + Toolkit + Callbacks |
| **CrewAI** | `sardis-crewai` | Python | Tools + Pre-built agents + Templates |
| **Google ADK** | `sardis-adk` | Python | FunctionTool wrappers + Gemini declarations |
| **Claude / Anthropic** | `sardis-agent-sdk` | Python | tool_use JSON + SardisToolHandler |
| **Vercel AI SDK** | `@sardis/ai-sdk` | TypeScript | Zod-validated tools + SardisProvider |
| **MCP Server** | `@sardis/mcp-server` | TypeScript | 65+ tools for Claude/Cursor/Windsurf |
| **OpenClaw** | `sardis-openclaw` | Python | SKILL.md for 5,700+ skill ecosystem |
| **ChatGPT Actions** | OpenAPI spec | REST | 10 endpoints via Custom GPT |

## How It Works

Every integration follows the same pattern:

1. **Define tools** - Framework-specific tool definitions
2. **Agent calls tool** - AI agent decides to make a payment
3. **Policy check** - Sardis verifies the action against spending policies
4. **Execute** - Transaction executed via MPC wallet
5. **Audit** - Double-entry ledger records everything

## Quick Comparison

### Which integration should I use?

- **Building with OpenAI API?** → `sardis-openai`
- **Using LangChain?** → `sardis-langchain`
- **Multi-agent with CrewAI?** → `sardis-crewai`
- **Google Gemini / ADK?** → `sardis-adk`
- **Claude Desktop / Cursor?** → `@sardis/mcp-server`
- **Vercel AI SDK / Next.js?** → `@sardis/ai-sdk`
- **ChatGPT Custom GPT?** → MCP or OpenAPI Actions
- **OpenClaw ecosystem?** → `sardis-openclaw`
