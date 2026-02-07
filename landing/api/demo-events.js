import { neon } from '@neondatabase/serverless';
import { readSessionFromReq } from './_demoAuth.js';

const DATABASE_URL = process.env.DATABASE_URL || process.env.POSTGRES_URL;
const sql = DATABASE_URL ? neon(DATABASE_URL) : null;

async function ensureTable() {
  if (!sql) return false;
  await sql`
    CREATE TABLE IF NOT EXISTS demo_events (
      id BIGSERIAL PRIMARY KEY,
      run_id TEXT NOT NULL,
      mode TEXT NOT NULL,
      scenario TEXT NOT NULL,
      event_type TEXT NOT NULL,
      step TEXT,
      status TEXT,
      message TEXT,
      metadata JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ DEFAULT NOW()
    )
  `;
  await sql`CREATE INDEX IF NOT EXISTS idx_demo_events_created_at ON demo_events (created_at DESC)`;
  await sql`CREATE INDEX IF NOT EXISTS idx_demo_events_run_id ON demo_events (run_id)`;
  return true;
}

function json(res, code, payload) {
  res.status(code).json(payload);
}

function bodyOf(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  if (typeof req.body === 'string') {
    try {
      return JSON.parse(req.body);
    } catch {
      return {};
    }
  }
  return {};
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return json(res, 405, { error: 'method_not_allowed' });
  }

  if (!sql) {
    return json(res, 503, { error: 'database_not_configured' });
  }

  const body = bodyOf(req);
  const mode = String(body.mode || 'simulated');
  if (mode === 'live' && !readSessionFromReq(req)) {
    return json(res, 401, { error: 'operator_auth_required' });
  }

  const runId = String(body.runId || '');
  const scenario = String(body.scenario || 'unknown');
  const eventType = String(body.eventType || 'unknown');
  const step = body.step ? String(body.step) : null;
  const status = body.status ? String(body.status) : null;
  const message = body.message ? String(body.message).slice(0, 500) : null;
  const metadata = body.metadata && typeof body.metadata === 'object' ? body.metadata : {};

  if (!runId || runId.length > 120) {
    return json(res, 400, { error: 'invalid_run_id' });
  }

  await ensureTable();
  await sql`
    INSERT INTO demo_events (
      run_id,
      mode,
      scenario,
      event_type,
      step,
      status,
      message,
      metadata
    ) VALUES (
      ${runId},
      ${mode},
      ${scenario},
      ${eventType},
      ${step},
      ${status},
      ${message},
      ${JSON.stringify(metadata)}
    )
  `;

  return json(res, 201, { success: true });
}
