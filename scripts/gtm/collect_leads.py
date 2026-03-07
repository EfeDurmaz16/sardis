#!/usr/bin/env python3
"""Collect leads from lightweight public sources into SQLite."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List

import time

from config import DEFAULT_QUERIES_FILE, DEFAULT_TARGETS_FILE, max_items_per_source
from store import connect, init_schema, upsert_lead

USER_AGENT = "sardis-gtm-bot/0.1 (+https://sardis.sh)"


def _github_token() -> str:
    return os.environ.get("GITHUB_TOKEN", "")


def get_json(url: str, extra_headers: Dict | None = None) -> Dict:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as res:
        return json.loads(res.read().decode("utf-8", errors="ignore"))


def safe_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.lower().split(":")[0]
        return host.replace("www.", "")
    except Exception:
        return ""


def company_from_domain(domain: str) -> str:
    if not domain:
        return ""
    first = domain.split(".")[0]
    return first.replace("-", " ").replace("_", " ").strip().title()


def load_queries(path: Path) -> List[str]:
    if not path.exists():
        return []
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [line for line in lines if line and not line.startswith("#")]


def collect_github(query: str, limit: int) -> Iterable[Dict]:
    q = urllib.parse.quote_plus(f"{query} in:name,description,readme stars:>20")
    url = f"https://api.github.com/search/repositories?q={q}&sort=updated&order=desc&per_page={limit}"
    gh_headers = {}
    token = _github_token()
    if token:
        gh_headers["Authorization"] = f"Bearer {token}"
    data = get_json(url, extra_headers=gh_headers if gh_headers else None)
    for item in data.get("items", []):
        homepage = item.get("homepage") or item.get("html_url") or ""
        domain = safe_domain(homepage)
        owner = (item.get("owner") or {}).get("login")
        stars = item.get("stargazers_count", 0)
        updated_at = item.get("updated_at", "")
        yield {
            "external_id": str(item.get("id")),
            "source": "github",
            "source_url": item.get("html_url"),
            "company_name": company_from_domain(domain) or owner,
            "person_name": owner,
            "role": "builder",
            "website": homepage,
            "description": item.get("description") or "",
            "raw_text": f"{item.get('full_name', '')} {item.get('topics', [])} stars:{stars}",
            "tags": ["github", query, "ai-agents"],
        }
    time.sleep(1)  # Rate limit: GitHub allows 10 req/min unauthenticated


def collect_hn(query: str, limit: int) -> Iterable[Dict]:
    q = urllib.parse.quote_plus(query)
    url = f"https://hn.algolia.com/api/v1/search?query={q}&tags=story&hitsPerPage={limit}"
    data = get_json(url)
    for hit in data.get("hits", []):
        post_url = hit.get("url") or ""
        domain = safe_domain(post_url)
        title = hit.get("title") or ""
        points = hit.get("points") or 0
        yield {
            "external_id": hit.get("objectID", ""),
            "source": "hn",
            "source_url": post_url or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
            "company_name": company_from_domain(domain) or title[:50],
            "person_name": hit.get("author") or "",
            "role": "founder",
            "website": post_url,
            "description": title,
            "raw_text": f"{hit.get('_highlightResult', {}).get('title', {}).get('value', '') if isinstance(hit.get('_highlightResult'), dict) else ''} points:{points}",
            "tags": ["hn", query],
        }


def collect_reddit(query: str, limit: int) -> Iterable[Dict]:
    q = urllib.parse.quote_plus(query)
    url = f"https://www.reddit.com/search.json?q={q}&sort=new&limit={limit}"
    data = get_json(url)
    posts = (((data.get("data") or {}).get("children")) or [])
    for post in posts:
        item = post.get("data") or {}
        permalink = item.get("permalink", "")
        source_url = f"https://www.reddit.com{permalink}" if permalink else ""
        subreddit = item.get("subreddit", "")
        title = item.get("title", "")
        ups = item.get("ups", 0)
        yield {
            "external_id": item.get("id", ""),
            "source": "reddit",
            "source_url": source_url,
            "company_name": subreddit,
            "person_name": item.get("author", ""),
            "role": "builder",
            "website": "",
            "description": title,
            "raw_text": f"{item.get('selftext', '')[:800]} ups:{ups}",
            "tags": ["reddit", query, subreddit],
        }


def collect_manual_targets(path: Path) -> Iterable[Dict]:
    if not path.exists():
        return []
    leads: List[Dict] = []
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            domain = safe_domain(row.get("website", ""))
            external_id = row.get("external_id") or re.sub(r"[^a-z0-9]+", "-", (row.get("company_name") or domain or "manual").lower())
            leads.append(
                {
                    "external_id": external_id,
                    "source": row.get("source") or "manual",
                    "source_url": row.get("source_url") or row.get("website") or "",
                    "company_name": row.get("company_name") or company_from_domain(domain),
                    "person_name": row.get("person_name") or "",
                    "role": row.get("role") or "",
                    "email": row.get("email") or "",
                    "website": row.get("website") or "",
                    "description": row.get("description") or "",
                    "raw_text": row.get("notes") or "",
                    "tags": [tag.strip() for tag in (row.get("tags") or "manual").split("|") if tag.strip()],
                }
            )
    return leads


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect GTM leads from public sources.")
    parser.add_argument("--queries-file", type=Path, default=DEFAULT_QUERIES_FILE)
    parser.add_argument("--manual-targets", type=Path, default=DEFAULT_TARGETS_FILE)
    parser.add_argument("--limit-per-source", type=int, default=max_items_per_source())
    parser.add_argument("--sources", default="github,hn,reddit,manual", help="Comma-separated sources")
    args = parser.parse_args()

    sources = {s.strip().lower() for s in args.sources.split(",") if s.strip()}
    queries = load_queries(args.queries_file)
    if not queries:
        queries = ["ai agents payments", "agentic workflow", "llm agent infrastructure"]

    conn = connect()
    init_schema(conn)

    inserted = 0
    for lead in collect_manual_targets(args.manual_targets):
        upsert_lead(conn, lead)
        inserted += 1

    for query in queries:
        if "github" in sources:
            try:
                for lead in collect_github(query, args.limit_per_source):
                    upsert_lead(conn, lead)
                    inserted += 1
            except Exception as exc:
                print(f"[collect][github] {query}: {exc}")

        if "hn" in sources:
            try:
                for lead in collect_hn(query, args.limit_per_source):
                    upsert_lead(conn, lead)
                    inserted += 1
            except Exception as exc:
                print(f"[collect][hn] {query}: {exc}")

        if "reddit" in sources:
            try:
                for lead in collect_reddit(query, args.limit_per_source):
                    upsert_lead(conn, lead)
                    inserted += 1
            except Exception as exc:
                print(f"[collect][reddit] {query}: {exc}")

    print(f"[collect] upsert attempts: {inserted}")


if __name__ == "__main__":
    main()
