"""Dependency injection for FastAPI routes."""

from functools import lru_cache

from sardis_core.ledger import InMemoryLedger
from sardis_core.services import WalletService, PaymentService, FeeService


class Container:
    """
    Simple dependency container for services.
    
    In a production system, this would use a proper DI framework.
    For the MVP, we use a simple singleton pattern.
    """
    
    _instance = None
    
    def __init__(self):
        # Initialize the ledger
        self._ledger = InMemoryLedger()
        
        # Initialize services
        self._fee_service = FeeService()
        self._wallet_service = WalletService(self._ledger)
        self._payment_service = PaymentService(
            self._ledger,
            self._wallet_service,
            self._fee_service
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
    def ledger(self) -> InMemoryLedger:
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


def get_ledger() -> InMemoryLedger:
    """Dependency for ledger."""
    return get_container().ledger

