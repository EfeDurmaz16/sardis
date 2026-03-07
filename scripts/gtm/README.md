# GTM Automation Scaffold (`scripts/gtm`)

This folder provides a low-cost, founder-led GTM automation scaffold for Sardis:

- lead collection (GitHub, HN, Reddit, manual CSV)
- deterministic scoring with engagement/recency signals
- email enrichment waterfall (GitHub -> Hunter.io -> Apollo.io)
- pain-focused, personalized cold emails (tag-based hooks) with CAN-SPAM unsubscribe
- automated follow-up sequences (configurable delay + max touches)
- cross-source deduplication
- Resend queue/sender
- daily orchestration and cron setup

## Pipeline

```
collect -> score -> enrich -> generate emails -> follow-ups -> send
                                    |
                              dedup (in daily run)
```

## Files

- `collect_leads.py`: Collects leads from GitHub, Hacker News, Reddit, and manual CSV targets. Embeds engagement signals (stars, points, upvotes).
- `score_leads.py`: Scores leads using keyword heuristics + recency/engagement bonuses.
- `enrich_leads.py`: Waterfall email enrichment (GitHub public email -> Hunter.io -> Apollo.io).
- `generate_pg_emails.py`: Generates concise PG-style cold emails with unsubscribe footer.
- `follow_up.py`: Generates follow-up emails for non-responders (day 3, day 7).
- `resend_queue.py`: Sends queued emails through Resend (supports dry-run).
- `run_daily.py`: Runs the full pipeline in sequence with cross-source dedup.
- `gtm_daily.sh`: Shell wrapper for cron.
- `store.py`: SQLite schema + DB operations (leads, scores, enrichment log, email queue).
- `config.py`: Environment-based config.
- `seeds/queries.txt`: Initial discovery queries.
- `seeds/manual_targets.csv`: Optional high-priority manual targets.
- `attio_sync.py`: Syncs scored leads (with email) to Attio CRM as People + Company records with score notes.
- `clay_sync.py`: Push leads to Clay webhook for enrichment (`push`), import enriched CSV back (`pull`).
- `content_plan_4_weeks.md`: 4-week X/Reddit/email plan.

## Setup

```bash
cd /Users/efebarandurmaz/sardis
python3 scripts/gtm/run_daily.py
```

By default, sending is dry-run.

## Send Real Emails

```bash
export RESEND_API_KEY="re_xxx"
export GTM_FROM_EMAIL="Efe <efe@sardis.sh>"
python3 scripts/gtm/resend_queue.py --send --limit 20
```

Optional safety override for testing:

```bash
export GTM_TO_OVERRIDE="your@email.com"
```

## Useful Flags

```bash
# More collection depth
python3 scripts/gtm/collect_leads.py --limit-per-source 40

# Score only
python3 scripts/gtm/score_leads.py --limit 1000

# Enrich top leads with emails
python3 scripts/gtm/enrich_leads.py --limit 50 --providers github,hunter,apollo

# Queue PG emails for high-score leads
python3 scripts/gtm/generate_pg_emails.py --min-overall 72 --limit 100

# Generate follow-ups for non-responders
python3 scripts/gtm/follow_up.py --delay-days 3 --max-touches 2

# Full daily run with real sends
python3 scripts/gtm/run_daily.py --send

# Skip enrichment or follow-ups if needed
python3 scripts/gtm/run_daily.py --skip-enrich --skip-followup
```

## Suggested Env Vars

### Core
- `GTM_DB_PATH` (default `scripts/gtm/data/gtm.sqlite3`)
- `GTM_SCORE_THRESHOLD` (default `70`)
- `GTM_MAX_ITEMS_PER_SOURCE` (default `25`)
- `GTM_DRY_RUN` (`1` default, set `0` to disable dry-run default)
- `GTM_FROM_EMAIL` (default `Efe <efe@sardis.sh>`)
- `GTM_TO_OVERRIDE` (optional forced recipient)
- `RESEND_API_KEY` (required for actual send)
- `OPENAI_API_KEY` (optional, only for `--use-llm-refine`)

### Enrichment
- `GITHUB_TOKEN` (recommended, raises GitHub API limit from 60 to 5000 req/hr)
- `HUNTER_API_KEY` (Hunter.io, 25 free searches/month)
- `APOLLO_API_KEY` (Apollo.io, 50 free credits/month)

### Follow-ups
- `GTM_FOLLOWUP_DELAY_DAYS` (default `3`, days after last email before follow-up)
- `GTM_FOLLOWUP_MAX_TOUCHES` (default `2`, max follow-up emails per lead)

### Compliance
- `GTM_UNSUBSCRIBE_URL` (default `https://sardis.sh/unsubscribe`)

### Clay + Attio
- `CLAY_WEBHOOK_URL` (webhook URL from your Clay table — auto-pushes leads for enrichment)
- `CLAY_API_KEY` (optional, for future HTTP API use)
- `ATTIO_API_KEY` (Bearer token from Attio Settings > Developers > API Keys)
- `ATTIO_LIST_SLUG` (default `gtm_pipeline`)

## Clay Workflow

```bash
# 1. Push scored leads (without emails) to Clay for enrichment
python3 scripts/gtm/clay_sync.py push --min-score 50 --limit 200

# 2. In Clay: add "Waterfall Email Finder" enrichment column
#    Clay enriches using 50+ providers (Hunter, Apollo, Clearbit, etc.)

# 3. Export enriched table from Clay as CSV

# 4. Import enriched leads back
python3 scripts/gtm/clay_sync.py pull ~/Downloads/clay-export.csv
```

## Attio CRM Sync

```bash
# Sync scored leads with emails to Attio (creates People + Company records)
python3 scripts/gtm/attio_sync.py --min-score 70 --limit 100

# Preview what would sync
python3 scripts/gtm/attio_sync.py --dry-run
```

Attio MCP is also available for interactive use in Claude — add `https://mcp.attio.com/mcp` as a remote MCP server.

## Cron

Use `cron.daily.example` as template. Example:

```bash
crontab -e
# paste jobs from scripts/gtm/cron.daily.example
```

## Notes

- ICP: Companies building AI agents that need financial actions (procurement, invoicing, vendor mgmt, etc.) — NOT payment companies
- Clay is the highest-ROI enrichment path (50+ providers vs our DIY 3-provider waterfall)
- Attio handles reply detection for free via inbox sync (no Resend webhooks needed)
- Keep outreach semi-automated: draft + review + send
