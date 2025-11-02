# Phase 2: Testing & CI/CD - Implementation Plan

**Timeline**: 8 weeks (can be parallelized with other work)
**Priority**: BLOCKING for commercial release
**Current Coverage**: ~2-3%
**Target Coverage**: 80%+

---

## 🎯 GOALS

1. **80%+ test coverage** across all critical code paths
2. **GitHub Actions CI/CD** - automated testing on every commit
3. **Integration tests** - validate end-to-end workflows
4. **Test documentation** - make testing easy for team
5. **Confidence to deploy** - catch regressions before production

---

## 📊 CURRENT STATE

**Existing Tests** (only 3 files):
- `ml_models/test_db_connection.py` - Basic DB check
- `ml_models/test_predictions.py` - Model prediction test
- `test_rl_integration.py` - RL integration test

**Coverage**: ~2-3% (need 77-78% more!)

**No CI/CD**: Manual testing only, no automation

---

## 🗓️ 8-WEEK ROADMAP

### Week 1-2: Setup & Infrastructure
**Goal**: Testing framework and structure

**Tasks**:
1. Install pytest and plugins
2. Create test directory structure
3. Configure pytest settings
4. Set up test database
5. Create test fixtures and factories
6. Set up coverage reporting

**Deliverables**:
- `pytest.ini` configuration
- `tests/` directory structure
- `conftest.py` with fixtures
- `requirements-test.txt`
- Initial coverage baseline

---

### Week 3-4: Backend API Tests (Target: 80% API coverage)
**Goal**: Comprehensive API endpoint testing

**Priority Tests**:
1. **Authentication** (`tests/api/test_auth.py`)
   - Login endpoint
   - Password verification
   - JWT token generation
   - Token expiration

2. **Clients API** (`tests/api/test_clients.py`)
   - CRUD operations
   - Validation
   - Edge cases

3. **Portfolio API** (`tests/api/test_portfolio.py`)
   - Portfolio health
   - Rebalancing
   - Position management

4. **ML Models API** (`tests/api/test_ml_models.py`)
   - Model listing
   - Training status
   - Predictions

5. **Trading API** (`tests/api/test_trading.py`)
   - Order placement
   - Order status
   - Trade history

**Deliverables**:
- 50+ API endpoint tests
- ~1,000 lines of test code
- API coverage: 80%+

---

### Week 5-6: ML/RL Tests (Target: 60% ML/RL coverage)
**Goal**: Validate ML and RL pipelines

**Priority Tests**:
1. **XGBoost Training** (`tests/ml/test_xgboost_training.py`)
   - Feature loading
   - Model training
   - Model evaluation
   - Metadata generation

2. **Feature Engineering** (`tests/ml/test_feature_engineering.py`)
   - Feature calculation
   - Data validation
   - Missing value handling

3. **RL Agent** (`tests/rl/test_ppo_agent.py`)
   - Environment setup
   - Reward calculation
   - Action selection
   - Training convergence

4. **Portfolio Manager** (`tests/portfolio/test_portfolio_manager.py`)
   - Drift calculation
   - Rebalancing logic
   - Risk management

**Deliverables**:
- 40+ ML/RL tests
- Mock data generators
- ML/RL coverage: 60%+

---

### Week 7: Integration Tests (Target: 20 integration tests)
**Goal**: End-to-end workflow validation

**Priority Integration Tests**:
1. **Complete Trading Flow** (`tests/integration/test_trading_flow.py`)
   - Client login → Generate signals → Place orders → Execute

2. **ML Pipeline** (`tests/integration/test_ml_pipeline.py`)
   - Data fetch → Feature engineering → Training → Evaluation

3. **EOD Pipeline** (`tests/integration/test_eod_pipeline.py`)
   - Data update → View refresh → Model retrain

4. **Brokerage Integration** (`tests/integration/test_brokerage.py`)
   - OAuth flow → Account sync → Order execution

**Deliverables**:
- 20+ integration tests
- Test data seeders
- Integration test suite

---

### Week 8: CI/CD & Documentation
**Goal**: Automate testing and document

**Tasks**:
1. **GitHub Actions Setup**
   - `.github/workflows/tests.yml`
   - Run on every PR
   - Run on main branch push
   - Fail if coverage drops

2. **Pre-commit Hooks**
   - Run tests before commit
   - Check code formatting
   - Lint checks

3. **Test Documentation**
   - How to run tests
   - How to write tests
   - Test best practices

4. **Coverage Reporting**
   - Codecov integration
   - Coverage badges
   - Coverage reports

**Deliverables**:
- GitHub Actions pipeline
- Pre-commit configuration
- Testing documentation
- Automated coverage reports

---

## 📁 TEST DIRECTORY STRUCTURE

```
tests/
├── conftest.py                 # Shared fixtures
├── pytest.ini                  # Pytest configuration
├── requirements-test.txt       # Test dependencies
│
├── unit/                       # Unit tests (fast, isolated)
│   ├── api/
│   │   ├── test_auth.py       # Authentication tests
│   │   ├── test_clients.py    # Client CRUD tests
│   │   ├── test_portfolio.py  # Portfolio API tests
│   │   ├── test_ml_models.py  # ML models API tests
│   │   └── test_trading.py    # Trading API tests
│   │
│   ├── ml/
│   │   ├── test_xgboost.py    # XGBoost training tests
│   │   ├── test_features.py   # Feature engineering tests
│   │   └── test_evaluation.py # Model evaluation tests
│   │
│   ├── rl/
│   │   ├── test_ppo_agent.py  # PPO agent tests
│   │   ├── test_environment.py # Gym environment tests
│   │   └── test_rewards.py    # Reward function tests
│   │
│   └── portfolio/
│       ├── test_manager.py    # Portfolio manager tests
│       └── test_analyzer.py   # Portfolio analyzer tests
│
├── integration/                # Integration tests (slower, full stack)
│   ├── test_trading_flow.py   # Complete trading workflow
│   ├── test_ml_pipeline.py    # ML training pipeline
│   ├── test_eod_pipeline.py   # EOD data pipeline
│   └── test_brokerage.py      # Brokerage integration
│
├── fixtures/                   # Test data
│   ├── sample_data.py         # Sample market data
│   ├── model_fixtures.py      # Sample models
│   └── client_fixtures.py     # Sample clients
│
└── mocks/                      # Mock objects
    ├── mock_database.py       # Database mocks
    ├── mock_brokerage.py      # Brokerage API mocks
    └── mock_models.py         # ML model mocks
```

---

## 🛠️ TOOLS & DEPENDENCIES

### Core Testing
```txt
pytest==8.0.0                  # Testing framework
pytest-asyncio==0.23.0         # Async test support
pytest-cov==4.1.0              # Coverage reporting
pytest-mock==3.12.0            # Mocking utilities
pytest-xdist==3.5.0            # Parallel test execution
```

### API Testing
```txt
httpx==0.26.0                  # Async HTTP client
faker==22.0.0                  # Fake data generation
factory-boy==3.3.0             # Test factories
```

### Database Testing
```txt
pytest-postgresql==5.0.0       # PostgreSQL fixtures
sqlalchemy-utils==0.41.1       # DB testing utilities
```

### Coverage & Reporting
```txt
coverage[toml]==7.4.0          # Coverage measurement
pytest-html==4.1.1             # HTML test reports
```

---

## 📝 EXAMPLE TEST FILES

### Example 1: API Test (`tests/unit/api/test_auth.py`)

```python
"""
Authentication API Tests

Tests login, JWT generation, password verification
"""
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)


def test_login_success():
    """Test successful login with correct credentials"""
    response = client.post(
        "/api/auth/login",
        auth=("admin@acis-ai.com", "admin123")
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == "admin@acis-ai.com"


def test_login_invalid_password():
    """Test login fails with wrong password"""
    response = client.post(
        "/api/auth/login",
        auth=("admin@acis-ai.com", "wrongpassword")
    )

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_invalid_email():
    """Test login fails with wrong email"""
    response = client.post(
        "/api/auth/login",
        auth=("wrong@email.com", "admin123")
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_jwt_token_expiration():
    """Test JWT token expires after configured time"""
    # Login and get token
    response = client.post(
        "/api/auth/login",
        auth=("admin@acis-ai.com", "admin123")
    )
    token = response.json()["access_token"]

    # Use token immediately (should work)
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    # TODO: Test expiration (mock time)
```

### Example 2: ML Test (`tests/unit/ml/test_xgboost.py`)

```python
"""
XGBoost Training Tests

Tests model training, evaluation, and saving
"""
import pytest
import pandas as pd
import numpy as np
from ml_models.train_xgboost import GrowthStrategy


@pytest.fixture
def sample_training_data():
    """Generate sample training data"""
    np.random.seed(42)
    n_samples = 1000

    data = {
        'ticker': ['AAPL'] * n_samples,
        'date': pd.date_range('2020-01-01', periods=n_samples),
        'return_1d': np.random.randn(n_samples),
        'return_5d': np.random.randn(n_samples),
        'volatility_21d': np.abs(np.random.randn(n_samples)),
        'volume_ratio': np.abs(np.random.randn(n_samples)),
        'market_cap': np.random.uniform(1e9, 100e9, n_samples)
    }

    return pd.DataFrame(data)


def test_strategy_initialization():
    """Test strategy initializes with correct parameters"""
    strategy = GrowthStrategy(
        market_cap="mid",
        start_date="2020-01-01",
        end_date="2024-12-31"
    )

    assert strategy.market_cap == "mid"
    assert strategy.start_date == "2020-01-01"
    assert strategy.end_date == "2024-12-31"


def test_feature_engineering(sample_training_data):
    """Test feature engineering produces correct features"""
    strategy = GrowthStrategy()

    df_engineered = strategy.engineer_features(sample_training_data)

    # Check features were added
    assert len(df_engineered.columns) >= len(sample_training_data.columns)

    # Check no NaN values introduced
    assert df_engineered.isnull().sum().sum() == 0


def test_training_data_preparation(sample_training_data):
    """Test training data is prepared correctly"""
    strategy = GrowthStrategy()

    X, y = strategy.prepare_training_data(sample_training_data)

    # Check shapes
    assert len(X) == len(y)
    assert len(X) > 0

    # Check label distribution
    assert y.min() in [0, 1]
    assert y.max() in [0, 1]


@pytest.mark.slow
def test_model_training(sample_training_data, tmp_path):
    """Test model can be trained and saved"""
    strategy = GrowthStrategy()

    # Prepare data
    X, y = strategy.prepare_training_data(sample_training_data)

    # Train model
    params = strategy.get_model_params()
    model = strategy.train_model(X, y, params)

    # Check model exists
    assert model is not None

    # Test predictions
    predictions = model.predict_proba(X)
    assert predictions.shape[0] == len(X)
    assert predictions.min() >= 0
    assert predictions.max() <= 1
```

### Example 3: Integration Test (`tests/integration/test_trading_flow.py`)

```python
"""
Complete Trading Flow Integration Test

Tests entire workflow from login to trade execution
"""
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app
from sqlalchemy import create_engine

client = TestClient(app)


@pytest.fixture(scope="module")
def test_database():
    """Set up test database"""
    engine = create_engine("postgresql://postgres@localhost:5432/acis-ai-test")
    # Set up tables
    # ...
    yield engine
    # Teardown
    engine.dispose()


@pytest.mark.integration
def test_complete_trading_workflow(test_database):
    """Test complete trading flow end-to-end"""

    # Step 1: Login
    response = client.post(
        "/api/auth/login",
        auth=("admin@acis-ai.com", "admin123")
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Create test client
    response = client.post(
        "/api/clients/",
        json={
            "first_name": "Test",
            "last_name": "Client",
            "email": "test@example.com",
            "risk_tolerance": "moderate"
        },
        headers=headers
    )
    assert response.status_code == 201
    client_id = response.json()["client_id"]

    # Step 3: Generate portfolio recommendations
    response = client.post(
        f"/api/portfolio/generate-signals",
        json={"client_id": client_id, "strategy": "growth"},
        headers=headers
    )
    assert response.status_code == 200
    signals = response.json()

    # Step 4: Place orders
    for signal in signals["buy_signals"][:5]:  # Place 5 orders
        response = client.post(
            "/api/trading/place-order",
            json={
                "client_id": client_id,
                "ticker": signal["ticker"],
                "quantity": signal["quantity"],
                "order_type": "market"
            },
            headers=headers
        )
        assert response.status_code == 200

    # Step 5: Verify positions were created
    response = client.get(
        f"/api/portfolio/positions/{client_id}",
        headers=headers
    )
    assert response.status_code == 200
    positions = response.json()
    assert len(positions) == 5
```

---

## 🚀 QUICK START

### Week 1 Tasks (Do These First):

```bash
# 1. Install test dependencies
pip install pytest pytest-cov pytest-asyncio httpx faker

# 2. Create test directory structure
mkdir -p tests/{unit/{api,ml,rl,portfolio},integration,fixtures,mocks}

# 3. Create pytest.ini
cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --cov=backend
    --cov=ml_models
    --cov=rl_trading
    --cov=portfolio
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
EOF

# 4. Create conftest.py with fixtures
cat > tests/conftest.py << 'EOF'
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)

@pytest.fixture
def auth_headers(client):
    """Get authentication headers"""
    response = client.post(
        "/api/auth/login",
        auth=("admin@acis-ai.com", "admin123")
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
EOF

# 5. Run first test
pytest tests/ -v
```

---

## 📈 COVERAGE TARGETS

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| API Routes | 5% | 80% | HIGH |
| Auth System | 0% | 95% | CRITICAL |
| ML Training | 10% | 70% | HIGH |
| RL Agent | 5% | 60% | MEDIUM |
| Portfolio Manager | 0% | 70% | HIGH |
| Trading Execution | 0% | 85% | CRITICAL |
| Database | 20% | 60% | MEDIUM |
| **Overall** | **2-3%** | **80%+** | **CRITICAL** |

---

## 🎯 SUCCESS CRITERIA

Phase 2 is complete when:

- [ ] 80%+ test coverage achieved
- [ ] All critical paths have tests
- [ ] GitHub Actions CI/CD running
- [ ] Tests pass on every commit
- [ ] Integration tests cover main workflows
- [ ] Test documentation complete
- [ ] Team can run tests locally easily
- [ ] Coverage reports generated automatically

---

## 💰 EFFORT ESTIMATE

**Total Effort**: ~280-320 hours (7-8 weeks for 1 person)

Breakdown:
- Setup & Infrastructure: 40 hours
- API Tests: 80 hours
- ML/RL Tests: 60 hours
- Integration Tests: 40 hours
- CI/CD Setup: 20 hours
- Documentation: 20 hours
- Buffer: 40 hours

**Cost** (at $100/hour): $28K-32K

**Can be Parallelized**: Yes, split API/ML/RL tests across team members

---

## 🆘 GETTING HELP

If this feels overwhelming, consider:

1. **Hire QA Engineer**: Someone experienced in pytest can do this in 6-8 weeks
2. **Start Small**: Focus on critical paths first (auth, trading, portfolio)
3. **Use AI Tools**: GitHub Copilot can help write tests faster
4. **Test as You Go**: Add tests for new features from now on

---

## 📚 RESOURCES

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Test-Driven Development](https://testdriven.io/)
- [GitHub Actions CI/CD](https://docs.github.com/en/actions)

---

**Ready to start?** I can help you implement Week 1 tasks right now!
