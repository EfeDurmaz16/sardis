#!/usr/bin/env python3
"""Create a demo API key for testing."""

import asyncio
from sardis_core.database.session import async_session_factory
from sardis_core.database.models import DBApiKey
from sardis_core.auth.security import hash_key

async def create_demo_key():
    # Demo key format: sk_{key_id}_{key_secret}
    key_id = "sardis_demo"
    key_secret = "abc123xyz789"
    raw_key = f"sk_{key_id}_{key_secret}"
    
    print(f"Creating demo API key: {raw_key}")
    
    async with async_session_factory() as session:
        async with session.begin():
            # Check if exists
            from sqlalchemy import select
            stmt = select(DBApiKey).where(DBApiKey.key_id == key_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                print("Demo key already exists!")
                return
            
            # Create new key
            key_hash = hash_key(key_secret)
            db_key = DBApiKey(
                key_id=key_id,
                key_hash=key_hash,
                owner_id="admin_dashboard",
                name="Demo Key"
            )
            session.add(db_key)
            await session.commit()
            
    print(f"✅ Demo API key created successfully!")
    print(f"Key: {raw_key}")
    print(f"\nThe dashboard will use this key automatically.")

if __name__ == "__main__":
    asyncio.run(create_demo_key())
