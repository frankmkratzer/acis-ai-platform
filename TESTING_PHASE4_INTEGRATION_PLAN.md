# Phase 4: Integration Tests

**Objective**: Create end-to-end integration tests that validate complete workflows across multiple APIs and services.

**Timeline**: 3-4 days
**Prerequisites**: Phase 2 Complete ✅, Phase 3 Complete (optional but recommended)

---

## 🎯 Goals

1. Test complete user workflows end-to-end
2. Validate API interactions and data flow
3. Test database transactions and rollbacks
4. Mock external services (Schwab API, market data)
5. Test authentication and authorization flows
6. Validate data consistency across services
7. Test error handling and recovery

**Target**: 50-75 integration tests covering critical workflows

---

## 📋 Test Categories

### Category 1: Client Onboarding Workflow
**File**: `tests/integration/test_client_onboarding.py`

**Workflow**:
```
1. Create client account
2. Link brokerage account
3. Set up portfolio preferences
4. Initialize trading strategy
5. Verify client data across all endpoints
```

**Tests** (8-10):
- Complete onboarding flow
- Onboarding with missing data
- Duplicate client prevention
- Account linking validation
- Portfolio initialization
- OAuth flow integration

**Estimated Time**: 4-5 hours

---

### Category 2: Trading Workflow
**File**: `tests/integration/test_trading_flow.py`

**Workflow**:
```
1. Authenticate client
2. Get portfolio recommendations
3. Generate rebalance orders
4. Approve orders
5. Execute trades
6. Verify execution results
7. Update portfolio state
```

**Tests** (10-12):
- Complete trading cycle
- RL-generated rebalancing
- ML-recommended positions
- Order approval workflow
- Dry-run execution
- Live execution (paper trading)
- Trade execution failure handling
- Portfolio state updates

**Estimated Time**: 6-8 hours

---

### Category 3: OAuth & External API Integration
**File**: `tests/integration/test_schwab_integration.py`

**Workflow**:
```
1. Start ngrok tunnel
2. Initiate OAuth flow
3. Handle callback
4. Store tokens
5. Refresh tokens
6. Make authenticated API calls
7. Handle token expiration
```

**Tests** (6-8):
- Complete OAuth flow (mocked)
- Token refresh cycle
- Authenticated API calls
- Token expiration handling
- Multiple account management
- Concurrent token requests

**Mocking Strategy**:
```python
@pytest.fixture
def mock_schwab_api():
    with responses.RequestsMock() as rsps:
        # Mock OAuth token endpoint
        rsps.add(
            responses.POST,
            "https://api.schwabapi.com/v1/oauth/token",
            json={"access_token": "mock_token", "expires_in": 3600},
            status=200
        )
        # Mock account endpoint
        rsps.add(
            responses.GET,
            "https://api.schwabapi.com/trader/v1/accounts",
            json=[{"accountId": "123", "balance": 100000}],
            status=200
        )
        yield rsps
```

**Estimated Time**: 5-6 hours

---

### Category 4: ML/RL Training Pipeline
**File**: `tests/integration/test_ml_rl_pipeline.py`

**Workflow**:
```
1. Trigger training job
2. Monitor training status
3. Evaluate model performance
4. Deploy model to production
5. Generate predictions
6. Use predictions in trading
```

**Tests** (8-10):
- ML training workflow (mocked)
- RL training workflow (mocked)
- Model evaluation
- Model versioning
- Prediction generation
- Model rollback
- Training failure handling

**Estimated Time**: 6-7 hours

---

### Category 5: Autonomous Trading System
**File**: `tests/integration/test_autonomous_trading.py`

**Workflow**:
```
1. Check market regime
2. Select strategy
3. Generate portfolio
4. Create rebalance orders
5. Execute rebalance
6. Monitor performance
7. Adjust strategy
```

**Tests** (6-8):
- Daily rebalancing cycle
- Strategy switching
- Market regime detection
- Performance tracking
- Risk management
- Manual intervention
- System health monitoring

**Estimated Time**: 5-6 hours

---

### Category 6: Data Pipeline Integration
**File**: `tests/integration/test_data_pipeline.py`

**Workflow**:
```
1. Fetch market data
2. Process fundamentals
3. Calculate indicators
4. Store in database
5. Trigger ML feature engineering
6. Validate data quality
```

**Tests** (5-7):
- Daily data pipeline
- Incremental updates
- Data validation
- Error recovery
- Backfill operations

**Estimated Time**: 4-5 hours

---

### Category 7: Database Transactions
**File**: `tests/integration/test_database_transactions.py`

**Tests** (8-10):
- Transaction rollback on error
- Concurrent access handling
- Cascade delete behavior
- Foreign key constraints
- Data integrity validation
- Lock handling
- Connection pooling

**Estimated Time**: 4-5 hours

---

## 🛠️ Test Infrastructure

### Setup Test Database
**File**: `tests/integration/conftest.py`

```python
import pytest
from sqlalchemy import create_engine
from backend.api.database.connection import Base

@pytest.fixture(scope="session")
def integration_db():
    """Create integration test database"""
    engine = create_engine("postgresql://postgres:password@localhost/acis-ai-integration-test")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_transaction(integration_db):
    """Provide transaction that rolls back after test"""
    connection = integration_db.connect()
    transaction = connection.begin()
    yield connection
    transaction.rollback()
    connection.close()
```

**Estimated Time**: 2 hours

---

### Mock External Services
**File**: `tests/integration/mocks/schwab_mock.py`

```python
class MockSchwabAPI:
    """Mock Schwab API for integration testing"""

    def __init__(self):
        self.accounts = {}
        self.positions = {}
        self.orders = []

    def get_accounts(self, access_token):
        return [{"accountId": "12345", "balance": 100000}]

    def place_order(self, account_id, order_data):
        order_id = f"ORDER_{len(self.orders)}"
        self.orders.append({"id": order_id, **order_data})
        return {"orderId": order_id, "status": "PENDING"}

    def get_order_status(self, order_id):
        for order in self.orders:
            if order["id"] == order_id:
                return {"status": "FILLED", "filledPrice": 150.00}
        return {"status": "NOT_FOUND"}
```

**Estimated Time**: 3 hours

---

### Test Data Factories
**File**: `tests/integration/factories.py`

```python
from faker import Faker
import factory

fake = Faker()

class ClientFactory(factory.Factory):
    class Meta:
        model = dict

    client_id = factory.Sequence(lambda n: n)
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')
    is_active = True

class AccountFactory(factory.Factory):
    class Meta:
        model = dict

    account_number = factory.Sequence(lambda n: f"ACC{n:06d}")
    account_hash = factory.Faker('sha256')
    account_type = "individual"
    brokerage_id = 1
```

**Estimated Time**: 2 hours

---

## 📊 Integration Test Structure

```
tests/
├── integration/
│   ├── conftest.py              # Integration test fixtures
│   ├── factories.py             # Test data factories
│   ├── mocks/
│   │   ├── __init__.py
│   │   ├── schwab_mock.py       # Mock Schwab API
│   │   ├── market_data_mock.py  # Mock market data
│   │   └── ml_model_mock.py     # Mock ML models
│   ├── test_client_onboarding.py
│   ├── test_trading_flow.py
│   ├── test_schwab_integration.py
│   ├── test_ml_rl_pipeline.py
│   ├── test_autonomous_trading.py
│   ├── test_data_pipeline.py
│   └── test_database_transactions.py
└── unit/
    └── api/
        └── ... (existing unit tests)
```

---

## 🚀 Example Integration Test

```python
"""
Integration Test Example: Complete Trading Flow
"""
import pytest
from tests.integration.mocks.schwab_mock import MockSchwabAPI
from tests.integration.factories import ClientFactory, AccountFactory

class TestCompleteTradingFlow:
    """Test end-to-end trading workflow"""

    @pytest.fixture
    def setup_client_and_account(self, test_client, db_transaction):
        """Set up client with linked brokerage account"""
        # Create client
        client_data = ClientFactory.build()
        response = test_client.post("/api/clients/", json=client_data)
        assert response.status_code == 200
        client = response.json()

        # Link brokerage account
        account_data = AccountFactory.build(client_id=client["client_id"])
        response = test_client.post("/api/brokerages/accounts", json=account_data)
        assert response.status_code == 200
        account = response.json()

        return client, account

    def test_complete_trading_cycle(
        self,
        test_client,
        setup_client_and_account,
        mock_schwab_api
    ):
        """Test complete workflow: recommendation → order → execution → verification"""
        client, account = setup_client_and_account

        # Step 1: Get ML recommendations
        response = test_client.get(f"/api/ml-models/predict/{client['client_id']}")
        assert response.status_code == 200
        predictions = response.json()
        assert len(predictions) > 0

        # Step 2: Generate rebalancing orders
        rebalance_request = {
            "client_id": client["client_id"],
            "account_hash": account["account_hash"],
            "portfolio_id": 1,
            "max_positions": 10,
            "require_approval": True
        }
        response = test_client.post("/api/rl/trading/rebalance", json=rebalance_request)
        assert response.status_code == 200
        batch = response.json()
        batch_id = batch["batch_id"]

        # Step 3: Verify batch was created
        response = test_client.get(f"/api/rl/trading/batches/{batch_id}")
        assert response.status_code == 200
        assert batch["status"] == "pending_approval"

        # Step 4: Approve batch
        response = test_client.post(f"/api/rl/trading/batches/{batch_id}/approve")
        assert response.status_code == 200

        # Step 5: Execute batch (dry run)
        execute_request = {"batch_id": batch_id, "dry_run": True}
        response = test_client.post("/api/rl/trading/execute-batch", json=execute_request)
        assert response.status_code == 200
        result = response.json()

        # Step 6: Verify execution results
        assert "trades_executed" in result
        assert result["success"] is True

        # Step 7: Check portfolio updated
        response = test_client.get(f"/api/portfolio-health/{client['client_id']}")
        assert response.status_code == 200
        portfolio = response.json()
        assert portfolio["total_value"] > 0
```

---

## ✅ Verification Checklist

After completing Phase 4, verify:

- [ ] All integration tests pass
- [ ] Complete workflows tested end-to-end
- [ ] External services properly mocked
- [ ] Database transactions work correctly
- [ ] Data consistency validated
- [ ] Error scenarios covered
- [ ] Test data factories working
- [ ] Integration test documentation complete

---

## 📊 Success Metrics

Phase 4 will be considered complete when:

1. ✅ 50-75 integration tests created
2. ✅ All critical workflows covered
3. ✅ 100% of integration tests passing
4. ✅ External services properly mocked
5. ✅ Database transaction tests working
6. ✅ Test infrastructure robust and reusable

---

## 🔗 Dependencies

**Required Libraries**:
```bash
pip install pytest-asyncio
pip install responses  # For HTTP mocking
pip install factory-boy  # For test data factories
pip install faker  # For fake data generation
pip install pytest-mock  # For advanced mocking
```

---

## 📚 References

- [pytest Integration Testing Guide](https://docs.pytest.org/en/stable/how-to/integration.html)
- [responses Library Documentation](https://github.com/getsentry/responses)
- [factory_boy Documentation](https://factoryboy.readthedocs.io/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/core/connections.html#testing)

---

## 🎯 Estimated Total Time

- Test Infrastructure: 7 hours
- Category 1-7 Tests: 34-44 hours
- Documentation: 3 hours
- **Total: 44-54 hours (5.5-6.5 days)**

Split across 3-4 days with focused effort.
