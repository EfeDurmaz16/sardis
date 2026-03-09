#!/usr/bin/env python3
"""Generate follow-up emails for leads that haven't replied.

Follow-up philosophy:
  - Touch 2 (day 3): Add value — share a specific insight, not just "bumping"
  - Touch 3 (day 7): Breakup with a useful resource, no guilt
  - Never say "just following up" or "circling back" without adding something new
"""

from __future__ import annotations

import argparse
import re

from config import followup_delay_days, followup_max_touches, unsubscribe_url
from store import connect, init_schema, list_leads_for_followup, queue_email

SIGNOFF = "Efe\nFounder, Sardis"


FOLLOWUP_TEMPLATES = [
    # Touch 2 (day 3) — add value, share an insight
    {
        "subject_prefix": "Re: ",
        "body": (
            "Hi {first_name},\n"
            "\n"
            "Wanted to share something relevant — we just published a teardown of how "
            "agent spending failures happen in production. The pattern is always the same: "
            "agent reasons itself into a purchase, no policy check, money gone.\n"
            "\n"
            "If {company} agents will handle any financial actions, might be useful context. "
            "Happy to walk through it in 10 min.\n"
            "\n"
            "{signoff}\n"
            "{unsubscribe}"
        ),
    },
    # Touch 3 (day 7) — breakup with a resource
    {
        "subject_prefix": "Re: ",
        "body": (
            "Hi {first_name},\n"
            "\n"
            "Last note from me. Totally get if the timing isn't right.\n"
            "\n"
            "If agent spending controls ever become relevant for {company}, "
            "our docs are at sardis.sh/docs — shows the policy engine, "
            "audit trail, and how it plugs into existing agent frameworks.\n"
            "\n"
            "Rooting for what you're building.\n"
            "\n"
            "{signoff}\n"
            "{unsubscribe}"
        ),
    },
]


def first_name(person_name: str) -> str:
    if not person_name:
        return "there"
    clean = re.sub(r"[^a-zA-Z\s-]", "", person_name).strip()
    return clean.split(" ")[0] if clean else "there"


def build_followup(lead: dict, touch_index: int) -> tuple[str, str]:
    """Build follow-up email for the given touch number (0-indexed)."""
    template_idx = min(touch_index, len(FOLLOWUP_TEMPLATES) - 1)
    template = FOLLOWUP_TEMPLATES[template_idx]

    company = lead.get("company_name") or "your team"
    person = first_name(lead.get("person_name") or "")
    unsub = f"\n---\nUnsubscribe: {unsubscribe_url()}"

    # Reconstruct original subject from tags/company
    tags = str(lead.get("tags") or "")
    if any(t in tags for t in ["ap-automation", "ai-procurement"]):
        orig_subject = f"When {company}'s agents approve their own invoices"
    elif any(t in tags for t in ["browser-agent", "agent-commerce"]):
        orig_subject = f"Who controls spend when {company}'s agents buy things?"
    elif any(t in tags for t in ["agentic-payments", "fintech-agent"]):
        orig_subject = "Complementary infra — agent payment policies"
    elif any(t in tags for t in ["agent-framework", "agent-platform", "multi-agent"]):
        orig_subject = "Your developers' agents are about to move real money"
    elif any(t in tags for t in ["enterprise-agent"]):
        orig_subject = f"Agent guardrails for {company}"
    else:
        orig_subject = f"Quick question for {company}"

    subject = f"{template['subject_prefix']}{orig_subject}"
    body = template["body"].format(
        first_name=person,
        company=company,
        signoff=SIGNOFF,
        unsubscribe=unsub,
    )
    return subject, body


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate follow-up emails.")
    parser.add_argument("--delay-days", type=int, default=followup_delay_days())
    parser.add_argument("--max-touches", type=int, default=followup_max_touches())
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    conn = connect()
    init_schema(conn)

    leads = list_leads_for_followup(
        conn,
        delay_days=args.delay_days,
        max_touches=args.max_touches + 1,  # +1 because touch_count includes initial email
        limit=args.limit,
    )
    queued = 0

    for lead in leads:
        lead_dict = dict(lead)
        touch_count = int(lead["touch_count"])
        email = (lead["email"] or "").strip()
        if not email:
            continue

        followup_index = touch_count - 1
        subject, body = build_followup(lead_dict, followup_index)

        tone = f"followup-{touch_count + 1}"
        queue_email(conn, lead_id=int(lead["id"]), to_email=email, subject=subject, body_text=body, tone=tone)
        queued += 1
        print(f"[followup] lead={lead['id']} touch={touch_count + 1} to={email}")

    print(f"[followup] queued={queued}")


if __name__ == "__main__":
    main()
