# Apache Superset — Internal BI Setup

> Apache-2.0 license, safe for any use.

## Quick Start

```bash
# Run Superset locally with Docker
docker run -d -p 8088:8088 --name superset apache/superset:latest

# Initialize admin user
docker exec -it superset superset fab create-admin \
  --username admin \
  --firstname Sardis \
  --lastname Admin \
  --email admin@sardis.sh \
  --password admin

# Initialize DB + load examples
docker exec -it superset superset db upgrade
docker exec -it superset superset init
```

## Connect to Neon PostgreSQL

1. Open http://localhost:8088
2. Settings → Database Connections → + Database
3. Choose PostgreSQL
4. Connection string: `postgresql://neondb_owner:***@ep-proud-firefly-ahb3kc55-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require`

## Useful Dashboards to Create

- **Transaction Volume** — daily/weekly GMV chart
- **Agent Activity** — active agents, payment frequency
- **Policy Decisions** — allow/block ratio over time
- **KYC Funnel** — not_started → pending → approved conversion
- **Revenue** — platform fees collected
