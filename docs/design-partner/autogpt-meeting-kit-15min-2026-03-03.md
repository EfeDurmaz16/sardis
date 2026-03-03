# AutoGPT Meeting Kit (15 min, Talk-Only, No Demo)

Date: 2026-03-03  
Owner: Efe (Founder, Sardis)  
Format: conversation only, no live product demo

## 1) Meeting objective

By the end of 15 minutes, get clear agreement on:
1. The fastest integration surface (`Platform blocks` vs `Classic plugin/tool`)
2. A 2-week pilot scope with 3 workflows
3. A technical owner on AutoGPT side
4. A follow-up architecture session (45 min)

## 2) Opening script (say this first)

`Thanks for taking the time. I’ll keep this practical and short. We’re not doing a live demo today. I’ll walk you through exactly where Sardis plugs into AutoGPT, which failures we remove, and a concrete 2-week pilot proposal with clear ownership and KPIs.`

## 3) 15-minute agenda with sentence-level script

## 0:00-2:00 - Context and problem

Use these lines:
- `AutoGPT is strong at planning and execution, but procurement-like steps still break many real workflows.`
- `Typical breakpoints are: paid API key needed, dataset paywall, subscription checkout, or card-required purchase.`
- `The agent can discover what to buy, but cannot safely complete payment and continue on its own.`
- `Sardis exists exactly for this execution gap: policy-controlled agent payments with auditability.`

## 2:00-5:00 - What Sardis is (simple, non-technical wording)

Use these lines:
- `Think of Sardis as a wallet + policy firewall for agents.`
- `The agent can spend, but only inside human-defined rules in plain English.`
- `Every payment decision is checked before execution, and every action is logged for audit/compliance.`
- `So this is not “unlimited agent spending.” It is controlled autonomy.`

## 5:00-9:00 - How AutoGPT integration works (no dedicated adapter yet)

Use these lines:
- `Today, we do not have a separate AutoGPT-only adapter package.`
- `The fastest path is to use our existing API/SDK through AutoGPT’s tool/block model.`
- `So integration is not blocked by missing infra; it is mostly packaging and workflow wiring.`

Then explain the 3 paths:

1. `Fastest MVP: AutoGPT Platform HTTP/Web Request block calls Sardis APIs directly.`
2. `Cleaner product path: publish a Sardis custom block pack in AutoGPT Platform.`
3. `Classic compatibility path: add Sardis as a Classic tool/plugin wrapper for legacy users.`

## 9:00-12:00 - Pilot proposal (talk-only, no demo)

Use these lines:
- `I propose a 2-week pilot with three workflows.`
- `Workflow 1: agent detects missing paid API dependency, requests/executes payment under policy, then resumes task.`
- `Workflow 2: agent buys access to a required data source under budget and merchant constraints.`
- `Workflow 3: agent executes cross-rail treasury move (e.g., stablecoin transfer/bridge) before continuing task execution.`
- `Success KPI is simple: fewer human interrupts at procurement/payment steps, with clear audit trail.`

## 12:00-15:00 - Direct close and ask

Use these lines:
- `If this direction makes sense, I need three concrete things today.`
- `First: one technical owner on your side.`
- `Second: confirmation of preferred first surface, Platform blocks or Classic.`
- `Third: pilot start window and a shared KPI definition.`
- `If we align now, we can do architecture deep-dive this week and start implementation immediately after.`

## 4) If they ask “Why no demo today?”

Use these lines:
- `We’re in active infrastructure transition, so I chose to make this call decision-oriented, not demo-oriented.`
- `The right goal for today is integration alignment and ownership, then a focused technical session with concrete build steps.`

## 5) If they ask “What exactly is missing right now?”

Use these lines:
- `What is missing is a dedicated AutoGPT packaging layer, not core payment primitives.`
- `Core APIs and policy checks already exist; the work is to package and map them to your preferred tool runtime.`

## 6) Objection handling (quick answers)

1. `We do not want risky autonomous payments.`  
Answer: `Agreed. Sardis is policy-first and fail-closed. No policy pass, no transaction.`

2. `This sounds heavy for our users.`  
Answer: `MVP can be a single block/tool wrapper. Users do not need to learn a new financial stack.`

3. `How does this fit open-source expectations?`  
Answer: `Open-core model: open SDK/integration surface, managed compliance/ops as hosted layer.`

## 7) Final sentence to end meeting

`If you send one technical owner and preferred integration surface today, I’ll send the pilot spec and implementation checklist within 24 hours.`

