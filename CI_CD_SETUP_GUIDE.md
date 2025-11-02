# CI/CD Setup Guide - Quick Start

**Status**: ✅ Configuration Complete - Ready to Commit

---

## 📋 What's Been Configured

### GitHub Actions
- **File**: `.github/workflows/tests.yml`
- **Features**: PostgreSQL service, pytest with coverage, Codecov integration
- **Triggers**: Push/PR to `main` and `develop` branches

### Pre-commit Hooks
- **File**: `.pre-commit-config.yaml`
- **Tools**: black, flake8, isort, basic quality checks
- **Status**: Installed locally with `pre-commit install`

### Documentation
- **File**: `README.md`
- **Content**: Project overview, badges, 5-Phase Roadmap, installation instructions

### Configuration
- **File**: `.gitignore`
- **Added**: `.pre-commit-cache/` exclusion

---

## 🚀 Step 1: Commit CI/CD Configuration

```bash
# Add CI/CD files
git add .github/workflows/tests.yml
git add .pre-commit-config.yaml
git add README.md
git add .gitignore

# Add documentation
git add TESTING_PHASE2_CICD_COMPLETE.md
git add TESTING_PHASE2_COMPLETE.md
git add TESTING_ROADMAP.md
git add TESTING_PHASE3_CICD_PLAN.md
git add TESTING_PHASE4_INTEGRATION_PLAN.md

# Commit with descriptive message
git commit -m "$(cat <<'EOF'
Add GitHub Actions CI/CD and pre-commit hooks

- Configure GitHub Actions workflow with PostgreSQL service
- Add pre-commit hooks (black, flake8, isort)
- Create README with CI/CD badges and project overview
- Update .gitignore for test artifacts
- Add Phase 2 CI/CD completion documentation

This completes the CI/CD portion of Phase 2: Testing.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# Push to GitHub
git push origin main
```

---

## 🔑 Step 2: Configure Codecov (Required for Coverage Reporting)

### A. Sign Up for Codecov

1. Go to https://codecov.io/
2. Click "Sign up with GitHub"
3. Authorize Codecov to access your repositories

### B. Add Repository

1. In Codecov dashboard, click "Add Repository"
2. Find `acis-ai-platform` and click "Setup repo"
3. Copy the `CODECOV_TOKEN` provided

### C. Add Token to GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `CODECOV_TOKEN`
5. Value: Paste the token from Codecov
6. Click **Add secret**

---

## 🛡️ Step 3: Enable Branch Protection (Optional but Recommended)

### Configure Branch Protection Rules

1. Go to GitHub repository **Settings** → **Branches**
2. Click **Add rule** or **Add branch protection rule**
3. Branch name pattern: `main`
4. Enable the following:

   **Status Checks**:
   - ☑️ Require status checks to pass before merging
   - ☑️ Require branches to be up to date before merging
   - Select: `test (ubuntu-latest)` (appears after first workflow run)

   **Pull Request Reviews** (Optional):
   - ☑️ Require a pull request before merging
   - ☑️ Require approvals: 1

   **Other Settings**:
   - ☑️ Include administrators (enforces rules on all users)

5. Click **Create** or **Save changes**

---

## ✅ Step 4: Verify CI/CD is Working

### Test the Workflow

```bash
# Create a test branch
git checkout -b test-ci-workflow

# Make a small change (e.g., update README)
echo "\n<!-- CI/CD test -->" >> README.md

# Commit and push
git add README.md
git commit -m "Test CI/CD workflow"
git push origin test-ci-workflow

# Create a pull request on GitHub
# Go to: https://github.com/YOUR_USERNAME/acis-ai-platform/pulls
# Click "New pull request"
# Select: base: main, compare: test-ci-workflow
# Click "Create pull request"
```

### Verify in GitHub Actions

1. Go to your repository on GitHub
2. Click **Actions** tab
3. You should see the workflow running
4. Click on the workflow run to see details
5. Verify all steps complete successfully:
   - ✅ Checkout code
   - ✅ Set up Python 3.12
   - ✅ Install dependencies
   - ✅ Set up test database schema
   - ✅ Run unit tests
   - ✅ Upload coverage reports
   - ✅ Archive coverage HTML report

### Check Coverage on Codecov

1. After workflow completes, go to https://codecov.io/
2. Navigate to your repository
3. You should see coverage report with metrics
4. Click through to see file-by-file coverage

### Verify Badges in README

1. Check that badges in README show correct status
2. Tests badge should show "passing" (green)
3. Coverage badge should show percentage

---

## 🧪 Step 5: Test Pre-commit Hooks Locally

### Verify Hooks are Installed

```bash
# Check if pre-commit is installed
pre-commit --version

# Run hooks on all files
pre-commit run --all-files
```

### Test a Commit

```bash
# Make a change to a Python file
echo "# Test comment" >> backend/api/main.py

# Stage the file
git add backend/api/main.py

# Try to commit (pre-commit hooks will run automatically)
git commit -m "Test pre-commit hooks"

# Hooks should run and format the file
# If hooks make changes, you'll need to add them again:
git add backend/api/main.py
git commit -m "Test pre-commit hooks"
```

---

## 📊 Expected Results

After completing all steps:

- ✅ GitHub Actions workflow runs on every push to `main`/`develop`
- ✅ All 275 unit tests pass in CI environment
- ✅ Coverage reports uploaded to Codecov
- ✅ Pre-commit hooks enforce code quality before commits
- ✅ Branch protection prevents merging failing code
- ✅ README badges show current status

---

## 🐛 Troubleshooting

### Issue: Workflow Fails with "Database connection error"

**Solution**: Check that PostgreSQL service is configured correctly in `.github/workflows/tests.yml`

```yaml
services:
  postgres:
    image: postgres:14
    env:
      POSTGRES_PASSWORD: $@nJose420
```

### Issue: Coverage Upload Fails

**Solution**: Ensure `CODECOV_TOKEN` is added to GitHub Secrets (Step 2C)

### Issue: Pre-commit Hooks Not Running

**Solution**: Re-install pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

### Issue: Tests Pass Locally but Fail in CI

**Solution**: Check environment variables and database setup scripts

```bash
# Ensure database migrations are run in CI
psql -h localhost -U postgres -d acis-ai-test -f database/create_rl_trading_tables.sql
psql -h localhost -U postgres -d acis-ai-test -f database/fix_brokerage_id_autoincrement.sql
```

### Issue: Branch Protection Not Showing Status Check

**Solution**: Status checks only appear after the first workflow run. Push a commit first, then configure branch protection.

---

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Codecov Documentation](https://docs.codecov.com/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [Flake8 Linter](https://flake8.pycqa.org/)

---

## 🔗 Related Documents

- [TESTING_PHASE2_CICD_COMPLETE.md](./TESTING_PHASE2_CICD_COMPLETE.md) - Detailed CI/CD completion report
- [TESTING_PHASE2_COMPLETE.md](./TESTING_PHASE2_COMPLETE.md) - Unit test completion report
- [README.md](./README.md) - Project README with badges

---

## ✨ What's Next?

After CI/CD is fully operational:

**Phase 2 Continuation**: Integration Tests
- Create 50-75 integration tests
- Test end-to-end workflows
- Mock external services
- Estimated: 3-4 days

**Reference**: [TESTING_PHASE4_INTEGRATION_PLAN.md](./TESTING_PHASE4_INTEGRATION_PLAN.md)

---

**Last Updated**: November 2, 2025
