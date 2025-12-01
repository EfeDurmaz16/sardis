"""
Database Session Management

Provides connection pooling, session management, and database initialization
for PostgreSQL production deployment.
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from sardis_core.config import get_settings
from .models import Base


# Database engine singleton
_engine = None
_SessionLocal = None


def get_database_url() -> str:
    """Get database URL from settings or environment."""
    settings = get_settings()
    
    # Priority: settings -> environment -> default SQLite
    if settings.database_url:
        return settings.database_url
    
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Handle Heroku-style postgres:// URLs
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    
    # Default to SQLite for development
    return "sqlite:///./sardis.db"


def get_engine():
    """Get or create the database engine."""
    global _engine
    
    if _engine is None:
        db_url = get_database_url()
        
        # Configure engine based on database type
        if db_url.startswith("sqlite"):
            # SQLite configuration
            _engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            )
            
            # Enable foreign keys for SQLite
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            # PostgreSQL configuration with connection pooling
            _engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,  # Recycle connections after 30 min
                echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            )
    
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _SessionLocal
    
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )
    
    return _SessionLocal


class DatabaseSession:
    """Context manager for database sessions."""
    
    def __init__(self):
        self.session: Optional[Session] = None
    
    def __enter__(self) -> Session:
        SessionLocal = get_session_factory()
        self.session = SessionLocal()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type:
                self.session.rollback()
            self.session.close()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage:
        @app.get("/agents")
        def list_agents(db: Session = Depends(get_db)):
            return db.query(AgentDB).all()
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Usage:
        with db_session() as db:
            agent = db.query(AgentDB).filter_by(agent_id="...").first()
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """
    Initialize the database.
    Creates all tables if they don't exist.
    """
    engine = get_engine()
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print(f"Database initialized: {get_database_url()}")


def drop_db():
    """
    Drop all tables.
    WARNING: This will delete all data!
    """
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    print("Database tables dropped")


def reset_db():
    """
    Reset the database.
    Drops all tables and recreates them.
    WARNING: This will delete all data!
    """
    drop_db()
    init_db()
    print("Database reset complete")


# Health check
def check_db_health() -> dict:
    """Check database connectivity."""
    try:
        with db_session() as db:
            db.execute("SELECT 1")
            return {
                "status": "healthy",
                "database": get_database_url().split("://")[0],
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }

