# @sardis/openclaw

OpenClaw skill pack for **Sardis as a TOOL**. Pure markdown skills that teach an
OpenClaw agent how to use Sardis to set a budget, check policy before spending,
pay invoices, issue cards, and verify the audit trail — with a fail-closed
dangerous-pattern block-list. **Instructions only; no money code.**

## Skills

| Skill | Teaches |
|---|---|
| `skills/spending-policy/SKILL.md` | Set a natural-language budget, then ALWAYS `sardis_check_policy` before `sardis_spend`; honor `allow / requires_approval / deny`. |
| `skills/payments/SKILL.md` | Give-wallet / spend / pay-invoice / issue-card / freeze-card with reversibility classes + a dangerous-pattern block-list. |
| `skills/audit/SKILL.md` | Read the audit ledger (`sardis_list_transactions`) and verify a portable Proof-of-Authority offline. |

All skills are `user-invocable: false` and env-gated by `SARDIS_API_KEY`. The
agent consumes governance as *instructions* — the actual verbs are provided by
[`@sardis/agent-tools`](https://www.npmjs.com/package/@sardis/agent-tools) (and
its LangChain / Vercel-AI / MCP adapters) or the Sardis MCP server.

## Validation

`pnpm test` runs `scripts/validate-skills.mjs`, which lints every SKILL.md for
valid frontmatter, the `SARDIS_API_KEY` gate, at least one real `sardis_*` verb,
and zero Aspendos/YULA branding leaks.

## Provenance

Adapted from the Aspendos OpenClaw skill-pack structure, fully rebranded to
Sardis verbs (no Aspendos/YULA/fides/agit naming survives; no emoji per the
Sardis design rule).

## License

MIT — see `LICENSE`.
