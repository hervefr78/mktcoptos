# Development Environment Setup Guide

This guide will help you set up your development environment for the Marketer App.

## Prerequisites

- Docker & Docker Compose (recommended)
- OR: Python 3.11+, Node.js 18+, PostgreSQL 16, Redis 7

## Quick Start (Docker - Recommended)

### 1. Clone and Setup

```bash
# Clone the repository
cd marketingAssistant

# Create environment file
make env
# OR manually:
cp .env.example .env
```

### 2. Review Environment Variables

Edit `.env` and update values as needed:

```bash
# Most important settings for local development:
POSTGRES_PASSWORD=your-secure-password
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-admin-password
```

### 3. Start All Services

```bash
# Build and start all services
make dev

# OR use docker-compose directly:
docker-compose up --build
```

This will start:
- **PostgreSQL** (port 5432) - Database
- **Redis** (port 6379) - Cache & queue
- **Backend API** (port 8000) - FastAPI application
- **Frontend** (port 3000) - React application
- **Ollama** (port 11434) - Local LLM server
- **ChromaDB** (port 8001) - Vector database
- **Celery Worker** - Background task processor

### 4. Verify Services

```bash
# Check service health
make health

# View logs
make logs

# Check running containers
make ps
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ChromaDB**: http://localhost:8001

### 6. Default Admin Login

```
Email: admin@marketer.local
Password: admin (or value from ADMIN_PASSWORD env var)
```

## Manual Setup (Without Docker)

### Backend Setup

```bash
# Create virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL database
# Create database: marketer_db
# Run initialization script: backend/db/init.sql

# Create .env file with database connection
echo "DATABASE_URL=postgresql://user:pass@localhost:5432/marketer_db" > .env

# Start backend
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

### Start Required Services

You'll need to run separately:
- PostgreSQL 16
- Redis 7
- Ollama (optional, for local LLM)
- ChromaDB (optional, for RAG features)

## Common Development Commands

### Docker Commands

```bash
make up              # Start all services
make up-d            # Start in detached mode
make down            # Stop all services
make restart         # Restart all services
make logs            # View all logs
make logs-backend    # View backend logs only
make logs-frontend   # View frontend logs only
```

### Database Commands

```bash
make db-shell        # Connect to PostgreSQL
make db-reset        # Reset database (WARNING: destroys data)
make db-backup       # Backup database
make db-restore file=backup.sql  # Restore from backup
```

### Testing Commands

```bash
make test            # Run backend tests
make test-all        # Run all tests (backend + frontend)
make backend-test-cov  # Run tests with coverage
```

### Code Quality

```bash
make backend-lint    # Lint backend code
make backend-format  # Format backend code
make backend-type    # Type check backend
```

### Ollama Commands

```bash
make ollama-pull model=llama3     # Pull LLM model
make ollama-list                   # List installed models
make ollama-run model=llama3       # Run model interactively
```

## Project Structure

```
marketingAssistant/
├── backend/              # FastAPI backend
│   ├── app/             # Application code
│   │   ├── main.py      # FastAPI app & routes
│   │   ├── auth.py      # Authentication
│   │   ├── users.py     # User management
│   │   └── rag/         # RAG implementation
│   ├── db/              # Database scripts
│   │   └── init.sql     # Schema initialization
│   ├── tests/           # Backend tests
│   ├── utils/           # Utility functions
│   ├── requirements.txt # Python dependencies
│   └── Dockerfile
├── frontend/            # React frontend
│   ├── src/            # Source code
│   ├── public/         # Static files
│   ├── package.json    # Node dependencies
│   └── Dockerfile
├── docs/               # Documentation
├── data/               # Data files
├── logs/               # Application logs
├── docker-compose.yml  # Docker orchestration
├── Makefile           # Development commands
├── .env.example       # Environment template
└── README.md          # Main readme
```

## Environment Variables Reference

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_DB` | PostgreSQL database name | `marketer_db` |
| `POSTGRES_USER` | PostgreSQL username | `marketer_user` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `marketer_pass` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |

### LLM Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_CLOUD` | Use cloud LLM vs local | `false` |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |

### Application Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_USERNAME` | Default admin username | `admin` |
| `ADMIN_PASSWORD` | Default admin password | `admin` |
| `REACT_APP_BYPASS_AUTH` | Skip login (dev only) | `false` |
| `DEBUG` | Enable debug mode | `true` |

## Troubleshooting

### Port Already in Use

If you see "port already in use" errors:

```bash
# Stop all services
make down

# Kill specific port (example for 8000)
lsof -ti:8000 | xargs kill -9

# Restart
make up
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Reset database
make db-reset
```

### Frontend Build Errors

```bash
# Clear node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Backend Import Errors

```bash
# Reinstall Python dependencies
cd backend
pip install -r requirements.txt --force-reinstall
```

### Service Health Check Failures

```bash
# Check all service health
make health

# View detailed status
make status

# Restart specific service
docker-compose restart backend
```

## Development Workflow

### 1. Start Development Session

```bash
make dev              # Start all services
make logs-backend     # Monitor backend in another terminal
```

### 2. Make Changes

- Backend code changes auto-reload (FastAPI + uvicorn)
- Frontend code changes auto-reload (React hot reload)
- Database changes require migration

### 3. Run Tests

```bash
make test             # Run tests
make backend-test-cov # Check coverage
```

### 4. Commit Changes

```bash
git add .
git commit -m "Your message"
git push
```

## Next Steps

1. **Phase 2**: Set up development tooling (linting, formatting)
2. **Phase 3**: Implement database models with SQLAlchemy
3. **Phase 4**: Set up testing infrastructure
4. **Phase 5**: Add comprehensive documentation

## Support

For issues or questions:
- Check the [main README](../README.md)
- Review [Technical Specification](TECHNICAL_SPECIFICATION.md)
- Review [Installation & Testing](INSTALLATION_AND_TESTING.md)
