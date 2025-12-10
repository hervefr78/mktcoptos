# ============================================================================
# MARKETER APP - DEVELOPMENT MAKEFILE
# ============================================================================
# Convenient commands for common development tasks

.PHONY: help
help: ## Show this help message
	@echo "Marketer App - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

.PHONY: setup
setup: ## Initial setup - create .env and install dependencies
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file - please review and update values"; \
	else \
		echo ".env file already exists"; \
	fi
	@echo "Installing backend dependencies..."
	@cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "Setup complete!"

.PHONY: env
env: ## Copy .env.example to .env
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ".env file created"; \
	else \
		echo ".env file already exists"; \
	fi

# ============================================================================
# DOCKER COMMANDS
# ============================================================================

.PHONY: up
up: ## Start all services with docker-compose
	docker-compose up

.PHONY: up-build
up-build: ## Build and start all services
	docker-compose up --build

.PHONY: up-d
up-d: ## Start all services in detached mode
	docker-compose up -d

.PHONY: down
down: ## Stop all services
	docker-compose down

.PHONY: down-v
down-v: ## Stop all services and remove volumes
	docker-compose down -v

.PHONY: restart
restart: ## Restart all services
	docker-compose restart

.PHONY: logs
logs: ## View logs from all services
	docker-compose logs -f

.PHONY: logs-backend
logs-backend: ## View backend logs
	docker-compose logs -f backend

.PHONY: logs-frontend
logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

.PHONY: ps
ps: ## Show running containers
	docker-compose ps

# ============================================================================
# DATABASE COMMANDS
# ============================================================================

.PHONY: db-shell
db-shell: ## Connect to PostgreSQL shell
	docker-compose exec -e PGPASSWORD=$${POSTGRES_PASSWORD:-marketer_pass} postgres psql -U marketer_user -d marketer_db

.PHONY: db-reset
db-reset: ## Reset database (WARNING: destroys all data)
	@echo "WARNING: This will destroy all database data!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	docker-compose down -v
	docker-compose up -d postgres
	@echo "Database reset complete"

.PHONY: db-migrate
db-migrate: ## Run database migrations (when Alembic is set up)
	docker-compose exec backend alembic upgrade head

.PHONY: db-migrate-create
db-migrate-create: ## Create new migration
	@read -p "Migration name: " name; \
	docker-compose exec backend alembic revision --autogenerate -m "$$name"

.PHONY: db-backup
db-backup: ## Backup database to ./backups/
	@mkdir -p backups
	docker-compose exec -T -e PGPASSWORD=$${POSTGRES_PASSWORD:-marketer_pass} postgres pg_dump -U marketer_user marketer_db > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup created in backups/"

.PHONY: db-restore
db-restore: ## Restore database from backup (provide file=backups/file.sql)
	@if [ -z "$(file)" ]; then \
		echo "Usage: make db-restore file=backups/backup_YYYYMMDD_HHMMSS.sql"; \
		exit 1; \
	fi
	docker-compose exec -T -e PGPASSWORD=$${POSTGRES_PASSWORD:-marketer_pass} postgres psql -U marketer_user marketer_db < $(file)
	@echo "Database restored from $(file)"

# ============================================================================
# BACKEND COMMANDS
# ============================================================================

.PHONY: backend-shell
backend-shell: ## Open shell in backend container
	docker-compose exec backend /bin/bash

.PHONY: backend-test
backend-test: ## Run backend tests
	docker-compose exec backend pytest

.PHONY: backend-test-cov
backend-test-cov: ## Run backend tests with coverage
	docker-compose exec backend pytest --cov=app --cov-report=html --cov-report=term

.PHONY: backend-lint
backend-lint: ## Lint backend code (when linting tools are set up)
	docker-compose exec backend flake8 app/

.PHONY: backend-format
backend-format: ## Format backend code (when black is installed)
	docker-compose exec backend black app/

.PHONY: backend-type
backend-type: ## Type check backend (when mypy is installed)
	docker-compose exec backend mypy app/

# ============================================================================
# FRONTEND COMMANDS
# ============================================================================

.PHONY: frontend-shell
frontend-shell: ## Open shell in frontend container
	docker-compose exec frontend /bin/sh

.PHONY: frontend-test
frontend-test: ## Run frontend tests
	docker-compose exec frontend npm test

.PHONY: frontend-build
frontend-build: ## Build frontend for production
	docker-compose exec frontend npm run build

.PHONY: frontend-lint
frontend-lint: ## Lint frontend code (when ESLint is set up)
	docker-compose exec frontend npm run lint

.PHONY: frontend-format
frontend-format: ## Format frontend code (when Prettier is set up)
	docker-compose exec frontend npm run format

# ============================================================================
# OLLAMA COMMANDS
# ============================================================================

.PHONY: ollama-pull
ollama-pull: ## Pull Ollama model (default: llama3)
	docker-compose exec ollama ollama pull $(or $(model),llama3)

.PHONY: ollama-list
ollama-list: ## List available Ollama models
	docker-compose exec ollama ollama list

.PHONY: ollama-run
ollama-run: ## Run Ollama model interactively
	docker-compose exec ollama ollama run $(or $(model),llama3)

# ============================================================================
# DEVELOPMENT COMMANDS
# ============================================================================

.PHONY: dev
dev: env up-build ## Complete development setup and start

.PHONY: dev-quick
dev-quick: up-d ## Quick start (detached mode)
	@echo "Services starting in background..."
	@echo "Run 'make logs' to view logs"

.PHONY: clean
clean: ## Clean up containers, volumes, and cache
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete"

.PHONY: health
health: ## Check health of all services
	@echo "Checking service health..."
	@echo "\nPostgreSQL:"
	@docker-compose exec -T postgres pg_isready -U marketer_user || echo "  Not ready"
	@echo "\nRedis:"
	@docker-compose exec -T redis redis-cli ping || echo "  Not ready"
	@echo "\nBackend API:"
	@curl -sf http://localhost:8000/health || echo "  Not ready"
	@echo "\nChromaDB:"
	@curl -sf http://localhost:8001/api/v1/heartbeat || echo "  Not ready"
	@echo "\nOllama:"
	@curl -sf http://localhost:11434/api/tags || echo "  Not ready"

.PHONY: status
status: ps health ## Show status of all services

# ============================================================================
# TESTING
# ============================================================================

.PHONY: test
test: backend-test ## Run all tests

.PHONY: test-all
test-all: backend-test frontend-test ## Run backend and frontend tests

.PHONY: test-watch
test-watch: ## Run tests in watch mode
	docker-compose exec backend pytest -f

# ============================================================================
# MONITORING
# ============================================================================

.PHONY: stats
stats: ## Show Docker stats for all containers
	docker stats $(shell docker-compose ps -q)

.PHONY: top
top: ## Show running processes in containers
	docker-compose top

# ============================================================================
# REDIS COMMANDS
# ============================================================================

.PHONY: redis-shell
redis-shell: ## Connect to Redis CLI
	docker-compose exec redis redis-cli

.PHONY: redis-flush
redis-flush: ## Flush all Redis data (WARNING: clears cache)
	@echo "WARNING: This will clear all Redis data!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	docker-compose exec redis redis-cli FLUSHALL
	@echo "Redis flushed"

# ============================================================================
# PRODUCTION BUILD
# ============================================================================

.PHONY: build
build: ## Build production images
	docker-compose build

.PHONY: prod-test
prod-test: ## Test production build locally
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up

# ============================================================================
# DOCKER SWARM DEPLOYMENT
# ============================================================================

.PHONY: swarm-init
swarm-init: ## Initialize Docker Swarm on this node
	docker swarm init
	@echo "Swarm initialized! This node is now a manager."
	@echo "To add workers, run the join command shown above on other nodes."

.PHONY: swarm-deploy
swarm-deploy: ## Deploy stack to Docker Swarm
	@if [ ! -f .env.prod ]; then \
		echo "Error: .env.prod not found. Copy .env.production and configure it."; \
		exit 1; \
	fi
	docker stack deploy -c docker-stack.yml --env-file .env.prod marketer
	@echo "Stack deployed! Check status with: make swarm-status"

.PHONY: swarm-update
swarm-update: ## Update running Swarm stack
	docker stack deploy -c docker-stack.yml --env-file .env.prod marketer
	@echo "Stack updated!"

.PHONY: swarm-remove
swarm-remove: ## Remove stack from Swarm
	@echo "WARNING: This will remove the entire stack!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	docker stack rm marketer
	@echo "Stack removed. Volumes remain. Use 'docker volume prune' to remove volumes."

.PHONY: swarm-status
swarm-status: ## Show Swarm stack status
	@echo "=== Stack Services ==="
	docker stack services marketer
	@echo "\n=== Stack Tasks ==="
	docker stack ps marketer --no-trunc

.PHONY: swarm-logs
swarm-logs: ## View logs from Swarm service (usage: make swarm-logs service=backend)
	@if [ -z "$(service)" ]; then \
		echo "Usage: make swarm-logs service=<service-name>"; \
		echo "Available services: backend, frontend, worker, postgres, redis, ollama, chromadb"; \
		exit 1; \
	fi
	docker service logs -f marketer_$(service)

.PHONY: swarm-scale
swarm-scale: ## Scale a service (usage: make swarm-scale service=backend replicas=3)
	@if [ -z "$(service)" ] || [ -z "$(replicas)" ]; then \
		echo "Usage: make swarm-scale service=<name> replicas=<number>"; \
		exit 1; \
	fi
	docker service scale marketer_$(service)=$(replicas)
	@echo "Service scaled. Check status with: make swarm-status"

.PHONY: swarm-rollback
swarm-rollback: ## Rollback a service to previous version (usage: make swarm-rollback service=backend)
	@if [ -z "$(service)" ]; then \
		echo "Usage: make swarm-rollback service=<service-name>"; \
		exit 1; \
	fi
	docker service rollback marketer_$(service)
	@echo "Service rolled back!"

.PHONY: swarm-build-push
swarm-build-push: ## Build and push images to registry (set REGISTRY env var)
	@if [ -z "$(REGISTRY)" ]; then \
		echo "Error: REGISTRY environment variable not set"; \
		echo "Usage: REGISTRY=your-registry.com make swarm-build-push"; \
		exit 1; \
	fi
	@echo "Building and pushing to $(REGISTRY)..."
	docker build -t $(REGISTRY)/marketer-backend:$(or $(VERSION),latest) ./backend
	docker build -t $(REGISTRY)/marketer-frontend:$(or $(VERSION),latest) ./frontend
	docker push $(REGISTRY)/marketer-backend:$(or $(VERSION),latest)
	docker push $(REGISTRY)/marketer-frontend:$(or $(VERSION),latest)
	@echo "Images pushed successfully!"

.PHONY: swarm-visualizer
swarm-visualizer: ## Deploy Swarm visualizer for monitoring
	docker service create \
		--name=visualizer \
		--publish=8888:8080 \
		--constraint=node.role==manager \
		--mount=type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
		dockersamples/visualizer
	@echo "Visualizer deployed! Access at http://localhost:8888"

.PHONY: swarm-health
swarm-health: ## Check health of all Swarm services
	@echo "Checking Swarm service health..."
	@docker stack services marketer --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}"

.PHONY: swarm-nodes
swarm-nodes: ## List all Swarm nodes
	docker node ls

.PHONY: swarm-leave
swarm-leave: ## Leave Swarm (WARNING: destructive)
	@echo "WARNING: This will remove this node from the Swarm!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	docker swarm leave --force

# ============================================================================
# UTILITY COMMANDS
# ============================================================================

.PHONY: install-hooks
install-hooks: ## Install git pre-commit hooks (when pre-commit is set up)
	pre-commit install

.PHONY: update-deps
update-deps: ## Update all dependencies
	cd backend && pip install --upgrade -r requirements.txt
	cd frontend && npm update

.PHONY: check-deps
check-deps: ## Check for outdated dependencies
	@echo "Backend dependencies:"
	cd backend && pip list --outdated
	@echo "\nFrontend dependencies:"
	cd frontend && npm outdated
