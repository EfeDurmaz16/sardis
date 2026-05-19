# Sardis OpenAI Package Boundary

Sardis keeps two OpenAI-facing packages because the OpenAI API tool-calling
surface and the OpenAI Agents SDK surface have different integration contracts.

## Package Roles

| Package | Runtime surface | Primary user | Owns | Does not own |
| --- | --- | --- | --- | --- |
| `packages/sardis-openai/` | OpenAI API Chat Completions and function/tool calling | Developers using `openai` client tool definitions directly | Strict-mode tool schemas, Chat Completions tool definitions, generic tool-call handling, compatibility shims used by other framework packages | OpenAI Agents SDK decorators, agent runners, framework-specific lifecycle |
| `packages/sardis-openai-agents/` | OpenAI Agents SDK | Developers building `Agent` and `Runner` workflows | Agents SDK tool functions, optional `openai-agents` integration, agent-friendly configuration helpers, simulation-safe payment tools | Generic Chat Completions tool-call schemas, SDK-neutral OpenAI helper behavior |

## Naming Decision

Keep both package directories for now:

- `sardis-openai` remains the generic OpenAI API tool-calling package.
- `sardis-openai-agents` remains the OpenAI Agents SDK package.
- Do not merge them unless one package can preserve the other's public install
  command, imports, optional dependencies, examples, and validation behavior.

## Contribution Rules

- Put Chat Completions/function-calling schema changes in
  `packages/sardis-openai/`.
- Put OpenAI Agents SDK tool/decorator/runner behavior in
  `packages/sardis-openai-agents/`.
- Put generic payment authority semantics in `packages/sardis-core/` or
  `packages/sardis-protocol/`, not in either OpenAI package.
- Put Python SDK resources in `packages/sardis-sdk-python/`.
- Keep provider credentials, hosted dashboard behavior, and production payment
  runbooks outside both packages.

## Validation

Run the owning package command before changing either package:

```bash
uv run pytest packages/sardis-openai/tests -q
uv run pytest packages/sardis-openai-agents/tests -q
```

Run the contributor gate before landing cross-package changes:

```bash
pnpm run check:contributor
```
