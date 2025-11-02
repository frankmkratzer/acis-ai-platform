# ACIS AI Platform - Deployment Guide

**Date**: November 2, 2025
**Phase**: 3 - Operations & Deployment

---

## Table of Contents
1. [Docker Local Development](#docker-local-development)
2. [Docker Compose](#docker-compose)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Monitoring Stack](#monitoring-stack)
5. [Environment Variables](#environment-variables)
6. [Troubleshooting](#troubleshooting)

---

## Docker Local Development

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- 20GB free disk space

### Quick Start

1. **Clone Repository**
```bash
git clone https://github.com/frankmkratzer/acis-ai-platform.git
cd acis-ai-platform
```

2. **Create Environment File**
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. **Build and Run**
```bash
docker-compose up -d
```

4. **Access Services**
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs
- Frontend: http://localhost:3000
- Grafana: http://localhost:3001 (admin/admin)
- Prometheus: http://localhost:9090

### Building Individual Images

**Backend**:
```bash
docker build -t acis-backend:latest -f backend/Dockerfile .
```

**Frontend**:
```bash
cd frontend
docker build -t acis-frontend:latest .
```

---

## Docker Compose

### Services Included

| Service | Port | Description |
|---------|------|-------------|
| postgres | 5432 | PostgreSQL 14 database |
| redis | 6379 | Redis cache |
| backend | 8000 | FastAPI backend |
| frontend | 3000 | Next.js frontend |
| prometheus | 9090 | Metrics collection |
| grafana | 3001 | Dashboards |
| node-exporter | 9100 | System metrics |
| postgres-exporter | 9187 | Database metrics |

### Commands

**Start all services**:
```bash
docker-compose up -d
```

**View logs**:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Stop all services**:
```bash
docker-compose down
```

**Stop and remove volumes**:
```bash
docker-compose down -v
```

**Rebuild services**:
```bash
docker-compose up -d --build
```

**Scale backend**:
```bash
docker-compose up -d --scale backend=3
```

---

## Kubernetes Deployment

### Prerequisites
- Kubernetes 1.24+
- kubectl configured
- Helm 3.0+ (optional)
- Ingress controller (nginx)
- Cert-manager for TLS

### Deploy to Kubernetes

1. **Create Namespace**
```bash
kubectl apply -f k8s/base/namespace.yaml
```

2. **Create Secrets**
```bash
kubectl create secret generic acis-secrets \
  --from-literal=database-url='postgresql://postgres:password@postgres:5432/acis-ai' \
  --from-literal=anthropic-api-key='your-key' \
  --from-literal=schwab-app-key='your-key' \
  --from-literal=schwab-secret='your-secret' \
  --from-literal=postgres-password='your-password' \
  -n acis-ai
```

3. **Deploy PostgreSQL**
```bash
kubectl apply -f k8s/base/postgres-statefulset.yaml
```

4. **Deploy Backend**
```bash
kubectl apply -f k8s/base/backend-deployment.yaml
```

5. **Deploy Ingress**
```bash
kubectl apply -f k8s/base/ingress.yaml
```

### Verify Deployment

```bash
# Check pods
kubectl get pods -n acis-ai

# Check services
kubectl get svc -n acis-ai

# Check logs
kubectl logs -f deployment/acis-backend -n acis-ai

# Port forward for testing
kubectl port-forward svc/acis-backend 8000:8000 -n acis-ai
```

### Scaling

```bash
# Scale backend
kubectl scale deployment acis-backend --replicas=5 -n acis-ai

# Auto-scaling (HPA)
kubectl autoscale deployment acis-backend \
  --cpu-percent=70 \
  --min=3 \
  --max=10 \
  -n acis-ai
```

---

## Monitoring Stack

### Prometheus

**Access**: http://localhost:9090

**Key Metrics**:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `process_cpu_seconds_total` - CPU usage
- `process_resident_memory_bytes` - Memory usage

**Query Examples**:
```promql
# Request rate
rate(http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

### Grafana

**Access**: http://localhost:3001
**Default Credentials**: admin/admin

**Dashboards**:
1. **API Overview**
   - Request rate
   - Response times
   - Error rates
   - Active connections

2. **Database Metrics**
   - Query performance
   - Connection pool
   - Cache hit ratio
   - Transaction rate

3. **System Metrics**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network traffic

### Alerts

Create alerts in Prometheus:

```yaml
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
```

---

## Environment Variables

### Required Variables

**Database**:
```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/acis-ai
PGPASSWORD=your-password
```

**API Keys**:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
SCHWAB_APP_KEY=your-schwab-key
SCHWAB_SECRET=your-schwab-secret
```

**Application**:
```bash
ENVIRONMENT=production  # development, staging, production
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
```

**Frontend**:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Monitoring** (optional):
```bash
GRAFANA_USER=admin
GRAFANA_PASSWORD=your-password
```

### Optional Variables

```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# Ngrok (for OAuth development)
NGROK_DOMAIN=acis.ngrok.app
NGROK_AUTH_TOKEN=your-token

# ML Models
MODEL_PATH=/app/models
LOG_PATH=/app/logs
```

---

## Troubleshooting

### Docker Issues

**Problem**: Container won't start
```bash
# Check logs
docker-compose logs backend

# Check if port is in use
sudo lsof -i :8000

# Restart service
docker-compose restart backend
```

**Problem**: Database connection failed
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U postgres -d acis-ai -c "SELECT 1"

# Check logs
docker-compose logs postgres
```

**Problem**: Out of disk space
```bash
# Clean up Docker
docker system prune -a --volumes

# Remove old images
docker images prune
```

### Kubernetes Issues

**Problem**: Pods not starting
```bash
# Describe pod
kubectl describe pod <pod-name> -n acis-ai

# Check events
kubectl get events -n acis-ai --sort-by='.lastTimestamp'

# Check node resources
kubectl top nodes
```

**Problem**: ImagePullBackOff
```bash
# Check image exists
docker images | grep acis

# Push to registry
docker tag acis-backend:latest your-registry/acis-backend:latest
docker push your-registry/acis-backend:latest

# Update deployment
kubectl set image deployment/acis-backend backend=your-registry/acis-backend:latest -n acis-ai
```

**Problem**: CrashLoopBackOff
```bash
# Check logs
kubectl logs <pod-name> -n acis-ai --previous

# Check liveness probe
kubectl describe pod <pod-name> -n acis-ai | grep -A 10 "Liveness"

# Increase startup time
kubectl patch deployment acis-backend -n acis-ai -p '{"spec":{"template":{"spec":{"containers":[{"name":"backend","livenessProbe":{"initialDelaySeconds":60}}]}}}}'
```

### Monitoring Issues

**Problem**: Prometheus not scraping
```bash
# Check targets
curl http://localhost:9090/api/v1/targets

# Check service discovery
curl http://localhost:9090/api/v1/sd

# Restart Prometheus
docker-compose restart prometheus
```

**Problem**: Grafana can't connect to Prometheus
```bash
# Test from Grafana container
docker-compose exec grafana curl http://prometheus:9090/api/v1/query?query=up

# Check datasource
# Go to Grafana > Configuration > Data Sources > Prometheus > Test
```

---

## Performance Tuning

### Backend

**Uvicorn workers**:
```bash
# In Dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Or set via environment
UVICORN_WORKERS=4
```

**Database connections**:
```python
# In database connection
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True
)
```

### PostgreSQL

```sql
-- Increase connections
ALTER SYSTEM SET max_connections = 200;

-- Tune memory
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';

-- Restart required
-- docker-compose restart postgres
```

### Kubernetes Resource Limits

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

---

## Security Checklist

- [ ] All secrets in Kubernetes secrets (not env vars)
- [ ] TLS enabled on ingress
- [ ] Network policies configured
- [ ] RBAC enabled
- [ ] Container images scanned for vulnerabilities
- [ ] Database encrypted at rest
- [ ] API rate limiting enabled
- [ ] CORS configured properly
- [ ] Security headers enabled
- [ ] Regular dependency updates

---

## Backup & Recovery

### Database Backup

```bash
# Manual backup
docker-compose exec postgres pg_dump -U postgres acis-ai > backup.sql

# Kubernetes backup
kubectl exec -n acis-ai postgres-0 -- pg_dump -U postgres acis-ai > backup.sql
```

### Database Restore

```bash
# Docker
docker-compose exec -T postgres psql -U postgres acis-ai < backup.sql

# Kubernetes
kubectl exec -i -n acis-ai postgres-0 -- psql -U postgres acis-ai < backup.sql
```

### Automated Backups

Use cron job in Kubernetes:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2am
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:14
            command:
            - sh
            - -c
            - pg_dump -U postgres -h postgres acis-ai | gzip > /backup/$(date +\%Y\%m\%d).sql.gz
```

---

## Next Steps

1. **Set up CI/CD** - Automate builds and deployments
2. **Configure monitoring alerts** - PagerDuty/Slack integration
3. **Set up log aggregation** - ELK or Loki stack
4. **Implement blue/green deployment** - Zero-downtime releases
5. **Set up disaster recovery** - Multi-region deployment

---

**Last Updated**: November 2, 2025
**Maintained By**: ACIS AI Platform Team
