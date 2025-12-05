
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from unittest.mock import patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from sardis_core.api.main import app
from sardis_core.config import settings

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.asyncio
class TestAuth:
    
    @pytest.fixture(autouse=True)
    async def setup_postgres(self):
        # Restore DB URL
        settings.database_url = "postgresql+asyncpg://efebarandurmaz@localhost:5432/sardis"
        
        # Create new engine/factory for this loop
        test_engine = create_async_engine(settings.database_url, echo=False, future=True)
        test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        
        # Cleanup DB
        async with test_session_factory() as session:
            async with session.begin():
                await session.execute(text("TRUNCATE TABLE api_keys CASCADE"))
        
        # Patch the factory in the session module (used by get_db)
        with patch("sardis_core.database.session.async_session_factory", test_session_factory):
            yield
            
        await test_engine.dispose()

    async def test_create_api_key(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Login first
            login_resp = await ac.post("/api/v1/auth/login", data={
                "username": "admin",
                "password": settings.admin_password
            })
            assert login_resp.status_code == 200
            token = login_resp.json()["access_token"]
            
            # Create key with token
            response = await ac.post(
                "/api/v1/auth/keys", 
                json={
                    "name": "Test Key",
                    "owner_id": "tester"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 201
            data = response.json()
            assert "api_key" in data
            assert data["api_key"].startswith("sk_")
            assert "key_id" in data
            assert data["name"] == "Test Key"

    async def test_access_protected_route_without_key(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Missing header
            response = await ac.get("/api/v1/agents")
            assert response.status_code == 422 
            
            # Invalid header
            response = await ac.get("/api/v1/agents", headers={"X-API-Key": "invalid"})
            assert response.status_code == 401

    async def test_access_protected_route_with_key(self):
        # First create a key
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Login first
            login_resp = await ac.post("/api/v1/auth/login", data={
                "username": "admin",
                "password": settings.admin_password
            })
            token = login_resp.json()["access_token"]
            
            create_resp = await ac.post(
                "/api/v1/auth/keys", 
                json={
                    "name": "Access Key",
                    "owner_id": "tester"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            assert create_resp.status_code == 201
            api_key = create_resp.json()["api_key"]
            
            # Now access agents
            response = await ac.get("/api/v1/agents", headers={"X-API-Key": api_key})
            # Should be 200 OK (empty list)
            assert response.status_code == 200
            assert response.json() == []
