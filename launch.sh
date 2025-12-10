#!/bin/bash

# Marketing Assistant Launch Script
# This script starts the application and ensures all dependencies are ready

set -e  # Exit on error

echo "=========================================="
echo "  Marketing Assistant Launch Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if Docker is running
print_info "Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi
print_success "Docker is running"

# Check if docker compose is available
print_info "Checking Docker Compose..."
if ! docker compose version > /dev/null 2>&1; then
    print_error "Docker Compose is not available. Please install Docker Compose."
    exit 1
fi
print_success "Docker Compose is available"

# Stop existing containers (if any)
print_info "Stopping existing containers..."
docker compose down 2>/dev/null || true
print_success "Existing containers stopped"

# Build and start containers
print_info "Building and starting containers..."
docker compose up -d --build

# Wait for containers to be healthy
print_info "Waiting for services to be ready..."

# Function to wait for a service to be healthy
wait_for_service() {
    local service_name=$1
    local container_name=$2
    local max_attempts=60
    local attempt=1

    echo -n "  Waiting for $service_name"

    while [ $attempt -le $max_attempts ]; do
        # Check if container is running
        if docker ps --filter "name=$container_name" --filter "status=running" | grep -q "$container_name"; then
            # Container is running, now check if it's healthy or responsive
            local status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "no-health")

            if [ "$status" = "healthy" ] || [ "$status" = "no-health" ]; then
                echo ""
                print_success "$service_name is ready"
                return 0
            fi
        fi

        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo ""
    print_error "$service_name failed to start or become healthy"
    print_info "Last 30 log lines from $service_name:"
    docker compose logs --tail=30 "$service_name"

    print_info "Container status:"
    docker ps -a --filter "name=$container_name"

    return 1
}

# Wait for critical services
echo ""
if ! wait_for_service "postgres" "marketer_postgres"; then
    print_error "PostgreSQL failed to start. Cannot continue."
    exit 1
fi

if ! wait_for_service "redis" "marketer_redis"; then
    print_error "Redis failed to start. Cannot continue."
    exit 1
fi

wait_for_service "backend" "marketer_backend" || true
wait_for_service "frontend" "marketer_frontend" || true

echo ""
print_success "Core services are running!"

# Check if local Ollama is running (Ollama runs locally on Mac, not in Docker)
echo ""
print_info "Checking local Ollama installation..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    print_success "Local Ollama is running on localhost:11434"
    OLLAMA_MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null | grep -o '"name"' | wc -l | tr -d ' ')
    if [ "$OLLAMA_MODELS" -gt "0" ] 2>/dev/null; then
        print_success "Found $OLLAMA_MODELS Ollama model(s)"
    else
        print_info "No Ollama models found. Install models with: ollama pull <model-name>"
        print_info "Recommended: ollama pull llama3.1:8b"
    fi
else
    print_error "Local Ollama is not running!"
    print_info "Please start Ollama on your Mac:"
    echo "  1. Install Ollama from https://ollama.com/download"
    echo "  2. Run 'ollama serve' or start the Ollama app"
    echo "  3. Install a model: ollama pull llama3.1:8b"
    echo ""
    print_info "The app will work, but LLM features will be unavailable until Ollama is running."
fi

# Check for ComfyUI on macOS with Apple Silicon
if [[ "$OSTYPE" == "darwin"* ]] && [[ $(uname -m) == "arm64" ]]; then
    echo ""
    print_info "Detected macOS with Apple Silicon"

    # Look for ComfyUI installation
    COMFYUI_PATH=""
    COMFYUI_LOCATIONS=(
        "$HOME/ComfyUI"
        "$HOME/Applications/ComfyUI"
        "/Applications/ComfyUI"
        "./ComfyUI"
    )

    for loc in "${COMFYUI_LOCATIONS[@]}"; do
        if [ -f "$loc/main.py" ]; then
            COMFYUI_PATH="$loc"
            break
        fi
    done

    if [ -n "$COMFYUI_PATH" ]; then
        print_success "Found ComfyUI at: $COMFYUI_PATH"

        # Check if ComfyUI is already running
        if curl -s http://localhost:8188 > /dev/null 2>&1; then
            print_success "ComfyUI is already running on port 8188"
        else
            print_info "Would you like to start ComfyUI? (y/n)"
            read -r start_comfyui

            if [ "$start_comfyui" = "y" ] || [ "$start_comfyui" = "Y" ]; then
                print_info "Starting ComfyUI..."

                # Start ComfyUI in background
                cd "$COMFYUI_PATH"
                if [ -f "venv/bin/activate" ]; then
                    source venv/bin/activate
                fi

                # Run ComfyUI in background and redirect output to log
                nohup python main.py > "$HOME/.comfyui.log" 2>&1 &
                COMFYUI_PID=$!

                # Return to original directory
                cd - > /dev/null

                # Wait for ComfyUI to start
                echo -n "  Waiting for ComfyUI to start"
                for i in {1..30}; do
                    if curl -s http://localhost:8188 > /dev/null 2>&1; then
                        echo ""
                        print_success "ComfyUI is running (PID: $COMFYUI_PID)"
                        break
                    fi
                    echo -n "."
                    sleep 2
                done

                if ! curl -s http://localhost:8188 > /dev/null 2>&1; then
                    echo ""
                    print_error "ComfyUI failed to start"
                    print_info "Check logs at: $HOME/.comfyui.log"
                fi
            fi
        fi
    else
        print_info "ComfyUI not found. For image generation with SDXL, install ComfyUI:"
        echo "  See COMFYUI_SETUP.md for macOS installation instructions"
    fi
fi

# Display running services
echo ""
echo "=========================================="
echo "  Services Status"
echo "=========================================="
docker compose ps

# Display access information
echo ""
echo "=========================================="
echo "  Access Information"
echo "=========================================="
echo ""
echo "  Frontend:    http://localhost:3000"
echo "  Backend API: http://localhost:8000"
echo "  API Docs:    http://localhost:8000/docs"
echo "  PostgreSQL:  localhost:5433"
echo "  Redis:       localhost:6379"
echo "  Ollama:      http://localhost:11434 (local installation)"
echo "  ChromaDB:    http://localhost:8001"
if curl -s http://localhost:8188 > /dev/null 2>&1; then
echo "  ComfyUI:     http://localhost:8188"
fi
echo ""
echo "  Default Admin Credentials:"
echo "    Username: admin"
echo "    Password: admin"
echo ""
echo "=========================================="
echo ""

# Ask if user wants to view logs
print_info "Would you like to view the logs? (y/n)"
read -r view_logs

if [ "$view_logs" = "y" ] || [ "$view_logs" = "Y" ]; then
    print_info "Showing logs (press Ctrl+C to exit)..."
    docker compose logs -f
else
    print_success "Application is running! Use 'docker compose logs -f' to view logs."
fi
