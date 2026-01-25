/**
 * Sardis Load Testing with k6
 *
 * High-performance load tests using k6 (grafana/k6).
 *
 * Run with:
 *   k6 run tests/load/k6_load_test.js --env API_URL=http://localhost:8000
 *
 * With custom settings:
 *   k6 run tests/load/k6_load_test.js -u 100 -d 5m --env API_URL=http://localhost:8000
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';
import { randomIntBetween, randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// Custom metrics
const paymentSuccess = new Counter('sardis_payment_success');
const paymentBlocked = new Counter('sardis_payment_blocked');
const paymentFailed = new Counter('sardis_payment_failed');
const policyCheckTime = new Trend('sardis_policy_check_ms');
const paymentTime = new Trend('sardis_payment_ms');
const errorRate = new Rate('sardis_error_rate');

// Configuration
const API_URL = __ENV.API_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'sk_test_load_test';
const WALLET_ID = __ENV.WALLET_ID || 'wallet_load_test';

// Test options
export const options = {
  stages: [
    { duration: '1m', target: 20 },   // Ramp up to 20 users
    { duration: '3m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Ramp up to 100 users
    { duration: '3m', target: 100 },  // Stay at 100 users
    { duration: '1m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],  // 95% < 500ms, 99% < 1s
    sardis_error_rate: ['rate<0.05'],                 // Error rate < 5%
    sardis_payment_ms: ['p(95)<300'],                 // 95% payments < 300ms
    sardis_policy_check_ms: ['p(95)<100'],            // 95% policy checks < 100ms
  },
};

// Test vendors
const VENDORS = [
  { name: 'OpenAI', category: 'saas', maxAmount: 100 },
  { name: 'GitHub', category: 'devtools', maxAmount: 50 },
  { name: 'Vercel', category: 'saas', maxAmount: 75 },
  { name: 'AWS', category: 'cloud', maxAmount: 200 },
  { name: 'Anthropic', category: 'saas', maxAmount: 100 },
];

// Headers
const headers = {
  'Authorization': `Bearer ${API_KEY}`,
  'Content-Type': 'application/json',
};

function generateId(prefix = 'k6') {
  return `${prefix}_${Date.now()}_${randomString(8)}`;
}

export default function () {
  group('Wallet Operations', function () {
    // Check balance
    const balanceRes = http.get(
      `${API_URL}/api/v2/wallets/${WALLET_ID}/balance`,
      { headers, tags: { name: 'GetBalance' } }
    );

    check(balanceRes, {
      'balance status 200': (r) => r.status === 200,
    });

    errorRate.add(balanceRes.status !== 200);

    sleep(0.1);

    // Get wallet info
    const walletRes = http.get(
      `${API_URL}/api/v2/wallets/${WALLET_ID}`,
      { headers, tags: { name: 'GetWallet' } }
    );

    check(walletRes, {
      'wallet status 200': (r) => r.status === 200,
    });
  });

  group('Policy Check', function () {
    const vendor = VENDORS[randomIntBetween(0, VENDORS.length - 1)];
    const amount = randomIntBetween(10, vendor.maxAmount);

    const payload = JSON.stringify({
      vendor: vendor.name,
      amount: amount,
      category: vendor.category,
    });

    const startTime = Date.now();
    const policyRes = http.post(
      `${API_URL}/api/v2/policies/check`,
      payload,
      { headers, tags: { name: 'PolicyCheck' } }
    );
    const endTime = Date.now();

    policyCheckTime.add(endTime - startTime);

    check(policyRes, {
      'policy check success': (r) => r.status === 200 || r.status === 403,
    });

    errorRate.add(policyRes.status !== 200 && policyRes.status !== 403);
  });

  group('Execute Payment', function () {
    const vendor = VENDORS[randomIntBetween(0, VENDORS.length - 1)];
    const amount = randomIntBetween(5, vendor.maxAmount);

    const mandate = {
      mandate_id: generateId('mandate'),
      subject: WALLET_ID,
      destination: `vendor:${vendor.name.toLowerCase()}`,
      amount_minor: String(amount * 1_000_000),
      token: 'USDC',
      chain: 'base_sepolia',
      purpose: `k6 load test - ${vendor.name}`,
      vendor_name: vendor.name,
      metadata: {
        category: vendor.category,
        load_test: true,
      },
    };

    const payload = JSON.stringify({ mandate });

    const startTime = Date.now();
    const paymentRes = http.post(
      `${API_URL}/api/v2/mandates/execute`,
      payload,
      { headers, tags: { name: 'ExecutePayment' } }
    );
    const endTime = Date.now();

    paymentTime.add(endTime - startTime);

    if (paymentRes.status === 200 || paymentRes.status === 201) {
      paymentSuccess.add(1);
    } else if (paymentRes.status === 403) {
      paymentBlocked.add(1);
    } else {
      paymentFailed.add(1);
      errorRate.add(1);
    }

    check(paymentRes, {
      'payment processed': (r) => r.status === 200 || r.status === 201 || r.status === 403,
    });

    sleep(randomIntBetween(1, 3) / 10);
  });

  group('Hold Operations', function () {
    const amount = randomIntBetween(10, 50);

    const holdPayload = JSON.stringify({
      wallet_id: WALLET_ID,
      amount_minor: amount * 1_000_000,
      token: 'USDC',
      chain: 'base_sepolia',
      purpose: 'k6 hold test',
    });

    const holdRes = http.post(
      `${API_URL}/api/v2/holds`,
      holdPayload,
      { headers, tags: { name: 'CreateHold' } }
    );

    if (holdRes.status === 200 || holdRes.status === 201) {
      let holdData;
      try {
        holdData = JSON.parse(holdRes.body);
      } catch (e) {
        holdData = {};
      }

      const holdId = holdData.hold_id || holdData.id;

      if (holdId) {
        // Capture the hold
        const captureRes = http.post(
          `${API_URL}/api/v2/holds/${holdId}/capture`,
          JSON.stringify({ amount_minor: amount * 1_000_000 }),
          { headers, tags: { name: 'CaptureHold' } }
        );

        check(captureRes, {
          'hold captured': (r) => r.status === 200 || r.status === 201,
        });
      }
    }

    check(holdRes, {
      'hold created': (r) => r.status === 200 || r.status === 201,
    });

    errorRate.add(holdRes.status !== 200 && holdRes.status !== 201);
  });

  group('List Transactions', function () {
    const listRes = http.get(
      `${API_URL}/api/v2/wallets/${WALLET_ID}/transactions?limit=20`,
      { headers, tags: { name: 'ListTransactions' } }
    );

    check(listRes, {
      'transactions listed': (r) => r.status === 200,
    });

    errorRate.add(listRes.status !== 200);
  });

  sleep(randomIntBetween(5, 15) / 10);
}

// Lifecycle functions
export function setup() {
  console.log(`\n=== Sardis k6 Load Test ===`);
  console.log(`Target: ${API_URL}`);
  console.log(`Wallet: ${WALLET_ID}`);
  console.log(`==========================\n`);

  // Verify API is accessible
  const healthRes = http.get(`${API_URL}/health`);
  if (healthRes.status !== 200) {
    console.warn(`Warning: Health check returned ${healthRes.status}`);
  }

  return { startTime: Date.now() };
}

export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log(`\n=== Test Complete ===`);
  console.log(`Duration: ${duration.toFixed(2)}s`);
  console.log(`=====================\n`);
}

// Scenario for spike testing
export function spikeTest() {
  group('Spike Test - Rapid Payments', function () {
    for (let i = 0; i < 10; i++) {
      const vendor = VENDORS[randomIntBetween(0, VENDORS.length - 1)];

      const mandate = {
        mandate_id: generateId('spike'),
        subject: WALLET_ID,
        destination: `vendor:${vendor.name.toLowerCase()}`,
        amount_minor: String(randomIntBetween(1, 20) * 1_000_000),
        token: 'USDC',
        chain: 'base_sepolia',
        purpose: 'Spike test',
        vendor_name: vendor.name,
      };

      http.post(
        `${API_URL}/api/v2/mandates/execute`,
        JSON.stringify({ mandate }),
        { headers, tags: { name: 'SpikePayment' } }
      );
    }
  });
}
