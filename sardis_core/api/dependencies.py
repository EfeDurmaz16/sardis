"""Dependency injection for FastAPI routes."""

from functools import lru_cache

from sardis_core.config import settings
from sardis_core.ledger import BaseLedger, InMemoryLedger, PostgresLedger
from sardis_core.services import WalletService, PaymentService, FeeService, AgentService


class Container:
    """
    Simple dependency container for services.
    
    In a production system, this would use a proper DI framework.
    For the MVP, we use a simple singleton pattern.
    """
    
    _instance = None
    
    def __init__(self):
        # Initialize the ledger based on config
        if settings.database_url and "postgresql" in settings.database_url:
            self._ledger: BaseLedger = PostgresLedger()
        else:
            self._ledger: BaseLedger = InMemoryLedger()
        
        # Initialize services
        self._fee_service = FeeService()
        self._wallet_service = WalletService(self._ledger)
        self._payment_service = PaymentService(
            self._ledger,
            self._wallet_service,
            self._fee_service
        )
        self._agent_service = AgentService(
            self._wallet_service,
            self._payment_service
        )
    
    @classmethod
    def get_instance(cls) -> "Container":
        """Get or create the singleton container."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset the container (useful for testing)."""
        cls._instance = None
    
    @property
    def ledger(self) -> BaseLedger:
        return self._ledger
    
    @property
    def wallet_service(self) -> WalletService:
        return self._wallet_service
    
    @property
    def payment_service(self) -> PaymentService:
        return self._payment_service
    
    @property
    def fee_service(self) -> FeeService:
        return self._fee_service

    @property
    def agent_service(self) -> "AgentService":
        return self._agent_service


@lru_cache()
def get_container() -> Container:
    """Get the dependency container."""
    return Container.get_instance()


def get_wallet_service() -> WalletService:
    """Dependency for wallet service."""
    return get_container().wallet_service


def get_payment_service() -> PaymentService:
    """Dependency for payment service."""
    return get_container().payment_service


def get_fee_service() -> FeeService:
    """Dependency for fee service."""
    return get_container().fee_service


def get_ledger() -> BaseLedger:
    """Dependency for ledger."""
    return get_container().ledger


def get_agent_service() -> "AgentService":
    """Dependency for agent service."""
    return get_container().agent_service

