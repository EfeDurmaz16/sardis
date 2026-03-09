#!/usr/bin/env python3
"""SQLite storage for GTM automation scaffold."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config import db_path


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def connect(path: Path | None = None) -> sqlite3.Connection:
    db = Path(path or db_path())
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;

        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT,
            company_name TEXT,
            person_name TEXT,
            role TEXT,
            email TEXT,
            website TEXT,
            description TEXT,
            raw_text TEXT,
            tags TEXT,
            status TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(source, external_id)
        );

        CREATE TABLE IF NOT EXISTS lead_scores (
            lead_id INTEGER PRIMARY KEY,
            fit_score INTEGER NOT NULL,
            intent_score INTEGER NOT NULL,
            overall_score INTEGER NOT NULL,
            reasons_json TEXT NOT NULL,
            scored_at TEXT NOT NULL,
            FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS email_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            tone TEXT NOT NULL,
            to_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            body_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            scheduled_at TEXT NOT NULL,
            queued_at TEXT NOT NULL,
            sent_at TEXT,
            provider_message_id TEXT,
            error_message TEXT,
            FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS enrichment_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            result_email TEXT,
            confidence TEXT,
            raw_response TEXT,
            enriched_at TEXT NOT NULL,
            FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
        CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_queue(status);
        CREATE INDEX IF NOT EXISTS idx_enrichment_lead ON enrichment_log(lead_id);
        CREATE INDEX IF NOT EXISTS idx_leads_domain ON leads(website);
        """
    )
    conn.commit()


def upsert_lead(conn: sqlite3.Connection, lead: dict[str, Any]) -> int:
    now = utc_now_iso()
    payload = {
        "external_id": str(lead.get("external_id", "")).strip() or str(lead.get("source_url", "")),
        "source": lead.get("source", "unknown"),
        "source_url": lead.get("source_url"),
        "company_name": lead.get("company_name"),
        "person_name": lead.get("person_name"),
        "role": lead.get("role"),
        "email": lead.get("email"),
        "website": lead.get("website"),
        "description": lead.get("description"),
        "raw_text": lead.get("raw_text"),
        "tags": ",".join(lead.get("tags", [])) if isinstance(lead.get("tags"), list) else (lead.get("tags") or ""),
        "status": lead.get("status", "new"),
        "updated_at": now,
        "created_at": now,
    }

    conn.execute(
        """
        INSERT INTO leads (
            external_id, source, source_url, company_name, person_name, role, email,
            website, description, raw_text, tags, status, created_at, updated_at
        ) VALUES (
            :external_id, :source, :source_url, :company_name, :person_name, :role, :email,
            :website, :description, :raw_text, :tags, :status, :created_at, :updated_at
        )
        ON CONFLICT(source, external_id) DO UPDATE SET
            source_url = excluded.source_url,
            company_name = COALESCE(excluded.company_name, leads.company_name),
            person_name = COALESCE(excluded.person_name, leads.person_name),
            role = COALESCE(excluded.role, leads.role),
            email = COALESCE(excluded.email, leads.email),
            website = COALESCE(excluded.website, leads.website),
            description = COALESCE(excluded.description, leads.description),
            raw_text = COALESCE(excluded.raw_text, leads.raw_text),
            tags = CASE
                WHEN excluded.tags IS NULL OR excluded.tags = '' THEN leads.tags
                WHEN leads.tags IS NULL OR leads.tags = '' THEN excluded.tags
                ELSE leads.tags || ',' || excluded.tags
            END,
            status = CASE
                WHEN leads.status IN ('emailed', 'replied') THEN leads.status
                ELSE 'new'
            END,
            updated_at = excluded.updated_at
        """,
        payload,
    )
    conn.commit()

    row = conn.execute(
        "SELECT id FROM leads WHERE source = ? AND external_id = ?",
        (payload["source"], payload["external_id"]),
    ).fetchone()
    return int(row["id"])


def list_leads_for_scoring(conn: sqlite3.Connection, limit: int = 200, rescore_all: bool = False) -> list[sqlite3.Row]:
    if rescore_all:
        return conn.execute(
            "SELECT l.* FROM leads l WHERE l.status != 'merged' ORDER BY l.updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return conn.execute(
        """
        SELECT l.* FROM leads l
        LEFT JOIN lead_scores s ON s.lead_id = l.id
        WHERE l.status IN ('new', 'scored') OR s.lead_id IS NULL
        ORDER BY l.updated_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def save_score(
    conn: sqlite3.Connection,
    lead_id: int,
    fit_score: int,
    intent_score: int,
    overall_score: int,
    reasons: Iterable[str],
) -> None:
    scored_at = utc_now_iso()
    reasons_json = json.dumps(list(reasons), ensure_ascii=True)
    conn.execute(
        """
        INSERT INTO lead_scores (lead_id, fit_score, intent_score, overall_score, reasons_json, scored_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(lead_id) DO UPDATE SET
          fit_score = excluded.fit_score,
          intent_score = excluded.intent_score,
          overall_score = excluded.overall_score,
          reasons_json = excluded.reasons_json,
          scored_at = excluded.scored_at
        """,
        (lead_id, fit_score, intent_score, overall_score, reasons_json, scored_at),
    )

    status = "hot" if overall_score >= 80 else "warm" if overall_score >= 65 else "cold"
    conn.execute("UPDATE leads SET status = ?, updated_at = ? WHERE id = ?", (status, scored_at, lead_id))
    conn.commit()


def list_leads_for_email(conn: sqlite3.Connection, min_score: int, limit: int = 100) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT l.*, s.fit_score, s.intent_score, s.overall_score, s.reasons_json
        FROM leads l
        JOIN lead_scores s ON s.lead_id = l.id
        WHERE s.overall_score >= ?
          AND l.status IN ('hot', 'warm')
          AND NOT EXISTS (
            SELECT 1 FROM email_queue q
            WHERE q.lead_id = l.id AND q.tone = 'pg' AND q.status IN ('queued', 'sent')
          )
        ORDER BY s.overall_score DESC, l.updated_at DESC
        LIMIT ?
        """,
        (min_score, limit),
    ).fetchall()


def queue_email(
    conn: sqlite3.Connection,
    lead_id: int,
    to_email: str,
    subject: str,
    body_text: str,
    tone: str = "pg",
    scheduled_at: str | None = None,
) -> int:
    now = utc_now_iso()
    schedule = scheduled_at or now
    cur = conn.execute(
        """
        INSERT INTO email_queue (
            lead_id, tone, to_email, subject, body_text, status, scheduled_at, queued_at
        ) VALUES (?, ?, ?, ?, ?, 'queued', ?, ?)
        """,
        (lead_id, tone, to_email, subject, body_text, schedule, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_queued_emails(conn: sqlite3.Connection, limit: int = 50) -> list[sqlite3.Row]:
    now = utc_now_iso()
    return conn.execute(
        """
        SELECT q.*, l.company_name, l.person_name
        FROM email_queue q
        JOIN leads l ON l.id = q.lead_id
        WHERE q.status = 'queued' AND q.scheduled_at <= ?
        ORDER BY q.queued_at ASC
        LIMIT ?
        """,
        (now, limit),
    ).fetchall()


def mark_email_sent(conn: sqlite3.Connection, queue_id: int, provider_message_id: str = "") -> None:
    now = utc_now_iso()
    conn.execute(
        "UPDATE email_queue SET status = 'sent', sent_at = ?, provider_message_id = ? WHERE id = ?",
        (now, provider_message_id, queue_id),
    )
    conn.execute(
        """
        UPDATE leads SET status = 'emailed', updated_at = ?
        WHERE id = (SELECT lead_id FROM email_queue WHERE id = ?)
        """,
        (now, queue_id),
    )
    conn.commit()


def mark_email_failed(conn: sqlite3.Connection, queue_id: int, error_message: str) -> None:
    conn.execute(
        "UPDATE email_queue SET status = 'failed', error_message = ? WHERE id = ?",
        (error_message[:900], queue_id),
    )
    conn.commit()


def list_leads_for_enrichment(conn: sqlite3.Connection, limit: int = 100) -> list[sqlite3.Row]:
    """Leads that have been scored but have no email yet."""
    return conn.execute(
        """
        SELECT l.* FROM leads l
        JOIN lead_scores s ON s.lead_id = l.id
        WHERE (l.email IS NULL OR l.email = '')
          AND l.status NOT IN ('emailed', 'replied', 'unsubscribed')
          AND NOT EXISTS (
            SELECT 1 FROM enrichment_log e
            WHERE e.lead_id = l.id AND e.provider = 'exhausted'
          )
        ORDER BY s.overall_score DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def log_enrichment(
    conn: sqlite3.Connection,
    lead_id: int,
    provider: str,
    result_email: str = "",
    confidence: str = "",
    raw_response: str = "",
) -> None:
    now = utc_now_iso()
    conn.execute(
        """
        INSERT INTO enrichment_log (lead_id, provider, result_email, confidence, raw_response, enriched_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (lead_id, provider, result_email, confidence, raw_response[:2000], now),
    )
    if result_email:
        conn.execute(
            "UPDATE leads SET email = ?, updated_at = ? WHERE id = ? AND (email IS NULL OR email = '')",
            (result_email, now, lead_id),
        )
    conn.commit()


def list_leads_for_followup(conn: sqlite3.Connection, delay_days: int = 3, max_touches: int = 2, limit: int = 50) -> list[sqlite3.Row]:
    """Leads that were emailed but haven't replied, eligible for follow-up."""
    return conn.execute(
        """
        SELECT l.*, s.overall_score,
               (SELECT COUNT(*) FROM email_queue q2 WHERE q2.lead_id = l.id AND q2.status = 'sent') AS touch_count,
               (SELECT MAX(q3.sent_at) FROM email_queue q3 WHERE q3.lead_id = l.id AND q3.status = 'sent') AS last_sent_at
        FROM leads l
        JOIN lead_scores s ON s.lead_id = l.id
        WHERE l.status = 'emailed'
          AND (SELECT COUNT(*) FROM email_queue q2 WHERE q2.lead_id = l.id AND q2.status = 'sent') < ?
          AND (SELECT MAX(q3.sent_at) FROM email_queue q3 WHERE q3.lead_id = l.id AND q3.status = 'sent')
              <= datetime('now', '-' || ? || ' days')
          AND NOT EXISTS (
            SELECT 1 FROM email_queue q4
            WHERE q4.lead_id = l.id AND q4.status = 'queued'
          )
        ORDER BY s.overall_score DESC
        LIMIT ?
        """,
        (max_touches, delay_days, limit),
    ).fetchall()


def find_duplicate_leads(conn: sqlite3.Connection) -> list[tuple]:
    """Find leads that share the same normalized domain across sources."""
    return conn.execute(
        """
        SELECT l1.id AS keep_id, l2.id AS dup_id, l1.website
        FROM leads l1
        JOIN leads l2 ON l1.website = l2.website
            AND l1.id < l2.id
            AND l1.source != l2.source
        WHERE l1.website IS NOT NULL AND l1.website != ''
          AND l2.status NOT IN ('emailed', 'replied')
        ORDER BY l1.id
        """,
    ).fetchall()


def merge_duplicate_lead(conn: sqlite3.Connection, keep_id: int, dup_id: int) -> None:
    """Merge dup_id into keep_id: transfer email/scores, then soft-delete dup."""
    now = utc_now_iso()
    dup = conn.execute("SELECT * FROM leads WHERE id = ?", (dup_id,)).fetchone()
    if not dup:
        return
    # Copy email if keep doesn't have one
    if dup["email"]:
        conn.execute(
            "UPDATE leads SET email = ?, updated_at = ? WHERE id = ? AND (email IS NULL OR email = '')",
            (dup["email"], now, keep_id),
        )
    # Merge tags
    if dup["tags"]:
        conn.execute(
            "UPDATE leads SET tags = tags || ',' || ?, updated_at = ? WHERE id = ?",
            (dup["tags"], now, keep_id),
        )
    # Mark dup as merged
    conn.execute("UPDATE leads SET status = 'merged', updated_at = ? WHERE id = ?", (now, dup_id))
    conn.commit()


def metrics_snapshot(conn: sqlite3.Connection) -> dict[str, int]:
    keys = {
        "leads": "SELECT COUNT(*) FROM leads WHERE status != 'merged'",
        "hot": "SELECT COUNT(*) FROM leads WHERE status = 'hot'",
        "warm": "SELECT COUNT(*) FROM leads WHERE status = 'warm'",
        "with_email": "SELECT COUNT(*) FROM leads WHERE email IS NOT NULL AND email != '' AND status != 'merged'",
        "enriched": "SELECT COUNT(DISTINCT lead_id) FROM enrichment_log WHERE result_email != ''",
        "queued_emails": "SELECT COUNT(*) FROM email_queue WHERE status = 'queued'",
        "sent_emails": "SELECT COUNT(*) FROM email_queue WHERE status = 'sent'",
        "failed_emails": "SELECT COUNT(*) FROM email_queue WHERE status = 'failed'",
        "merged": "SELECT COUNT(*) FROM leads WHERE status = 'merged'",
    }
    out: dict[str, int] = {}
    for key, sql in keys.items():
        row = conn.execute(sql).fetchone()
        out[key] = int(row[0] if row else 0)
    return out
