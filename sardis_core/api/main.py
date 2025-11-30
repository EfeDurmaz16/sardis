"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sardis_core.config import settings
from sardis_core.api.routes import agents, payments, merchants, catalog
from sardis_core.api.dependencies import get_container


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Sardis API",
        description="""
        Sardis Payment Infrastructure for AI Agents.
        
        Sardis provides a payment layer that enables AI agents to pay for 
        things online using stablecoins with strict spending limits.
        
        ## Features
        
        - **Agent Management**: Register AI agents with wallets and spending limits
        - **Payment Processing**: Execute payments with automatic fee handling
        - **Merchant Integration**: Register merchants to receive payments
        - **Transaction History**: Full audit trail of all payments
        
        ## Authentication
        
        This MVP uses simple API access. In production, implement proper 
        API key authentication.
        """,
        version="0.1.0",
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
    
    @app.get("/", tags=["health"])
    async def root():
        """Health check endpoint."""
        return {
            "service": "Sardis API",
            "version": "0.1.0",
            "status": "healthy"
        }
    
    @app.get("/health", tags=["health"])
    async def health_check():
        """Detailed health check."""
        return {
            "status": "healthy",
            "components": {
                "api": "up",
                "ledger": "up"
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

