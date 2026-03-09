#!/usr/bin/env python3
"""Push leads to Clay for enrichment and import enriched data back.

Clay integration works in two directions:
  1. PUSH: Export scored leads to a Clay table via webhook URL
  2. PULL: Import enriched leads (with emails) from Clay CSV export

Clay webhook setup:
  1. Create a new table in Clay
  2. Click "+ Add" at bottom -> search "Webhooks" -> "Monitor webhook"
  3. Copy the webhook URL and set as CLAY_WEBHOOK_URL env var
  4. Add enrichment columns in Clay (Waterfall Email Finder, etc.)

Requires:
  - CLAY_WEBHOOK_URL (webhook URL from your Clay table)
  - Optionally CLAY_API_KEY (for future HTTP API use)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.request
from pathlib import Path

from config import score_threshold
from store import connect, init_schema, upsert_lead

USER_AGENT = "sardis-gtm/0.1"


def clay_webhook_url() -> str:
    return os.getenv("CLAY_WEBHOOK_URL", "")


def clay_api_key() -> str:
    return os.getenv("CLAY_API_KEY", "")


def _extract_domain(website: str) -> str:
    if not website:
        return ""
    import urllib.parse as up
    try:
        parsed = up.urlparse(website if "://" in website else f"https://{website}")
        host = parsed.netloc.lower().split(":")[0]
        return host.replace("www.", "")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# PUSH: Send leads to Clay webhook for enrichment
# ---------------------------------------------------------------------------

def push_to_clay(leads: list[dict], webhook_url: str, dry_run: bool = False) -> int:
    """Push leads to Clay table via webhook. Returns count of successful pushes."""
    pushed = 0

    for lead in leads:
        # Target decision-makers: VP/Director/Head level at startups, Founders at small cos
        target_roles = [
            "CTO", "VP Engineering", "VP Product", "VP Platform",
            "Head of AI", "Head of Platform", "Head of Partnerships",
            "Head of Engineering", "Head of Product",
            "Director of Engineering", "Director of Product",
            "Founder", "Co-Founder", "CEO",
            "Staff Engineer", "Principal Engineer",
        ]

        payload = {
            "sardis_lead_id": lead.get("id"),
            "company_name": lead.get("company_name", ""),
            "person_name": lead.get("person_name", ""),
            "domain": _extract_domain(lead.get("website", "")),
            "website": lead.get("website", ""),
            "role": lead.get("role", ""),
            "target_roles": ", ".join(target_roles),
            "description": lead.get("description", ""),
            "source": lead.get("source", ""),
            "source_url": lead.get("source_url", ""),
            "overall_score": lead.get("overall_score", 0),
            "fit_score": lead.get("fit_score", 0),
            "intent_score": lead.get("intent_score", 0),
            "existing_email": lead.get("email", ""),
            "tags": lead.get("tags", ""),
        }

        if dry_run:
            print(f"[clay-dry] push: {payload['company_name']} | {payload['domain']} | score={payload['overall_score']}")
            pushed += 1
            continue

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                if 200 <= res.getcode() < 300:
                    pushed += 1
                else:
                    print(f"[clay] push failed for {payload['company_name']}: status={res.getcode()}")
        except Exception as exc:
            print(f"[clay] push failed for {payload['company_name']}: {exc}")

        time.sleep(0.2)  # Don't hammer Clay webhook

    return pushed


# ---------------------------------------------------------------------------
# PULL: Import enriched data from Clay CSV export
# ---------------------------------------------------------------------------

def import_from_clay_csv(csv_path: Path) -> int:
    """Import enriched leads from a Clay CSV export back into GTM SQLite.

    Expected CSV columns (flexible, maps common Clay column names):
      - company_name / Company Name / Company
      - person_name / Full Name / Name / First Name + Last Name
      - email / Email / Work Email / Enriched Email
      - domain / Domain / Website
      - role / Title / Job Title
      - sardis_lead_id (if originally pushed from our system)
    """
    if not csv_path.exists():
        print(f"[clay] CSV not found: {csv_path}")
        return 0

    conn = connect()
    init_schema(conn)
    imported = 0

    with csv_path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # Flexible column name mapping
            email = (
                row.get("email")
                or row.get("Email")
                or row.get("Work Email")
                or row.get("Enriched Email")
                or row.get("work_email")
                or ""
            ).strip()

            if not email or "@" not in email:
                continue

            company = (
                row.get("company_name")
                or row.get("Company Name")
                or row.get("Company")
                or row.get("company")
                or ""
            ).strip()

            person = (
                row.get("person_name")
                or row.get("Full Name")
                or row.get("Name")
                or row.get("name")
                or ""
            ).strip()

            if not person:
                first = (row.get("First Name") or row.get("first_name") or "").strip()
                last = (row.get("Last Name") or row.get("last_name") or "").strip()
                person = f"{first} {last}".strip()

            domain = (
                row.get("domain")
                or row.get("Domain")
                or row.get("Website")
                or row.get("website")
                or ""
            ).strip()

            role = (
                row.get("role")
                or row.get("Title")
                or row.get("Job Title")
                or row.get("title")
                or ""
            ).strip()

            description = (
                row.get("description")
                or row.get("Description")
                or row.get("Company Description")
                or ""
            ).strip()

            linkedin = (
                row.get("LinkedIn URL")
                or row.get("linkedin_url")
                or row.get("LinkedIn")
                or ""
            ).strip()

            external_id = (
                row.get("sardis_lead_id")
                or row.get("Sardis Lead ID")
                or email  # Fallback to email as ID
            )

            lead = {
                "external_id": str(external_id),
                "source": "clay",
                "source_url": linkedin or domain,
                "company_name": company,
                "person_name": person,
                "email": email,
                "role": role,
                "website": f"https://{domain}" if domain and not domain.startswith("http") else domain,
                "description": description,
                "raw_text": f"clay-enriched linkedin:{linkedin}",
                "tags": ["clay", "enriched"],
            }

            upsert_lead(conn, lead)
            imported += 1

    print(f"[clay] imported {imported} enriched leads from {csv_path}")
    return imported


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Clay integration: push leads for enrichment or import enriched data.")
    sub = parser.add_subparsers(dest="command")

    # Push subcommand
    push_parser = sub.add_parser("push", help="Push scored leads to Clay webhook for enrichment")
    push_parser.add_argument("--min-score", type=int, default=score_threshold())
    push_parser.add_argument("--limit", type=int, default=200)
    push_parser.add_argument("--dry-run", action="store_true")
    push_parser.add_argument("--include-with-email", action="store_true", help="Also push leads that already have emails")

    # Pull subcommand
    pull_parser = sub.add_parser("pull", help="Import enriched leads from Clay CSV export")
    pull_parser.add_argument("csv_file", type=Path, help="Path to Clay CSV export file")

    args = parser.parse_args()

    if args.command == "push":
        webhook = clay_webhook_url()
        if not webhook and not args.dry_run:
            print("[clay] CLAY_WEBHOOK_URL not set. Use --dry-run to preview.")
            return

        conn = connect()
        init_schema(conn)

        email_filter = "" if args.include_with_email else "AND (l.email IS NULL OR l.email = '')"
        query = f"""
            SELECT l.*, s.overall_score, s.fit_score, s.intent_score
            FROM leads l
            JOIN lead_scores s ON s.lead_id = l.id
            WHERE s.overall_score >= ?
              AND l.status != 'merged'
              {email_filter}
            ORDER BY s.overall_score DESC
            LIMIT ?
        """
        rows = conn.execute(query, (args.min_score, args.limit)).fetchall()
        leads = [dict(r) for r in rows]

        if not leads:
            print("[clay] no leads to push")
            return

        pushed = push_to_clay(leads, webhook or "dry-run", dry_run=args.dry_run)
        print(f"[clay] pushed={pushed} total={len(leads)}")

    elif args.command == "pull":
        import_from_clay_csv(args.csv_file)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
