# PAN Boundary Provider Matrix

This matrix documents the intended default card-data boundary by provider
profile. It is deliberately conservative for OSS pilots.

| Provider profile | Default boundary | Break-glass support | Reason |
| --- | --- | --- | --- |
| Stripe issuing | Provider hosted | No by default | Keep PAN handling outside Sardis and use provider-hosted reveal controls. |
| Lithic issuing | Hosted only | Optional with explicit override | Lithic can support deeper card operations, but OSS pilots should default to hosted-only. |
| Partner card issuer | Provider hosted | Provider-specific | The provider adapter must declare whether direct PAN entry is supported. |
| Mock/simulation | Synthetic only | Yes in local dev | Test data may exercise control logic but must not model real PAN storage. |

## Required Runtime Behavior

- The API must expose the effective provider boundary through a security policy
  endpoint.
- Provider profile locks must explain why PAN entry is disallowed.
- Invalid revealed card details must fail closed before execution.
- Break-glass modes must require explicit environment configuration and
  approval quorum before use.
