#!/usr/bin/env python3
"""Clean up database - remove all user agents and merchants, keep only system wallets."""

import asyncio
from sardis_core.database.session import async_session_factory
from sardis_core.database.models import DBAgent, DBWallet, DBTransaction
from sqlalchemy import select, delete

async def cleanup_database():
    """Remove all non-system agents and their wallets."""
    
    async with async_session_factory() as session:
        async with session.begin():
            # Get all agents that are NOT system agents
            stmt = select(DBAgent).where(
                DBAgent.owner_id != "system",
                DBAgent.owner_id != "system_merchants"
            )
            result = await session.execute(stmt)
            user_agents = result.scalars().all()
            
            print(f"Found {len(user_agents)} user-created agents to delete")
            
            # Delete transactions for these agents' wallets
            for agent in user_agents:
                # Find wallet for this agent
                wallet_stmt = select(DBWallet).where(DBWallet.agent_id == agent.agent_id)
                wallet_result = await session.execute(wallet_stmt)
                wallet = wallet_result.scalar_one_or_none()
                
                if wallet:
                    # Delete transactions
                    tx_delete = delete(DBTransaction).where(
                        (DBTransaction.from_wallet == wallet.wallet_id) |
                        (DBTransaction.to_wallet == wallet.wallet_id)
                    )
                    await session.execute(tx_delete)
                    print(f"  Deleted transactions for wallet {wallet.wallet_id}")
                    
                    # Delete wallet
                    await session.delete(wallet)
                    print(f"  Deleted wallet {wallet.wallet_id}")
                
                # Delete agent
                await session.delete(agent)
                print(f"  Deleted agent {agent.name} ({agent.agent_id})")
            
            await session.commit()
    
    print("\n✅ Database cleaned successfully!")
    print("Remaining agents:")
    
    # Show what's left
    async with async_session_factory() as session:
        stmt = select(DBAgent)
        result = await session.execute(stmt)
        remaining = result.scalars().all()
        
        for agent in remaining:
            print(f"  - {agent.name} (owner: {agent.owner_id})")

if __name__ == "__main__":
    print("⚠️  This will delete all user-created agents and merchants!")
    print("System wallets (treasury, fees, settlement) will be preserved.\n")
    
    response = input("Continue? (yes/no): ")
    if response.lower() == "yes":
        asyncio.run(cleanup_database())
    else:
        print("Cancelled.")
