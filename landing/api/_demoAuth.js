import crypto from 'crypto';

const SESSION_COOKIE = 'sardis_demo_session';
const SESSION_TTL_SECONDS = 60 * 60 * 8; // 8h

function base64url(input) {
  return Buffer.from(input).toString('base64url');
}

function getSigningSecret() {
  const pass = process.env.DEMO_OPERATOR_PASSWORD || '';
  return crypto.createHash('sha256').update(`sardis-demo:${pass}`).digest('hex');
}

export function hasDemoPasswordConfigured() {
  return Boolean((process.env.DEMO_OPERATOR_PASSWORD || '').trim());
}

function sign(value) {
  return crypto.createHmac('sha256', getSigningSecret()).update(value).digest('base64url');
}

function parseCookies(cookieHeader = '') {
  return cookieHeader
    .split(';')
    .map((part) => part.trim())
    .filter(Boolean)
    .reduce((acc, part) => {
      const idx = part.indexOf('=');
      if (idx === -1) return acc;
      const k = part.slice(0, idx);
      const v = part.slice(idx + 1);
      acc[k] = decodeURIComponent(v);
      return acc;
    }, {});
}

export function createSessionToken() {
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    iat: now,
    exp: now + SESSION_TTL_SECONDS,
    nonce: crypto.randomBytes(8).toString('hex'),
  };
  const encoded = base64url(JSON.stringify(payload));
  const signature = sign(encoded);
  return `${encoded}.${signature}`;
}

export function verifySessionToken(token) {
  if (!token || !token.includes('.')) return false;
  const [encoded, signature] = token.split('.', 2);
  if (!encoded || !signature) return false;

  const expected = sign(encoded);
  if (expected.length !== signature.length) return false;
  if (
    !crypto.timingSafeEqual(
      Buffer.from(expected, 'utf8'),
      Buffer.from(signature, 'utf8')
    )
  ) {
    return false;
  }

  try {
    const payload = JSON.parse(Buffer.from(encoded, 'base64url').toString('utf8'));
    const now = Math.floor(Date.now() / 1000);
    return typeof payload.exp === 'number' && payload.exp > now;
  } catch {
    return false;
  }
}

export function readSessionFromReq(req) {
  const cookies = parseCookies(req.headers.cookie || '');
  const token = cookies[SESSION_COOKIE];
  return verifySessionToken(token);
}

export function buildSessionCookie(token) {
  const secure = process.env.NODE_ENV === 'production' ? '; Secure' : '';
  return `${SESSION_COOKIE}=${encodeURIComponent(token)}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${SESSION_TTL_SECONDS}${secure}`;
}

export function clearSessionCookie() {
  const secure = process.env.NODE_ENV === 'production' ? '; Secure' : '';
  return `${SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${secure}`;
}
