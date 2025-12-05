# Sardis Operations Runbook

## Table of Contents
1. [Service Overview](#service-overview)
2. [Health Checks](#health-checks)
3. [Common Issues](#common-issues)
4. [Deployment](#deployment)
5. [Database Operations](#database-operations)
6. [Monitoring & Alerts](#monitoring--alerts)
7. [Incident Response](#incident-response)
8. [Rollback Procedures](#rollback-procedures)

---

## Service Overview

### Architecture
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Dashboard     │────▶│   Sardis API    │────▶│   PostgreSQL    │
│   (React)       │     │   (FastAPI)     │     │   (Neon/Supabase)│
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Redis/Upstash │
                        │   (Caching)     │
                        └─────────────────┘
```

### Key Services
| Service | Port | Health Endpoint |
|---------|------|-----------------|
| API | 8000 | `/health` |
| Dashboard | 3000 | `/` |

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SARDIS_SECRET_KEY` | Yes (prod) | 32+ char secret key |
| `SARDIS_REDIS_URL` | No | Redis/Upstash URL |
| `SARDIS_ENVIRONMENT` | No | dev/sandbox/prod |

---

## Health Checks

### API Health Check
```bash
# Basic health
curl https://api.sardis.network/health

# Expected response
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected",
  "cache": "connected"
}
```

### Database Health
```bash
# Check PostgreSQL connection
psql $DATABASE_URL -c "SELECT 1"

# Check connection count
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity"
```

### Redis Health
```bash
# Check Redis connection
redis-cli -u $SARDIS_REDIS_URL PING
```

---

## Common Issues

### Issue: API Returns 500 Errors

**Symptoms:**
- All API requests return 500
- Logs show database connection errors

**Diagnosis:**
```bash
# Check API logs
vercel logs --follow

# Check database connectivity
curl https://api.sardis.network/health
```

**Resolution:**
1. Check DATABASE_URL is set correctly
2. Verify database is accessible (not in maintenance)
3. Check connection pool limits
4. Restart API if needed

---

### Issue: High Latency

**Symptoms:**
- API responses > 1s
- Dashboard feels slow

**Diagnosis:**
```bash
# Check response times
curl -w "@curl-format.txt" https://api.sardis.network/health

# Check database query times
psql $DATABASE_URL -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10"
```

**Resolution:**
1. Check Redis cache is working
2. Review slow queries in pg_stat_statements
3. Add missing indexes
4. Scale database if needed

---

### Issue: Rate Limiting Triggered

**Symptoms:**
- 429 Too Many Requests responses
- X-RateLimit-Remaining: 0 header

**Diagnosis:**
```bash
# Check rate limit headers
curl -I https://api.sardis.network/api/v2/health
```

**Resolution:**
1. Wait for rate limit window to reset (1 minute)
2. Implement exponential backoff in client
3. Request rate limit increase if legitimate

---

### Issue: Webhook Delivery Failures

**Symptoms:**
- Webhooks not being received
- Delivery attempts showing errors

**Diagnosis:**
```bash
# Check webhook deliveries
curl https://api.sardis.network/api/v2/webhooks/{id}/deliveries

# Test webhook endpoint
curl -X POST https://api.sardis.network/api/v2/webhooks/{id}/test
```

**Resolution:**
1. Verify webhook URL is accessible
2. Check webhook secret is correct
3. Verify HMAC signature validation
4. Check for SSL/TLS issues

---

## Deployment

### Vercel Deployment
```bash
# Deploy to production
vercel --prod

# Deploy to preview
vercel

# Check deployment status
vercel ls
```

### Environment Variables
```bash
# Set production variable
vercel env add DATABASE_URL production

# List variables
vercel env ls
```

### Rollback
```bash
# List deployments
vercel ls

# Rollback to previous deployment
vercel rollback [deployment-url]
```

---

## Database Operations

### Migrations
```bash
# Run migrations (via API startup)
# Migrations run automatically on startup

# Manual migration
psql $DATABASE_URL -f sardis-core/src/sardis_v2_core/database.py
```

### Backup
```bash
# Create backup (Neon)
# Use Neon dashboard for point-in-time recovery

# Manual backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### Connection Pool
```bash
# Check active connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"

# Kill idle connections
psql $DATABASE_URL -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < NOW() - INTERVAL '1 hour'"
```

---

## Monitoring & Alerts

### Key Metrics
| Metric | Warning | Critical |
|--------|---------|----------|
| API Response Time (p95) | > 500ms | > 2s |
| Error Rate | > 1% | > 5% |
| Database Connections | > 80% | > 95% |
| Memory Usage | > 80% | > 95% |

### Log Queries

**Find errors:**
```bash
# Vercel logs
vercel logs --filter "level:error"

# Search for specific correlation ID
vercel logs --filter "correlation_id:req_abc123"
```

**Find slow requests:**
```bash
vercel logs --filter "duration_ms:>1000"
```

### Datadog Integration
```python
# Add to environment
DD_API_KEY=your_datadog_api_key
DD_SITE=datadoghq.com

# Metrics are automatically sent via structured logging
```

---

## Incident Response

### Severity Levels
| Level | Description | Response Time |
|-------|-------------|---------------|
| P1 | Service down | 15 min |
| P2 | Major feature broken | 1 hour |
| P3 | Minor issue | 4 hours |
| P4 | Low priority | 24 hours |

### Incident Checklist
1. [ ] Acknowledge incident
2. [ ] Check health endpoints
3. [ ] Review recent deployments
4. [ ] Check error logs
5. [ ] Identify root cause
6. [ ] Implement fix or rollback
7. [ ] Verify fix
8. [ ] Write post-mortem

### Communication Template
```
**Incident: [Title]**
**Status:** Investigating / Identified / Monitoring / Resolved
**Impact:** [Description of user impact]
**Start Time:** [UTC timestamp]
**Updates:**
- [Time] [Update]
```

---

## Rollback Procedures

### API Rollback
```bash
# 1. List recent deployments
vercel ls

# 2. Identify last known good deployment
# Look for deployment before the issue started

# 3. Rollback
vercel rollback [deployment-url]

# 4. Verify
curl https://api.sardis.network/health
```

### Database Rollback
```bash
# For Neon: Use point-in-time recovery in dashboard

# For manual backup:
psql $DATABASE_URL < backup_YYYYMMDD.sql
```

### Feature Flag Rollback
```bash
# Disable feature via environment variable
vercel env add FEATURE_X_ENABLED false production

# Redeploy
vercel --prod
```

---

## Contacts

| Role | Contact |
|------|---------|
| On-call Engineer | [Slack/PagerDuty] |
| Database Admin | [Contact] |
| Security | [Contact] |

---

## Appendix

### Useful Commands
```bash
# API health
curl https://api.sardis.network/health | jq

# Check rate limits
curl -I https://api.sardis.network/api/v2/health

# Test webhook
curl -X POST https://api.sardis.network/api/v2/webhooks/{id}/test

# Check transaction status
curl https://api.sardis.network/api/v2/transactions/status/{tx_hash}?chain=base_sepolia
```

### curl-format.txt
```
     time_namelookup:  %{time_namelookup}s\n
        time_connect:  %{time_connect}s\n
     time_appconnect:  %{time_appconnect}s\n
    time_pretransfer:  %{time_pretransfer}s\n
       time_redirect:  %{time_redirect}s\n
  time_starttransfer:  %{time_starttransfer}s\n
                     ----------\n
          time_total:  %{time_total}s\n
```
