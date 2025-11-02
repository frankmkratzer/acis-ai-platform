"""
Database connection for FastAPI backend

Uses existing database configuration from utils/db_config.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from utils.db_config import SessionLocal, engine, get_psycopg2_connection


# SQLAlchemy session dependency for FastAPI
def get_db():
    """
    FastAPI dependency for database sessions.

    Usage in routes:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Export for convenience
__all__ = ["engine", "SessionLocal", "get_db", "get_psycopg2_connection"]
