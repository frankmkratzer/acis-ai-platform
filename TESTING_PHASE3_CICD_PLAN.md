# Phase 3: GitHub Actions CI/CD Setup

**Objective**: Automate testing with GitHub Actions to run tests on every commit and pull request.

**Timeline**: 1-2 days
**Prerequisites**: Phase 2 Complete ✅

---

## 🎯 Goals

1. Set up GitHub Actions workflow for automated testing
2. Run pytest on every push and pull request
3. Generate and publish coverage reports
4. Add test result badges to README
5. Configure branch protection rules
6. Set up notifications for test failures

---

## 📋 Tasks Breakdown

### Task 1: Create GitHub Actions Workflow
**File**: `.github/workflows/tests.yml`

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: acis-ai-test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python 3.12
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio

    - name: Set up test database
      env:
        PGPASSWORD: test_password
      run: |
        psql -h localhost -U postgres -d acis-ai-test -f database/schema.sql
        psql -h localhost -U postgres -d acis-ai-test -f database/create_rl_trading_tables.sql
        psql -h localhost -U postgres -d acis-ai-test -f database/fix_brokerage_id_autoincrement.sql

    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:test_password@localhost:5432/acis-ai-test
      run: |
        pytest tests/unit/api/ -v --cov=backend/api --cov-report=xml --cov-report=html

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

    - name: Archive coverage results
      uses: actions/upload-artifact@v3
      with:
        name: coverage-report
        path: htmlcov/
```

**Estimated Time**: 2-3 hours

---

### Task 2: Create Test Configuration for CI
**File**: `.github/pytest-ci.ini`

```ini
[pytest]
testpaths = tests/unit
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=backend/api
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=0
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
asyncio_mode = auto
```

**Estimated Time**: 30 minutes

---

### Task 3: Add Coverage Badge to README
**File**: `README.md`

Add badges at the top:

```markdown
# ACIS AI Platform

[![Tests](https://github.com/username/acis-ai-platform/actions/workflows/tests.yml/badge.svg)](https://github.com/username/acis-ai-platform/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/username/acis-ai-platform/branch/main/graph/badge.svg)](https://codecov.io/gh/username/acis-ai-platform)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
```

**Estimated Time**: 15 minutes

---

### Task 4: Configure Branch Protection Rules

**Settings to Enable**:
1. Require pull request reviews before merging
2. Require status checks to pass before merging
   - Required check: `test (ubuntu-latest)`
3. Require branches to be up to date before merging
4. Include administrators in restrictions

**Steps**:
1. Go to GitHub repo Settings → Branches
2. Add rule for `main` branch
3. Enable above settings
4. Save changes

**Estimated Time**: 15 minutes

---

### Task 5: Create Pre-commit Hooks
**File**: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100', '--ignore=E203,W503']

  - repo: local
    hooks:
      - id: pytest-fast
        name: pytest-fast
        entry: pytest tests/unit/api/test_auth.py -v
        language: system
        pass_filenames: false
        always_run: true
```

**Installation**:
```bash
pip install pre-commit
pre-commit install
```

**Estimated Time**: 1 hour

---

### Task 6: Add Test Job Matrix (Optional)

Test against multiple Python versions and OS:

```yaml
strategy:
  matrix:
    python-version: ['3.11', '3.12']
    os: [ubuntu-latest, macos-latest]
```

**Estimated Time**: 30 minutes

---

### Task 7: Create Deployment Workflow (Future)
**File**: `.github/workflows/deploy.yml`

```yaml
name: Deploy

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        run: echo "Deploy steps here"
```

**Estimated Time**: 1 hour (when needed)

---

## ✅ Verification Checklist

After completing Phase 3, verify:

- [ ] GitHub Actions workflow runs on every push
- [ ] Tests pass in CI environment
- [ ] Coverage reports are generated
- [ ] Codecov integration works
- [ ] Branch protection prevents merging failing PRs
- [ ] Pre-commit hooks catch issues locally
- [ ] Badges display correctly in README
- [ ] Test artifacts are uploaded
- [ ] Notifications work for failures

---

## 🚨 Common Issues & Solutions

### Issue 1: Database Connection Fails in CI
**Solution**: Ensure PostgreSQL service is configured correctly with health checks

### Issue 2: Tests Pass Locally, Fail in CI
**Solution**: Check environment variables and database setup scripts

### Issue 3: Coverage Report Not Generated
**Solution**: Verify pytest-cov is installed and --cov flag is used

### Issue 4: Slow CI Runs
**Solution**:
- Use dependency caching
- Run only changed tests on PRs
- Use test parallelization with pytest-xdist

---

## 📊 Success Metrics

Phase 3 will be considered complete when:

1. ✅ CI workflow runs successfully on main branch
2. ✅ All 275 tests pass in CI environment
3. ✅ Coverage reports are generated and uploaded
4. ✅ Branch protection rules enforce test passing
5. ✅ Pre-commit hooks are installed and working
6. ✅ Documentation updated with CI/CD information

---

## 🔗 Next Phase

After completing Phase 3, proceed to:
**Phase 4: Integration Tests** - End-to-end workflow testing

---

## 📚 References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [Codecov Documentation](https://docs.codecov.com/)
- [Pre-commit Documentation](https://pre-commit.com/)
