#!/usr/bin/env python3
"""Clean up database completely - keep only system wallets."""

import asyncio
from sardis_core.database.session import async_session_factory
from sardis_core.database.models import DBAgent, DBWallet, DBTransaction
from sqlalchemy import select, delete

async def full_cleanup():
    """Remove ALL agents except system wallets."""
    
    system_agent_ids = ["system_treasury", "system_fees", "system_settlement"]
    
    async with async_session_factory() as session:
        async with session.begin():
            # Delete ALL transactions first
            print("Deleting all transactions...")
            await session.execute(delete(DBTransaction))
            
            # Get all agents that are NOT system agents
            stmt = select(DBAgent).where(
                ~DBAgent.agent_id.in_(system_agent_ids)
            )
            result = await session.execute(stmt)
            agents_to_delete = result.scalars().all()
            
            print(f"Found {len(agents_to_delete)} agents to delete")
            
            # Delete all wallets for these agents
            for agent in agents_to_delete:
                wallet_stmt = select(DBWallet).where(DBWallet.agent_id == agent.agent_id)
                wallet_result = await session.execute(wallet_stmt)
                wallet = wallet_result.scalar_one_or_none()
                
                if wallet:
                    await session.delete(wallet)
                    print(f"  Deleted wallet for {agent.name}")
                
                await session.delete(agent)
                print(f"  Deleted agent {agent.name}")
            
            await session.commit()
    
    print("\n✅ Database cleaned successfully!")
    print("\nRemaining agents:")
    
    # Show what's left
    async with async_session_factory() as session:
        stmt = select(DBAgent)
        result = await session.execute(stmt)
        remaining = result.scalars().all()
        
        for agent in remaining:
            print(f"  - {agent.name} ({agent.agent_id})")

if __name__ == "__main__":
    print("⚠️  This will delete EVERYTHING except system wallets!")
    print("System wallets to keep: treasury, fees, settlement\n")
    
    response = input("Continue? (yes/no): ")
    if response.lower() == "yes":
        asyncio.run(full_cleanup())
    else:
        print("Cancelled.")
