/**
 * Sardis MPP Proxy — Policy enforcement
 *
 * Before accepting an MPP payment, we check the agent's spending
 * mandate via the Sardis API. If the payment would exceed the
 * mandate limit or hit a blocked vendor, we reject — even if the
 * on-chain payment itself is valid.
 *
 * This is the core Sardis differentiator on top of vanilla MPP:
 * financial-hallucination prevention at the proxy layer.
 */

export interface PolicyCheckRequest {
  /** Amount in USD */
  amount: string;
  /** Payer wallet address (from MPP credential) */
  payerAddress: string;
  /** The API route being accessed */
  route: string;
  /** Origin API hostname */
  merchant: string;
  /** Payment method used */
  paymentMethod: string;
}

export interface PolicyCheckResult {
  allowed: boolean;
  reason: string;
  mandateId?: string;
  remainingBudget?: string;
  checksRun?: number;
}

/**
 * Check Sardis spending policy for an MPP payment.
 *
 * Calls the Sardis API `/api/v2/mpp/evaluate` endpoint to verify
 * the agent has sufficient mandate budget and the vendor is allowed.
 *
 * If the Sardis API is unreachable while policy enforcement is enabled,
 * we fail closed so production traffic is never allowed through without
 * an authoritative Sardis policy decision.
 */
export async function checkPolicy(
  request: PolicyCheckRequest,
  sardisApiUrl: string,
  sardisApiKey: string,
): Promise<PolicyCheckResult> {
  if (!sardisApiKey) {
    return {
      allowed: true,
      reason: 'SARDIS_API_KEY not configured — policy check skipped',
    };
  }

  try {
    const response = await fetch(`${sardisApiUrl}/api/v2/mpp/evaluate`, {
      method: 'POST',
      headers: {
        'X-API-Key': sardisApiKey,
        'Content-Type': 'application/json',
        'User-Agent': 'sardis-mpp-proxy/0.1.0',
      },
      body: JSON.stringify({
        amount: parseFloat(request.amount),
        merchant: request.merchant,
        payment_type: `mpp_${request.paymentMethod}`,
        currency: 'USDC',
        network: request.paymentMethod,
        payer_address: request.payerAddress,
        route: request.route,
      }),
    });

    if (!response.ok) {
      const body = await response.text();
      console.error(
        `Sardis policy API error ${response.status}: ${body}`,
      );
      return {
        allowed: false,
        reason: `Policy API returned ${response.status}; payment blocked because policy enforcement is unavailable`,
      };
    }

    const result = (await response.json()) as {
      allowed: boolean;
      reason?: string;
      mandate_id?: string;
      remaining_budget?: string;
      checks_passed?: number;
      checks_total?: number;
    };

    return {
      allowed: result.allowed,
      reason: result.reason || (result.allowed ? 'ALLOWED' : 'BLOCKED'),
      mandateId: result.mandate_id,
      remainingBudget: result.remaining_budget,
      checksRun: result.checks_total,
    };
  } catch (error) {
    console.error('Sardis policy check failed:', error);
    return {
      allowed: false,
      reason: 'Policy check unreachable; payment blocked because policy enforcement is unavailable',
    };
  }
}
