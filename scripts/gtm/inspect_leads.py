#!/usr/bin/env python3
"""Quick inspection of current GTM leads."""
from store import connect, init_schema

conn = connect()
init_schema(conn)

print("=== TOP SCORED LEADS ===")
rows = conn.execute(
    """
    SELECT l.id, l.source, l.company_name, l.person_name, l.email, l.website,
           l.description, l.status, s.fit_score, s.intent_score, s.overall_score
    FROM leads l
    LEFT JOIN lead_scores s ON s.lead_id = l.id
    WHERE l.status != 'merged'
    ORDER BY s.overall_score DESC NULLS LAST
    LIMIT 30
    """
).fetchall()

for r in rows:
    score = r["overall_score"] or 0
    email = r["email"] or "-"
    desc = (r["description"] or "")[:60]
    company = (r["company_name"] or "")[:30]
    person = (r["person_name"] or "")[:20]
    print(f"  [{r['status']:>6}] score={score:>3} | {r['source']:>7} | {company:<30} | {person:<20} | email={email:<30} | {desc}")

print()
print("=== STATS ===")
total = conn.execute("SELECT COUNT(*) FROM leads WHERE status != 'merged'").fetchone()[0]
scored = conn.execute("SELECT COUNT(*) FROM lead_scores").fetchone()[0]
with_email = conn.execute("SELECT COUNT(*) FROM leads WHERE email IS NOT NULL AND email != '' AND status != 'merged'").fetchone()[0]
hot = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'hot'").fetchone()[0]
warm = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'warm'").fetchone()[0]
cold = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'cold'").fetchone()[0]
new = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'new'").fetchone()[0]
sources = conn.execute("SELECT source, COUNT(*) as c FROM leads WHERE status != 'merged' GROUP BY source ORDER BY c DESC").fetchall()

print(f"  Total: {total} | Scored: {scored} | With email: {with_email}")
print(f"  Hot: {hot} | Warm: {warm} | Cold: {cold} | New (unscored): {new}")
print(f"  By source: {[(r['source'], r['c']) for r in sources]}")
