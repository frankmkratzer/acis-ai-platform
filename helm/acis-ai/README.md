# ACIS AI Platform Helm Chart

This Helm chart deploys the ACIS AI Platform on Kubernetes.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.0+
- kubectl configured
- Ingress controller (nginx recommended)
- cert-manager for TLS certificates

## Installation

### 1. Add Dependencies

```bash
cd helm/acis-ai
helm dependency update
```

### 2. Create Namespace

```bash
kubectl create namespace acis-ai
```

### 3. Create Secrets

```bash
kubectl create secret generic acis-secrets \
  --from-literal=database-url='postgresql://postgres:password@postgres:5432/acis-ai' \
  --from-literal=postgres-password='your-postgres-password' \
  --from-literal=anthropic-api-key='your-anthropic-key' \
  --from-literal=schwab-app-key='your-schwab-key' \
  --from-literal=schwab-secret='your-schwab-secret' \
  -n acis-ai
```

### 4. Install Chart

**Development:**
```bash
helm install acis-ai . -n acis-ai -f values-dev.yaml
```

**Production:**
```bash
helm install acis-ai . -n acis-ai -f values-prod.yaml
```

**Custom values:**
```bash
helm install acis-ai . -n acis-ai \
  --set backend.replicaCount=5 \
  --set ingress.enabled=true
```

## Upgrading

```bash
# Development
helm upgrade acis-ai . -n acis-ai -f values-dev.yaml

# Production
helm upgrade acis-ai . -n acis-ai -f values-prod.yaml
```

## Uninstalling

```bash
helm uninstall acis-ai -n acis-ai
```

## Configuration

### Backend Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `backend.enabled` | Enable backend deployment | `true` |
| `backend.replicaCount` | Number of backend replicas | `3` |
| `backend.image.repository` | Backend image repository | `acis-ai-backend` |
| `backend.image.tag` | Backend image tag | `latest` |
| `backend.resources.limits.cpu` | CPU limit | `2000m` |
| `backend.resources.limits.memory` | Memory limit | `2Gi` |
| `backend.autoscaling.enabled` | Enable HPA | `true` |
| `backend.autoscaling.minReplicas` | Minimum replicas | `3` |
| `backend.autoscaling.maxReplicas` | Maximum replicas | `10` |

### Frontend Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `frontend.enabled` | Enable frontend deployment | `true` |
| `frontend.replicaCount` | Number of frontend replicas | `2` |
| `frontend.image.repository` | Frontend image repository | `acis-ai-frontend` |
| `frontend.image.tag` | Frontend image tag | `latest` |

### Database Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable PostgreSQL | `true` |
| `postgresql.auth.database` | Database name | `acis-ai` |
| `postgresql.primary.persistence.size` | Storage size | `50Gi` |

### Redis Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Enable Redis | `true` |
| `redis.master.persistence.size` | Storage size | `8Gi` |

### Ingress Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class | `nginx` |
| `ingress.hosts[0].host` | API hostname | `api.acis-ai.com` |
| `ingress.hosts[1].host` | App hostname | `app.acis-ai.com` |

### Monitoring Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `monitoring.enabled` | Enable monitoring stack | `true` |
| `monitoring.prometheus.enabled` | Enable Prometheus | `true` |
| `monitoring.grafana.enabled` | Enable Grafana | `true` |

## Verification

### Check Deployment Status

```bash
# Check all pods
kubectl get pods -n acis-ai

# Check services
kubectl get svc -n acis-ai

# Check ingress
kubectl get ingress -n acis-ai

# Check HPA
kubectl get hpa -n acis-ai
```

### View Logs

```bash
# Backend logs
kubectl logs -f deployment/acis-backend -n acis-ai

# Frontend logs
kubectl logs -f deployment/acis-frontend -n acis-ai

# PostgreSQL logs
kubectl logs -f statefulset/postgres -n acis-ai
```

### Port Forwarding

```bash
# Backend API
kubectl port-forward svc/acis-backend 8000:8000 -n acis-ai

# Frontend
kubectl port-forward svc/acis-frontend 3000:3000 -n acis-ai

# Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n acis-ai

# Grafana
kubectl port-forward svc/grafana 3000:3000 -n acis-ai
```

## Scaling

### Manual Scaling

```bash
# Scale backend
kubectl scale deployment acis-backend --replicas=10 -n acis-ai

# Scale frontend
kubectl scale deployment acis-frontend --replicas=5 -n acis-ai
```

### Auto-scaling

HPA is enabled by default for backend and frontend. Configure in values:

```yaml
backend:
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
```

## Troubleshooting

### Pods Not Starting

```bash
# Describe pod
kubectl describe pod <pod-name> -n acis-ai

# Check events
kubectl get events -n acis-ai --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n acis-ai
```

### Database Connection Issues

```bash
# Test database connection
kubectl exec -it deployment/acis-backend -n acis-ai -- \
  psql -h postgres -U postgres -d acis-ai -c "SELECT 1"
```

### Ingress Issues

```bash
# Check ingress
kubectl describe ingress acis-ingress -n acis-ai

# Check ingress controller
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

## Backup and Restore

### Backup Database

```bash
kubectl exec -n acis-ai postgres-0 -- \
  pg_dump -U postgres acis-ai > backup.sql
```

### Restore Database

```bash
kubectl exec -i -n acis-ai postgres-0 -- \
  psql -U postgres acis-ai < backup.sql
```

## Support

For issues and questions:
- GitHub: https://github.com/frankmkratzer/acis-ai-platform
- Documentation: [DEPLOYMENT_GUIDE.md](../../DEPLOYMENT_GUIDE.md)
