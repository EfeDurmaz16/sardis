# One-Page Technical Summary: AutoGPT x Sardis

Date: 2026-03-03  
Prepared by: Efe (Sardis)  
Use case: partner call handoff document (no demo required)

## What problem this solves

AutoGPT workflows can stall when execution requires paid actions:
1. API top-up or subscription
2. paid dataset or asset access
3. treasury refill before transaction continuation

Sardis adds policy-controlled payment execution so workflows can continue without unrestricted financial risk.

## Integration model

No core AutoGPT infra rewrite is required.

Recommended first surface:
1. AutoGPT Platform block/tool invocation
2. Sardis policy check before payment
3. allowed transaction execution
4. structured result back to workflow

High-level flow:
1. Agent decides action requiring payment
2. Sardis evaluates action against human-defined policy
3. If allowed, Sardis executes payment rail step
4. Agent resumes next workflow node
5. If denied, policy reason is returned for alternate path

## Security and control posture

1. Policy-first, fail-closed execution
2. Budget and constraint enforcement before spend
3. Deterministic transaction receipts and audit records
4. No unrestricted raw-card pattern required for agent logic

## Proposed 2-week pilot

Workflow 1:
1. API credit refill during task execution

Workflow 2:
1. one-time paid dataset/asset purchase under budget rule

Workflow 3:
1. cross-rail treasury refill to preserve agent continuity

Pilot outputs:
1. integration package for first surface
2. KPI baseline vs pilot delta
3. go/no-go recommendation for broader rollout

## Pilot KPIs

1. reduction in human interruptions at payment steps
2. increase in end-to-end workflow completion rate
3. policy deny/allow accuracy review
4. completeness of payment audit evidence

## Immediate decisions requested from AutoGPT

1. assign one technical owner
2. confirm first surface: Platform block first
3. schedule 45-minute architecture deep-dive this week

## 24-hour deliverables after owner assignment

1. pilot spec
2. API and block mapping
3. security and policy package

