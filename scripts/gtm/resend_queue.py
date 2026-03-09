#!/usr/bin/env python3
"""Send queued emails through Resend."""

from __future__ import annotations

import argparse
import json
import urllib.request

from config import dry_run_default, resend_api_key, resend_from_email, resend_to_override
from store import connect, init_schema, list_queued_emails, mark_email_failed, mark_email_sent

RESEND_ENDPOINT = "https://api.resend.com/emails"


def send_via_resend(payload: dict, api_key: str) -> tuple[int, str]:
    req = urllib.request.Request(
        RESEND_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        status = res.getcode()
        body = res.read().decode("utf-8", errors="ignore")
        return status, body


def main() -> None:
    parser = argparse.ArgumentParser(description="Send queued GTM emails.")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--send", action="store_true", help="Actually send via Resend")
    args = parser.parse_args()

    dry_run = not args.send if args.send else dry_run_default()

    conn = connect()
    init_schema(conn)
    rows = list_queued_emails(conn, limit=args.limit)

    if not rows:
        print("[queue] no queued emails")
        return

    api_key = resend_api_key()
    if not dry_run and not api_key:
        print("[queue] RESEND_API_KEY is missing. Use dry-run or set env var.")
        return

    from_email = resend_from_email()
    override = resend_to_override().strip()

    sent = 0
    failed = 0

    for row in rows:
        to_email = override or row["to_email"]
        payload = {
            "from": from_email,
            "to": [to_email],
            "subject": row["subject"],
            "text": row["body_text"],
        }

        if dry_run:
            print(f"[dry-run] queue_id={row['id']} to={to_email} subject={row['subject']}")
            sent += 1
            continue

        try:
            status, body = send_via_resend(payload, api_key)
            if 200 <= status < 300:
                provider_id = ""
                try:
                    provider_id = json.loads(body).get("id", "")
                except Exception:
                    provider_id = ""
                mark_email_sent(conn, int(row["id"]), provider_message_id=provider_id)
                sent += 1
            else:
                mark_email_failed(conn, int(row["id"]), f"status={status} body={body}")
                failed += 1
        except Exception as exc:
            mark_email_failed(conn, int(row["id"]), str(exc))
            failed += 1

    print(f"[queue] sent={sent} failed={failed} dry_run={dry_run}")


if __name__ == "__main__":
    main()
