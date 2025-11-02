# API Server Down Runbook

## When to Use This Runbook

Use when the FastAPI backend is not responding:

- HTTP 502/503/504 errors
- Connection timeout
- "Cannot connect to server" errors
- Frontend cannot fetch data
- Uvicorn process crashed

**Severity**: 🟠 HIGH - User-facing downtime

---

## Quick Diagnosis (30 seconds)

```bash
# Check if API is responding
curl -s http://localhost:8000/health || echo "❌ API down"

# Check if process is running
ps aux | grep uvicorn
```

---

## Step 1: Check Uvicorn Process (30 seconds)

```bash
# Check if uvicorn is running
pgrep -fa uvicorn

# Check process tree
pstree -p | grep uvicorn

# If not running, check recent crashes
journalctl -u uvicorn --since "1 hour ago"
```

---

## Step 2: Check API Logs (1 minute)

```bash
# Check recent API logs
tail -n 100 logs/api.log

# Look for errors
grep -i "error\|exception\|fatal" logs/api.log | tail -n 20

# Check for recent crashes
grep -i "killed\|segfault\|core dump" logs/api.log
```

### Common error patterns:

**"ImportError" or "ModuleNotFoundError"**
```bash
# Virtual environment not activated or missing package
cd backend
source ../venv/bin/activate
pip install -r requirements.txt
```

**"Address already in use"**
```bash
# Port 8000 is occupied
lsof -i :8000
# Kill the process
kill -9 $(lsof -t -i :8000)
```

**"Database connection failed"**
```bash
# Database issue - see database-connection-failure.md runbook
```

---

## Step 3: Restart API Server (1 minute)

### Stop any running instances:

```bash
# Kill all uvicorn processes
pkill -f uvicorn

# Verify stopped
pgrep -fa uvicorn
```

### Start API server:

```bash
# Navigate to backend directory
cd /home/fkratzer/acis-ai-platform/backend

# Activate virtual environment
source ../venv/bin/activate

# Start uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &

# Save PID
echo $! > /tmp/uvicorn.pid

# Wait for startup
sleep 5

# Test health endpoint
curl http://localhost:8000/health
```

**Expected output**: `{"status": "healthy"}`

---

## Step 4: Verify API Endpoints (1 minute)

```bash
# Test key endpoints
echo "Testing health..."
curl -s http://localhost:8000/health | jq

echo "Testing clients endpoint..."
curl -s http://localhost:8000/api/clients/ | jq

echo "Testing models endpoint..."
curl -s http://localhost:8000/api/ml-models/ | jq

echo "Testing database connection..."
curl -s http://localhost:8000/api/status/database | jq
```

---

## Step 5: Check Dependencies (1 minute)

### Database connection:

```bash
# Test database
PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost -c "SELECT 1;"
```

### Python environment:

```bash
# Check Python version
python --version  # Should be 3.11+

# Verify virtual environment
which python  # Should be in venv

# Check critical packages
pip list | grep -E "fastapi|uvicorn|psycopg2|xgboost"
```

### File permissions:

```bash
# Check logs directory is writable
touch logs/test.log && rm logs/test.log || echo "❌ Cannot write to logs/"

# Check model files are readable
ls -la models/
```

---

## Step 6: Check System Resources (1 minute)

```bash
# Check memory usage
free -h

# Check disk space
df -h

# Check CPU usage
top -bn1 | head -n 20

# Check for OOM killer
dmesg | grep -i "killed process"
```

**If out of memory**:
```bash
# Clear cache
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

# Restart with limited workers
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## Step 7: Check Network/Firewall (30 seconds)

```bash
# Check if port 8000 is open
netstat -tlnp | grep 8000

# Check firewall rules
sudo ufw status | grep 8000
# OR
sudo iptables -L | grep 8000

# Test local connection
telnet localhost 8000
```

---

## Step 8: Review Configuration (1 minute)

### Check main.py:

```bash
# Verify main.py exists and is valid Python
python -m py_compile backend/api/main.py

# Check for syntax errors
python -c "import sys; sys.path.insert(0, 'backend'); from api import main"
```

### Check environment variables:

```bash
# Check .env file
cat backend/.env

# Verify required variables
grep -E "DATABASE_URL|API_KEY" backend/.env
```

---

## Step 9: Start with Debug Mode (If issues persist)

```bash
# Stop current process
pkill -f uvicorn

# Start in debug mode with verbose logging
cd backend
python -m uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level debug \
  --reload
```

Watch for errors during startup

---

## Step 10: Test Frontend Connection (30 seconds)

```bash
# Check if frontend can reach API
cd frontend

# Test API connection from frontend
curl -s http://localhost:8000/api/clients/ || echo "❌ Cannot reach API"

# Check CORS settings in main.py
grep -A 10 "CORS" backend/api/main.py
```

---

## Quick Recovery Script

```bash
#!/bin/bash
# Quick API recovery script

echo "🔄 Restarting ACIS AI API..."

# Kill existing processes
pkill -f uvicorn
sleep 2

# Navigate to backend
cd /home/fkratzer/acis-ai-platform/backend

# Activate venv
source ../venv/bin/activate

# Start API
nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload \
  > ../logs/uvicorn.log 2>&1 &

sleep 5

# Test
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API is running"
    curl http://localhost:8000/health | jq
else
    echo "❌ API failed to start"
    tail -n 50 ../logs/uvicorn.log
    exit 1
fi
```

Save as `.claude/scripts/restart-api.sh` and run:
```bash
bash .claude/scripts/restart-api.sh
```

---

## Recovery Checklist

- [ ] Uvicorn process is running
- [ ] Port 8000 is listening
- [ ] Health endpoint responds
- [ ] Database connection works
- [ ] Key endpoints return data
- [ ] No errors in logs
- [ ] System resources adequate
- [ ] Frontend can connect
- [ ] CORS configured correctly

---

## Prevention

### Set up systemd service:

```bash
# Create service file
sudo cat > /etc/systemd/system/acis-api.service << 'EOF'
[Unit]
Description=ACIS AI Platform API
After=postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=fkratzer
WorkingDirectory=/home/fkratzer/acis-ai-platform/backend
Environment="PATH=/home/fkratzer/acis-ai-platform/venv/bin"
ExecStart=/home/fkratzer/acis-ai-platform/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable acis-api
sudo systemctl start acis-api

# Check status
sudo systemctl status acis-api
```

### Set up monitoring:

```bash
# Add health check to crontab
*/5 * * * * curl -s http://localhost:8000/health || echo "API down at $(date)" >> /var/log/api_monitor.log
```

---

## Common Causes

1. **Process killed (OOM)** → Increase memory or reduce workers
2. **Database connection lost** → Check database status
3. **Port conflict** → Change port or kill conflicting process
4. **Import errors** → Reinstall dependencies
5. **Configuration errors** → Check main.py and .env
6. **File permission issues** → Check logs/ and models/ permissions

---

## Escalation

If API cannot be recovered:

1. **Check system logs**: `journalctl -xe`
2. **Review error logs**: `tail -n 200 logs/api.log`
3. **Test in isolation**: Start minimal FastAPI app to test server
4. **Contact**: {BACKEND_TEAM_CONTACT}

---

**Last Updated**: 2025-11-02
**Review Frequency**: Quarterly
**Owner**: Backend Team
