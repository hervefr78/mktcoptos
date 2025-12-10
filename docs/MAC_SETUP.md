# Running Marketer App on Mac M4 Pro

Complete guide for running the application on Apple Silicon (M4 Pro).

## Prerequisites

### Required Software

1. **Docker Desktop for Mac**
   - Download: https://www.docker.com/products/docker-desktop/
   - Version: 4.25.0 or later (Apple Silicon native)
   - **Important**: Make sure you download the **Apple Silicon** version

2. **Homebrew** (optional but recommended)
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

3. **Git** (usually pre-installed)
   ```bash
   git --version
   ```

### System Requirements

Your Mac M4 Pro is perfect for this:
- ✅ 12-16 CPU cores (excellent for containers)
- ✅ 18-36GB RAM (plenty for all services)
- ✅ Fast SSD (great for databases)
- ✅ ARM64 architecture (all images support it)

## Quick Start

### 1. Install Docker Desktop

```bash
# Download and install Docker Desktop for Apple Silicon
# https://desktop.docker.com/mac/main/arm64/Docker.dmg

# After installation, verify:
docker --version
docker-compose --version

# Check Docker is using Apple Silicon
docker version | grep "OS/Arch"
# Should show: linux/arm64
```

### 2. Configure Docker Desktop

Open Docker Desktop → Settings:

**Resources**:
- CPUs: 6-8 (leave some for macOS)
- Memory: 8-12 GB
- Disk: 60 GB

**General**:
- ✅ Use Virtualization framework
- ✅ Use VirtioFS (faster file sharing)
- ✅ Use Rosetta for x86/amd64 emulation

**Save & Restart Docker**

### 3. Clone Repository

```bash
# Create projects directory
mkdir -p ~/Projects
cd ~/Projects

# Clone repository
git clone https://github.com/yourusername/marketingAssistant.git
cd marketingAssistant
```

### 4. Setup Environment

```bash
# Create .env file
make env
# OR
cp .env.example .env

# Edit .env (use TextEdit, nano, or VS Code)
nano .env
```

**Mac-optimized .env settings**:
```bash
# Database
POSTGRES_DB=marketer_db
POSTGRES_USER=marketer_user
POSTGRES_PASSWORD=marketer_dev_pass

# Redis
REDIS_URL=redis://redis:6379/0

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin

# LLM (start with local)
USE_CLOUD=false
OLLAMA_HOST=http://ollama:11434

# Development
DEBUG=true
ENVIRONMENT=development
```

### 5. Start Services

```bash
# Build and start all services
make dev

# OR use docker-compose directly
docker-compose up --build
```

**First startup will take 5-10 minutes**:
- Building images
- Downloading base images (optimized for ARM64)
- Initializing database
- Starting all services

### 6. Verify Services

Open a new terminal:

```bash
# Check all services are running
make health

# View logs
make logs

# Check containers
docker ps
```

Expected output - all services healthy:
- ✅ marketer_postgres
- ✅ marketer_redis
- ✅ marketer_backend
- ✅ marketer_frontend
- ✅ marketer_worker
- ✅ marketer_ollama
- ✅ marketer_chromadb

### 7. Access Application

Open your browser:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **ChromaDB**: http://localhost:8001

**Default login**:
- Email: `admin@marketer.local`
- Password: `admin` (or value from .env)

## Apple Silicon Optimizations

### Native ARM64 Images

All services use ARM64-native images:
- ✅ PostgreSQL 16 (native ARM)
- ✅ Redis 7 (native ARM)
- ✅ Python 3.11 (native ARM)
- ✅ Node 18 (native ARM)
- ✅ Ollama (Apple Silicon optimized)
- ✅ ChromaDB (native ARM)

**Result**: 2-3x faster than x86 emulation!

### Ollama for Apple Silicon

Ollama is optimized for Apple Silicon and will use:
- Metal GPU acceleration
- Neural Engine when available
- Unified memory architecture

```bash
# Pull a model (happens automatically on first use)
make ollama-pull model=llama3

# Or manually
docker-compose exec ollama ollama pull llama3

# List installed models
make ollama-list

# Test it
docker-compose exec ollama ollama run llama3
```

**Recommended models for M4 Pro**:
- `llama3:8b` - Fast, good quality (4.7 GB)
- `mistral:7b` - Very fast (4.1 GB)
- `phi-3` - Smallest, fastest (2.3 GB)

### Performance Tips

1. **Use Ollama's Metal GPU**:
   - Already enabled by default on Mac
   - Much faster inference than CPU

2. **Enable VirtioFS** (Docker Desktop):
   - Settings → General → Use VirtioFS
   - 10x faster file sharing

3. **Allocate Enough RAM**:
   - 8GB minimum
   - 12GB recommended
   - 16GB for heavy use (large models)

## Development Workflow on Mac

### Hot Reload

Both backend and frontend have hot reload:

```bash
# Make changes to code
# Backend (FastAPI) - auto-reloads
# Frontend (React) - auto-reloads

# View logs in real-time
make logs-backend
make logs-frontend
```

### Using VS Code

```bash
# Install VS Code
brew install --cask visual-studio-code

# Open project
code .
```

**Recommended extensions**:
- Python
- Pylance
- Docker
- ESLint
- Prettier

### Database Access

```bash
# Connect to PostgreSQL
make db-shell

# Or use a GUI tool
brew install --cask postico  # PostgreSQL GUI
```

Connect to:
- Host: `localhost`
- Port: `5432`
- Database: `marketer_db`
- User: `marketer_user`
- Password: (from .env)

### Running Tests

```bash
# Backend tests
make backend-test

# With coverage
make backend-test-cov

# Frontend tests
make frontend-test
```

## Common Mac-Specific Issues

### Issue: Docker daemon not running

**Solution**:
```bash
# Open Docker Desktop application
open -a Docker

# Wait for Docker to start (green icon in menu bar)
```

### Issue: Port already in use

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or stop all containers
make down
make up
```

### Issue: Slow performance

**Solutions**:

1. **Increase Docker resources**:
   - Docker Desktop → Settings → Resources
   - Increase CPUs to 6-8
   - Increase Memory to 12GB

2. **Enable VirtioFS**:
   - Docker Desktop → General → Use VirtioFS

3. **Prune unused data**:
   ```bash
   docker system prune -a --volumes
   ```

### Issue: Database won't start

**Solution**:
```bash
# Reset database
make db-reset

# Check logs
make logs-backend
docker-compose logs postgres
```

### Issue: Ollama model download slow

**Solution**:
```bash
# Download models manually (faster)
docker-compose exec ollama ollama pull llama3

# Or download smaller model first
docker-compose exec ollama ollama pull phi-3
```

## Mac-Specific Commands

### Using Homebrew for Tools

```bash
# Install useful tools
brew install postgresql  # For psql command
brew install redis       # For redis-cli
brew install httpie      # For API testing

# Test API
http http://localhost:8000/health
```

### Opening Applications

```bash
# Open frontend in browser
open http://localhost:3000

# Open API docs
open http://localhost:8000/docs

# Open in specific browser
open -a "Google Chrome" http://localhost:3000
```

### Activity Monitor

```bash
# Monitor resource usage
# Applications → Utilities → Activity Monitor

# Or use htop
brew install htop
htop
```

## Stopping & Starting

### Normal Shutdown

```bash
# Stop all services gracefully
make down

# OR
docker-compose down
```

### Force Stop

```bash
# If services won't stop
docker-compose down --remove-orphans

# Force kill
docker kill $(docker ps -q)
```

### Restart

```bash
# Restart all services
make restart

# Restart specific service
docker-compose restart backend
```

## Data Persistence

### Where Data is Stored

```bash
# Docker volumes location on Mac
~/Library/Containers/com.docker.docker/Data/vms/0/data/docker/volumes/

# List volumes
docker volume ls

# Inspect volume
docker volume inspect marketingassistant_postgres_data
```

### Backup Database

```bash
# Using make
make db-backup

# Manual backup
docker-compose exec postgres pg_dump -U marketer_user marketer_db > ~/backups/marketer_$(date +%Y%m%d).sql
```

### Clean Start

```bash
# Stop and remove everything (including volumes)
make down-v

# Start fresh
make dev
```

## Optimized Mac Workflow

### Morning Routine

```bash
# Start Docker Desktop
open -a Docker

# Wait for Docker to start
sleep 10

# Start all services
cd ~/Projects/marketingAssistant
make dev
```

### End of Day

```bash
# Stop services (free up resources)
make down

# Quit Docker Desktop (optional)
# Docker Desktop → Quit Docker Desktop
```

### Quick Status Check

```bash
# One command to check everything
make health

# Detailed status
make status
```

## Performance Benchmarks (M4 Pro)

Expected performance on M4 Pro:

| Task | Time |
|------|------|
| Full stack startup | 30-60s |
| Backend API response | <50ms |
| Frontend page load | <2s |
| Database query | <10ms |
| Ollama inference (llama3) | 20-50 tokens/s |

## Alternative: Running Without Docker

For even better performance on Mac:

### Backend (Python)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://user:pass@localhost:5432/marketer_db

# Run
uvicorn app.main:app --reload
```

### Frontend (Node)

```bash
cd frontend
npm install
npm start
```

### Services

```bash
# Install PostgreSQL
brew install postgresql@16
brew services start postgresql@16

# Install Redis
brew install redis
brew services start redis

# Install Ollama natively (best performance on Mac!)
brew install ollama
ollama serve
```

**Native Ollama is 2x faster than Docker on Mac!**

## Tips for M4 Pro

1. **Use Native Ollama**: Install Ollama natively for best AI performance
2. **Enable Metal**: Automatic GPU acceleration
3. **Use VirtioFS**: Much faster file sharing
4. **Allocate RAM**: 12GB to Docker is sweet spot
5. **Enable Rosetta**: For any x86 images (rare)

## Troubleshooting Resources

```bash
# Docker logs
docker-compose logs

# Specific service logs
docker-compose logs backend

# System resources
docker stats

# Check Docker info
docker info
```

## Next Steps

1. ✅ Verify all services running: `make health`
2. ✅ Access frontend: http://localhost:3000
3. ✅ Check API docs: http://localhost:8000/docs
4. ✅ Pull an LLM model: `make ollama-pull model=llama3`
5. ✅ Start developing!

## Support

For issues:
- Check logs: `make logs`
- View status: `make status`
- Reset everything: `make down-v && make dev`
- Review [Development Setup](DEVELOPMENT_SETUP.md)

---

**Enjoy coding on your M4 Pro! 🚀**
