#!/usr/bin/env python3
"""Generate short, pain-focused cold emails and queue them for sending.

Learnings applied from outreach analysis (50 sent, ~11% reply rate):
  - Lead with THEIR pain, not our features
  - Max 4-5 sentences for cold email body
  - Reference something specific about them (product, funding, tech)
  - Target VP/Director/Head level, not C-suite at Fortune 500s
  - Never batch-send identical emails
  - Include clear, low-friction CTA
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from typing import Dict, List, Tuple

from config import default_model, openai_api_key, score_threshold, unsubscribe_url
from store import connect, init_schema, list_leads_for_email, queue_email

SIGNOFF = "Efe\nFounder, Sardis"
UNSUB_FOOTER = f"\n\n---\nUnsubscribe: {unsubscribe_url()}"


def first_name(person_name: str) -> str:
    if not person_name:
        return "there"
    clean = re.sub(r"[^a-zA-Z\s-]", "", person_name).strip()
    return clean.split(" ")[0] if clean else "there"


def _get_tier(lead: Dict) -> str:
    """Determine lead tier from tags."""
    tags = str(lead.get("tags") or "")
    if "tier-1" in tags:
        return "tier-1"
    if "tier-2" in tags:
        return "tier-2"
    if "tier-3" in tags:
        return "tier-3"
    # Infer from tags
    if any(t in tags for t in ["agent-framework", "agent-platform", "agent-tools", "agent-ide"]):
        return "tier-1"
    if any(t in tags for t in ["browser-agent", "agent-ops", "agent-deployment", "voice-agent"]):
        return "tier-2"
    if any(t in tags for t in ["enterprise-agent", "series-c", "series-d", "series-f"]):
        return "tier-3"
    return "tier-2"


def _build_tier1_email(lead: Dict, person: str, company: str) -> Tuple[str, str]:
    """Tier 1: Integration partners. Pitch = we build it, your users get wallets."""
    tags = str(lead.get("tags") or "")

    if "agent-framework" in tags or "multi-agent" in tags:
        subject = f"Native payment tool for {company} agents"
        hook = (
            f"Developers on {company} are starting to build agents that spend money — "
            f"buying APIs, provisioning cloud, paying vendors.\n"
            f"\n"
            f"There's no payment primitive for this yet. We'd like to build one for {company}.\n"
            f"\n"
            f"Sardis gives each agent its own wallet with plain-English spending policies. "
            f"We'd build and maintain the integration. Your users get a new capability. "
            f"We take a small transaction fee. Zero work for your team."
        )
    elif "agent-tools" in tags or "integrations" in tags:
        subject = f"Payment connector for {company}"
        hook = (
            f"{company} connects agents to 250+ tools — but there's no payment tool yet.\n"
            f"\n"
            f"We built Sardis: agent wallets with spending policies. "
            f"Could be a native connector — agents get a wallet, policies control every transaction.\n"
            f"\n"
            f"We'd build the integration. Your users get payment capabilities. "
            f"Transaction fee model, no cost to you."
        )
    elif "agent-infra" in tags or "sandbox" in tags:
        subject = f"Spending controls for {company} agents"
        hook = (
            f"Agents running in {company} sandboxes are making paid API calls and provisioning resources.\n"
            f"\n"
            f"We built Sardis — agent wallets with spending limits. "
            f"Could plug into your runtime so every agent gets automatic financial guardrails.\n"
            f"\n"
            f"We'd build the integration and maintain it. Transaction fee model."
        )
    else:
        subject = f"Agent wallets for {company} users"
        hook = (
            f"{company} users are building agents that will need to spend money.\n"
            f"\n"
            f"We built Sardis — each agent gets its own wallet with plain-English spending policies. "
            f"We'd build the native integration so your users get wallets out of the box.\n"
            f"\n"
            f"Zero work for your team. We take a small transaction fee."
        )

    return subject, hook


def _build_tier2_email(lead: Dict, person: str, company: str) -> Tuple[str, str]:
    """Tier 2: Early adopters. Pitch = try our SDK, we'll white-glove onboard."""
    tags = str(lead.get("tags") or "")

    if "browser-agent" in tags:
        subject = f"When {company}'s agent hits checkout"
        hook = (
            f"{company} agents take real actions on the web — including purchases.\n"
            f"\n"
            f"Right now there's nothing between the agent deciding to buy and the money moving. "
            f"We built Sardis: plain-English spending policies per agent. "
            f"\"Max $200/day, only approved vendors, require human approval above $500.\"\n"
            f"\n"
            f"Would love to get {company} on our early access. We'll white-glove the setup."
        )
    elif "voice-agent" in tags:
        subject = f"When {company}'s agent commits to a payment on a call"
        hook = (
            f"Voice agents make bookings and purchases in real-time — no undo button.\n"
            f"\n"
            f"Sardis adds spending policies that check every transaction before it goes through. "
            f"Works for card payments, API purchases, and on-chain transfers.\n"
            f"\n"
            f"Would love to get {company} on early access. We'll handle the integration."
        )
    elif any(t in tags for t in ["agent-ops", "agent-deployment"]):
        subject = f"Spending controls for {company}'s AI employees"
        hook = (
            f"{company} deploys AI agents that run 24/7. "
            f"When those agents start spending money — buying tools, paying for APIs — "
            f"you need guardrails before the bill arrives.\n"
            f"\n"
            f"Sardis gives each agent a wallet with spending limits. "
            f"We're onboarding early partners now and would handle the setup for you."
        )
    elif any(t in tags for t in ["agent-observability", "agent-testing", "agent-safety"]):
        subject = f"Stopping bad transactions, not just observing them"
        hook = (
            f"{company} sees what agents do. But when the action is a $5,000 purchase, "
            f"you need to stop it before it happens, not log it after.\n"
            f"\n"
            f"Sardis is the policy layer that sits before the transaction. "
            f"Could be complementary to what you're building — would love to explore."
        )
    else:
        subject = f"Agent wallets for {company}"
        hook = (
            f"Agents on {company} are starting to take actions that cost money.\n"
            f"\n"
            f"We built Sardis — each agent gets a wallet with plain-English spending policies. "
            f"If the policy says no, the money doesn't move.\n"
            f"\n"
            f"We're onboarding early partners now. Happy to white-glove the setup."
        )

    return subject, hook


def _build_tier3_email(lead: Dict, person: str, company: str) -> Tuple[str, str]:
    """Tier 3: Enterprise pipeline. Pitch = when you're ready, we're here."""
    tags = str(lead.get("tags") or "")

    if any(t in tags for t in ["agentic-payments", "agent-wallet"]):
        subject = f"Complementary infrastructure for {company}"
        hook = (
            f"{company} is building agent payment rails. "
            f"We built the trust and policy layer that sits on top — "
            f"spending limits, approval workflows, audit trails.\n"
            f"\n"
            f"Might be complementary. Would love to compare notes on what we're each seeing "
            f"in the agentic payments space."
        )
    elif "enterprise-agent" in tags:
        subject = f"Financial guardrails for {company}'s agents"
        hook = (
            f"When {company}'s agents handle transactions — refunds, credits, purchases — "
            f"one reasoning loop can mean an unauthorized charge.\n"
            f"\n"
            f"We built Sardis: deterministic spending policies that gate every agent transaction. "
            f"Built for enterprise compliance. Would love to share what we're seeing."
        )
    else:
        subject = f"Agent spending controls"
        hook = (
            f"As {company}'s agents start taking financial actions, "
            f"the trust and compliance layer becomes critical.\n"
            f"\n"
            f"We're building Sardis for exactly this — policy-controlled agent wallets "
            f"with full audit trails. Would love to get on your radar for when it's relevant."
        )

    return subject, hook


def build_email(lead: Dict) -> Tuple[str, str]:
    """Build a short, personalized cold email based on lead tier."""
    person = first_name(lead.get("person_name") or "")
    company = lead.get("company_name") or "your team"
    tier = _get_tier(lead)

    if tier == "tier-1":
        subject, hook = _build_tier1_email(lead, person, company)
    elif tier == "tier-3":
        subject, hook = _build_tier3_email(lead, person, company)
    else:
        subject, hook = _build_tier2_email(lead, person, company)

    body = "\n".join([
        f"Hi {person},",
        "",
        hook,
        "",
        SIGNOFF,
        UNSUB_FOOTER,
    ])
    return subject, body


def maybe_refine_with_llm(subject: str, body: str, lead: Dict) -> Tuple[str, str]:
    """Optional LLM refinement for more natural tone."""
    api_key = openai_api_key()
    if not api_key:
        return subject, body

    company = lead.get("company_name") or "unknown"
    desc = lead.get("description") or ""

    prompt = {
        "model": default_model(),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You rewrite cold emails to be more natural and compelling. Rules:\n"
                    "- Max 5 sentences in body (excluding greeting and signoff)\n"
                    "- Lead with THEIR pain, not our features\n"
                    "- Sound like a founder texting a friend, not a sales rep\n"
                    "- No buzzwords: 'leverage', 'synergy', 'revolutionary', 'game-changing'\n"
                    "- No exclamation marks\n"
                    "- Keep the unsubscribe footer exactly as-is\n"
                    "- Subject line: short, curiosity-driven, no company pitch"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Company: {company}\nDescription: {desc}\n\n"
                    f"Subject: {subject}\n\nBody:\n{body}\n\n"
                    "Return JSON with keys subject, body."
                ),
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "email",
                "schema": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["subject", "body"],
                    "additionalProperties": False,
                },
            },
        },
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(prompt).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            payload = json.loads(res.read().decode("utf-8", errors="ignore"))
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return parsed.get("subject", subject), parsed.get("body", body)
    except Exception as exc:
        print(f"[email] llm refine skipped: {exc}")
        return subject, body


def valid_business_email(email: str) -> bool:
    if not email:
        return False
    lowered = email.lower().strip()
    blocked = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "proton.me", "protonmail.com"]
    if "@" not in lowered:
        return False
    domain = lowered.split("@", 1)[1]
    return domain not in blocked


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate cold emails and queue them.")
    parser.add_argument("--min-overall", type=int, default=score_threshold())
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--allow-personal-emails", action="store_true")
    parser.add_argument("--use-llm-refine", action="store_true")
    args = parser.parse_args()

    conn = connect()
    init_schema(conn)

    leads = list_leads_for_email(conn, min_score=args.min_overall, limit=args.limit)
    queued = 0
    skipped = 0

    for lead in leads:
        email = (lead["email"] or "").strip()
        if not email:
            skipped += 1
            continue
        if not args.allow_personal_emails and not valid_business_email(email):
            skipped += 1
            continue

        subject, body = build_email(dict(lead))
        if args.use_llm_refine:
            subject, body = maybe_refine_with_llm(subject, body, dict(lead))

        queue_email(
            conn,
            lead_id=int(lead["id"]),
            to_email=email,
            subject=subject,
            body_text=body,
            tone="pg",
        )
        queued += 1

    print(f"[email] queued={queued} skipped={skipped}")


if __name__ == "__main__":
    main()
