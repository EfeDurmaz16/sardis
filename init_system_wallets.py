#!/usr/bin/env python3
"""Initialize system wallets (treasury, fees, settlement)."""

import asyncio
from decimal import Decimal
from sardis_core.database.session import async_session_factory
from sardis_core.database.models import DBAgent, DBWallet
from sardis_core.config import settings

async def init_system_wallets():
    """Create system wallets if they don't exist."""
    
    system_wallets = [
        {
            "agent_id": "system_treasury",
            "wallet_id": "wallet_system_treasury",
            "name": "System Treasury",
            "description": "System treasury for funding new agent wallets"
        },
        {
            "agent_id": "system_fees",
            "wallet_id": settings.fee_pool_wallet_id,
            "name": "System Fees",
            "description": "Collects transaction fees"
        },
        {
            "agent_id": "system_settlement",
            "wallet_id": settings.settlement_wallet_id,
            "name": "System Settlement",
            "description": "Settlement wallet for merchant payouts"
        }
    ]
    
    async with async_session_factory() as session:
        async with session.begin():
            for sys_wallet in system_wallets:
                # Check if agent exists
                from sqlalchemy import select
                stmt = select(DBAgent).where(DBAgent.agent_id == sys_wallet["agent_id"])
                result = await session.execute(stmt)
                agent = result.scalar_one_or_none()
                
                if not agent:
                    print(f"Creating system agent: {sys_wallet['name']}")
                    agent = DBAgent(
                        agent_id=sys_wallet["agent_id"],
                        name=sys_wallet["name"],
                        owner_id="system",
                        description=sys_wallet["description"],
                        is_active=True
                    )
                    session.add(agent)
                
                # Check if wallet exists
                stmt = select(DBWallet).where(DBWallet.wallet_id == sys_wallet["wallet_id"])
                result = await session.execute(stmt)
                wallet = result.scalar_one_or_none()
                
                if not wallet:
                    print(f"Creating system wallet: {sys_wallet['wallet_id']}")
                    wallet = DBWallet(
                        wallet_id=sys_wallet["wallet_id"],
                        agent_id=sys_wallet["agent_id"],
                        balances={"USDC": "1000000.00"},  # 1M USDC for treasury
                        currency="USDC",
                        limit_per_tx=Decimal("999999999.00"),
                        limit_total=Decimal("999999999.00"),
                        spent_total=Decimal("0.00"),
                        virtual_card=None,
                        is_active=True
                    )
                    session.add(wallet)
            
            await session.commit()
    
    print("✅ System wallets initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_system_wallets())
