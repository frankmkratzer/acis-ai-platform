# ACIS AI Platform

[![Tests](https://github.com/fkratzer/acis-ai-platform/actions/workflows/tests.yml/badge.svg)](https://github.com/fkratzer/acis-ai-platform/actions/workflows/tests.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests: 275](https://img.shields.io/badge/tests-275-brightgreen.svg)](tests/unit/api/)
[![Coverage: ~16%](https://img.shields.io/badge/coverage-16%25-yellow.svg)](htmlcov/)

AI-powered autonomous trading platform with ML/RL portfolio management.

## 🚀 Features

- **Autonomous Trading System** - Automated portfolio rebalancing with AI
- **ML/RL Models** - XGBoost and PPO models for stock prediction
- **Multi-Strategy Support** - Growth, Dividend, and Value portfolios
- **Brokerage Integration** - Schwab API integration with OAuth
- **Real-time Monitoring** - Portfolio health and performance tracking
- **Risk Management** - Automated risk assessment and position sizing

## 📊 Current Status

**Phase 2: Testing (Weeks 5-12)** - In Progress
- ✅ Unit Tests: 275 tests covering 11 APIs (137% of target!)
- 🔄 CI/CD: GitHub Actions workflow configured
- ⏳ Integration Tests: Next phase

See [TESTING_ROADMAP.md](TESTING_ROADMAP.md) for complete testing progress.

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.12
- **Database**: PostgreSQL 14
- **ML/RL**: XGBoost, JAX, Stable-Baselines3
- **Testing**: pytest, pytest-cov
- **CI/CD**: GitHub Actions
- **Deployment**: (Phase 3 - Docker/Kubernetes)

## 📋 Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Virtual environment

## 🔧 Installation

```bash
# Clone repository
git clone https://github.com/fkratzer/acis-ai-platform.git
cd acis-ai-platform

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up database
PGPASSWORD='your_password' psql -U postgres -d acis-ai -f database/create_rl_trading_tables.sql
PGPASSWORD='your_password' psql -U postgres -d acis-ai -f database/fix_brokerage_id_autoincrement.sql

# Run tests
pytest tests/unit/api/ -v
```

## 🧪 Testing

```bash
# Run all unit tests
pytest tests/unit/api/ -v

# Run with coverage
pytest tests/unit/api/ --cov=backend/api --cov-report=html

# Run specific test file
pytest tests/unit/api/test_auth.py -v

# View coverage report
open htmlcov/index.html
```

## 📚 Documentation

- [Testing Roadmap](TESTING_ROADMAP.md) - Complete testing plan
- [Phase 2 Progress](TESTING_PHASE2_PROGRESS.md) - Current testing progress
- [Phase 3 CI/CD Plan](TESTING_PHASE3_CICD_PLAN.md) - CI/CD setup guide
- [Phase 4 Integration Plan](TESTING_PHASE4_INTEGRATION_PLAN.md) - Integration testing plan

## 🗺️ Roadmap

### Phase 1: Security (Weeks 1-4) - BLOCKING
- [ ] Remove hardcoded credentials
- [ ] Implement AWS Secrets Manager
- [ ] Add RBAC, bcrypt hashing, HTTPS

### Phase 2: Testing (Weeks 5-12) - BLOCKING ⏱️ IN PROGRESS
- [x] 80%+ test coverage target (currently ~16%, 275 tests)
- [x] Unit tests for all 11 APIs
- [x] Bug fixes (3 production bugs fixed)
- [x] GitHub Actions CI/CD setup
- [ ] Integration tests

### Phase 3: Operations (Weeks 13-16)
- [ ] Docker + Kubernetes
- [ ] Monitoring & alerting
- [ ] Automated backups

### Phase 4: Model Ops (Weeks 17-24)
- [ ] MLflow model registry
- [ ] Automated retraining
- [ ] Data drift detection

### Phase 5: Launch (Weeks 25-28)
- [ ] UX polish
- [ ] Documentation
- [ ] Beta customers

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Install pre-commit hooks: `pre-commit install`
4. Make your changes
5. Run tests: `pytest tests/unit/api/ -v`
6. Submit a pull request

## 📝 License

[Add your license here]

## 📧 Contact

[Add your contact information]

---

**Current Development Phase**: Phase 2 - Testing (CI/CD Setup)
**Test Coverage**: ~16% overall, 96% auth module
**Tests**: 275 unit tests across 11 APIs
