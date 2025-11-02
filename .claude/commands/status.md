---
description: Quick system health check - database, API, models, and services
---

Check the health status of the ACIS AI Platform. Show:

1. **Database Status**
   - PostgreSQL connection
   - Latest data date in daily_bars
   - Row count in ml_training_features
   - Number of active clients

2. **API Status**
   - Backend running (port 8000)
   - Frontend running (port 3000)
   - Response time check

3. **Model Status**
   - List production models
   - Last training date for each strategy
   - Model file sizes

4. **Recent Activity**
   - Last EOD pipeline run
   - Last rebalance execution
   - Recent errors in logs (last 24h)

Format the output in a clean, easy-to-read summary with ✅/❌ indicators.
