import crypto from 'crypto';
import {
  buildSessionCookie,
  clearSessionCookie,
  createSessionToken,
  hasDemoPasswordConfigured,
  readSessionFromReq,
} from './_demoAuth.js';

function json(res, code, payload) {
  res.status(code).json(payload);
}

function safeEquals(a, b) {
  const left = Buffer.from(String(a || ''), 'utf8');
  const right = Buffer.from(String(b || ''), 'utf8');
  if (left.length !== right.length) return false;
  return crypto.timingSafeEqual(left, right);
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
  const method = req.method || 'GET';
  const authenticated = readSessionFromReq(req);
  const liveConfigured = Boolean(
    (process.env.SARDIS_API_URL || '').trim() &&
      (process.env.SARDIS_API_KEY || '').trim()
  );
  const passwordConfigured = hasDemoPasswordConfigured();

  if (method === 'GET') {
    return json(res, 200, {
      authenticated,
      liveConfigured,
      passwordConfigured,
    });
  }

  if (method === 'DELETE') {
    res.setHeader('Set-Cookie', clearSessionCookie());
    return json(res, 200, { success: true, authenticated: false });
  }

  if (method !== 'POST') {
    return json(res, 405, { error: 'method_not_allowed' });
  }

  if (!passwordConfigured) {
    return json(res, 503, {
      error: 'demo_password_not_configured',
      hint: 'Set DEMO_OPERATOR_PASSWORD to enable live demo auth.',
    });
  }

  const body = bodyOf(req);
  const password = String(body.password || '');
  const expected = String(process.env.DEMO_OPERATOR_PASSWORD || '');
  if (!safeEquals(password, expected)) {
    return json(res, 401, { error: 'invalid_password' });
  }

  const token = createSessionToken();
  res.setHeader('Set-Cookie', buildSessionCookie(token));
  return json(res, 200, {
    success: true,
    authenticated: true,
    liveConfigured,
  });
}
