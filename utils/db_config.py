"""
Database configuration and connection utilities
"""

import os
from contextlib import contextmanager

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

load_dotenv()

# Database credentials
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = os.getenv("DB_NAME", "acis-ai")
DB_USER = "postgres"
_db_pass_env = os.getenv("DB_PASSWORD", "")
# Handle dotenv's variable expansion issues with $@
if _db_pass_env and "@nJose420" in _db_pass_env:
    DB_PASSWORD = "$@nJose420"  # Hardcode due to dotenv $@ expansion issue
else:
    DB_PASSWORD = _db_pass_env or "$@nJose420"

# Connection strings
SQLALCHEMY_DATABASE_URL = os.getenv(
    "POSTGRES_URL", f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

PSYCOPG2_CONN_STRING = (
    f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"
)


# SQLAlchemy engine with connection pooling
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session():
    """Context manager for SQLAlchemy sessions"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


@contextmanager
def get_psycopg2_connection():
    """Context manager for raw psycopg2 connections"""
    conn = psycopg2.connect(PSYCOPG2_CONN_STRING)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_psycopg2_cursor(conn, dict_cursor=True):
    """Get a cursor from psycopg2 connection"""
    if dict_cursor:
        return conn.cursor(cursor_factory=RealDictCursor)
    return conn.cursor()


def test_connection():
    """Test database connection"""
    try:
        with get_psycopg2_connection() as conn:
            with get_psycopg2_cursor(conn, dict_cursor=False) as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
                print(f"[OK] Database connection successful!")
                print(f"PostgreSQL version: {version}")
                return True
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()
