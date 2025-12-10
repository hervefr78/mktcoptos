# Docker Swarm - Quick Reference

One-page cheat sheet for Docker Swarm deployment and management.

## Setup (One-Time)

```bash
# On your server
./scripts/server-setup.sh           # Prepare fresh server
./scripts/swarm-deploy.sh --init    # Initialize Swarm
```

## Deployment

```bash
# Configure environment
cp .env.production .env.prod
nano .env.prod  # Update passwords, secrets, domain

# Deploy stack
make swarm-deploy
# OR
./scripts/swarm-deploy.sh --deploy

# Check status
make swarm-status
```

## Common Commands

### Stack Management

```bash
make swarm-deploy        # Deploy or update stack
make swarm-status        # Show service status
make swarm-remove        # Remove stack
make swarm-health        # Health check
```

### Logs & Monitoring

```bash
make swarm-logs service=backend      # View service logs
make swarm-logs service=frontend
make swarm-logs service=worker
make swarm-logs service=postgres

make swarm-visualizer    # Deploy visual monitor (port 8888)
```

### Scaling

```bash
make swarm-scale service=backend replicas=4
make swarm-scale service=worker replicas=3
make swarm-scale service=frontend replicas=2
```

### Updates & Rollbacks

```bash
# Update application
git pull
make swarm-build-push    # Build & push new images
make swarm-update        # Rolling update

# Rollback if needed
make swarm-rollback service=backend
```

### Node Management

```bash
make swarm-nodes         # List cluster nodes
docker node ls           # Same as above

# Label nodes
docker node update --label-add gpu=true node-1
docker node update --label-add role=worker node-2
```

## Direct Docker Commands

### Stack

```bash
docker stack ls                                    # List stacks
docker stack services marketer                     # List services
docker stack ps marketer                          # List tasks
docker stack rm marketer                          # Remove stack
```

### Services

```bash
docker service ls                                  # List all services
docker service ps marketer_backend                # Service tasks
docker service logs -f marketer_backend           # Service logs
docker service inspect marketer_backend           # Service details
docker service scale marketer_backend=3           # Scale service
docker service update --force marketer_backend    # Force update
docker service rollback marketer_backend          # Rollback
```

### Nodes

```bash
docker node ls                                     # List nodes
docker node inspect node-1                        # Node details
docker node update --availability drain node-1    # Drain node
docker node update --availability active node-1   # Activate node
```

### Swarm

```bash
docker swarm init                                 # Initialize swarm
docker swarm join-token manager                   # Get manager token
docker swarm join-token worker                    # Get worker token
docker swarm leave --force                        # Leave swarm
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
docker service ps marketer_backend --no-trunc

# View detailed logs
docker service logs marketer_backend --tail 100

# Check events
docker events --filter 'type=service'

# Inspect service
docker service inspect marketer_backend
```

### Update Failed

```bash
# Check update status
docker service ps marketer_backend

# Rollback
make swarm-rollback service=backend

# Force update
docker service update --force marketer_backend
```

### Database Issues

```bash
# Connect to PostgreSQL
docker exec -it $(docker ps -q -f name=marketer_postgres) bash
psql -U marketer_user -d marketer_db

# Check database logs
make swarm-logs service=postgres

# Backup database
make db-backup
```

### Network Issues

```bash
# List networks
docker network ls

# Inspect overlay network
docker network inspect marketer_marketer_network

# Check connectivity
docker exec -it <container-id> ping postgres
```

## Useful Queries

### Resource Usage

```bash
# Service resource usage
docker stats $(docker ps -q -f name=marketer)

# Node resource usage
docker node ls --format "table {{.Hostname}}\t{{.Status}}\t{{.Availability}}"
```

### Service Information

```bash
# Which node is service running on?
docker service ps marketer_backend --format "{{.Name}}\t{{.Node}}"

# How many replicas?
docker service ls --format "table {{.Name}}\t{{.Replicas}}"

# Service update status
docker service ps marketer_backend --filter "desired-state=running"
```

## Environment Files

```bash
# Development (.env)
make dev                 # Uses docker-compose.yml + .env

# Production (.env.prod)
make swarm-deploy        # Uses docker-stack.yml + .env.prod
```

## Ports & Access

| Service | Port | Access |
|---------|------|--------|
| Frontend | 80/443 | http://your-domain.com |
| Backend API | 8000 | http://api.your-domain.com |
| Traefik Dashboard | 8080 | http://your-server:8080 |
| Visualizer | 8888 | http://your-server:8888 |
| PostgreSQL | 5432 | Internal only |
| Redis | 6379 | Internal only |
| ChromaDB | 8001 | Internal only |
| Ollama | 11434 | Internal only |

## Backup & Restore

```bash
# Backup database
make db-backup

# Manual backup
docker exec $(docker ps -q -f name=marketer_postgres) \
  pg_dump -U marketer_user marketer_db > backup.sql

# Restore
docker exec -i $(docker ps -q -f name=marketer_postgres) \
  psql -U marketer_user marketer_db < backup.sql

# Backup volumes
docker run --rm \
  -v marketer_postgres_data:/data \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/postgres-data.tar.gz /data
```

## Security

```bash
# Create Docker secret
echo "secret-value" | docker secret create my_secret -

# List secrets
docker secret ls

# Use in service
docker service update --secret-add my_secret marketer_backend

# Update SSL certificates (automatic with Traefik)
# Just point your domain to server IP
```

## Performance

```bash
# Limit service resources
docker service update \
  --limit-cpu 1 \
  --limit-memory 1g \
  marketer_backend

# Reserve resources
docker service update \
  --reserve-cpu 0.5 \
  --reserve-memory 512m \
  marketer_backend
```

## Emergency Procedures

### Complete Stack Restart

```bash
make swarm-remove        # Remove stack
make swarm-deploy        # Redeploy
```

### Drain Node (Maintenance)

```bash
docker node update --availability drain node-1
# Wait for tasks to move
# Perform maintenance
docker node update --availability active node-1
```

### Force Service Restart

```bash
docker service update --force marketer_backend
```

### Emergency Rollback

```bash
# Rollback all services
for service in $(docker service ls --format '{{.Name}}'); do
  docker service rollback $service
done
```

## Cost Optimization

```bash
# Scale down non-critical services
make swarm-scale service=worker replicas=1
make swarm-scale service=backend replicas=1

# Scale up for high traffic
make swarm-scale service=backend replicas=4
make swarm-scale service=frontend replicas=3
```

## Monitoring URLs

After deployment, access:

- Application: `http://your-domain.com`
- API Docs: `http://api.your-domain.com/docs`
- Traefik: `http://your-server:8080`
- Visualizer: `http://your-server:8888`
- Health: `http://api.your-domain.com/health`

## Resources

- Full guide: [docs/SWARM_DEPLOYMENT.md](SWARM_DEPLOYMENT.md)
- Docker Swarm docs: https://docs.docker.com/engine/swarm/
- Traefik docs: https://doc.traefik.io/traefik/

---

**Pro Tip**: Use `make help` to see all available commands!
