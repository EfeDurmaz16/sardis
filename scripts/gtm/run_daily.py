#!/usr/bin/env python3
"""Run daily GTM pipeline end-to-end."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from store import connect, find_duplicate_leads, init_schema, merge_duplicate_lead, metrics_snapshot

HAS_ATTIO = bool(os.environ.get("ATTIO_API_KEY", ""))
HAS_CLAY = bool(os.environ.get("CLAY_WEBHOOK_URL", ""))

BASE = Path(__file__).resolve().parent


def run_step(name: str, args: list[str]) -> int:
    cmd = [sys.executable, str(BASE / name), *args]
    print(f"[daily] running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"[daily] step failed: {name} rc={result.returncode}")
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GTM daily jobs")
    parser.add_argument("--collect-limit", type=int, default=20)
    parser.add_argument("--score-limit", type=int, default=500)
    parser.add_argument("--email-limit", type=int, default=100)
    parser.add_argument("--queue-limit", type=int, default=50)
    parser.add_argument("--min-overall", type=int, default=70)
    parser.add_argument("--enrich-limit", type=int, default=50)
    parser.add_argument("--followup-limit", type=int, default=30)
    parser.add_argument("--send", action="store_true", help="Actually send queued emails")
    parser.add_argument("--skip-enrich", action="store_true", help="Skip enrichment step")
    parser.add_argument("--skip-followup", action="store_true", help="Skip follow-up step")
    parser.add_argument("--halt-on-error", action="store_true")
    args = parser.parse_args()

    steps = [
        ("collect_leads.py", ["--limit-per-source", str(args.collect_limit)]),
        ("score_leads.py", ["--limit", str(args.score_limit)]),
    ]

    if not args.skip_enrich:
        steps.append(("enrich_leads.py", ["--limit", str(args.enrich_limit)]))

    steps.append(("generate_pg_emails.py", ["--min-overall", str(args.min_overall), "--limit", str(args.email_limit)]))

    if not args.skip_followup:
        steps.append(("follow_up.py", ["--limit", str(args.followup_limit)]))

    steps.append(("resend_queue.py", ["--limit", str(args.queue_limit)] + (["--send"] if args.send else [])))

    # Optional: push to Clay for enrichment (runs after scoring, before email gen)
    if HAS_CLAY and not args.skip_enrich:
        steps.insert(2, ("clay_sync.py", ["push", "--limit", str(args.enrich_limit)]))

    # Optional: sync to Attio CRM (runs last)
    if HAS_ATTIO:
        steps.append(("attio_sync.py", ["--limit", "100"]))

    for name, step_args in steps:
        rc = run_step(name, step_args)
        if rc != 0 and args.halt_on_error:
            raise SystemExit(rc)

    # Cross-source deduplication
    conn = connect()
    init_schema(conn)

    dupes = find_duplicate_leads(conn)
    merged = 0
    for row in dupes:
        merge_duplicate_lead(conn, int(row["keep_id"]), int(row["dup_id"]))
        merged += 1
    if merged:
        print(f"[daily] merged {merged} cross-source duplicates")

    metrics = metrics_snapshot(conn)
    print(f"[daily] metrics={metrics}")


if __name__ == "__main__":
    main()
