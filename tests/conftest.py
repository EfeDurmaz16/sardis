import pytest
from sardis_core.api.dependencies import Container, get_container

@pytest.fixture(autouse=True)
def reset_container():
    """Reset the dependency container before each test."""
    # Force InMemoryLedger for tests
    from sardis_core.config import settings
    settings.database_url = None
    
    Container.reset()
    # Clear lru_cache of get_container
    get_container.cache_clear()
    yield
