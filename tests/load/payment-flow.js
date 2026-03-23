/**
 * Sardis Payment Pipeline Load Test (k6)
 *
 * Usage:
 *   k6 run tests/load/payment-flow.js
 *   k6 run --vus 50 --duration 60s tests/load/payment-flow.js
 *
 * Environment:
 *   K6_API_URL  — API base URL (default: https://api.sardis.sh)
 *   K6_API_KEY  — Test API key (sk_test_...)
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const API_URL = __ENV.K6_API_URL || "https://api.sardis.sh";
const API_KEY = __ENV.K6_API_KEY || "";

// Custom metrics
const healthLatency = new Trend("health_latency", true);
const agentCreateLatency = new Trend("agent_create_latency", true);
const policyCheckLatency = new Trend("policy_check_latency", true);
const errorRate = new Rate("errors");

export const options = {
  stages: [
    { duration: "10s", target: 10 }, // ramp up
    { duration: "30s", target: 50 }, // sustained load
    { duration: "10s", target: 0 }, // ramp down
  ],
  thresholds: {
    health_latency: ["p(95)<500"], // 95% of health checks under 500ms
    agent_create_latency: ["p(95)<2000"], // 95% of agent creates under 2s
    policy_check_latency: ["p(95)<200"], // 95% of policy checks under 200ms
    errors: ["rate<0.05"], // less than 5% errors
  },
};

const headers = {
  "Content-Type": "application/json",
  "X-API-Key": API_KEY,
};

export default function () {
  // 1. Health check
  const health = http.get(`${API_URL}/health`);
  healthLatency.add(health.timings.duration);
  check(health, {
    "health 200": (r) => r.status === 200,
    "health status healthy": (r) => {
      try {
        return JSON.parse(r.body).status === "healthy";
      } catch {
        return false;
      }
    },
  }) || errorRate.add(1);

  sleep(0.5);

  // 2. Create agent (if API key provided)
  if (API_KEY) {
    const agentName = `k6-agent-${__VU}-${__ITER}`;
    const createAgent = http.post(
      `${API_URL}/api/v2/agents`,
      JSON.stringify({ name: agentName, description: "k6 load test" }),
      { headers }
    );
    agentCreateLatency.add(createAgent.timings.duration);
    check(createAgent, {
      "agent created": (r) => r.status === 200 || r.status === 201,
    }) || errorRate.add(1);

    sleep(0.3);

    // 3. Policy check (sandbox)
    const policyCheck = http.post(
      `${API_URL}/api/v2/sandbox/policy-check`,
      JSON.stringify({
        agent_id: "demo-agent",
        amount: 25.0,
        currency: "USDC",
        merchant: "OpenAI",
        memo: "k6 load test",
      }),
      { headers }
    );
    policyCheckLatency.add(policyCheck.timings.duration);
    check(policyCheck, {
      "policy check responded": (r) => r.status < 500,
    }) || errorRate.add(1);
  }

  sleep(1);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: " ", enableColors: true }),
    "tests/load/results.json": JSON.stringify(data, null, 2),
  };
}

function textSummary(data, opts) {
  // k6 built-in text summary
  return "";
}
