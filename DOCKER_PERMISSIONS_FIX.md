# Docker Permissions Fix

## Issue
The current user does not have permission to access the Docker daemon socket. This prevents running Docker and Docker Compose commands.

## Solution

Add your user to the `docker` group:

```bash
# Add your user to the docker group
sudo usermod -aG docker $USER

# Apply the new group membership (requires logout/login or run this)
newgrp docker

# Verify group membership
groups | grep docker
```

## After Fix

Once the user is added to the docker group, you can run:

```bash
# Start all services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## Alternative (Temporary)

If you need to run Docker commands immediately without logging out:

```bash
# Run with sudo (not recommended for regular use)
sudo docker compose up -d

# Or start a new shell with the docker group
newgrp docker
```

## Testing the Fix

After adding the user to the docker group:

```bash
# Test Docker access
docker ps

# Test Docker Compose
docker compose version

# Start the ACIS AI Platform
cd /home/fkratzer/acis-ai-platform
docker compose up -d
```

## Services to Verify

After starting with `docker compose up -d`, verify all services are healthy:

```bash
# Check all services
docker compose ps

# Should see:
# - postgres (healthy)
# - redis (healthy)
# - backend (healthy)
# - frontend (healthy)
# - prometheus (running)
# - grafana (running)
# - node-exporter (running)
# - postgres-exporter (running)
```

## Accessing Services

Once running:
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs
- Frontend: http://localhost:3000
- Grafana: http://localhost:3001 (admin/admin)
- Prometheus: http://localhost:9090
