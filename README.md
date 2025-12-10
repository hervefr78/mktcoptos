# marketingAssistant

AI-powered app to help marketing departments create content efficiently with multi-agent LLM workflows.

## Features

- **Multi-Agent Content Pipeline** – 7-stage AI pipeline with specialized agents for trends, tone, structure, writing, SEO, originality, and review
- **Project-Centric Workflow** – Create and manage projects, then generate content within project context
- **Content Persistence** – All pipeline executions and step results saved to database with full history
- **Wizard State Persistence** – Content wizard state saved to localStorage, survives page navigation
- **Retrieval-Augmented Generation (RAG)** – Enhanced RAG with cross-encoder reranking and hierarchical retrieval
- **Login & User Administration** – Authenticate, manage roles and access control
- **Dashboard with Quick Actions** – Jump directly into common marketing tasks
- **Redis Caching** – Cache trends and keywords for repeated topics
- **Real-time SSE Streaming** – Watch content generation progress in real-time
- **Export/Sharing** – Download or share marketing outputs to WordPress, LinkedIn, X
- **LLM Flexibility** – Use local (Ollama) or cloud LLMs (OpenAI, Anthropic, Mistral)
- **Automatic Migrations** – Database migrations run automatically on backend startup
- **Responsive Design** – Works on desktop and mobile screens

## Quick Start

### For Mac (Apple Silicon)

```bash
# 1. Install Docker Desktop for Mac (Apple Silicon version)
# https://www.docker.com/products/docker-desktop/

# 2. Install Ollama (runs locally for best performance)
# Download from https://ollama.com/download
# Then pull a model:
ollama pull llama3.1:8b

# 3. Clone repository
git clone https://github.com/yourusername/marketingAssistant.git
cd marketingAssistant

# 4. Setup and start
make env        # Create .env file
make dev        # Start all services

# 5. Access application
open http://localhost:3000
```

> **Note**: Ollama runs locally on your Mac (not in Docker) for better performance with Apple Silicon. Make sure Ollama is running before using LLM features.

**See [Mac Setup Guide](docs/MAC_SETUP.md) for detailed instructions optimized for Apple Silicon.**

### For Linux/Windows

```bash
# 1. Install Docker and Docker Compose

# 2. Clone and setup
git clone https://github.com/yourusername/marketingAssistant.git
cd marketingAssistant
make env
make dev

# 3. Access at http://localhost:3000
```

**See [Development Setup Guide](docs/DEVELOPMENT_SETUP.md) for detailed instructions.**

## Default Admin Credentials

On startup, the backend creates a default admin user. Override the credentials with the `ADMIN_USERNAME` and `ADMIN_PASSWORD` environment variables. By default, the username is `admin` and the password is `admin`.

## Temporary Auth Bypass for Testing

For local development, set the environment variable `REACT_APP_BYPASS_AUTH=true` when running the frontend. This skips the login screen and automatically populates placeholder authentication data in `localStorage` so that protected routes and role checks work. **Do not enable this flag in production.**

## Documentation

### Setup & Development
- **[Mac Setup Guide](docs/MAC_SETUP.md)** – Optimized for Apple Silicon (M-series chips)
- **[Development Setup](docs/DEVELOPMENT_SETUP.md)** – Complete local development guide
- **[Installation & Testing](docs/INSTALLATION_AND_TESTING.md)** – Docker setup and testing

### Deployment
- **[Docker Swarm Deployment](docs/SWARM_DEPLOYMENT.md)** – Production deployment guide
- **[Swarm Quick Reference](docs/SWARM_QUICK_REFERENCE.md)** – Command cheat sheet

### Architecture & Design
- **[Technical Specification](docs/TECHNICAL_SPECIFICATION.md)** – Complete system architecture
- **[Database Schema](docs/DATABASE_SCHEMA.md)** – PostgreSQL schema documentation
- **[SaaS Architecture](docs/SAAS_ARCHITECTURE.md)** – Multi-tenant architecture
- [UI Design](UI.pdf) – User interface specifications
- [RAG Interface](rag_page.md) – RAG interface specification
- [Architecture Overview](readme_Architecture.md) – System architecture

## Tech Stack

### Backend
- FastAPI (Python 3.11+)
- PostgreSQL 16 (database)
- Redis (cache + queue)
- Celery (async tasks)
- ChromaDB (vector store)
- LangGraph (agent orchestration)
- SQLAlchemy (ORM)

### Frontend
- React 18
- React Router v6
- Modern component architecture

### AI/ML
- Ollama (local LLM server – runs on host, not in Docker)
- OpenAI, Anthropic, Mistral (cloud LLMs)
- ChromaDB (vector database)
- Sentence Transformers (embeddings)

### Infrastructure
- Docker & Docker Compose
- Docker Swarm (production orchestration)
- Traefik (reverse proxy)
- Nginx (production serving)

## Common Commands

```bash
# Development
make dev              # Start all services
make health           # Check service health
make logs             # View all logs
make logs-backend     # View backend logs
make down             # Stop all services

# Database
make db-shell         # Connect to PostgreSQL
make db-backup        # Backup database
make db-reset         # Reset database (WARNING: destructive)

# Testing
make test             # Run tests
make backend-test     # Run backend tests
make frontend-test    # Run frontend tests

# Ollama (LLM - runs locally on host)
ollama pull llama3.1:8b         # Download LLM model
ollama list                     # List installed models
ollama serve                    # Start Ollama server (if not running)

# Production Deployment
make swarm-init       # Initialize Docker Swarm
make swarm-deploy     # Deploy to production
make swarm-status     # Check deployment status
```

See `make help` for all available commands.

## Deployment Options

### Development (Mac/Local)
- **Docker Compose** on your local machine
- Perfect for development and testing
- Optimized for Apple Silicon (M-series)
- **Cost**: Free

### Staging/Small Production
- **Single-node Docker Swarm** on VPS
- Providers: Hetzner ($9/mo), DigitalOcean ($24/mo)
- Easy setup, managed orchestration
- **Cost**: $10-50/month

### Production
- **Multi-node Docker Swarm cluster**
- High availability, auto-scaling
- Load balancing, zero-downtime deploys
- **Cost**: $40-120/month

See [Swarm Deployment Guide](docs/SWARM_DEPLOYMENT.md) for details.
