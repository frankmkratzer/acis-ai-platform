# Performance Testing Guide

This directory contains performance and load testing scripts for the ACIS AI Platform.

## Prerequisites

```bash
pip install locust
```

## Running Load Tests

### Basic Load Test

Test with gradually increasing load:

```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

Then open http://localhost:8089 in your browser to configure:
- Number of users (total)
- Spawn rate (users started/second)
- Host URL

### Headless Mode

Run tests without the web UI:

```bash
# Run with 100 users, spawning 10 per second, for 5 minutes
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless
```

### Stress Test

Test with high load using the stress test user class:

```bash
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users 500 \
  --spawn-rate 50 \
  --run-time 10m \
  --headless \
  ACISStressTestUser
```

### Background Jobs Test

Test long-running operations:

```bash
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users 10 \
  --spawn-rate 2 \
  --run-time 30m \
  --headless \
  ACISBackgroundJobUser
```

## Test Scenarios

### 1. Normal Load (ACISAPIUser)
- **Purpose**: Simulate typical user behavior
- **Users**: 50-100
- **Spawn Rate**: 5-10/sec
- **Duration**: 10-30 minutes
- **Tasks**:
  - Get clients (50% weight)
  - Get ML predictions (40% weight)
  - Execute trades (10% weight)

### 2. Stress Test (ACISStressTestUser)
- **Purpose**: Find breaking point
- **Users**: 500-1000
- **Spawn Rate**: 50-100/sec
- **Duration**: 5-15 minutes
- **Tasks**:
  - Rapid ML predictions (high frequency)
  - Concurrent optimizations
  - Bulk trades

### 3. Background Jobs (ACISBackgroundJobUser)
- **Purpose**: Test long-running operations
- **Users**: 5-20
- **Spawn Rate**: 1-2/sec
- **Duration**: 30-60 minutes
- **Tasks**:
  - Model training
  - Bulk data fetches
  - Portfolio rebalancing

## Performance Baselines

Expected performance metrics:

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Average Response Time | < 500ms | < 1000ms | > 2000ms |
| 95th Percentile | < 1000ms | < 2000ms | > 5000ms |
| 99th Percentile | < 2000ms | < 5000ms | > 10000ms |
| Error Rate | < 0.1% | < 1% | > 5% |
| Requests/sec | > 100 | > 50 | < 20 |

## Interpreting Results

### Response Time Distribution

```
Name                          # reqs  Avg     Min     Max     Med     95%     99%
------------------------------------------------------------------------------------------
GET /api/clients              1000    250ms   50ms    2000ms  200ms   500ms   1000ms
GET /api/ml/predict           800     800ms   200ms   5000ms  700ms   2000ms  3000ms
POST /api/trading/execute     200     1500ms  500ms   10000ms 1200ms  4000ms  8000ms
```

**Analysis**:
- Client listings are fast (250ms avg)
- ML predictions are acceptable (800ms avg)
- Trade execution needs optimization (1500ms avg, high max)

### Request Statistics

```
Method  Name                    # reqs  # fails  Req/s   Failure %
---------------------------------------------------------------------------
GET     /api/clients            5000    0        83.3    0.00%
GET     /api/ml/predict         4000    50       66.7    1.25%
POST    /api/trading/execute    1000    100      16.7    10.00%
```

**Analysis**:
- Client endpoint is stable (0% failures)
- ML predictions mostly stable (1.25% failures)
- Trade execution has issues (10% failures) - investigate

### Response Time Percentiles

```
Name                          50%    66%    75%    80%    90%    95%    98%    99%   100%
------------------------------------------------------------------------------------------
GET /api/clients              200    250    300    350    450    500    800    1000   2000
GET /api/ml/predict           700    850    950    1050   1500   2000   2800   3000   5000
```

**Analysis**:
- Most requests (50%) complete in reasonable time
- Long tail exists (99th percentile much higher)
- Consider adding caching or optimization

## Common Issues and Solutions

### High Response Times

**Symptoms**: Average response time > 2000ms

**Possible Causes**:
- Database queries not optimized
- Missing indexes
- N+1 query problems
- External API calls blocking

**Solutions**:
1. Enable database query logging
2. Add database indexes
3. Implement caching (Redis)
4. Use async operations for external calls

### High Error Rate

**Symptoms**: Error rate > 5%

**Possible Causes**:
- Database connection pool exhausted
- API rate limits exceeded
- Memory leaks
- Unhandled exceptions

**Solutions**:
1. Increase connection pool size
2. Implement request queuing
3. Add circuit breakers
4. Fix memory leaks

### Low Throughput

**Symptoms**: Requests/sec < 20

**Possible Causes**:
- CPU bottleneck
- Insufficient workers
- Blocking I/O operations
- Resource contention

**Solutions**:
1. Scale horizontally (more instances)
2. Increase Uvicorn workers
3. Use async operations
4. Optimize CPU-intensive code

## Running in CI/CD

GitHub Actions workflow:

```yaml
- name: Run performance tests
  run: |
    locust -f tests/performance/locustfile.py \
      --host=http://localhost:8000 \
      --users 50 \
      --spawn-rate 5 \
      --run-time 5m \
      --headless \
      --html performance-report.html \
      --csv performance-results
```

## Monitoring During Tests

While running load tests, monitor:

1. **Prometheus Metrics**:
   - http://localhost:9090
   - Query: `rate(http_requests_total[1m])`

2. **Grafana Dashboards**:
   - http://localhost:3001
   - View API Performance dashboard

3. **System Resources**:
   ```bash
   # CPU and memory
   htop

   # Database connections
   psql -c "SELECT count(*) FROM pg_stat_activity;"

   # Docker stats
   docker stats
   ```

## Best Practices

1. **Start Small**: Begin with low user count and gradually increase
2. **Ramp Up Slowly**: Use appropriate spawn rate (10-20% of total users)
3. **Run Long Enough**: Minimum 10 minutes to see memory leaks and degradation
4. **Test Production-Like**: Use production-like data and infrastructure
5. **Baseline First**: Establish baseline metrics before optimization
6. **One Change at a Time**: Test impact of individual optimizations
7. **Monitor Everything**: Watch metrics during tests
8. **Document Results**: Keep records for comparison

## Advanced Scenarios

### Spike Test

Sudden traffic increase:

```bash
# Phase 1: Normal load (5 min)
locust ... --users 50 --spawn-rate 5 --run-time 5m

# Phase 2: Spike (2 min)
locust ... --users 500 --spawn-rate 100 --run-time 2m

# Phase 3: Return to normal (5 min)
locust ... --users 50 --spawn-rate 5 --run-time 5m
```

### Soak Test

Long-running stability test:

```bash
# Run for 24 hours with consistent load
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 24h \
  --headless
```

### Breakpoint Test

Find maximum capacity:

```bash
# Gradually increase until failure
for users in 100 200 400 800 1600 3200; do
  echo "Testing with $users users..."
  locust ... --users $users --spawn-rate 50 --run-time 5m --headless
  sleep 60  # Cool down between tests
done
```

## Resources

- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Best Practices](https://www.apdex.org/)
- [Load Testing Patterns](https://k6.io/docs/test-types/)
