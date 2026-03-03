# AutoGPT x Sardis Integration Playbook (No Demo Version)

Date: 2026-03-03  
Audience: AutoGPT partnership + technical team  
Purpose: show where Sardis plugs into AutoGPT, what gap it closes, and how to ship fast

## 1) The gap Sardis closes in AutoGPT workflows

AutoGPT agents can plan and execute multi-step tasks, but real-world runs often stop when money is required:
1. paid API key required
2. dataset/report paywall
3. subscription checkout
4. wallet/card funding before action

Sardis closes this by adding:
1. policy-gated spending
2. deterministic allow/deny before execution
3. auditable payment trail
4. optional compliance checks in the decision path

## 2) Current integration reality (important)

There is no dedicated AutoGPT-only Sardis adapter package yet.

This is not a hard blocker.
The practical path is to use existing Sardis APIs/SDK via AutoGPT tools/blocks, then package a first-party integration.

## 3) Fastest integration path (recommended)

## Path A - MVP in days: AutoGPT Platform HTTP/Web Request block

Flow:
1. Agent identifies payment/procurement requirement.
2. Agent calls Sardis policy check endpoint.
3. If approved, agent calls payment action endpoint.
4. Agent receives result and continues workflow.
5. If denied, agent receives structured reason and fallback action.

Why this is best first:
1. no deep framework fork
2. no custom runtime dependency
3. fastest way to validate KPI impact

## Path B - Productized integration: AutoGPT custom block pack

Expose Sardis-native blocks, for example:
1. `sardis.policy_check`
2. `sardis.transfer_usdc`
3. `sardis.bridge_funds`
4. `sardis.get_balance`
5. `sardis.get_receipt`

Why this is phase 2:
1. better UX for AutoGPT users
2. reusable templates/workflows
3. easier marketplace/ecosystem distribution

## Path C - Legacy support: AutoGPT Classic tool/plugin wrapper

Useful for existing Classic users.
Ship thin wrapper around Sardis SDK/API with the same policy-first pattern.

## 4) Example use cases for pilot

## Use case 1: API dependency unlock
1. Agent task needs a paid third-party API.
2. Agent requests payment under budget/merchant policy.
3. Agent gets credential/access and continues original task.

## Use case 2: Paid data acquisition
1. Agent finds required premium dataset/report.
2. Agent checks allowed merchants + monthly budget.
3. Agent completes payment and proceeds to analysis.

## Use case 3: Cross-rail preparation before execution
1. Agent needs USDC on target chain/wallet.
2. Agent executes policy-approved transfer/bridge step.
3. Agent continues downstream workflow.

## 5) Open-source and open-core fit

Positioning for AutoGPT team:
1. Open integration layer (SDK/wrapper/block definitions)
2. Open contribution path for community workflows
3. Hosted controls/compliance/ops for teams that need production guarantees

This fits AutoGPT’s open ecosystem while giving enterprise-safe execution options.

## 6) Security and control posture (talk track)

1. `No policy pass, no payment execution.`
2. `Budgets, merchant categories, limits, and approval rules are explicit.`
3. `All payment actions are auditable with deterministic logs/receipts.`
4. `Fail-closed behavior is default for blocked or uncertain states.`

## 7) What we ask from AutoGPT

1. Confirm first integration surface: `Platform block` or `Classic`.
2. Assign one technical owner for pilot execution.
3. Approve a 2-week pilot with 3 workflows.
4. Define shared KPI baseline and target.
5. If successful, align on marketplace/listing and co-marketing timeline.

## 8) 2-week pilot skeleton (no demo required)

Week 1:
1. finalize workflow definitions
2. wire first integration surface
3. run internal test flows

Week 2:
1. run controlled pilot flows
2. capture KPI deltas
3. produce go/no-go summary and next integration scope

## 9) KPI suggestion set

1. payment/procurement step completion rate
2. human-interrupt rate at payment steps
3. mean time to recover from denied/failed payments
4. policy false-positive and false-negative review count
5. audit completeness for each transaction path

