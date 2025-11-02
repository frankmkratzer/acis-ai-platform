---
description: Show recent logs with option to filter by component or error level
---

Show recent logs from the ACIS AI Platform.

Ask the user what they want to see:
- All recent logs (last 50 lines)
- Specific component: ml_training, rl_training, eod_pipeline, api, trading
- Error level: errors only, warnings+errors, all

Then display:

1. **Recent Log Entries**
   - Timestamp
   - Component
   - Log level
   - Message

2. **Error Summary** (if errors present)
   - Count of errors in last 24h
   - Most common error types
   - When they occurred

3. **Quick Actions**
   - Suggest fixes for common errors
   - Offer to analyze logs in detail
   - Option to clear old logs

Format with color coding (🔴 errors, 🟡 warnings, ⚪ info) and highlight recent entries.
