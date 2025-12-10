# Docker Swarm Deployment Guide

Complete guide to deploying Marketer App to production using Docker Swarm.

## Why Docker Swarm?

- **Simple**: Uses familiar docker-compose syntax
- **Built-in**: No additional tools needed
- **Scalable**: Easy horizontal scaling
- **Resilient**: Automatic failover and health checks
- **Cost-effective**: Run on any Linux server(s)

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Single-Node Setup](#single-node-setup)
3. [Multi-Node Cluster](#multi-node-cluster)
4. [Deployment](#deployment)
5. [Scaling](#scaling)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Topics](#advanced-topics)

---

## Prerequisites

### Server Requirements

**Minimum (Single Node)**:
- 4 CPU cores
- 8 GB RAM
- 40 GB disk space
- Ubuntu 22.04 LTS (or any Docker-compatible Linux)
- Docker 20.10+ and Docker Compose

**Recommended (Production)**:
- 8 CPU cores
- 16 GB RAM
- 100 GB SSD
- Load balancer (Traefik included)

### VPS Providers

Good options for running Docker Swarm:
- **DigitalOcean**: Droplet $24/month (4 vCPU, 8GB RAM)
- **Hetzner**: CX31 $9/month (2 vCPU, 8GB RAM)
- **Linode**: Dedicated 8GB $36/month
- **Vultr**: High Frequency 8GB $24/month

### Local Requirements

- SSH access to server(s)
- Docker installed locally (for building images)
- Git

---

## Single-Node Setup

Perfect for staging, small production, or testing.

### Step 1: Prepare Server

```bash
# SSH into your server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Enable Docker to start on boot
systemctl enable docker
systemctl start docker

# Verify installation
docker --version
```

### Step 2: Configure Firewall

```bash
# Allow SSH, HTTP, HTTPS
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 2377/tcp  # Swarm management
ufw allow 7946/tcp  # Swarm node communication
ufw allow 7946/udp
ufw allow 4789/udp  # Swarm overlay network
ufw enable
```

### Step 3: Initialize Docker Swarm

```bash
# Initialize Swarm
docker swarm init

# You'll see output like:
# Swarm initialized: current node (xxx) is now a manager.
```

### Step 4: Clone Repository

```bash
# Create app directory
mkdir -p /opt/marketer
cd /opt/marketer

# Clone your repository
git clone https://github.com/yourusername/marketingAssistant.git .
```

### Step 5: Configure Environment

```bash
# Copy production environment template
cp .env.production .env.prod

# Edit with your settings
nano .env.prod
```

**Critical settings to update**:
```bash
# Strong passwords!
POSTGRES_PASSWORD=your-super-strong-password-here
ADMIN_PASSWORD=your-admin-password-here

# Generate secret key
SECRET_KEY=$(openssl rand -hex 32)

# Your domain (or server IP)
API_URL=https://api.yourdomain.com

# Email for SSL certificates
ACME_EMAIL=admin@yourdomain.com

# Docker registry (if using one)
REGISTRY=docker.io/yourusername
```

### Step 6: Build Images (Option A - Local Registry)

For single-node, you can build locally:

```bash
# Build images locally
docker build -t localhost/marketer-backend:latest ./backend
docker build -t localhost/marketer-frontend:latest ./frontend
```

### Step 6: Build Images (Option B - Docker Hub)

For multi-node, use a registry:

```bash
# Login to Docker Hub
docker login

# Build and push
export REGISTRY=docker.io/yourusername
export VERSION=1.0.0

make swarm-build-push
```

### Step 7: Deploy Stack

```bash
# Deploy to Swarm
make swarm-deploy

# OR manually:
docker stack deploy -c docker-stack.yml --env-file .env.prod marketer
```

### Step 8: Verify Deployment

```bash
# Check services
make swarm-status

# Check specific service logs
make swarm-logs service=backend

# All services should show 1/1 or 2/2 replicas running
```

### Step 9: Access Application

```bash
# Get your server IP
curl -4 icanhazip.com

# Access in browser:
# http://YOUR_SERVER_IP          (Frontend)
# http://YOUR_SERVER_IP:8000     (Backend API)
# http://YOUR_SERVER_IP:8080     (Traefik Dashboard)
```

---

## Multi-Node Cluster

For high availability and better performance.

### Architecture

```
┌─────────────────┐
│  Manager Node   │  (Leader - runs stateful services)
│  - PostgreSQL   │
│  - Redis        │
│  - Traefik      │
└────────┬────────┘
         │
    ┌────┴─────┐
    │          │
┌───▼──┐   ┌───▼──┐
│Worker│   │Worker│  (Run stateless services)
│ Node │   │ Node │
│      │   │      │
└──────┘   └──────┘
```

### Setup Manager Node

```bash
# On manager node
ssh root@manager-ip

# Initialize Swarm
docker swarm init --advertise-addr MANAGER_IP

# Save the join token shown
```

### Setup Worker Nodes

```bash
# On each worker node
ssh root@worker-ip

# Join the swarm (use token from manager)
docker swarm join --token SWMTKN-1-xxxxx MANAGER_IP:2377
```

### Label Nodes

```bash
# On manager node, label nodes for specific workloads

# Label a node with GPU for Ollama
docker node update --label-add gpu=true worker-1

# Label nodes for different roles
docker node update --label-add role=api worker-1
docker node update --label-add role=worker worker-2
```

### Deploy to Cluster

```bash
# Same deployment process
make swarm-deploy
```

Services will automatically distribute across nodes based on:
- Placement constraints
- Resource requirements
- Node labels

---

## Deployment

### Initial Deployment

```bash
# 1. Prepare environment
cp .env.production .env.prod
nano .env.prod  # Configure

# 2. Build and push images (if using registry)
export REGISTRY=docker.io/yourusername
make swarm-build-push

# 3. Deploy stack
make swarm-deploy

# 4. Verify
make swarm-status
make swarm-health
```

### Update Deployment

```bash
# Update code
git pull origin main

# Rebuild images
make swarm-build-push

# Update stack (rolling update)
make swarm-update
```

Services will update one by one (zero downtime).

### Rollback Deployment

```bash
# Rollback specific service
make swarm-rollback service=backend

# Swarm automatically reverts to previous version
```

---

## Scaling

### Manual Scaling

```bash
# Scale backend to 4 replicas
make swarm-scale service=backend replicas=4

# Scale workers to 3 replicas
make swarm-scale service=worker replicas=3

# Check status
make swarm-status
```

### Auto-scaling Preparation

Swarm doesn't have built-in auto-scaling, but you can:

1. **Monitor metrics**:
```bash
# Add Prometheus/Grafana for monitoring
# Create alerts for high CPU/memory
```

2. **Scale based on metrics**:
```bash
# Create cron job or script
if [ $CPU_USAGE -gt 80 ]; then
  make swarm-scale service=backend replicas=4
fi
```

3. **Consider external tools**:
- Orbiter (Docker Swarm auto-scaler)
- Custom scripts with monitoring

---

## Monitoring

### Built-in Monitoring

```bash
# Service status
make swarm-status

# Service logs
make swarm-logs service=backend

# Health check
make swarm-health

# Node status
make swarm-nodes
```

### Swarm Visualizer

Visual representation of your cluster:

```bash
# Deploy visualizer
make swarm-visualizer

# Access at http://your-server:8888
```

### Traefik Dashboard

Monitor HTTP traffic and services:

```bash
# Access at http://your-server:8080
# Configure in docker-stack.yml
```

### Advanced Monitoring Stack

Add Prometheus + Grafana:

```yaml
# Add to docker-stack.yml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana:latest
  ports:
    - "3001:3000"
  environment:
    GF_SECURITY_ADMIN_PASSWORD: admin
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check service status
docker service ps marketer_backend --no-trunc

# Check logs
docker service logs marketer_backend

# Common issues:
# - Image not found (check REGISTRY in .env.prod)
# - Resource constraints (check 'docker node ls')
# - Configuration errors (check .env.prod)
```

### Database Connection Issues

```bash
# Check PostgreSQL service
docker service ps marketer_postgres

# Check logs
docker service logs marketer_postgres

# Connect to database
docker exec -it $(docker ps -q -f name=marketer_postgres) \
  psql -U marketer_user -d marketer_db
```

### Service Unhealthy

```bash
# Check health status
docker service ps marketer_backend

# If health checks failing:
# 1. Check logs
docker service logs marketer_backend

# 2. Check if /health endpoint works
docker exec -it $(docker ps -q -f name=marketer_backend) \
  curl localhost:8000/health

# 3. Adjust health check in docker-stack.yml
```

### Volumes Not Persisting

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect marketer_postgres_data

# Backup volume
docker run --rm \
  -v marketer_postgres_data:/data \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/postgres-backup.tar.gz /data
```

### Rolling Update Stuck

```bash
# Check update status
docker service ps marketer_backend

# Force update
docker service update --force marketer_backend

# Or rollback
make swarm-rollback service=backend
```

---

## Advanced Topics

### SSL/TLS with Let's Encrypt

Traefik is configured to auto-generate SSL certificates:

1. **Update DNS**: Point your domain to server IP
2. **Configure .env.prod**:
```bash
ACME_EMAIL=your-email@example.com
```
3. **Update docker-stack.yml labels**:
```yaml
labels:
  - "traefik.http.routers.backend.tls=true"
  - "traefik.http.routers.backend.tls.certresolver=letsencrypt"
```

### Database Backups

Automated backup setup:

```bash
# Create backup script
cat > /opt/marketer/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec $(docker ps -q -f name=marketer_postgres) \
  pg_dump -U marketer_user marketer_db | \
  gzip > /opt/backups/marketer_${DATE}.sql.gz
# Keep only last 7 days
find /opt/backups -name "marketer_*.sql.gz" -mtime +7 -delete
EOF

chmod +x /opt/marketer/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /opt/marketer/backup.sh
```

### Secrets Management

Use Docker secrets for sensitive data:

```bash
# Create secrets
echo "strong-password" | docker secret create postgres_password -
echo "admin-pass" | docker secret create admin_password -

# Update docker-stack.yml
environment:
  POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password

secrets:
  - postgres_password

secrets:
  postgres_password:
    external: true
```

### CI/CD Integration

GitHub Actions example:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Swarm

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Build and push
        run: |
          docker build -t ${{ secrets.REGISTRY }}/marketer-backend:${{ github.sha }} ./backend
          docker push ${{ secrets.REGISTRY }}/marketer-backend:${{ github.sha }}

      - name: Deploy to Swarm
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/marketer
            git pull
            export VERSION=${{ github.sha }}
            make swarm-update
```

### Multi-Region Deployment

For global deployment:

```bash
# Setup Swarm in each region
# Region 1 (US)
docker swarm init --advertise-addr us-manager-ip

# Region 2 (EU)
docker swarm init --advertise-addr eu-manager-ip

# Use GeoDNS to route users to nearest region
```

---

## Quick Command Reference

```bash
# Deployment
make swarm-init          # Initialize Swarm
make swarm-deploy        # Deploy stack
make swarm-update        # Update stack
make swarm-remove        # Remove stack

# Monitoring
make swarm-status        # Service status
make swarm-health        # Health check
make swarm-logs service=backend  # View logs

# Scaling
make swarm-scale service=backend replicas=3

# Rollback
make swarm-rollback service=backend

# Utilities
make swarm-visualizer    # Deploy visual monitor
make swarm-nodes         # List cluster nodes
```

---

## Cost Estimates

### Single Node Setup

| Provider | Specs | Cost/Month |
|----------|-------|------------|
| Hetzner CX31 | 2 vCPU, 8GB RAM | $9 |
| DigitalOcean | 4 vCPU, 8GB RAM | $48 |
| Linode | 4 vCPU, 8GB RAM | $36 |

### 3-Node Cluster

| Configuration | Cost/Month |
|---------------|------------|
| 1 Manager (8GB) + 2 Workers (4GB) | ~$40-60 |
| 3 Managers (8GB each) | ~$75-120 |

### Additional Costs

- Domain name: $10-15/year
- Backups: $5-10/month (optional)
- Monitoring (external): $0-20/month

---

## Next Steps

1. **Test locally**: Use `make dev` to test everything works
2. **Deploy to staging**: Single-node Swarm for testing
3. **Configure monitoring**: Add Prometheus/Grafana
4. **Setup backups**: Automate database backups
5. **Scale**: Add worker nodes as needed
6. **Secure**: SSL certificates, firewall, secrets

## Support

For issues:
- Check logs: `make swarm-logs service=<name>`
- Review [Troubleshooting](#troubleshooting) section
- Docker Swarm docs: https://docs.docker.com/engine/swarm/
