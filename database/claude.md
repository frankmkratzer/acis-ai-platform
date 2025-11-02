# Database Directory - PostgreSQL Schema & Migrations

## Purpose
SQL schemas, views, and migration scripts for the PostgreSQL database.

## Key Files
- **`create_tables.sql`** - Full schema definition (47 tables)
- **`build_clean_ml_view.sql`** - Creates `ml_training_features` materialized view
- **`paper_trading_tables.sql`** - Paper trading account tables
- **`add_account_hash.sql`** - Account hash for brokerage linking

## Database Structure
- **Connection**: `postgresql://postgres:$@nJose420@localhost/acis-ai`
- **47 Tables** across 8 categories (see root claude.md)
- **Materialized View**: `ml_training_features` (100+ features, refresh after data updates)

## Important Operations
```sql
-- Refresh ML features (run after market data updates)
REFRESH MATERIALIZED VIEW CONCURRENTLY ml_training_features;

-- Check table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```
