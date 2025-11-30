"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sardis_core.config import settings
from sardis_core.api.routes import agents, payments, merchants, catalog, webhooks, risk, marketplace
from sardis_core.api.dependencies import get_container


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Sardis API",
        description="""
        # Sardis - Programmable Stablecoin Payment Network for AI Agents
        
        Sardis provides a payment layer that enables AI agents to pay for 
        things online using stablecoins with strict spending limits.
        
        ## Features
        
        - **Agent Wallets**: Create wallets with multiple stablecoin support (USDC, USDT, PYUSD, EURC)
        - **Multi-Chain**: Support for Base, Ethereum, Polygon, and Solana
        - **Spending Limits**: Per-transaction and total spending limits
        - **Webhooks**: Real-time event notifications
        - **Risk Scoring**: Basic fraud prevention
        - **Transaction History**: Full audit trail of all payments
        
        ## Supported Tokens
        
        | Token | Description |
        |-------|-------------|
        | USDC | USD Coin by Circle |
        | USDT | Tether USD |
        | PYUSD | PayPal USD |
        | EURC | Euro Coin by Circle |
        
        ## Authentication
        
        This MVP uses simple API access. In production, implement proper 
        API key authentication.
        """,
        version="0.3.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(agents.router, prefix=settings.api_prefix)
    app.include_router(payments.router, prefix=settings.api_prefix)
    app.include_router(merchants.router, prefix=settings.api_prefix)
    app.include_router(catalog.router, prefix=settings.api_prefix)
    app.include_router(webhooks.router, prefix=settings.api_prefix)
    app.include_router(risk.router, prefix=settings.api_prefix)
    app.include_router(marketplace.router, prefix=settings.api_prefix)
    
    @app.get("/", tags=["health"])
    async def root():
        """Health check endpoint."""
        return {
            "service": "Sardis API",
            "version": "0.3.0",
            "status": "healthy",
            "description": "Programmable stablecoin payment network for AI agents"
        }
    
    @app.get(f"{settings.api_prefix}/", tags=["health"])
    async def api_root():
        """API root endpoint with version info."""
        return {
            "service": "Sardis API",
            "version": "0.3.0",
            "status": "healthy",
            "endpoints": {
                "agents": f"{settings.api_prefix}/agents",
                "payments": f"{settings.api_prefix}/payments",
                "merchants": f"{settings.api_prefix}/merchants",
                "catalog": f"{settings.api_prefix}/catalog",
                "webhooks": f"{settings.api_prefix}/webhooks",
                "risk": f"{settings.api_prefix}/risk",
                "marketplace": f"{settings.api_prefix}/marketplace",
            },
            "docs": "/docs"
        }
    
    @app.get("/health", tags=["health"])
    async def health_check():
        """Detailed health check."""
        return {
            "status": "healthy",
            "components": {
                "api": "up",
                "ledger": "up",
                "webhooks": "up",
                "chains": {
                    "base": "ready",
                    "ethereum": "ready",
                    "polygon": "ready",
                    "solana": "ready"
                }
            }
        }
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup."""
        # Initialize the container (creates ledger and services)
        container = get_container()
        
        # Register mock merchants for the catalog
        wallet_service = container.wallet_service
        
        # Check if merchants already exist
        if not wallet_service.get_merchant("mock_merchant_electronics"):
            wallet_service.register_merchant(
                name="TechStore Electronics",
                description="Electronics and gadgets",
                category="electronics"
            )
        
        if not wallet_service.get_merchant("mock_merchant_office"):
            wallet_service.register_merchant(
                name="Office Supplies Co",
                description="Office supplies and accessories",
                category="office"
            )
    
    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "sardis_core.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
