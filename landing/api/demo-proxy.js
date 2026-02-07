import { readSessionFromReq } from './_demoAuth.js';

const DEFAULT_TIMEOUT_MS = 9000;

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

function getConfig() {
  const rawBase = String(process.env.SARDIS_API_URL || '').trim();
  let normalizedBase = rawBase.replace(/\/+$/, '');
  let invalidBaseUrl = false;
  if (normalizedBase) {
    try {
      new URL(normalizedBase);
    } catch {
      invalidBaseUrl = true;
      normalizedBase = '';
    }
  }
  return {
    baseUrl: normalizedBase,
    apiKey: String(process.env.SARDIS_API_KEY || ''),
    defaultAgentId: String(process.env.DEMO_LIVE_AGENT_ID || ''),
    defaultCardId: String(process.env.DEMO_LIVE_CARD_ID || ''),
    invalidBaseUrl,
  };
}

async function requestSardis(path, { method = 'GET', body, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  const { baseUrl, apiKey, invalidBaseUrl } = getConfig();
  if (invalidBaseUrl) {
    return {
      ok: false,
      status: 503,
      error: 'sardis_api_url_invalid',
      detail: 'SARDIS_API_URL must be a valid absolute URL (e.g. https://api-staging.sardis.sh)',
    };
  }
  if (!baseUrl || !apiKey) {
    return {
      ok: false,
      status: 503,
      error: 'sardis_api_not_configured',
      detail: 'Set SARDIS_API_URL and SARDIS_API_KEY',
    };
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort('timeout'), timeoutMs);
  const startedAt = Date.now();
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    const durationMs = Date.now() - startedAt;
    const text = await response.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text };
    }

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        durationMs,
        error: 'sardis_api_error',
        detail: data?.detail || data?.error || 'Request failed',
        data,
      };
    }

    return {
      ok: true,
      status: response.status,
      durationMs,
      data,
    };
  } catch (error) {
    const durationMs = Date.now() - startedAt;
    const timedOut = String(error || '').includes('timeout') || error?.name === 'AbortError';
    return {
      ok: false,
      status: timedOut ? 504 : 502,
      durationMs,
      error: timedOut ? 'sardis_api_timeout' : 'sardis_api_unreachable',
      detail: timedOut ? 'Request timed out' : String(error?.message || error || 'Unknown error'),
    };
  } finally {
    clearTimeout(timeout);
  }
}

async function checkHealth() {
  const attemptA = await requestSardis('/api/v2/metrics/health');
  if (attemptA.ok) return { ...attemptA, endpoint: '/api/v2/metrics/health' };
  const attemptB = await requestSardis('/health');
  return { ...(attemptB.ok ? attemptB : attemptA), endpoint: attemptB.ok ? '/health' : '/api/v2/metrics/health' };
}

function normalizeBlocked(reason, amount) {
  return {
    vendor: 'Policy Engine',
    amount,
    reasonCode: 'SARDIS.POLICY.DENIED',
    reason: reason || 'Policy denied this transaction',
    timestamp: new Date().toISOString(),
  };
}

export default async function handler(req, res) {
  const method = req.method || 'GET';
  const sessionOk = readSessionFromReq(req);
  const config = getConfig();

  if (method === 'GET') {
    let apiBaseHost = null;
    if (config.baseUrl) {
      try {
        apiBaseHost = new URL(config.baseUrl).host;
      } catch {
        apiBaseHost = config.baseUrl;
      }
    }
    return json(res, 200, {
      authenticated: sessionOk,
      liveConfigured: Boolean(config.baseUrl && config.apiKey),
      hasDefaultAgent: Boolean(config.defaultAgentId),
      hasDefaultCard: Boolean(config.defaultCardId),
      apiBaseHost,
    });
  }

  if (method !== 'POST') {
    return json(res, 405, { error: 'method_not_allowed' });
  }

  if (!sessionOk) {
    return json(res, 401, { error: 'operator_auth_required' });
  }

  const body = bodyOf(req);
  const action = String(body.action || 'run_flow');

  if (action !== 'run_flow') {
    return json(res, 400, { error: 'unsupported_action' });
  }

  const scenario = body.scenario === 'blocked' ? 'blocked' : 'approved';
  const amount = Number(body.amount ?? (scenario === 'blocked' ? 5000 : 25));
  const merchant = String(body.merchant || 'DataCorp');
  const mccCode = String(body.mccCode || '5734');
  const agentId = String(body.agentId || config.defaultAgentId || '');
  const cardId = String(body.cardId || config.defaultCardId || '');
  const steps = [];

  const health = await checkHealth();
  steps.push({
    step: 'health',
    ok: health.ok,
    status: health.status,
    durationMs: health.durationMs,
    endpoint: health.endpoint,
    error: health.ok ? null : health.error,
    detail: health.ok ? null : health.detail,
  });
  if (!health.ok) {
    return json(res, 200, {
      ok: false,
      mode: 'live',
      scenario,
      steps,
      error: {
        code: health.error || 'health_check_failed',
        message: health.detail || 'Unable to reach Sardis API',
      },
      fallback: { recommended: 'simulated' },
    });
  }

  if (!agentId) {
    steps.push({
      step: 'policy_check',
      ok: true,
      status: 200,
      durationMs: 0,
      error: null,
      detail: 'skipped_no_agent_id',
    });

    if (scenario === 'blocked') {
      return json(res, 200, {
        ok: true,
        mode: 'live',
        scenario,
        steps,
        result: {
          outcome: 'blocked',
          policy: {
            allowed: false,
            reason: 'Blocked by demo scenario (no live policy agent configured).',
            policyId: null,
          },
          blockedAttempt: normalizeBlocked('DEMO_SCENARIO_BLOCKED', amount),
        },
      });
    }

    return json(res, 200, {
      ok: true,
      mode: 'live',
      scenario,
      steps,
      result: {
        outcome: 'approved',
        policy: {
          allowed: true,
          reason: 'Policy check skipped (set DEMO_LIVE_AGENT_ID for strict live check).',
          policyId: null,
        },
        purchase: null,
        note: 'Live payment simulation skipped (set DEMO_LIVE_AGENT_ID and DEMO_LIVE_CARD_ID).',
      },
    });
  }

  const policy = await requestSardis('/api/v2/policies/check', {
    method: 'POST',
    body: {
      agent_id: agentId,
      amount,
      currency: 'USD',
      merchant_id: merchant.toLowerCase().replace(/\s+/g, '_'),
      merchant_category: 'saas',
      mcc_code: mccCode,
    },
  });

  steps.push({
    step: 'policy_check',
    ok: policy.ok,
    status: policy.status,
    durationMs: policy.durationMs,
    error: policy.ok ? null : policy.error,
    detail: policy.ok ? null : policy.detail,
  });

  if (!policy.ok) {
    return json(res, 200, {
      ok: false,
      mode: 'live',
      scenario,
      steps,
      error: {
        code: policy.error || 'policy_check_failed',
        message: policy.detail || 'Policy check failed',
      },
      fallback: { recommended: 'simulated' },
    });
  }

  const policyAllowed = Boolean(policy.data?.allowed);
  const policyReason = String(policy.data?.reason || '');
  if (!policyAllowed || scenario === 'blocked') {
    return json(res, 200, {
      ok: true,
      mode: 'live',
      scenario,
      steps,
      result: {
        outcome: 'blocked',
        policy: {
          allowed: policyAllowed,
          reason: policyReason || 'Blocked by demo scenario',
          policyId: policy.data?.policy_id || null,
        },
        blockedAttempt: normalizeBlocked(policyReason || 'LIMIT_EXCEEDED', amount),
      },
    });
  }

  if (!cardId) {
    return json(res, 200, {
      ok: true,
      mode: 'live',
      scenario,
      steps,
      result: {
        outcome: 'approved',
        policy: {
          allowed: true,
          reason: policyReason || 'OK',
          policyId: policy.data?.policy_id || null,
        },
        purchase: null,
        note: 'Live payment simulation skipped (set DEMO_LIVE_CARD_ID to enable).',
      },
    });
  }

  const purchase = await requestSardis(`/api/v2/cards/${encodeURIComponent(cardId)}/simulate-purchase`, {
    method: 'POST',
    body: {
      amount,
      currency: 'USD',
      merchant_name: merchant,
      mcc_code: mccCode,
      status: 'approved',
    },
  });

  steps.push({
    step: 'card_simulate_purchase',
    ok: purchase.ok,
    status: purchase.status,
    durationMs: purchase.durationMs,
    error: purchase.ok ? null : purchase.error,
    detail: purchase.ok ? null : purchase.detail,
  });

  if (!purchase.ok) {
    return json(res, 200, {
      ok: false,
      mode: 'live',
      scenario,
      steps,
      error: {
        code: purchase.error || 'purchase_failed',
        message: purchase.detail || 'Card purchase simulation failed',
      },
      fallback: { recommended: 'simulated' },
    });
  }

  const tx = purchase.data?.transaction || {};
  return json(res, 200, {
    ok: true,
    mode: 'live',
    scenario,
    steps,
    result: {
      outcome: 'approved',
      policy: {
        allowed: true,
        reason: policyReason || 'OK',
        policyId: policy.data?.policy_id || null,
      },
      purchase: purchase.data,
      transaction: {
        hash: tx.transaction_id || 'tx_live_demo',
        hashFull: tx.transaction_id || 'tx_live_demo',
        amount: Number(tx.amount || amount).toFixed(2),
        token: 'USD',
        to: tx.merchant_name || merchant,
        block: 'live',
        chain: 'Card Rail',
        url: null,
      },
    },
  });
}
