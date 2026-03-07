#!/usr/bin/env python3
"""Configuration helpers for GTM automation scaffold."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "gtm.sqlite3"
DEFAULT_QUERIES_FILE = BASE_DIR / "seeds" / "queries.txt"
DEFAULT_TARGETS_FILE = BASE_DIR / "seeds" / "manual_targets.csv"


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def db_path() -> Path:
    return Path(os.getenv("GTM_DB_PATH", str(DEFAULT_DB_PATH))).expanduser().resolve()


def score_threshold() -> int:
    return env_int("GTM_SCORE_THRESHOLD", 70)


def max_items_per_source() -> int:
    return env_int("GTM_MAX_ITEMS_PER_SOURCE", 25)


def resend_api_key() -> str:
    return os.getenv("RESEND_API_KEY", "")


def resend_from_email() -> str:
    return os.getenv("GTM_FROM_EMAIL", "Efe <efe@sardis.sh>")


def resend_to_override() -> str:
    return os.getenv("GTM_TO_OVERRIDE", "")


def dry_run_default() -> bool:
    return os.getenv("GTM_DRY_RUN", "1") != "0"


def openai_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "")


def default_model() -> str:
    return os.getenv("GTM_LLM_MODEL", "gpt-4o-mini")


# --- Enrichment provider keys ---

def hunter_api_key() -> str:
    return os.getenv("HUNTER_API_KEY", "")


def apollo_api_key() -> str:
    return os.getenv("APOLLO_API_KEY", "")


def github_token() -> str:
    return os.getenv("GITHUB_TOKEN", "")


# --- Email compliance ---

def unsubscribe_url() -> str:
    return os.getenv("GTM_UNSUBSCRIBE_URL", "https://sardis.sh/unsubscribe")


# --- Follow-up config ---

def followup_delay_days() -> int:
    return env_int("GTM_FOLLOWUP_DELAY_DAYS", 3)


def followup_max_touches() -> int:
    return env_int("GTM_FOLLOWUP_MAX_TOUCHES", 2)
