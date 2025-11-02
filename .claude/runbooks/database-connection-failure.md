# Database Connection Failure Runbook

## When to Use This Runbook

Use when the application cannot connect to PostgreSQL:

- "Connection refused" errors
- "FATAL: password authentication failed"
- "could not connect to server"
- Timeout errors
- Application crashes with database errors

**Severity**: 🔴 CRITICAL - System down

---

## Quick Diagnosis (1 minute)

### Test database connection:

```bash
# Quick connection test
PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost -c "SELECT 1 AS connection_test;"
```

**If this works**: Database is fine, issue is in application
**If this fails**: Database issue - continue below

---

## Step 1: Check PostgreSQL Service (30 seconds)

```bash
# Check service status
systemctl status postgresql

# If not running, start it
sudo systemctl start postgresql

# Enable auto-start on boot
sudo systemctl enable postgresql

# Verify it's running
systemctl is-active postgresql
```

**Expected output**: `active (running)`

---

## Step 2: Check PostgreSQL is Listening (30 seconds)

```bash
# Check if PostgreSQL is listening on port 5432
sudo netstat -plnt | grep 5432
# OR
sudo ss -plnt | grep 5432

# Should see:
# 0.0.0.0:5432  (listening on all interfaces)
# OR
# 127.0.0.1:5432 (listening on localhost only)
```

**If not listening**: Check PostgreSQL configuration

```bash
# Check listen_addresses in postgresql.conf
sudo grep "listen_addresses" /etc/postgresql/*/main/postgresql.conf

# Should be:
# listen_addresses = 'localhost' (for local connections)
# OR
# listen_addresses = '*' (for network connections)
```

---

## Step 3: Check Connection Authentication (1 minute)

### Review pg_hba.conf:

```bash
# Check authentication rules
sudo cat /etc/postgresql/*/main/pg_hba.conf | grep -v "^#" | grep -v "^$"
```

### Required entries for ACIS:

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                peer
host    all             postgres        127.0.0.1/32            md5
host    acis-ai         postgres        127.0.0.1/32            md5
host    acis-ai         claude_readonly 127.0.0.1/32            md5
```

### If authentication rules are wrong:

```bash
# Edit pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf

# Add required lines above
# Save and reload PostgreSQL
sudo systemctl reload postgresql
```

---

## Step 4: Verify Database Exists (30 seconds)

```bash
# List all databases
sudo -u postgres psql -l | grep acis-ai

# If database doesn't exist, restore from backup
# (See database-restore.md runbook)
```

---

## Step 5: Check Disk Space (30 seconds)

```bash
# Check disk usage
df -h /var/lib/postgresql

# PostgreSQL data directory
sudo du -sh /var/lib/postgresql/*/main/

# Check for out of disk space
df -h | grep -E "9[5-9]%|100%"
```

**If disk full**:
1. Clear old logs: `sudo find /var/log -type f -name "*.log.*" -delete`
2. Clear old model backups: `find models/*/backup_* -type d -mtime +30 -exec rm -rf {} \;`
3. Vacuum database: See Step 8

---

## Step 6: Check PostgreSQL Logs (1 minute)

```bash
# View recent PostgreSQL logs
sudo tail -n 100 /var/log/postgresql/postgresql-*.log

# Look for errors:
grep -i "error\|fatal\|panic" /var/log/postgresql/postgresql-*.log | tail -n 20
```

### Common errors and fixes:

**"too many connections"**
```sql
-- Check current connections
sudo -u postgres psql -c "SELECT COUNT(*) FROM pg_stat_activity;"

-- Show max connections
sudo -u postgres psql -c "SHOW max_connections;"

-- Kill idle connections
sudo -u postgres psql << 'EOF'
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND state_change < CURRENT_TIMESTAMP - INTERVAL '10 minutes';
EOF
```

**"could not open file"**
```bash
# Check file permissions
sudo ls -la /var/lib/postgresql/*/main/

# Fix permissions
sudo chown -R postgres:postgres /var/lib/postgresql
```

---

## Step 7: Test Connection with Different Users (1 minute)

```bash
# Test as postgres user
sudo -u postgres psql -d acis-ai -c "SELECT current_user;"

# Test with TCP connection
PGPASSWORD='$@nJose420' psql -U postgres -h localhost -d acis-ai -c "SELECT current_user;"

# Test read-only user
PGPASSWORD='claude_read_2025!' psql -U claude_readonly -h localhost -d acis-ai -c "SELECT COUNT(*) FROM clients;"
```

**If postgres user works but application doesn't**: Check application connection string

---

## Step 8: Database Maintenance (If issues persist)

### Check for corrupted indexes:

```bash
sudo -u postgres psql acis-ai << 'EOF'
-- Reindex all tables
REINDEX DATABASE "acis-ai";
EOF
```

### Vacuum the database:

```bash
sudo -u postgres psql acis-ai << 'EOF'
-- Vacuum and analyze all tables
VACUUM ANALYZE;

-- Check for bloat
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
EOF
```

---

## Step 9: Restart PostgreSQL (30 seconds)

**Last resort if nothing else works:**

```bash
# Graceful restart
sudo systemctl restart postgresql

# Check status
systemctl status postgresql

# Test connection
PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost -c "SELECT NOW();"
```

---

## Step 10: Application Connection String (1 minute)

### Check application is using correct connection details:

```bash
# Backend connection string (check .env or config)
grep -r "postgresql://" backend/

# Expected format:
# postgresql://postgres:$@nJose420@localhost:5432/acis-ai
```

### Common connection string issues:

1. **Wrong password**: Check `$@nJose420` is correct
2. **Wrong database name**: Should be `acis-ai` not `acis_ai`
3. **Wrong host**: Should be `localhost` or `127.0.0.1`
4. **Wrong port**: Should be `5432`
5. **Special characters**: Password needs URL encoding if special chars

---

## Quick Fix Checklist

Run through these quick fixes:

```bash
# 1. Restart PostgreSQL
sudo systemctl restart postgresql

# 2. Kill idle connections
sudo -u postgres psql acis-ai -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle' AND pid != pg_backend_pid();
"

# 3. Clear connection pool (if using pgbouncer)
# sudo systemctl restart pgbouncer

# 4. Restart backend API
pkill -f "uvicorn"
cd backend && uvicorn api.main:app --reload &

# 5. Test connection
PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost -c "SELECT 1;"
```

---

## Recovery Checklist

- [ ] PostgreSQL service is running
- [ ] PostgreSQL is listening on port 5432
- [ ] Database `acis-ai` exists
- [ ] Authentication rules are correct
- [ ] Disk space is sufficient (>20% free)
- [ ] No errors in PostgreSQL logs
- [ ] Can connect as postgres user
- [ ] Can connect as application user
- [ ] Backend API can connect
- [ ] Frontend can query API

---

## Prevention

### Set up monitoring:

```bash
# Add database connection monitoring
# Check connection every 5 minutes
*/5 * * * * PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost -c "SELECT 1;" || echo "DB down at $(date)" >> /var/log/db_monitor.log
```

### Regular maintenance:

```bash
# Weekly vacuum (add to crontab)
0 2 * * 0 sudo -u postgres psql acis-ai -c "VACUUM ANALYZE;"

# Monthly reindex
0 3 1 * * sudo -u postgres psql acis-ai -c "REINDEX DATABASE \"acis-ai\";"
```

---

## Escalation

If database cannot be restored:

1. **Check backups exist**:
   ```bash
   ls -lh /var/backups/postgresql/
   ```

2. **Restore from backup**: See `database-restore.md` runbook

3. **Contact DBA**: {DATABASE_ADMIN_CONTACT}

4. **System recovery**: May need to restore entire system

---

## Common Causes

1. **PostgreSQL not started after reboot** → Enable with `systemctl enable`
2. **Disk full** → Clear logs and old data
3. **Too many connections** → Increase max_connections or close connections
4. **Wrong authentication** → Fix pg_hba.conf
5. **Network firewall** → Check iptables/ufw rules
6. **Corrupted files** → Restore from backup

---

**Last Updated**: 2025-11-02
**Review Frequency**: Quarterly
**Owner**: Infrastructure Team
