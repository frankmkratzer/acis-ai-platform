---
description: Quick database queries and information
---

Provide quick access to database information.

Ask the user what they want:
1. **Show tables** - List all tables
2. **Table info** - Describe specific table
3. **Data stats** - Row counts, latest dates, data quality
4. **Quick query** - Run a custom SQL query
5. **Schema** - Show database schema overview

Then execute the appropriate action:

**Show Tables:**
```sql
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Data Stats:**
```sql
-- Latest dates
SELECT MAX(date) FROM daily_bars;
SELECT MAX(date) FROM ml_training_features;

-- Row counts
SELECT
  'daily_bars' as table, COUNT(*) as rows FROM daily_bars
UNION ALL
SELECT 'ml_training_features', COUNT(*) FROM ml_training_features
UNION ALL
SELECT 'clients', COUNT(*) FROM clients;
```

**Data Quality:**
```sql
-- Check for gaps
SELECT date
FROM generate_series('2020-01-01'::date, CURRENT_DATE, '1 day'::interval) date
WHERE date NOT IN (SELECT DISTINCT date FROM daily_bars WHERE date >= '2020-01-01')
  AND EXTRACT(DOW FROM date) NOT IN (0, 6); -- Exclude weekends
```

Format results in clear tables.
