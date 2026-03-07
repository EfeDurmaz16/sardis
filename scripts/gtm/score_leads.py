#!/usr/bin/env python3
"""Score leads with deterministic heuristics (no external dependency)."""

from __future__ import annotations

import argparse
import re
from typing import Dict, List, Tuple

from store import connect, init_schema, list_leads_for_scoring, save_score

FIT_KEYWORDS = {
    # Agent builders (our ICP)
    "ai agent": 16,
    "autonomous agent": 18,
    "agentic": 14,
    "multi-agent": 14,
    "agent framework": 16,
    "tool-use": 12,
    "tool calling": 12,
    "function calling": 10,
    "llm": 6,
    "orchestration": 8,
    "automation": 7,
    "workflow": 6,
    "crewai": 14,
    "langchain": 10,
    "autogen": 12,
    "sdk": 4,
    "production": 6,
    "deployment": 5,
    "observability": 5,
}

INTENT_KEYWORDS = {
    # Signs they need financial controls
    "procurement": 14,
    "invoice": 14,
    "purchasing": 14,
    "expense": 12,
    "accounts payable": 16,
    "vendor management": 12,
    "booking": 8,
    "ordering": 8,
    "subscription": 8,
    "api cost": 10,
    "saas spend": 12,
    "budget": 8,
    "approval": 10,
    "payroll": 10,
    "billing": 10,
    "spend": 10,
    "cost control": 12,
    "audit trail": 10,
    "policy": 8,
}

NEGATIVE_KEYWORDS = {
    # Competitors / not ICP
    "payment gateway": -12,
    "payment processor": -12,
    "crypto exchange": -10,
    # Noise signals
    "job": -8,
    "hiring": -6,
    "resume": -15,
    "remote jobs": -15,
    "career": -8,
    "interview": -6,
    "meme": -10,
    "giveaway": -12,
    "nsfw": -25,
    "tutorial": -5,
    "course": -5,
    "feeling inadequate": -20,
    "unhirable": -20,
    "eat healthy": -25,
    "tips?": -8,
    "guide:": -5,
    "beginner": -6,
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def score_text(text: str, weights: Dict[str, int]) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []
    for phrase, weight in weights.items():
        if phrase in text:
            score += weight
            reasons.append(f"+{weight}:{phrase}")
    return score, reasons


def recency_bonus(lead: Dict) -> Tuple[int, List[str]]:
    """Boost score for recently updated leads."""
    updated = lead.get("updated_at") or lead.get("created_at") or ""
    if not updated:
        return 0, []
    try:
        from datetime import datetime, timezone
        ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - ts).days
        if age_days <= 7:
            return 10, ["+10:updated-within-7d"]
        elif age_days <= 30:
            return 5, ["+5:updated-within-30d"]
        elif age_days > 180:
            return -5, ["-5:stale-6mo+"]
    except Exception:
        pass
    return 0, []


def source_bonus(lead: Dict) -> Tuple[int, List[str]]:
    """Boost based on source quality signals embedded in raw_text."""
    raw = str(lead.get("raw_text") or "")
    source = str(lead.get("source") or "")
    bonus = 0
    reasons: List[str] = []

    # Warm leads already engaged — highest priority
    if source == "warm-lead":
        bonus += 35
        reasons.append("+35:warm-engaged")
    elif source == "contacted":
        bonus += 30
        reasons.append("+30:previously-contacted")
    elif source == "manual":
        bonus += 25
        reasons.append("+25:curated-target")
    elif source == "rejected":
        bonus -= 50
        reasons.append("-50:partnership-rejected")

    # Tag-based scoring — only for curated leads (manual/warm/contacted)
    # Scraped leads stuff query strings into tags which causes false positives
    tags = str(lead.get("tags") or "") if source in ("manual", "warm-lead", "contacted") else ""
    tag_scores = {
        "design-partner": 15, "agent-framework": 12, "agent-platform": 12,
        "agentic-payments": 15, "agent-infra": 10, "browser-agent": 12,
        "enterprise-agent": 10, "ap-automation": 14, "fintech-agent": 15,
        "agent-wallet": 14, "agent-commerce": 12, "agent-ops": 10,
        "ai-procurement": 14, "agent-safety": 8, "agent-testing": 8,
        "agent-observability": 8, "coding-agent": 6, "voice-agent": 8,
        "sales-agent": 6, "healthcare-agent": 6, "security-agent": 6,
        "yc": 5, "yc-w24": 6, "yc-w25": 6, "yc-s25": 6,
        "series-a": 8, "series-b": 10, "series-c": 10, "series-d": 10,
        "funded": 6, "seed": 5, "open-source": 4, "collab": 8,
        "investor-prospect": 10, "chain-partner": 8, "infrastructure": 5,
        "ai-infra": 8, "prospect": 6, "observability": 5,
    }
    for tag, weight in tag_scores.items():
        if tag in tags:
            bonus += weight
            reasons.append(f"+{weight}:tag-{tag}")

    # GitHub stars (encoded as "stars:N" in raw_text by collector)
    stars_match = re.search(r"stars:(\d+)", raw)
    if stars_match:
        stars = int(stars_match.group(1))
        if stars >= 1000:
            bonus += 12
            reasons.append(f"+12:stars-{stars}")
        elif stars >= 200:
            bonus += 6
            reasons.append(f"+6:stars-{stars}")
        elif stars >= 50:
            bonus += 3
            reasons.append(f"+3:stars-{stars}")

    # HN points (encoded as "points:N")
    points_match = re.search(r"points:(\d+)", raw)
    if points_match:
        points = int(points_match.group(1))
        if points >= 100:
            bonus += 10
            reasons.append(f"+10:hn-points-{points}")
        elif points >= 30:
            bonus += 5
            reasons.append(f"+5:hn-points-{points}")

    # Reddit upvotes (encoded as "ups:N")
    ups_match = re.search(r"ups:(\d+)", raw)
    if ups_match:
        ups = int(ups_match.group(1))
        if ups >= 50:
            bonus += 8
            reasons.append(f"+8:reddit-ups-{ups}")
        elif ups >= 15:
            bonus += 4
            reasons.append(f"+4:reddit-ups-{ups}")

    # Has email already -> higher priority
    if lead.get("email"):
        bonus += 8
        reasons.append("+8:has-email")

    return bonus, reasons


def score_lead(lead: Dict) -> Tuple[int, int, int, List[str]]:
    text = normalize(
        " ".join(
            [
                str(lead.get("company_name") or ""),
                str(lead.get("description") or ""),
                str(lead.get("raw_text") or ""),
                str(lead.get("tags") or ""),
                str(lead.get("website") or ""),
            ]
        )
    )

    fit_score, fit_reasons = score_text(text, FIT_KEYWORDS)
    intent_score, intent_reasons = score_text(text, INTENT_KEYWORDS)
    penalty, neg_reasons = score_text(text, NEGATIVE_KEYWORDS)

    recency, recency_reasons = recency_bonus(lead)
    engagement, engagement_reasons = source_bonus(lead)

    fit_score = max(0, min(100, fit_score + penalty + recency))
    intent_score = max(0, min(100, intent_score + penalty))
    overall = max(0, min(100, round((fit_score * 0.55) + (intent_score * 0.45) + engagement)))

    reasons = fit_reasons + intent_reasons + [f"{v}" for v in neg_reasons] + recency_reasons + engagement_reasons
    if not reasons:
        reasons = ["no-strong-signals"]
    return fit_score, intent_score, overall, reasons


def main() -> None:
    parser = argparse.ArgumentParser(description="Score GTM leads.")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--rescore-all", action="store_true", help="Re-score all leads, not just new ones")
    args = parser.parse_args()

    conn = connect()
    init_schema(conn)

    rows = list_leads_for_scoring(conn, limit=args.limit, rescore_all=args.rescore_all)
    scored = 0
    for row in rows:
        fit, intent, overall, reasons = score_lead(dict(row))
        save_score(conn, int(row["id"]), fit, intent, overall, reasons)
        scored += 1

    print(f"[score] scored={scored}")


if __name__ == "__main__":
    main()
