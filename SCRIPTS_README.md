# Marketing Assistant - Launch Scripts

This directory contains helper scripts to manage the Marketing Assistant application.

## Quick Start

```bash
./launch.sh
```

This will:
- Stop any existing containers
- Build and start all services
- Wait for services to be healthy
- Optionally install Ollama models
- Display access information

## Available Scripts

### `launch.sh`
**Main launch script** - Starts the entire application with all dependencies.

```bash
./launch.sh
```

Features:
- Checks Docker is running
- Builds and starts all containers
- Waits for services to be healthy
- Offers to install Ollama models if none exist
- Shows service status and access URLs

### `stop.sh`
**Stop all services**

```bash
./stop.sh
```

To remove all data (including database and Ollama models):
```bash
docker compose down -v
```

### `restart.sh`
**Restart services**

```bash
# Restart all services
./restart.sh

# Restart specific service
./restart.sh backend
./restart.sh frontend
```

### `status.sh`
**Check service status**

```bash
./status.sh
```

Shows:
- Container status
- Ollama models
- Access URLs

### `logs.sh`
**View service logs**

```bash
# View all logs
./logs.sh

# View specific service logs
./logs.sh backend
./logs.sh frontend
./logs.sh ollama
```

### `install-ollama-model.sh`
**Install Ollama models**

```bash
./install-ollama-model.sh <model-name>
```

### `setup-comfyui.sh`
**Set up ComfyUI for image generation**

```bash
./setup-comfyui.sh
```

This script will:
- Check for NVIDIA GPU and Docker support
- Create model directories
- Optionally download SDXL Turbo model (~6.9 GB)
- Start ComfyUI with GPU support

See `COMFYUI_SETUP.md` for detailed ComfyUI setup instructions.

Examples:
```bash
# Install Qwen 2.5 7B (recommended for coding)
./install-ollama-model.sh qwen2.5:7b

# Install Llama 3.1 8B (excellent for chat)
./install-ollama-model.sh llama3.1:8b

# Install Mistral 7B
./install-ollama-model.sh mistral:7b

# Install Gemma 2 9B
./install-ollama-model.sh gemma2:9b
```

Popular models:
- `qwen2.5:7b` - 7B parameters, good for coding and general use
- `llama3.1:8b` - 8B parameters, excellent for chat and reasoning
- `mistral:7b` - 7B parameters, fast and capable
- `gemma2:9b` - 9B parameters, Google's model
- `phi3:3.8b` - 3.8B parameters, small and efficient

Browse more at: https://ollama.com/library

## Access Information

After launching, the application is available at:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6379
- **Ollama**: http://localhost:11434
- **ChromaDB**: http://localhost:8001

## Default Credentials

- **Username**: admin
- **Password**: admin

## Service Names

For use with `restart.sh` and `logs.sh`:

- `frontend` - React frontend application
- `backend` - FastAPI backend server
- `worker` - Celery worker for background tasks
- `postgres` - PostgreSQL database
- `redis` - Redis cache and message broker
- `ollama` - Ollama LLM server
- `chromadb` - ChromaDB vector database

## Troubleshooting

### Services won't start
```bash
# Check Docker is running
docker info

# View detailed logs
./logs.sh

# Try a clean restart
docker compose down -v
./launch.sh
```

### Frontend shows 404 error
```bash
# Restart frontend in development mode
./restart.sh frontend
./logs.sh frontend
```

### Ollama models not loading
```bash
# Check Ollama is running
docker exec marketer_ollama ollama list

# Install a model
./install-ollama-model.sh qwen2.5:7b

# Restart backend to pick up models
./restart.sh backend
```

### Database migration issues
```bash
# Migrations run automatically on backend startup
# Check backend logs for errors
./logs.sh backend

# Manual migration (if needed)
docker exec marketer_backend alembic upgrade head
```

## Development Workflow

```bash
# 1. Start the application
./launch.sh

# 2. Make code changes (hot-reload enabled for frontend and backend)

# 3. View logs to debug
./logs.sh backend

# 4. Restart specific service if needed
./restart.sh backend

# 5. Check status
./status.sh
```

## Clean Shutdown

```bash
# Stop services (keep data)
./stop.sh

# Stop and remove all data
docker compose down -v
```
