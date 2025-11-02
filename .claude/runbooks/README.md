# ACIS AI Platform - Emergency Runbooks

Step-by-step guides for handling critical incidents and system failures.

## Available Runbooks

### 🔴 Critical (Execute Immediately)

#### 1. [Emergency Model Rollback](emergency-model-rollback.md)
**When**: Production model is making bad predictions, causing losses
**Time to Execute**: 10 minutes
**Impact**: Trading stopped temporarily

**Quick Start**:
```bash
# 1. Stop trading
pkill -f "run_daily_rebalance"

# 2. Identify bad model
ls -lht models/{strategy}_{marketcap}/backup_*

# 3. Rollback
bash .claude/scripts/rollback-model.sh {model_name} {backup_version}

# 4. Verify and resume
```

---

#### 2. [Database Connection Failure](database-connection-failure.md)
**When**: Cannot connect to PostgreSQL, system down
**Time to Execute**: 5 minutes
**Impact**: Entire system unavailable

**Quick Start**:
```bash
# 1. Check PostgreSQL status
systemctl status postgresql

# 2. Restart if needed
sudo systemctl restart postgresql

# 3. Test connection
PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost -c "SELECT 1;"

# 4. Check application connection
```

---

### 🟠 High Priority (Act Within 15 Minutes)

#### 3. [API Server Down](api-down.md)
**When**: Backend API not responding, users cannot access platform
**Time to Execute**: 5 minutes
**Impact**: User-facing downtime

**Quick Start**:
```bash
# 1. Check if API is running
curl http://localhost:8000/health

# 2. Restart API
bash .claude/scripts/restart-api.sh

# 3. Verify endpoints work
curl http://localhost:8000/api/clients/
```

---

### 🟡 Medium Priority (Address Within 1 Hour)

#### 4. Training Job Failed (Coming Soon)
**When**: ML or RL training job crashes or produces poor results
**Time to Execute**: 15 minutes

#### 5. Data Pipeline Failure (Coming Soon)
**When**: EOD data pipeline fails, missing market data
**Time to Execute**: 30 minutes

#### 6. Trade Execution Errors (Coming Soon)
**When**: Orders failing to execute via Alpaca brokerage
**Time to Execute**: 10 minutes

---

## Runbook Usage Guide

### Before You Start

1. **Stay Calm** - Follow the steps methodically
2. **Read Entire Runbook** - Understand the full process first
3. **Document Actions** - Note what you do and when
4. **Notify Team** - Alert others that incident is in progress

### During Execution

- ✅ Check off each step as you complete it
- 📝 Note any deviations or issues
- ⏱️ Track time spent on each step
- 🔍 Verify each action succeeded before proceeding

### After Resolution

1. **Document Incident** - Create incident report
2. **Post-Mortem** - Analyze root cause
3. **Update Runbook** - Add learnings
4. **Share with Team** - Brief team on incident

---

## Runbook Structure

Each runbook follows this structure:

```markdown
1. When to Use This Runbook - Trigger conditions
2. Quick Diagnosis - Fast problem identification (1 min)
3. Step-by-Step Recovery - Detailed fix procedures
4. Verification - Confirm issue is resolved
5. Recovery Checklist - Ensure nothing missed
6. Prevention - How to avoid repeat incidents
7. Escalation - When and who to contact
```

---

## Incident Severity Levels

| Level | Symbol | Response Time | Example |
|-------|--------|---------------|---------|
| Critical | 🔴 | Immediate (0-5 min) | Production model causing losses |
| High | 🟠 | 15 minutes | API down, users affected |
| Medium | 🟡 | 1 hour | Training job failed |
| Low | 🟢 | 4 hours | Non-critical service degraded |

---

## Common Incident Workflows

### Scenario 1: Model Performance Degraded

```
Detect issue → Check /models runbook → Stop trading →
Rollback model → Verify → Resume → Post-mortem
```

### Scenario 2: System Completely Down

```
Check database → Check API → Check network →
Restart services → Verify health → Monitor
```

### Scenario 3: Data Issues

```
Check data pipeline → Verify data quality →
Refresh features → Retrain if needed → Deploy
```

---

## Quick Commands Reference

### System Status

```bash
# Database
systemctl status postgresql
PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost -c "SELECT 1;"

# API
curl http://localhost:8000/health
pgrep -fa uvicorn

# Frontend
curl http://localhost:3000
pgrep -fa "next-server"

# Models
ls -lh models/*/metadata.json
```

### Quick Restarts

```bash
# Database
sudo systemctl restart postgresql

# API
pkill -f uvicorn && cd backend && uvicorn api.main:app --reload &

# Frontend
cd frontend && npm run dev &
```

### Log Checking

```bash
# Recent errors across all logs
grep -i "error" logs/*.log | tail -n 50

# API logs
tail -f logs/api.log

# Training logs
tail -f logs/growth_momentum.log

# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

---

## Escalation Contacts

| Issue Type | Primary Contact | Backup Contact |
|------------|----------------|----------------|
| Model Issues | ML Team Lead | Platform Owner |
| Database Issues | DBA | Infrastructure |
| API/Backend | Backend Lead | DevOps |
| Data Pipeline | Data Team | ML Team |
| Trading/Brokerage | Trading Lead | Compliance |

---

## Incident Response Team

### Roles During Incident

1. **Incident Commander** - Coordinates response, makes decisions
2. **Technical Lead** - Executes runbook steps
3. **Communicator** - Updates stakeholders
4. **Scribe** - Documents actions and timeline

### Communication Channels

- **Slack**: `#incidents` channel
- **Email**: incidents@acis.ai
- **On-Call**: {PHONE_NUMBER}

---

## Post-Incident Process

### 1. Incident Report Template

```markdown
# Incident Report: {TITLE}

**Date**: {DATE}
**Duration**: {START} to {END}
**Severity**: {LEVEL}
**Runbook Used**: {RUNBOOK_NAME}

## Summary
{Brief description of what happened}

## Impact
- Users affected: {COUNT}
- System downtime: {DURATION}
- Financial impact: ${AMOUNT}

## Timeline
- HH:MM - Issue detected
- HH:MM - Runbook initiated
- HH:MM - Issue resolved
- HH:MM - System verified

## Root Cause
{What actually caused the issue}

## Actions Taken
1. {Step 1}
2. {Step 2}
...

## What Worked Well
- {Thing 1}
- {Thing 2}

## What Could Be Improved
- {Improvement 1}
- {Improvement 2}

## Prevention Measures
- {Measure 1}
- {Measure 2}

## Action Items
- [ ] {Action 1} - Owner: {NAME} - Due: {DATE}
- [ ] {Action 2} - Owner: {NAME} - Due: {DATE}
```

### 2. Runbook Updates

After each incident:
- Update runbook with new learnings
- Add commands that worked
- Document edge cases
- Improve time estimates

### 3. Team Learning

- Schedule post-mortem meeting (within 48 hours)
- Share lessons learned
- Update documentation
- Improve monitoring/alerts

---

## Testing Runbooks

**Test runbooks quarterly** in non-production environment:

```bash
# 1. Simulate failure
# 2. Execute runbook
# 3. Time each step
# 4. Document issues
# 5. Update runbook
```

---

## Creating New Runbooks

Use the template:

```bash
cp .claude/templates/runbook.md.template .claude/runbooks/new-runbook.md
```

Runbook checklist:
- [ ] Clear trigger conditions
- [ ] Quick diagnosis (< 1 min)
- [ ] Step-by-step recovery
- [ ] Time estimates for each step
- [ ] Verification steps
- [ ] Prevention measures
- [ ] Escalation criteria
- [ ] Tested at least once

---

## Resources

- [Incident Response Best Practices](https://www.pagerduty.com/resources/learn/incident-response/)
- [Writing Effective Runbooks](https://www.atlassian.com/incident-management/devops/runbooks)
- [On-Call Handbook](https://github.com/alextakahashi/oncall-handbook)

---

**Last Updated**: 2025-11-02
**Next Review**: 2025-12-02
**Owner**: Platform Team
**Review Frequency**: Monthly or after each incident
