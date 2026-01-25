#!/usr/bin/env python3
"""
End-to-End Demo Script for Sardis

This script demonstrates the full Sardis payment flow:
1. Create an agent with a wallet
2. Define spending policy using natural language
3. Fund the wallet (testnet)
4. Execute a payment
5. Verify the transaction

Requirements:
- OPENAI_API_KEY environment variable (for NL policy parsing)
- Optional: SARDIS_API_URL for remote API (defaults to local)

Usage:
    python scripts/e2e_demo.py
    python scripts/e2e_demo.py --api-url http://localhost:8000
    python scripts/e2e_demo.py --chain base_sepolia --live
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

# Add packages to path for local development
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "packages" / "sardis-core" / "src"))
sys.path.insert(0, str(root_dir / "packages" / "sardis-compliance" / "src"))
sys.path.insert(0, str(root_dir / "packages" / "sardis-chain" / "src"))
sys.path.insert(0, str(root_dir / "packages" / "sardis-wallet" / "src"))
sys.path.insert(0, str(root_dir / "packages" / "sardis-ledger" / "src"))
sys.path.insert(0, str(root_dir / "packages" / "sardis-protocol" / "src"))
sys.path.insert(0, str(root_dir / "sardis"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("e2e_demo")


# ============================================================================
# Demo Configuration
# ============================================================================

DEMO_CONFIG = {
    "agent_name": "Demo AI Agent",
    "agent_description": "A demonstration agent for Sardis E2E testing",
    "initial_balance": Decimal("1000.00"),  # USDC
    "policy": "Allow max $500 per day on OpenAI and AWS, block gambling, require approval over $200",
    "test_payment": {
        "amount": Decimal("50.00"),
        "currency": "USDC",
        "recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f26a1C",  # Example address
        "description": "OpenAI API Credits",
        "merchant": "openai.com",
    },
}


# ============================================================================
# Demo Steps
# ============================================================================

async def step_1_create_agent() -> dict:
    """Step 1: Create an AI agent with a wallet."""
    logger.info("=" * 60)
    logger.info("STEP 1: Creating AI Agent with Wallet")
    logger.info("=" * 60)

    try:
        from sardis_v2_core.agents import Agent, AgentPolicy, SpendingLimits
        from sardis_v2_core.wallet_repository import WalletRepository

        # Create agent with default spending limits
        agent = Agent.new(
            name=DEMO_CONFIG["agent_name"],
            description=DEMO_CONFIG["agent_description"],
            owner_id="demo_owner",
            spending_limits=SpendingLimits(
                per_transaction=Decimal("100.00"),
                daily=Decimal("500.00"),
                monthly=Decimal("5000.00"),
                total=Decimal("50000.00"),
            ),
            policy=AgentPolicy(
                blocked_categories=["gambling", "adult"],
                auto_approve_below=Decimal("50.00"),
            ),
        )

        logger.info(f"  Agent ID: {agent.agent_id}")
        logger.info(f"  Name: {agent.name}")
        logger.info(f"  Spending Limits: ${agent.spending_limits.daily}/day")

        return {
            "agent_id": agent.agent_id,
            "agent": agent,
            "status": "created",
        }

    except Exception as e:
        logger.error(f"  Failed to create agent: {e}")
        return {"status": "error", "error": str(e)}


async def step_2_parse_policy(agent_id: str) -> dict:
    """Step 2: Parse natural language policy."""
    logger.info("=" * 60)
    logger.info("STEP 2: Parsing Natural Language Policy")
    logger.info("=" * 60)
    logger.info(f"  Policy: \"{DEMO_CONFIG['policy']}\"")

    try:
        from sardis_v2_core.nl_policy_parser import (
            NLPolicyParser,
            RegexPolicyParser,
            HAS_INSTRUCTOR,
        )

        if HAS_INSTRUCTOR and os.getenv("OPENAI_API_KEY"):
            logger.info("  Using LLM-based policy parser (OpenAI)")
            parser = NLPolicyParser()
            extracted = await parser.parse(DEMO_CONFIG["policy"])
            policy = parser.to_spending_policy(extracted, agent_id)

            logger.info(f"  Parsed Policy ID: {policy.policy_id}")
            logger.info(f"  Daily Limit: ${policy.daily_limit.limit_amount if policy.daily_limit else 'None'}")
            logger.info(f"  Merchant Rules: {len(policy.merchant_rules)}")

            # Show extracted details
            for limit in extracted.spending_limits:
                logger.info(f"    - {limit.vendor_pattern}: ${limit.max_amount} {limit.period}")

            if extracted.category_restrictions:
                logger.info(f"  Blocked Categories: {extracted.category_restrictions.blocked_categories}")

            return {
                "policy_id": policy.policy_id,
                "policy": policy,
                "extracted": extracted,
                "status": "parsed",
            }
        else:
            logger.warning("  OpenAI API key not set, using regex parser (limited)")
            parser = RegexPolicyParser()
            parsed = parser.parse(DEMO_CONFIG["policy"])

            logger.info(f"  Regex parsed: {json.dumps(parsed, indent=2)}")

            return {
                "policy_id": "regex_policy",
                "parsed": parsed,
                "status": "parsed_regex",
            }

    except Exception as e:
        logger.error(f"  Failed to parse policy: {e}")
        return {"status": "error", "error": str(e)}


async def step_3_create_wallet(agent_id: str) -> dict:
    """Step 3: Create and fund a wallet."""
    logger.info("=" * 60)
    logger.info("STEP 3: Creating and Funding Wallet")
    logger.info("=" * 60)

    try:
        from sardis_v2_core.wallets import Wallet
        from uuid import uuid4

        wallet_id = f"wallet_{uuid4().hex[:16]}"
        test_address = "0x" + uuid4().hex[:40]

        wallet = Wallet(
            wallet_id=wallet_id,
            agent_id=agent_id,
            mpc_provider="turnkey",
            addresses={"base_sepolia": test_address},
            is_active=True,
        )

        logger.info(f"  Wallet ID: {wallet.wallet_id}")
        logger.info(f"  Address: {wallet.addresses.get('base_sepolia', 'N/A')}")
        logger.info(f"  MPC Provider: {wallet.mpc_provider}")
        logger.info(f"  Initial Balance: ${DEMO_CONFIG['initial_balance']} USDC (simulated)")

        return {
            "wallet_id": wallet.wallet_id,
            "wallet": wallet,
            "address": wallet.addresses.get("base_sepolia"),
            "status": "created",
        }

    except Exception as e:
        logger.error(f"  Failed to create wallet: {e}")
        return {"status": "error", "error": str(e)}


async def step_4_compliance_check(agent_id: str, policy: Optional[dict] = None) -> dict:
    """Step 4: Run compliance preflight check."""
    logger.info("=" * 60)
    logger.info("STEP 4: Running Compliance Preflight Check")
    logger.info("=" * 60)

    try:
        from sardis_v2_core import SardisSettings, load_settings
        from sardis_v2_core.mandates import PaymentMandate, VCProof
        from sardis_compliance.checks import ComplianceEngine, NLPolicyProvider
        from uuid import uuid4
        from datetime import datetime, timezone

        settings = load_settings()

        # Create mandate for test payment
        test_payment = DEMO_CONFIG["test_payment"]
        mandate_id = f"mandate_{uuid4().hex[:16]}"

        # Create a mock VCProof for demo
        proof = VCProof(
            verification_method="did:key:demo",
            created=datetime.now(timezone.utc).isoformat(),
            proof_value="demo_proof_value",
        )

        mandate = PaymentMandate(
            mandate_id=mandate_id,
            mandate_type="payment",
            issuer=f"did:agent:{agent_id}",
            subject=agent_id,
            expires_at=int(datetime.now(timezone.utc).timestamp()) + 300,
            nonce=uuid4().hex,
            proof=proof,
            domain="demo.sardis.sh",
            purpose="checkout",
            chain="base_sepolia",
            token=test_payment["currency"],
            amount_minor=int(test_payment["amount"] * 100),  # Convert to cents
            destination=test_payment["recipient"],
            audit_hash="demo_audit_hash",
        )

        logger.info(f"  Mandate ID: {mandate.mandate_id}")
        logger.info(f"  Amount: ${test_payment['amount']} {test_payment['currency']}")
        logger.info(f"  Recipient: {test_payment['recipient'][:10]}...{test_payment['recipient'][-6:]}")

        # Create compliance engine with NL policy provider
        provider = NLPolicyProvider(settings)
        if policy and policy.get("policy"):
            provider.set_policy_for_agent(agent_id, policy["policy"])
            logger.info("  Policy loaded into compliance engine")

        engine = ComplianceEngine(settings=settings, provider=provider)

        # Run preflight check
        result = engine.preflight(mandate)

        logger.info(f"  Compliance Result: {'APPROVED' if result.allowed else 'DENIED'}")
        logger.info(f"  Reason: {result.reason or 'N/A'}")
        logger.info(f"  Audit ID: {result.audit_id}")

        return {
            "mandate_id": mandate.mandate_id,
            "allowed": result.allowed,
            "reason": result.reason,
            "audit_id": result.audit_id,
            "status": "checked",
        }

    except Exception as e:
        logger.error(f"  Compliance check failed: {e}")
        return {"status": "error", "error": str(e)}


async def step_5_execute_payment(wallet: dict, mandate_id: str, simulated: bool = True) -> dict:
    """Step 5: Execute the payment."""
    logger.info("=" * 60)
    logger.info(f"STEP 5: Executing Payment ({'Simulated' if simulated else 'Live'})")
    logger.info("=" * 60)

    test_payment = DEMO_CONFIG["test_payment"]

    if simulated:
        # Simulate payment execution
        tx_hash = f"0x{'demo' * 16}"

        logger.info(f"  [SIMULATED] Transaction submitted")
        logger.info(f"  TX Hash: {tx_hash[:20]}...{tx_hash[-10:]}")
        logger.info(f"  Amount: ${test_payment['amount']} {test_payment['currency']}")
        logger.info(f"  Gas Used: 21000 (estimated)")
        logger.info(f"  Status: CONFIRMED (simulated)")

        return {
            "tx_hash": tx_hash,
            "status": "confirmed",
            "simulated": True,
            "gas_used": 21000,
        }
    else:
        try:
            from sardis_v2_core import SardisSettings, load_settings
            from sardis_chain.executor import ChainExecutor

            settings = load_settings()
            executor = ChainExecutor(settings=settings)

            # Execute on testnet
            result = await executor.transfer_erc20(
                from_address=wallet.get("address"),
                to_address=test_payment["recipient"],
                amount=test_payment["amount"],
                token="USDC",
                chain="base_sepolia",
            )

            logger.info(f"  Transaction submitted: {result.tx_hash}")
            logger.info(f"  Status: {result.status}")

            return {
                "tx_hash": result.tx_hash,
                "status": result.status,
                "simulated": False,
            }

        except Exception as e:
            logger.error(f"  Payment execution failed: {e}")
            return {"status": "error", "error": str(e)}


async def step_6_verify_audit_trail(audit_id: str) -> dict:
    """Step 6: Verify the audit trail."""
    logger.info("=" * 60)
    logger.info("STEP 6: Verifying Audit Trail")
    logger.info("=" * 60)

    try:
        from sardis_compliance.checks import get_audit_store

        store = get_audit_store()

        logger.info(f"  Total Audit Entries: {store.count()}")

        # Get recent audits
        recent = store.get_recent(5)
        for entry in recent:
            logger.info(f"  - {entry.audit_id[:12]}... | {entry.mandate_id[:12]}... | {'ALLOW' if entry.allowed else 'DENY'}")

        return {
            "total_entries": store.count(),
            "recent_entries": len(recent),
            "status": "verified",
        }

    except Exception as e:
        logger.error(f"  Audit verification failed: {e}")
        return {"status": "error", "error": str(e)}


# ============================================================================
# Main Demo Runner
# ============================================================================

async def run_demo(live: bool = False, chain: str = "base_sepolia"):
    """Run the complete E2E demo."""
    logger.info("\n" + "=" * 60)
    logger.info("       SARDIS END-TO-END DEMO")
    logger.info("       The Payment OS for the Agent Economy")
    logger.info("=" * 60)
    logger.info(f"  Mode: {'LIVE (Testnet)' if live else 'SIMULATED'}")
    logger.info(f"  Chain: {chain}")
    logger.info(f"  Time: {datetime.now().isoformat()}")
    logger.info("=" * 60 + "\n")

    results = {}

    # Step 1: Create Agent
    results["agent"] = await step_1_create_agent()
    if results["agent"]["status"] == "error":
        logger.error("Demo failed at Step 1")
        return results

    agent_id = results["agent"]["agent_id"]

    # Step 2: Parse Policy
    results["policy"] = await step_2_parse_policy(agent_id)

    # Step 3: Create Wallet
    results["wallet"] = await step_3_create_wallet(agent_id)
    if results["wallet"]["status"] == "error":
        logger.error("Demo failed at Step 3")
        return results

    # Step 4: Compliance Check
    results["compliance"] = await step_4_compliance_check(
        agent_id,
        policy=results.get("policy"),
    )

    if not results["compliance"].get("allowed", False):
        logger.warning("Payment blocked by compliance check")
        logger.info("Demo completed (payment blocked)")
        return results

    # Step 5: Execute Payment
    results["payment"] = await step_5_execute_payment(
        wallet=results["wallet"],
        mandate_id=results["compliance"]["mandate_id"],
        simulated=not live,
    )

    # Step 6: Verify Audit Trail
    results["audit"] = await step_6_verify_audit_trail(
        audit_id=results["compliance"].get("audit_id", ""),
    )

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("       DEMO COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Agent Created: {results['agent']['agent_id'][:20]}...")
    logger.info(f"  Wallet Created: {results['wallet'].get('wallet_id', 'N/A')[:20]}...")
    logger.info(f"  Policy Parsed: {results['policy']['status']}")
    logger.info(f"  Compliance: {'APPROVED' if results['compliance'].get('allowed') else 'DENIED'}")
    logger.info(f"  Payment: {results['payment']['status']}")
    logger.info(f"  Audit Trail: {results['audit']['status']}")
    logger.info("=" * 60 + "\n")

    return results


def main():
    parser = argparse.ArgumentParser(description="Sardis E2E Demo Script")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute on testnet (default: simulated)",
    )
    parser.add_argument(
        "--chain",
        default="base_sepolia",
        choices=["base_sepolia", "polygon_mumbai", "arbitrum_sepolia"],
        help="Testnet chain to use",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="API URL for remote execution",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.api_url:
        os.environ["SARDIS_API_URL"] = args.api_url

    # Run the demo
    results = asyncio.run(run_demo(live=args.live, chain=args.chain))

    # Exit with appropriate code
    if any(r.get("status") == "error" for r in results.values()):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
