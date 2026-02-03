# Approval Flow Documentation

## Overview

The Sardis approval system enables human operators to review and approve/deny agent actions that exceed policy limits or require manual review. This document describes the complete workflow from request creation to resolution.

## Architecture Components

### Core Modules

1. **ApprovalRepository** (`packages/sardis-core/src/sardis_v2_core/approval_repository.py`)
   - PostgreSQL CRUD operations for approval records
   - Database schema mapping and query building

2. **ApprovalService** (`packages/sardis-core/src/sardis_v2_core/approval_service.py`)
   - Business logic layer for approval workflows
   - Status transitions (pending → approved/denied/expired/cancelled)
   - Expiration management

3. **ApprovalNotifier** (`packages/sardis-core/src/sardis_v2_core/approval_notifier.py`)
   - Webhook-based notifications to operators
   - Real-time alerts for approval requests

4. **Approval Expiry Job** (`packages/sardis-core/src/sardis_v2_core/jobs/approval_expiry.py`)
   - Background job to expire stale approval requests
   - Runs periodically (typically every minute)

### Database Schema

```sql
CREATE TABLE approvals (
    -- Identity
    id VARCHAR(64) PRIMARY KEY,              -- Format: appr_<base36_timestamp>_<random>

    -- Core fields
    action VARCHAR(64) NOT NULL,             -- payment, create_card, etc.
    status approval_status NOT NULL,         -- pending, approved, denied, expired, cancelled
    urgency approval_urgency NOT NULL,       -- low, medium, high

    -- Actors
    requested_by VARCHAR(64) NOT NULL,       -- Agent ID that requested
    reviewed_by VARCHAR(255),                -- Email/ID of human reviewer

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,         -- Auto-expire if not reviewed
    reviewed_at TIMESTAMPTZ,                 -- When decision was made

    -- Action-specific details
    vendor VARCHAR(255),                     -- For payments
    amount DECIMAL(18, 6),                   -- For payments
    purpose TEXT,                            -- Description
    reason TEXT,                             -- Why approval needed
    card_limit DECIMAL(18, 6),              -- For create_card

    -- References
    agent_id VARCHAR(64),
    wallet_id VARCHAR(64),
    organization_id VARCHAR(64),

    -- Metadata
    metadata JSONB DEFAULT '{}'
);
```

## Approval Lifecycle

### 1. Request Creation

**Trigger**: Agent action exceeds policy limits (e.g., payment amount, velocity, vendor restrictions)

**Flow**:
```python
from sardis_v2_core.approval_service import ApprovalService

# Create approval request
approval = await approval_service.create_approval(
    action="payment",
    requested_by="agent_abc123",
    agent_id="agent_abc123",
    wallet_id="wallet_xyz789",
    vendor="AWS",
    amount=Decimal("5000.00"),
    purpose="Cloud infrastructure scaling",
    reason="Exceeds single payment limit of $1000",
    urgency="high",
    expires_in_hours=24,
)
# approval.id = "appr_k2h3n5_a1b2c3d4"
# approval.status = "pending"
```

**Actions**:
1. Generate unique approval ID (`appr_<timestamp_base36>_<random>`)
2. Calculate expiration time (default: 24 hours from now)
3. Save to PostgreSQL database
4. Send webhook notification to operators
5. Return approval object

**Webhook Payload** (via ApprovalNotifier):
```json
{
  "event_type": "risk_alert",
  "data": {
    "approval": {
      "id": "appr_k2h3n5_a1b2c3d4",
      "action": "payment",
      "status": "pending",
      "urgency": "high",
      "requested_by": "agent_abc123",
      "agent_id": "agent_abc123",
      "wallet_id": "wallet_xyz789",
      "vendor": "AWS",
      "amount": "5000.00",
      "purpose": "Cloud infrastructure scaling",
      "reason": "Exceeds single payment limit of $1000",
      "expires_at": "2026-02-04T12:00:00Z"
    }
  }
}
```

### 2. Operator Review

**Methods**:
- **Dashboard**: Operators view pending approvals in admin UI
- **Webhook Integration**: External systems (Slack, PagerDuty, etc.) receive notifications
- **API Polling**: `GET /api/v2/approvals?status=pending&urgency=high`

**Operator Actions**:
- **View Details**: `GET /api/v2/approvals/{approval_id}`
- **Approve**: `POST /api/v2/approvals/{approval_id}/approve`
- **Deny**: `POST /api/v2/approvals/{approval_id}/deny`

### 3. Approval Decision

#### 3a. Approve

```python
# Operator approves the request
approval = await approval_service.approve(
    approval_id="appr_k2h3n5_a1b2c3d4",
    reviewed_by="operator@company.com"
)
# approval.status = "approved"
# approval.reviewed_by = "operator@company.com"
# approval.reviewed_at = NOW()
```

**Actions**:
1. Verify approval is still pending
2. Update status to "approved"
3. Record reviewer and timestamp
4. Save to database
5. Send webhook notification
6. Agent proceeds with action

**Webhook Payload**:
```json
{
  "event_type": "risk_alert",
  "data": {
    "approval": {
      "id": "appr_k2h3n5_a1b2c3d4",
      "action": "payment",
      "status": "approved",
      "reviewed_by": "operator@company.com",
      "agent_id": "agent_abc123",
      "wallet_id": "wallet_xyz789"
    }
  }
}
```

#### 3b. Deny

```python
# Operator denies the request
approval = await approval_service.deny(
    approval_id="appr_k2h3n5_a1b2c3d4",
    reviewed_by="operator@company.com",
    reason="Vendor not on approved list"
)
# approval.status = "denied"
# approval.metadata['denial_reason'] = "Vendor not on approved list"
```

**Actions**:
1. Verify approval is still pending
2. Update status to "denied"
3. Record reviewer, timestamp, and optional reason
4. Save to database
5. Send webhook notification
6. Agent receives rejection, does not proceed

### 4. Automatic Expiration

**Trigger**: Background job runs every minute

**Flow**:
```python
# Scheduled job (runs every 60 seconds)
async def expire_approvals():
    # Direct SQL update for efficiency
    await db.execute(
        "UPDATE approvals SET status = 'expired' "
        "WHERE status = 'pending' AND expires_at <= NOW()"
    )
```

**Actions**:
1. Find all pending approvals where `expires_at <= NOW()`
2. Update status to "expired"
3. Log count of expired approvals
4. Send webhook notifications for each expired approval

**When**:
- Operator didn't review in time (default: 24 hours)
- Custom expiration time exceeded

### 5. Cancellation

**Trigger**: Agent or system cancels pending request

```python
# Agent cancels its own request
approval = await approval_service.cancel(
    approval_id="appr_k2h3n5_a1b2c3d4",
    reason="User changed requirements"
)
# approval.status = "cancelled"
```

**Use Cases**:
- Agent determines action no longer needed
- User manually cancels via UI
- System detects invalid state

## Urgency Levels

### Low
- **Response SLA**: 48-72 hours
- **Examples**:
  - Non-critical expense policy exceptions
  - Low-value payments ($100-$500)
  - Routine vendor additions

### Medium (Default)
- **Response SLA**: 24 hours
- **Examples**:
  - Standard payments exceeding limits ($500-$5000)
  - New card creation requests
  - Moderate policy exceptions

### High
- **Response SLA**: 4-8 hours
- **Examples**:
  - Large payments (>$5000)
  - Urgent vendor approvals
  - Time-sensitive transactions
  - Security-related actions

## Action Types

### Payment
- **Triggers**:
  - Amount exceeds single payment limit
  - Velocity limits exceeded
  - Vendor not on approved list
  - Unusual spending pattern detected
- **Required Fields**: `vendor`, `amount`, `purpose`, `wallet_id`

### Create Card
- **Triggers**:
  - Card limit exceeds policy
  - Maximum card count exceeded
  - High-risk merchant category
- **Required Fields**: `card_limit`, `agent_id`

### Transfer
- **Triggers**:
  - Cross-chain transfers
  - Large amounts
  - Destination address flagged
- **Required Fields**: `amount`, `wallet_id`

### Wallet Modification
- **Triggers**:
  - Spending policy changes
  - Wallet freeze/unfreeze
  - Owner changes
- **Required Fields**: `wallet_id`, `purpose`

## API Endpoints

### Create Approval
```http
POST /api/v2/approvals
Content-Type: application/json

{
  "action": "payment",
  "requested_by": "agent_abc123",
  "agent_id": "agent_abc123",
  "wallet_id": "wallet_xyz789",
  "vendor": "AWS",
  "amount": "5000.00",
  "purpose": "Cloud infrastructure",
  "reason": "Exceeds single payment limit",
  "urgency": "high",
  "expires_in_hours": 24
}
```

### List Approvals
```http
GET /api/v2/approvals?status=pending&urgency=high&limit=20
```

### Get Approval Details
```http
GET /api/v2/approvals/{approval_id}
```

### Approve
```http
POST /api/v2/approvals/{approval_id}/approve
Content-Type: application/json

{
  "reviewed_by": "operator@company.com"
}
```

### Deny
```http
POST /api/v2/approvals/{approval_id}/deny
Content-Type: application/json

{
  "reviewed_by": "operator@company.com",
  "reason": "Vendor not approved"
}
```

### Cancel
```http
POST /api/v2/approvals/{approval_id}/cancel
Content-Type: application/json

{
  "reason": "No longer needed"
}
```

## Integration Examples

### Agent SDK Usage
```python
from sardis import SardisClient

client = SardisClient(api_key="sk_...")

# Attempt payment
try:
    tx = await client.payments.create(
        wallet_id="wallet_xyz",
        vendor="AWS",
        amount=5000.00,
        purpose="Cloud infra"
    )
except ApprovalRequiredException as e:
    # Approval needed
    approval_id = e.approval_id
    print(f"Awaiting approval: {approval_id}")

    # Poll for approval
    while True:
        approval = await client.approvals.get(approval_id)
        if approval.status == "approved":
            # Retry payment
            tx = await client.payments.create(...)
            break
        elif approval.status in ["denied", "expired", "cancelled"]:
            print(f"Approval {approval.status}")
            break
        await asyncio.sleep(30)  # Poll every 30s
```

### Webhook Handler (Operator Dashboard)
```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhooks/sardis")
async def handle_approval_webhook(request: Request):
    payload = await request.json()

    if payload["event_type"] == "risk_alert":
        approval = payload["data"]["approval"]

        if approval["status"] == "pending":
            # New approval request - notify operator
            await notify_operator_slack(
                message=f"⚠️ Approval needed: {approval['action']}\n"
                        f"Amount: ${approval['amount']}\n"
                        f"Reason: {approval['reason']}\n"
                        f"Urgency: {approval['urgency']}\n"
                        f"Approve: /approve {approval['id']}"
            )

    return {"status": "ok"}
```

## Best Practices

### For Operators

1. **Set Clear SLAs**: Configure urgency levels to match your response capacity
2. **Monitor Webhooks**: Ensure notification systems are reliable (Slack, PagerDuty, email)
3. **Review Context**: Always check approval reason, amount, and agent history
4. **Use Metadata**: Add notes to approvals for audit trail
5. **Regular Audits**: Review approved/denied patterns monthly

### For Developers

1. **Graceful Degradation**: Handle approval required exceptions cleanly
2. **Polling Strategy**: Use exponential backoff when polling approval status
3. **Expiration Handling**: Set reasonable `expires_in_hours` based on urgency
4. **Clear Reasons**: Provide detailed `reason` field explaining why approval needed
5. **Metadata Usage**: Store additional context in `metadata` for debugging

### For System Admins

1. **Database Indexes**: Ensure indexes on `status`, `expires_at`, `created_at` exist
2. **Job Monitoring**: Monitor approval expiry job execution (should run every minute)
3. **Webhook Reliability**: Implement retry logic for failed webhook deliveries
4. **Cleanup Jobs**: Periodically archive old approvals (>90 days)
5. **Access Control**: Restrict approval endpoints to authenticated operators only

## Monitoring & Alerts

### Key Metrics

- **Pending Approval Count**: Alert if >50 pending for >1 hour
- **Approval Response Time**: Track time from creation to decision
- **Expiration Rate**: High expiration rate indicates SLA issues
- **Denial Rate**: Track denial patterns by vendor, amount, action type

### Recommended Alerts

```yaml
alerts:
  - name: High Pending Approvals
    query: SELECT COUNT(*) FROM approvals WHERE status = 'pending'
    threshold: 50
    action: Page on-call operator

  - name: Expiry Job Failed
    query: Check last_run_time of approval_expiry job
    threshold: 5 minutes ago
    action: Alert engineering team

  - name: High Urgency Pending
    query: SELECT COUNT(*) FROM approvals WHERE status = 'pending' AND urgency = 'high'
    threshold: 10
    action: Notify operator team
```

## Security Considerations

1. **Authentication**: All approval endpoints require operator authentication
2. **Authorization**: Role-based access control (RBAC) for approve/deny actions
3. **Audit Trail**: All status changes logged with reviewer identity and timestamp
4. **Webhook Security**: HMAC signature verification for webhook payloads
5. **Data Retention**: Approvals archived but never deleted for compliance

## Troubleshooting

### Approval Not Creating
- Check database connection
- Verify approval_service is initialized with repository
- Check logs for validation errors

### Webhook Not Received
- Verify webhook URL is configured and accessible
- Check webhook service logs
- Confirm HMAC secret is correct

### Expiry Job Not Running
- Check scheduler is started in FastAPI lifespan
- Verify PostgreSQL connection pool is active
- Check job execution logs

### Cannot Approve/Deny
- Verify approval is still in "pending" status
- Check operator has required permissions
- Ensure approval hasn't expired

## Future Enhancements

1. **Multi-level Approval**: Chain approvals (L1 → L2 → L3)
2. **Approval Templates**: Pre-configured approval rules by vendor/amount
3. **Conditional Auto-approval**: Auto-approve trusted patterns
4. **Mobile App**: Approve/deny from iOS/Android
5. **Analytics Dashboard**: Approval trends, bottlenecks, performance metrics
