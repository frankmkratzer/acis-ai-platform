"""
Integration Test Configuration and Fixtures

Provides database setup, test client, and shared fixtures for integration tests.
"""

import os

# Import the FastAPI app
import sys
from urllib.parse import quote_plus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.api.database.connection import get_db
from backend.api.main import app

# Test database URL - encode password for special characters
password = "$@nJose420"
encoded_password = quote_plus(password)

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", f"postgresql://postgres:{encoded_password}@localhost:5432/acis-ai-test"
)


@pytest.fixture(scope="session")
def integration_engine():
    """
    Create a database engine for integration tests.
    Scope: session (created once per test session)
    """
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def integration_db_setup(integration_engine):
    """
    Set up database schema for integration tests.
    Runs once at the start of the test session.
    """
    with integration_engine.connect() as conn:
        # Create necessary tables and views
        # Note: In a real setup, you'd run all schema files here
        try:
            with open("database/create_rl_trading_tables.sql", "r") as f:
                conn.execute(text(f.read()))
            conn.commit()
        except Exception as e:
            print(f"Schema setup note: {e}")

        try:
            with open("database/fix_brokerage_id_autoincrement.sql", "r") as f:
                conn.execute(text(f.read()))
            conn.commit()
        except Exception as e:
            print(f"Brokerage setup note: {e}")

    yield

    # Cleanup (optional - drop test tables)
    # with integration_engine.connect() as conn:
    #     conn.execute(text("DROP TABLE IF EXISTS rl_order_batches CASCADE"))


@pytest.fixture
def integration_db(integration_engine, integration_db_setup):
    """
    Provide a database session with transaction rollback for each test.
    Each test gets a clean slate.
    """
    connection = integration_engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def integration_client(integration_db):
    """
    Provide a FastAPI test client with database dependency override.
    """

    def override_get_db():
        try:
            yield integration_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def test_client_data():
    """Provide sample client data for testing"""
    return {
        "first_name": "Integration",
        "last_name": "TestUser",
        "email": "integration.test@example.com",
        "risk_tolerance": "moderate",
        "investment_goal": "growth",
        "is_active": True,
    }


@pytest.fixture
def test_account_data():
    """Provide sample brokerage account data for testing"""
    return {
        "account_number": "INT123456",
        "account_hash": "integration_test_hash_12345",
        "account_type": "margin",
        "brokerage_id": 1,
        "is_active": True,
    }


@pytest.fixture
def cleanup_test_data(integration_db):
    """
    Cleanup fixture that removes test data after each test.
    Use this fixture when you need to clean up specific test data.
    """
    yield

    # Cleanup test clients
    integration_db.execute(text("DELETE FROM clients WHERE email LIKE '%@example.com'"))
    integration_db.commit()
