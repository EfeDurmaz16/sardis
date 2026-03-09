#!/usr/bin/env python3
"""Sync GTM leads to Attio CRM.

Creates/updates People and Company records in Attio, then adds them to a
configurable list (default: 'GTM Pipeline').

Requires:
  - ATTIO_API_KEY (Bearer token from Attio Settings > Developers > API Keys)
  - Optionally ATTIO_LIST_SLUG for the target list (default: 'gtm_pipeline')
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from typing import Any

from config import score_threshold
from store import connect, init_schema

ATTIO_BASE = "https://api.attio.com/v2"
USER_AGENT = "sardis-gtm/0.1"


def attio_api_key() -> str:
    return os.getenv("ATTIO_API_KEY", "")


def attio_list_slug() -> str:
    return os.getenv("ATTIO_LIST_SLUG", "gtm_pipeline")


def _request(method: str, path: str, body: dict | None = None) -> dict:
    api_key = attio_api_key()
    if not api_key:
        raise RuntimeError("ATTIO_API_KEY not set")

    url = f"{ATTIO_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode("utf-8", errors="ignore"))


def upsert_company(company_name: str, domain: str, description: str = "") -> dict | None:
    """Create or update a company in Attio by domain."""
    if not domain and not company_name:
        return None

    values: dict[str, Any] = {}
    if company_name:
        values["name"] = [{"value": company_name}]
    if domain:
        values["domains"] = [{"domain": domain}]
    if description:
        values["description"] = [{"value": description[:500]}]

    body = {
        "data": {"values": values},
    }

    # Use matching_attribute to deduplicate on domain
    if domain:
        body["matching_attribute"] = "domains"

    try:
        result = _request("PUT", "/objects/companies/records", body)
        return result.get("data", {})
    except Exception as exc:
        print(f"[attio] company upsert failed: {company_name} / {domain}: {exc}")
        return None


def upsert_person(
    email: str,
    person_name: str = "",
    company_name: str = "",
    role: str = "",
    description: str = "",
) -> dict | None:
    """Create or update a person in Attio by email."""
    if not email:
        return None

    values: dict[str, Any] = {
        "email_addresses": [{"email_address": email}],
    }

    if person_name:
        parts = person_name.strip().split()
        first = parts[0] if parts else ""
        last = " ".join(parts[1:]) if len(parts) > 1 else ""
        name_val: dict[str, str] = {}
        if first:
            name_val["first_name"] = first
        if last:
            name_val["last_name"] = last
        name_val["full_name"] = person_name.strip()
        values["name"] = [name_val]

    if role:
        values["job_title"] = [{"value": role}]

    if description:
        values["description"] = [{"value": description[:500]}]

    body = {
        "data": {"values": values},
        "matching_attribute": "email_addresses",
    }

    try:
        result = _request("PUT", "/objects/people/records", body)
        return result.get("data", {})
    except Exception as exc:
        print(f"[attio] person upsert failed: {email}: {exc}")
        return None


def add_note(record_id: str, record_type: str, title: str, content: str) -> None:
    """Attach a note to a record (for scoring reasons, source info, etc.)."""
    body = {
        "data": {
            "title": title,
            "format": "plaintext",
            "content": content[:2000],
            "parent_object": record_type,
            "parent_record_id": record_id,
        }
    }
    try:
        _request("POST", "/notes", body)
    except Exception as exc:
        print(f"[attio] note failed for {record_id}: {exc}")


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


def sync_leads(min_score: int = 70, limit: int = 100, dry_run: bool = False) -> None:
    """Sync scored leads with email to Attio."""
    conn = connect()
    init_schema(conn)

    rows = conn.execute(
        """
        SELECT l.*, s.overall_score, s.fit_score, s.intent_score, s.reasons_json
        FROM leads l
        JOIN lead_scores s ON s.lead_id = l.id
        WHERE s.overall_score >= ?
          AND l.email IS NOT NULL AND l.email != ''
          AND l.status != 'merged'
        ORDER BY s.overall_score DESC
        LIMIT ?
        """,
        (min_score, limit),
    ).fetchall()

    synced_companies = 0
    synced_people = 0

    for row in rows:
        lead = dict(row)
        email = (lead.get("email") or "").strip()
        company_name = lead.get("company_name") or ""
        person_name = lead.get("person_name") or ""
        domain = _extract_domain(lead.get("website") or "")
        description = lead.get("description") or ""
        role = lead.get("role") or ""
        score = lead.get("overall_score", 0)
        reasons = lead.get("reasons_json", "[]")

        if dry_run:
            print(f"[attio-dry] company={company_name} person={person_name} email={email} score={score}")
            continue

        # Upsert company
        if company_name or domain:
            company_record = upsert_company(company_name, domain, description)
            if company_record:
                synced_companies += 1
                record_id = company_record.get("id", {}).get("record_id", "")
                if record_id:
                    score_label = "hot" if score >= 80 else "warm" if score >= 65 else "cold"
                    add_note(
                        record_id,
                        "companies",
                        f"GTM Score: {score} ({score_label})",
                        f"Fit: {lead.get('fit_score', 0)} | Intent: {lead.get('intent_score', 0)}\n"
                        f"Source: {lead.get('source', '')} | {lead.get('source_url', '')}\n"
                        f"Reasons: {reasons}",
                    )

        # Upsert person
        if email:
            person_record = upsert_person(email, person_name, company_name, role, description)
            if person_record:
                synced_people += 1

        time.sleep(0.3)  # Rate limiting

    print(f"[attio] synced companies={synced_companies} people={synced_people} (dry_run={dry_run})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync GTM leads to Attio CRM.")
    parser.add_argument("--min-score", type=int, default=score_threshold())
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not attio_api_key() and not args.dry_run:
        print("[attio] ATTIO_API_KEY not set. Use --dry-run to preview.")
        return

    sync_leads(min_score=args.min_score, limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
