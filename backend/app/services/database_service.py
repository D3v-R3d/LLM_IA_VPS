"""
PostgreSQL Database Service Module

This module provides database connectivity and operations for PostgreSQL
using SQLAlchemy ORM. It handles connection management, health checks,
and query execution.

The DatabaseService is the primary interface for interacting with the
PostgreSQL database where structured application data is stored.

Usage:
    from app.services.database_service import DatabaseService

    db = DatabaseService()
    session = db.get_session()
    result = session.execute(text("SELECT * FROM users"))
"""

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.database import SessionLocal


class DatabaseService:
    """
    Service class for PostgreSQL database operations.

    This service provides a consistent interface for database connectivity
    and operations throughout the application. It uses SQLAlchemy's session
    management for efficient connection handling.

    Attributes:
        session_local: SQLAlchemy session factory for creating new sessions.
    """

    def __init__(self):
        """
        Initialize the DatabaseService.

        Sets up the session factory from the SessionLocal configuration
        defined in the database models module.
        """
        self.session_local = SessionLocal

    def get_session(self) -> Session:
        """
        Create and return a new database session.

        Creates a new SQLAlchemy session that can be used for querying
        and transactions. The caller is responsible for closing the session.

        Returns:
            SQLAlchemy Session instance connected to PostgreSQL.

        Note:
            Always close the session when done to return connections
            to the pool:
            ```
            session = db.get_session()
            try:
                result = session.execute(text("SELECT 1"))
            finally:
                session.close()
            ```
        """
        return self.session_local()

    async def health_check(self) -> bool:
        """
        Check if the PostgreSQL database is reachable and responsive.

        Executes a simple query to verify the database connection is active.

        Returns:
            True if the database is reachable, False otherwise.
        """
        session = self.get_session()
        try:
            # Execute a simple query that should always succeed
            # if the database is healthy
            session.execute(text("SELECT 1"))
            return True
        except Exception:
            # Return False for any connection or query errors
            return False
        finally:
            # Always close the session to return it to the pool
            session.close()

    async def get_version(self) -> str:
        """
        Get the PostgreSQL server version.

        Useful for debugging and verifying the database server version.

        Returns:
            String containing the PostgreSQL version, or "unknown" if
            the query fails.
        """
        session = self.get_session()
        try:
            # Query for PostgreSQL version
            result = session.execute(text("SELECT version()"))
            # scalar() returns the first column of the first row
            return result.scalar()
        except Exception:
            # Return "unknown" if query fails
            return "unknown"
        finally:
            session.close()