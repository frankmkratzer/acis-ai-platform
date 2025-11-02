---
description: Quick model deployment to production with safety checks
---

Deploy a model to production safely.

Ask the user:
- Which model to deploy (e.g., growth_midcap, value_large)
- Model type (XGBoost or RL)

Then execute a streamlined deployment:

1. **Validate Model**
   - Check model file exists
   - Read metadata.json
   - Verify performance metrics meet threshold:
     - Spearman IC > 0.03
     - Sharpe ratio > 0.5

2. **Show Current Production**
   - What's currently in production
   - Performance comparison

3. **Confirm Deployment**
   - Show what will change
   - Ask for confirmation

4. **Execute Deployment**
   - Backup current production model
   - Set new model as production
   - Update database deployment log
   - Verify model loads correctly

5. **Post-Deployment**
   - Test prediction on sample data
   - Show deployment summary
   - Remind to monitor for 24-48 hours

Quick and safe deployment with all necessary checks built-in.
