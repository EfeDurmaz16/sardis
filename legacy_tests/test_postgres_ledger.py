
import pytest
from decimal import Decimal
from sardis_core.ledger.postgres import PostgresLedger
from sardis_core.models.wallet import Wallet, TokenType
from sardis_core.config import settings

from sqlalchemy import text
from unittest.mock import patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
class TestPostgresLedger:
    
    @pytest.fixture(autouse=True)
    async def setup_postgres(self):
        # Restore DB URL
        settings.database_url = "postgresql+asyncpg://efebarandurmaz@localhost:5432/sardis"
        
        # Create new engine/factory for this loop
        test_engine = create_async_engine(settings.database_url, echo=False, future=True)
        test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        
        # Cleanup DB and insert prerequisites
        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(text("TRUNCATE TABLE transactions, wallets, agents CASCADE"))
                
                # Insert test agents
                await session.execute(text("""
                    INSERT INTO agents (agent_id, name, owner_id, is_active, created_at, updated_at)
                    VALUES 
                    ('test_agent_pg_1', 'Test Agent 1', 'owner_1', true, NOW(), NOW()),
                    ('agent_sender', 'Sender Agent', 'owner_2', true, NOW(), NOW()),
                    ('agent_receiver', 'Receiver Agent', 'owner_3', true, NOW(), NOW()),
                    ('system_agent', 'System Agent', 'system', true, NOW(), NOW())
                """))
                
                # Insert fee pool wallet (needed for transfers with fees)
                # Assuming settings.fee_pool_wallet_id is 'fee_pool' or similar. 
                # Let's check config or just insert what we think it is.
                # Default config usually has 'fee_pool'.
                fee_wallet_id = settings.fee_pool_wallet_id
                await session.execute(text(f"""
                    INSERT INTO wallets (wallet_id, agent_id, balances, currency, limit_per_tx, limit_total, spent_total, is_active, created_at, updated_at)
                    VALUES 
                    ('{fee_wallet_id}', 'system_agent', '{{"USDC": "0.00"}}', 'USDC', 0, 0, 0, true, NOW(), NOW())
                """))
        
        # Patch the factory in the ledger module
        with patch("sardis_core.ledger.postgres.async_session_factory", test_session_factory):
            yield
            
        await test_engine.dispose()

    @pytest.fixture
    async def ledger(self):
        return PostgresLedger()

    async def test_create_and_get_wallet(self, ledger):
        wallet_id = "test_wallet_pg_1"
        wallet = Wallet(
            wallet_id=wallet_id,
            agent_id="test_agent_pg_1",
            limit_per_tx=Decimal("100.00"),
            limit_total=Decimal("1000.00")
        )
        
        # Create
        created = await ledger.create_wallet(wallet)
        assert created.wallet_id == wallet_id
        assert created.balance == Decimal("0.00")
        
        # Get
        retrieved = await ledger.get_wallet(wallet_id)
        assert retrieved is not None
        assert retrieved.wallet_id == wallet_id
        assert retrieved.agent_id == "test_agent_pg_1"
        assert retrieved.balance == Decimal("0.00")

    async def test_fund_and_transfer(self, ledger):
        # Setup wallets
        sender = Wallet(wallet_id="sender_pg", agent_id="agent_sender")
        receiver = Wallet(wallet_id="receiver_pg", agent_id="agent_receiver")
        
        await ledger.create_wallet(sender)
        await ledger.create_wallet(receiver)
        
        # Fund sender (mocking system wallet funding or using fund_wallet if implemented)
        # Note: fund_wallet relies on system_wallet_id existing. 
        # For this test, let's manually update sender balance via update_wallet or similar if possible,
        # but PostgresLedger.fund_wallet uses transfer from system wallet.
        # We need to ensure system wallet exists.
        
        # In a real test env, we might need to seed the system wallet.
        # Let's try to use a direct update for testing purposes or ensure system wallet is there.
        # Since we don't have a direct "set balance" method exposed for testing in Ledger interface,
        # we might need to rely on the fact that we can update the wallet object and save it?
        # No, update_wallet updates from the wallet object state? 
        # Let's check update_wallet implementation.
        
        sender.balance = Decimal("100.00")
        sender.set_token_balance(TokenType.USDC, Decimal("100.00"))
        await ledger.update_wallet(sender)
        
        # Verify funding
        s_check = await ledger.get_wallet("sender_pg")
        assert s_check.balance == Decimal("100.00")
        
        # Transfer
        tx = await ledger.transfer(
            from_wallet_id="sender_pg",
            to_wallet_id="receiver_pg",
            amount=Decimal("20.00"),
            fee=Decimal("0.10"),
            currency="USDC",
            purpose="Test Transfer"
        )
        
        assert tx.status.value == "completed"
        
        # Check balances
        s_final = await ledger.get_wallet("sender_pg")
        r_final = await ledger.get_wallet("receiver_pg")
        
        # 100 - 20 - 0.10 = 79.90
        assert s_final.balance == Decimal("79.90")
        assert r_final.balance == Decimal("20.00")

