"""
Sardis Load Testing with Locust

Load tests for the Sardis Payment OS API.
Tests concurrent payment processing, hold operations, and policy checks.

Run with:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

For headless mode:
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
        --headless -u 100 -r 10 -t 5m

Environment variables:
    SARDIS_API_KEY: API key for authentication
    SARDIS_TEST_WALLET_ID: Pre-existing wallet ID for tests
"""
import os
import json
import random
import string
from datetime import datetime, timezone
from locust import HttpUser, task, between, events


# Configuration
API_KEY = os.getenv("SARDIS_API_KEY", "sk_test_load_test")
TEST_WALLET_ID = os.getenv("SARDIS_TEST_WALLET_ID", "wallet_load_test")

# Test vendors for payment simulation
TEST_VENDORS = [
    {"name": "OpenAI", "category": "saas", "max_amount": 100},
    {"name": "GitHub", "category": "devtools", "max_amount": 50},
    {"name": "Vercel", "category": "saas", "max_amount": 75},
    {"name": "AWS", "category": "cloud", "max_amount": 200},
    {"name": "Anthropic", "category": "saas", "max_amount": 100},
    {"name": "Stripe", "category": "fintech", "max_amount": 150},
]


def generate_id(prefix: str = "load") -> str:
    """Generate a unique ID for testing."""
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}_{int(datetime.now(timezone.utc).timestamp())}_{suffix}"


class SardisAPIUser(HttpUser):
    """Simulates a Sardis API user (AI agent)."""

    wait_time = between(0.5, 2)
    wallet_id = TEST_WALLET_ID

    def on_start(self):
        """Set up authentication headers."""
        self.client.headers.update({
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "X-Request-ID": generate_id("req"),
        })

    @task(10)
    def check_balance(self):
        """Check wallet balance - most common operation."""
        with self.client.get(
            f"/api/v2/wallets/{self.wallet_id}/balance",
            name="/api/v2/wallets/[id]/balance",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.failure("Wallet not found")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(5)
    def check_policy(self):
        """Check payment policy before executing."""
        vendor = random.choice(TEST_VENDORS)
        amount = random.randint(10, vendor["max_amount"])

        payload = {
            "vendor": vendor["name"],
            "amount": amount,
            "category": vendor["category"],
        }

        with self.client.post(
            "/api/v2/policies/check",
            json=payload,
            name="/api/v2/policies/check",
            catch_response=True
        ) as response:
            if response.status_code in [200, 403]:  # 403 = blocked by policy
                response.success()
            else:
                response.failure(f"Policy check failed: {response.status_code}")

    @task(3)
    def execute_payment(self):
        """Execute a payment mandate."""
        vendor = random.choice(TEST_VENDORS)
        amount = random.randint(5, vendor["max_amount"])

        mandate = {
            "mandate_id": generate_id("mandate"),
            "subject": self.wallet_id,
            "destination": f"vendor:{vendor['name'].lower()}",
            "amount_minor": str(amount * 1_000_000),
            "token": "USDC",
            "chain": "base_sepolia",
            "purpose": f"Load test payment - {vendor['name']}",
            "vendor_name": vendor["name"],
            "metadata": {
                "category": vendor["category"],
                "load_test": True,
            },
        }

        with self.client.post(
            "/api/v2/mandates/execute",
            json={"mandate": mandate},
            name="/api/v2/mandates/execute",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 403:
                # Policy block is valid
                response.success()
            elif response.status_code == 400:
                response.failure("Bad request")
            else:
                response.failure(f"Payment failed: {response.status_code}")

    @task(2)
    def create_hold(self):
        """Create a payment hold."""
        amount = random.randint(10, 100)

        payload = {
            "wallet_id": self.wallet_id,
            "amount_minor": amount * 1_000_000,
            "token": "USDC",
            "chain": "base_sepolia",
            "purpose": "Load test hold",
            "expires_in_seconds": 3600,
        }

        with self.client.post(
            "/api/v2/holds",
            json=payload,
            name="/api/v2/holds",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 400:
                response.failure("Hold creation failed")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(2)
    def list_transactions(self):
        """List recent transactions."""
        with self.client.get(
            f"/api/v2/wallets/{self.wallet_id}/transactions?limit=20",
            name="/api/v2/wallets/[id]/transactions",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"List failed: {response.status_code}")

    @task(1)
    def get_wallet_info(self):
        """Get wallet details."""
        with self.client.get(
            f"/api/v2/wallets/{self.wallet_id}",
            name="/api/v2/wallets/[id]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.failure("Wallet not found")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(1)
    def get_spending_stats(self):
        """Get spending statistics."""
        with self.client.get(
            f"/api/v2/wallets/{self.wallet_id}/spending?period=daily",
            name="/api/v2/wallets/[id]/spending",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Stats failed: {response.status_code}")


class HighVolumePaymentUser(HttpUser):
    """Simulates high-volume payment processing."""

    wait_time = between(0.1, 0.5)  # Faster requests
    wallet_id = TEST_WALLET_ID

    def on_start(self):
        self.client.headers.update({
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        })

    @task
    def rapid_payments(self):
        """Execute payments rapidly to test throughput."""
        vendor = random.choice(TEST_VENDORS)
        amount = random.randint(1, 20)  # Small amounts

        mandate = {
            "mandate_id": generate_id("rapid"),
            "subject": self.wallet_id,
            "destination": f"vendor:{vendor['name'].lower()}",
            "amount_minor": str(amount * 1_000_000),
            "token": "USDC",
            "chain": "base_sepolia",
            "purpose": "Rapid payment test",
            "vendor_name": vendor["name"],
        }

        with self.client.post(
            "/api/v2/mandates/execute",
            json={"mandate": mandate},
            name="/api/v2/mandates/execute [rapid]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 403]:
                response.success()
            else:
                response.failure(f"Rapid payment failed: {response.status_code}")


class HoldLifecycleUser(HttpUser):
    """Tests the complete hold lifecycle under load."""

    wait_time = between(1, 3)
    wallet_id = TEST_WALLET_ID

    def on_start(self):
        self.client.headers.update({
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        })
        self.active_holds = []

    @task(3)
    def create_and_capture_hold(self):
        """Create a hold and immediately capture it."""
        amount = random.randint(10, 50)

        # Create hold
        payload = {
            "wallet_id": self.wallet_id,
            "amount_minor": amount * 1_000_000,
            "token": "USDC",
            "chain": "base_sepolia",
            "purpose": "Hold lifecycle test",
        }

        with self.client.post(
            "/api/v2/holds",
            json=payload,
            name="/api/v2/holds [create]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                data = response.json()
                hold_id = data.get("hold_id") or data.get("id")

                if hold_id:
                    # Capture the hold
                    with self.client.post(
                        f"/api/v2/holds/{hold_id}/capture",
                        json={"amount_minor": amount * 1_000_000},
                        name="/api/v2/holds/[id]/capture",
                        catch_response=True
                    ) as capture_response:
                        if capture_response.status_code in [200, 201]:
                            capture_response.success()
                        else:
                            capture_response.failure(f"Capture failed: {capture_response.status_code}")
                response.success()
            else:
                response.failure(f"Hold creation failed: {response.status_code}")

    @task(1)
    def create_and_void_hold(self):
        """Create a hold and void it."""
        amount = random.randint(10, 30)

        payload = {
            "wallet_id": self.wallet_id,
            "amount_minor": amount * 1_000_000,
            "token": "USDC",
            "chain": "base_sepolia",
            "purpose": "Hold void test",
        }

        with self.client.post(
            "/api/v2/holds",
            json=payload,
            name="/api/v2/holds [void test]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                data = response.json()
                hold_id = data.get("hold_id") or data.get("id")

                if hold_id:
                    with self.client.post(
                        f"/api/v2/holds/{hold_id}/void",
                        name="/api/v2/holds/[id]/void",
                        catch_response=True
                    ) as void_response:
                        if void_response.status_code in [200, 201]:
                            void_response.success()
                        else:
                            void_response.failure(f"Void failed: {void_response.status_code}")
                response.success()
            else:
                response.failure(f"Hold creation failed: {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test configuration at start."""
    print(f"\n=== Sardis Load Test Started ===")
    print(f"Target: {environment.host}")
    print(f"Test Wallet: {TEST_WALLET_ID}")
    print(f"================================\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log summary at end."""
    print(f"\n=== Sardis Load Test Complete ===")
    stats = environment.stats.total
    print(f"Total Requests: {stats.num_requests}")
    print(f"Failed Requests: {stats.num_failures}")
    print(f"Average Response Time: {stats.avg_response_time:.2f}ms")
    print(f"Requests/sec: {stats.total_rps:.2f}")
    print(f"==================================\n")
