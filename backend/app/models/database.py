"""
Database models and session management module.

This module sets up SQLAlchemy ORM for PostgreSQL database connections.
It provides the engine, session factory, and base class for database models.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Import application settings from config module
# Used to retrieve the DATABASE_URL configuration
from app.core.config import settings

# Create SQLAlchemy engine instance
# The engine manages database connections and dialect-specific operations
# create_engine() takes the database URL and creates the engine
engine = create_engine(settings.DATABASE_URL)

# Create session factory for database operations
# SessionLocal is a factory that creates new database sessions
# - autocommit=False: Each transaction must be explicitly committed
# - autoflush=False: Changes are not automatically flushed to the database
# - bind=engine: All sessions created by this factory use our engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base class for defining ORM models
# All database models should inherit from this Base class
# This allows SQLAlchemy to discover and manage all model classes
Base = declarative_base()


def get_db():
    """
    Dependency function for getting database sessions.

    This function is used as a FastAPI dependency to inject database
    sessions into route handlers. It ensures proper session cleanup.

    Yields:
        Session: A SQLAlchemy database session

    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    # Create a new session for each request
    db = SessionLocal()
    try:
        # Yield the session to the route handler
        # The session is passed to the endpoint that requested it
        yield db
    finally:
        # Ensure the session is closed after the request
        # This returns the connection to the pool and prevents leaks
        db.close()