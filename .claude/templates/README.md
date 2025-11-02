# ACIS AI Platform - Code Templates

Templates for quickly creating new components with consistent patterns and best practices.

## Available Templates

### 1. New Trading Strategy (`new_strategy.py.template`)
Template for implementing a new trading strategy with XGBoost.

**Usage:**
```bash
# Copy template
cp .claude/templates/new_strategy.py.template ml_models/train_mystrategy.py

# Replace placeholders
# {{STRATEGY_NAME}} → Name of your strategy (e.g., "Quality")
# {{STRATEGY_DESCRIPTION}} → What the strategy focuses on
# {{MARKET_CAP}} → Target market cap (small/mid/large)
# {{KEY_FEATURES}} → Most important features
# {{AUTHOR}} → Your name
# {{DATE}} → Current date
```

**Includes:**
- Data loading and filtering
- Feature engineering hooks
- XGBoost training pipeline
- Evaluation and metrics
- Model saving with metadata
- GPU support

### 2. API Endpoint (`new_api_endpoint.py.template`)
FastAPI router template with full CRUD operations.

**Usage:**
```bash
# Copy template
cp .claude/templates/new_api_endpoint.py.template backend/api/routes/my_endpoint.py

# Replace placeholders
# {{ENDPOINT_NAME}} → Resource name (e.g., "Portfolio Alerts")
# {{ROUTE_PREFIX}} → URL prefix (e.g., "portfolio-alerts")
# {{TABLE_NAME}} → Database table name
# {{REQUEST_MODEL_NAME}} → Pydantic request model name
# {{RESPONSE_MODEL_NAME}} → Pydantic response model name
```

**Includes:**
- GET (list) with pagination
- GET (single) by ID
- POST (create)
- PUT (update)
- DELETE
- Request/response models
- Error handling
- Logging
- OpenAPI documentation

### 3. Database Migration (`database_migration.sql.template`)
Safe database schema change template.

**Usage:**
```bash
# Copy template
cp .claude/templates/database_migration.sql.template database/migrations/003_my_migration.sql

# Replace placeholders
# {{MIGRATION_NAME}} → Migration identifier
# {{MIGRATION_DESCRIPTION}} → What this migration does
# {{TABLE_NAME}} → Table being modified
# {{NEW_COLUMN_1}} → Column name
# {{DATA_TYPE_1}} → PostgreSQL data type
```

**Includes:**
- Backup creation
- Column additions
- Constraint management
- Index creation
- View updates
- Permission grants
- Verification checks
- Rollback script

### 4. Backtest Configuration (`backtest_config.json.template`)
Complete backtest setup configuration.

**Usage:**
```bash
# Copy template
cp .claude/templates/backtest_config.json.template configs/backtest_mystrategy.json

# Edit configuration values
# Set date range, universe, strategy, risk parameters
```

**Includes:**
- Time period settings
- Universe definition
- Strategy configuration
- Portfolio rules
- Risk management
- Transaction costs
- Performance metrics
- Output settings

### 5. New Skill (`new_skill.yaml.template`)
Claude Code skill template for automation workflows.

**Usage:**
```bash
# Copy template
cp .claude/templates/new_skill.yaml.template .claude/skills/my-skill.yaml

# Replace placeholders with your workflow steps
```

**Includes:**
- User input collection
- Prerequisite validation
- Main execution
- Progress monitoring
- Result verification
- Error handling
- Safety checks

## Template Placeholders

Common placeholders used across templates:

### General
- `{{AUTHOR}}` - Your name
- `{{DATE}}` - Current date (YYYY-MM-DD)
- `{{DESCRIPTION}}` - Description of what this does

### Strategy Template
- `{{STRATEGY_NAME}}` - Strategy name (e.g., "Quality", "Momentum")
- `{{STRATEGY_CLASS_NAME}}` - Python class name (e.g., "QualityStrategy")
- `{{STRATEGY_NAME_LOWER}}` - Lowercase strategy name (e.g., "quality")
- `{{STRATEGY_DESCRIPTION}}` - What the strategy focuses on
- `{{MARKET_CAP}}` - Target market cap (small/mid/large)
- `{{KEY_FEATURES}}` - Comma-separated important features

### API Endpoint Template
- `{{ENDPOINT_NAME}}` - Resource name (e.g., "Portfolio Alerts")
- `{{ENDPOINT_DESCRIPTION}}` - What this endpoint does
- `{{ROUTE_PREFIX}}` - URL prefix (e.g., "portfolio-alerts")
- `{{ENDPOINT_PATH}}` - Endpoint path (e.g., "alerts")
- `{{ENDPOINT_FUNCTION_NAME}}` - Function name (e.g., "portfolio_alerts")
- `{{TABLE_NAME}}` - Database table name
- `{{REQUEST_MODEL_NAME}}` - Request model class name
- `{{RESPONSE_MODEL_NAME}}` - Response model class name
- `{{TAG_NAME}}` - API tag for grouping

### Database Migration Template
- `{{MIGRATION_NAME}}` - Migration identifier (e.g., "add_alert_columns")
- `{{MIGRATION_DESCRIPTION}}` - What changes are being made
- `{{TABLE_NAME}}` - Table being modified
- `{{NEW_COLUMN_1}}`, `{{NEW_COLUMN_2}}` - New column names
- `{{DATA_TYPE_1}}`, `{{DATA_TYPE_2}}` - PostgreSQL data types
- `{{DEFAULT_VALUE_1}}`, `{{DEFAULT_VALUE_2}}` - Default values
- `{{CONSTRAINT_NAME}}` - Constraint name
- `{{INDEX_NAME}}` - Index name
- `{{VIEW_NAME}}` - Materialized view name
- `{{DATE_TIMESTAMP}}` - Timestamp for backup table

### Backtest Config Template
- `{{BACKTEST_NAME}}` - Backtest identifier
- `{{BACKTEST_DESCRIPTION}}` - What this backtest tests

### Skill Template
- `{{SKILL_NAME}}` - Skill identifier (lowercase-with-hyphens)
- `{{SKILL_DESCRIPTION}}` - One-line description
- `{{SKILL_PROMPT}}` - Main task description
- `{{INPUT_1}}`, `{{INPUT_2}}`, `{{INPUT_3}}` - User inputs needed
- `{{VALIDATION_COMMAND_1}}` - Prerequisite check command
- `{{MAIN_COMMAND}}` - Primary execution command
- `{{EXPECTED_DURATION}}` - How long it takes
- `{{VERIFICATION_COMMAND_1}}` - Result validation command

## Quick Start Examples

### Example 1: Create a New "Quality" Strategy

```bash
# Copy template
cp .claude/templates/new_strategy.py.template ml_models/train_quality.py

# Edit file and replace:
# {{STRATEGY_NAME}} → Quality
# {{STRATEGY_CLASS_NAME}} → QualityStrategy
# {{STRATEGY_NAME_LOWER}} → quality
# {{STRATEGY_DESCRIPTION}} → High-quality businesses with strong fundamentals
# {{KEY_FEATURES}} → roe, roic, debt_to_equity, profit_margin, revenue_growth
# {{AUTHOR}} → Your Name
# {{DATE}} → 2025-11-02

# Train the strategy
python ml_models/train_quality.py --market-cap mid --gpu
```

### Example 2: Add Portfolio Alerts API

```bash
# Copy template
cp .claude/templates/new_api_endpoint.py.template backend/api/routes/alerts.py

# Replace placeholders
# {{ENDPOINT_NAME}} → Portfolio Alert
# {{ROUTE_PREFIX}} → alerts
# {{TABLE_NAME}} → portfolio_alerts
# etc.

# Add to main.py
# from .routes import alerts
# app.include_router(alerts.router)

# Test endpoint
curl http://localhost:8000/api/alerts
```

### Example 3: Database Migration

```bash
# Copy template
cp .claude/templates/database_migration.sql.template database/migrations/003_add_alert_system.sql

# Edit SQL file with your changes
# Run migration
PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost -f database/migrations/003_add_alert_system.sql
```

## Best Practices

1. **Always use templates** for new components to maintain consistency
2. **Replace ALL placeholders** before using template code
3. **Test templates** in development environment first
4. **Add comments** explaining strategy-specific logic
5. **Update documentation** after creating new components
6. **Version control** - commit templates and generated code separately

## Creating Your Own Templates

To add a new template:

1. Create template file in `.claude/templates/`
2. Use `{{PLACEHOLDER}}` syntax for variables
3. Include comprehensive comments
4. Add usage documentation to this README
5. Test template by creating example from it

## Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)
- [XGBoost Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html)

---

**Template Usage Tip**: Use find-and-replace in your editor to quickly fill all placeholders at once!
