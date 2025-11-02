"""
Pytest configuration and shared fixtures

This file is automatically loaded by pytest and provides fixtures
that can be used across all test files.
"""

import os
import sys
from typing import Generator

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Load environment variables before anything else
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path is set
from backend.api.main import app

# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """
    FastAPI test client for making API requests

    Scope: session (created once per test session)
    """
    return TestClient(app)


@pytest.fixture
def client(test_client: TestClient) -> TestClient:
    """
    Alias for test_client with function scope

    Use this for tests that need a fresh client
    """
    return test_client


# ============================================================================
# Authentication Fixtures
# ============================================================================


@pytest.fixture
def admin_credentials() -> tuple[str, str]:
    """
    Admin credentials for testing

    Returns: (email, password) tuple
    """
    return ("admin@acis-ai.com", "admin123")


@pytest.fixture
def auth_token(test_client: TestClient, admin_credentials: tuple[str, str]) -> str:
    """
    Get a valid JWT authentication token

    Returns: JWT token string
    """
    email, password = admin_credentials
    response = test_client.post("/api/auth/login", auth=(email, password))

    if response.status_code != 200:
        pytest.fail(f"Failed to get auth token: {response.text}")

    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """
    Get authentication headers for API requests

    Returns: Dictionary with Authorization header
    """
    return {"Authorization": f"Bearer {auth_token}"}


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_db_engine():
    """
    Test database engine

    NOTE: Currently uses the same database as development.
    In production, you should use a separate test database.

    TODO: Set up separate test database
    """
    db_url = os.getenv("POSTGRES_URL", "postgresql://postgres@localhost:5432/acis-ai")
    engine = create_engine(db_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_db_engine) -> Generator[Session, None, None]:
    """
    Database session for tests

    Creates a new session for each test and rolls back changes after.
    This ensures tests don't affect each other.
    """
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_client_data() -> dict:
    """
    Sample client data for testing client creation
    """
    return {
        "first_name": "Test",
        "last_name": "Client",
        "email": "test.client@example.com",
        "risk_tolerance": "moderate",
        "investment_horizon": "long_term",
        "initial_capital": 100000.0,
    }


@pytest.fixture
def sample_ticker_data() -> list[dict]:
    """
    Sample ticker data for testing
    """
    return [
        {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
        {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
        {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financial"},
    ]


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_model_prediction():
    """
    Mock ML model prediction
    """
    return {"ticker": "AAPL", "prediction": 0.75, "confidence": 0.85, "expected_return": 0.08}


@pytest.fixture
def mock_brokerage_response():
    """
    Mock brokerage API response
    """
    return {
        "order_id": "test-order-123",
        "status": "filled",
        "filled_price": 150.25,
        "filled_qty": 10,
    }


# ============================================================================
# Pytest Hooks
# ============================================================================


def pytest_configure(config):
    """
    Configure pytest with custom settings
    """
    # Set environment variables for testing
    os.environ["TESTING"] = "1"
    os.environ["LOG_LEVEL"] = "WARNING"  # Reduce noise during tests


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers automatically
    """
    for item in items:
        # Add marker based on test file location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Add marker based on test file name
        if "test_api" in item.nodeid or "test_auth" in item.nodeid:
            item.add_marker(pytest.mark.api)
        elif "test_ml" in item.nodeid or "test_xgboost" in item.nodeid:
            item.add_marker(pytest.mark.ml)
        elif "test_rl" in item.nodeid or "test_ppo" in item.nodeid:
            item.add_marker(pytest.mark.rl)


# ============================================================================
# Helper Functions
# ============================================================================


def assert_valid_datetime(dt_string: str):
    """
    Helper to assert a string is a valid ISO datetime
    """
    from datetime import datetime

    try:
        datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"Invalid datetime format: {dt_string}")


def assert_valid_uuid(uuid_string: str):
    """
    Helper to assert a string is a valid UUID
    """
    import uuid

    try:
        uuid.UUID(uuid_string)
    except ValueError:
        pytest.fail(f"Invalid UUID format: {uuid_string}")
