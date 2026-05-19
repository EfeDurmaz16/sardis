## Summary

Explain the problem and the change.

Link the relevant package or contribution path:

- Contribution map: `docs/oss/contribution-map.md`
- Public/private boundary: `docs/oss/public-private-boundary.md`
- Public CI/CD map: `docs/oss/ci-cd.md`

## Type

- [ ] Protocol / API contract
- [ ] SDK / CLI
- [ ] MCP / integration
- [ ] Docs / examples
- [ ] Tests / CI
- [ ] Security-sensitive change
- [ ] Cleanup / refactor

## Validation

List the commands you ran.

```bash
pnpm run check:contributor
```

## OSS Boundary

- [ ] This PR does not add private commercial, customer, sales, investor, hiring, or provider-credential material.
- [ ] Public examples run without private credentials or clearly use placeholders.
- [ ] New dependencies are justified and documented.
- [ ] Package maturity and contribution-map entries are updated when adding, moving, or deleting public packages.

## Security

- [ ] No secrets, tokens, private keys, raw KYC payloads, or sensitive payment data are logged or committed.
- [ ] Payment, wallet, signing, webhook, policy, or evidence changes fail closed and include tests.
