# Payment Hardening SLO Alerts

Sardis payment pilots should alert on control-plane failures before they become
money-movement incidents.

## Alert Classes

- **Policy bypass risk:** any execution path that reaches signing or settlement
  without a policy decision and evidence record.
- **Approval quorum failure:** repeated attempts to approve with non-distinct
  reviewers or missing reviewer context.
- **Replay pressure:** elevated idempotency-key reuse, webhook replay rejection,
  or pagination cursor scope mismatches.
- **Provider boundary drift:** a provider profile asks for PAN entry or
  self-hosted card handling when hosted-only mode is required.
- **Trust graph mutation:** A2A trust relation changes without the expected
  approval, audit entry, or distinct reviewer quorum.

## Response

Critical alerts should page the operator for the affected environment. High
alerts should disable the affected rail or endpoint until the failing control is
understood. Medium alerts should create an incident note and require review
before expanding pilot limits.

## Evidence

Every alert must include the rail, tenant, environment, request identifier,
policy decision identifier when available, and the exact fail-closed reason.
