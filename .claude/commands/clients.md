---
description: Quick access to client information and portfolios
---

Show client information and portfolio details.

Ask the user:
- List all clients
- Show specific client by ID or name
- Show client portfolio positions

Then retrieve and display:

**List Clients:**
```sql
SELECT
  client_id,
  first_name || ' ' || last_name as name,
  email,
  risk_tolerance,
  investment_horizon,
  created_at
FROM clients
ORDER BY client_id;
```

**Client Details (if specific client):**
```sql
-- Client info
SELECT * FROM clients WHERE client_id = {ID};

-- Account info
SELECT
  account_id,
  account_type,
  cash,
  portfolio_value,
  created_at
FROM paper_accounts
WHERE client_id = {ID};

-- Current positions
SELECT
  p.ticker,
  p.quantity,
  p.avg_cost,
  db.close as current_price,
  (db.close - p.avg_cost) * p.quantity as unrealized_pnl,
  ((db.close - p.avg_cost) / p.avg_cost * 100) as return_pct
FROM paper_positions p
JOIN daily_bars db ON p.ticker = db.ticker
WHERE p.account_id = {ACCOUNT_ID}
  AND db.date = (SELECT MAX(date) FROM daily_bars)
ORDER BY p.quantity * db.close DESC;
```

Format as clean tables with totals and summary stats.
