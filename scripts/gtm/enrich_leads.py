#!/usr/bin/env python3
"""Enrich leads with email addresses using a waterfall of providers.

Order: GitHub public email (free) -> Hunter.io -> Apollo.io
Stops at first successful hit per lead.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request

from config import apollo_api_key, github_token, hunter_api_key, score_threshold
from store import connect, init_schema, list_leads_for_enrichment, log_enrichment

USER_AGENT = "sardis-gtm-bot/0.1 (+https://sardis.sh)"

# ---------------------------------------------------------------------------
# Provider: GitHub public email (free, 60 req/hr unauth, 5000 req/hr auth)
# ---------------------------------------------------------------------------

def _github_headers() -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    token = github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def enrich_github(lead: dict) -> tuple[str, str] | None:
    """Try to get public email from GitHub user profile."""
    source = (lead.get("source") or "").lower()
    person = (lead.get("person_name") or "").strip()

    if source != "github" or not person:
        return None

    # Clean username (GitHub login)
    username = re.sub(r"[^a-zA-Z0-9_-]", "", person)
    if not username:
        return None

    url = f"https://api.github.com/users/{urllib.parse.quote(username)}"
    req = urllib.request.Request(url, headers=_github_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read().decode("utf-8", errors="ignore"))
        email = (data.get("email") or "").strip()
        if email and "@" in email:
            return email, "high"
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Provider: Hunter.io Email Finder (25 free searches/month)
# ---------------------------------------------------------------------------

def enrich_hunter(lead: dict) -> tuple[str, str] | None:
    """Find email via Hunter.io domain search + person name."""
    api_key = hunter_api_key()
    if not api_key:
        return None

    domain = _extract_domain(lead)
    if not domain:
        return None

    person = (lead.get("person_name") or "").strip()
    parts = person.split() if person else []
    first_name = parts[0] if parts else ""
    last_name = parts[-1] if len(parts) > 1 else ""

    params: dict[str, str] = {"domain": domain, "api_key": api_key}
    if first_name:
        params["first_name"] = first_name
    if last_name:
        params["last_name"] = last_name

    # If no name, use domain search to find the most senior person
    if not first_name:
        return _hunter_domain_search(domain, api_key)

    url = f"https://api.hunter.io/v2/email-finder?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read().decode("utf-8", errors="ignore"))
        result = data.get("data", {})
        email = (result.get("email") or "").strip()
        confidence = str(result.get("confidence", ""))
        if email and "@" in email:
            return email, confidence
    except Exception:
        pass
    return None


def _hunter_domain_search(domain: str, api_key: str) -> tuple[str, str] | None:
    """Fallback: search domain for any email, prefer founders/C-level."""
    url = f"https://api.hunter.io/v2/domain-search?domain={urllib.parse.quote(domain)}&api_key={api_key}&limit=5"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read().decode("utf-8", errors="ignore"))
        emails = data.get("data", {}).get("emails", [])
        # Prefer founder/ceo/cto
        priority_roles = {"founder", "ceo", "cto", "co-founder", "owner"}
        for entry in emails:
            position = (entry.get("position") or "").lower()
            if any(r in position for r in priority_roles):
                email = (entry.get("value") or "").strip()
                if email:
                    return email, str(entry.get("confidence", ""))
        # Fallback to first result
        if emails:
            email = (emails[0].get("value") or "").strip()
            if email:
                return email, str(emails[0].get("confidence", ""))
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Provider: Apollo.io People Enrichment (50 free credits/month)
# ---------------------------------------------------------------------------

def enrich_apollo(lead: dict) -> tuple[str, str] | None:
    """Find email via Apollo.io people match."""
    api_key = apollo_api_key()
    if not api_key:
        return None

    domain = _extract_domain(lead)
    person = (lead.get("person_name") or "").strip()
    company = (lead.get("company_name") or "").strip()

    if not domain and not company:
        return None

    payload: dict = {}
    if person:
        parts = person.split()
        payload["first_name"] = parts[0]
        if len(parts) > 1:
            payload["last_name"] = parts[-1]
    if domain:
        payload["organization_domain"] = domain
    elif company:
        payload["organization_name"] = company

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.apollo.io/api/v1/people/match",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            data = json.loads(res.read().decode("utf-8", errors="ignore"))
        person_data = data.get("person", {}) or {}
        email = (person_data.get("email") or "").strip()
        if email and "@" in email:
            return email, "apollo-match"
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_domain(lead: dict) -> str:
    website = (lead.get("website") or "").strip()
    if not website:
        return ""
    try:
        parsed = urllib.parse.urlparse(website if "://" in website else f"https://{website}")
        host = parsed.netloc.lower().split(":")[0]
        return host.replace("www.", "")
    except Exception:
        return ""


PROVIDERS = [
    ("github", enrich_github),
    ("hunter", enrich_hunter),
    ("apollo", enrich_apollo),
]


def enrich_one(lead: dict) -> str | None:
    """Run waterfall enrichment on a single lead. Returns email or None."""
    for _provider_name, provider_fn in PROVIDERS:
        result = provider_fn(lead)
        if result:
            email, confidence = result
            return email
        # Polite delay between providers
        time.sleep(0.3)
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich leads with email addresses.")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--min-score", type=int, default=score_threshold())
    parser.add_argument("--providers", default="github,hunter,apollo", help="Comma-separated provider order")
    args = parser.parse_args()

    active_providers = {p.strip().lower() for p in args.providers.split(",") if p.strip()}
    active_list = [(name, fn) for name, fn in PROVIDERS if name in active_providers]

    conn = connect()
    init_schema(conn)

    leads = list_leads_for_enrichment(conn, limit=args.limit)
    enriched = 0
    exhausted = 0

    for lead in leads:
        lead_dict = dict(lead)
        lead_id = int(lead["id"])
        found_email = None

        for provider_name, provider_fn in active_list:
            result = provider_fn(lead_dict)
            if result:
                email, confidence = result
                log_enrichment(conn, lead_id, provider_name, result_email=email, confidence=confidence)
                found_email = email
                enriched += 1
                print(f"[enrich] lead={lead_id} provider={provider_name} email={email}")
                break
            time.sleep(0.5)  # Rate limiting between providers

        if not found_email:
            # Mark as exhausted so we don't retry
            log_enrichment(conn, lead_id, "exhausted", confidence="none")
            exhausted += 1

    print(f"[enrich] enriched={enriched} exhausted={exhausted} total={len(leads)}")


if __name__ == "__main__":
    main()
