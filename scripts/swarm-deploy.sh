#!/bin/bash
# ============================================================================
# MARKETER APP - DOCKER SWARM DEPLOYMENT SCRIPT
# ============================================================================
# This script automates the deployment of Marketer App to Docker Swarm
#
# Usage:
#   ./scripts/swarm-deploy.sh [options]
#
# Options:
#   --init          Initialize Docker Swarm (first time setup)
#   --deploy        Deploy or update the stack
#   --remove        Remove the stack
#   --status        Show stack status
#   --help          Show this help message

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="marketer"
STACK_FILE="docker-stack.yml"
ENV_FILE=".env.prod"

# Functions
print_header() {
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

print_info() {
    echo -e "${BLUE}→ $1${NC}"
}

check_requirements() {
    print_header "Checking Requirements"

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        echo "Install Docker: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    print_success "Docker is installed"

    # Check if Swarm is initialized
    if ! docker info 2>/dev/null | grep -q "Swarm: active"; then
        print_warning "Docker Swarm is not initialized"
        return 1
    fi
    print_success "Docker Swarm is active"

    # Check if stack file exists
    if [ ! -f "$STACK_FILE" ]; then
        print_error "Stack file not found: $STACK_FILE"
        exit 1
    fi
    print_success "Stack file found"

    return 0
}

check_env_file() {
    print_header "Checking Environment Configuration"

    if [ ! -f "$ENV_FILE" ]; then
        print_error "Environment file not found: $ENV_FILE"
        echo ""
        echo "Please create $ENV_FILE from .env.production template:"
        echo "  cp .env.production $ENV_FILE"
        echo "  nano $ENV_FILE  # Edit with your values"
        exit 1
    fi
    print_success "Environment file found"

    # Check critical variables
    source "$ENV_FILE"

    local missing_vars=()

    [ -z "$POSTGRES_PASSWORD" ] && missing_vars+=("POSTGRES_PASSWORD")
    [ -z "$ADMIN_PASSWORD" ] && missing_vars+=("ADMIN_PASSWORD")
    [ -z "$SECRET_KEY" ] && missing_vars+=("SECRET_KEY")

    if [ ${#missing_vars[@]} -ne 0 ]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi

    print_success "All required environment variables are set"
}

init_swarm() {
    print_header "Initializing Docker Swarm"

    if docker info 2>/dev/null | grep -q "Swarm: active"; then
        print_warning "Swarm is already initialized"
        return 0
    fi

    print_info "Initializing Swarm..."
    docker swarm init

    print_success "Swarm initialized successfully!"
    echo ""
    print_info "This node is now a Swarm manager"
    print_info "To add worker nodes, run the 'docker swarm join' command shown above"
}

deploy_stack() {
    print_header "Deploying Stack"

    check_env_file

    # Check if stack exists
    if docker stack ls | grep -q "$STACK_NAME"; then
        print_warning "Stack '$STACK_NAME' already exists. This will update it."
        ACTION="Updating"
    else
        ACTION="Deploying"
    fi

    print_info "$ACTION stack '$STACK_NAME'..."

    # Deploy the stack
    docker stack deploy -c "$STACK_FILE" --env-file "$ENV_FILE" "$STACK_NAME"

    print_success "Stack deployed successfully!"
    echo ""
    print_info "Waiting for services to start..."
    sleep 5

    show_status

    echo ""
    print_info "Monitor deployment:"
    echo "  make swarm-status        # Check service status"
    echo "  make swarm-logs service=backend  # View logs"
    echo "  make swarm-health        # Check health"
}

remove_stack() {
    print_header "Removing Stack"

    if ! docker stack ls | grep -q "$STACK_NAME"; then
        print_warning "Stack '$STACK_NAME' does not exist"
        return 0
    fi

    print_warning "This will remove all services in the stack!"
    print_info "Volumes will be preserved"
    echo ""
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cancelled"
        return 0
    fi

    print_info "Removing stack..."
    docker stack rm "$STACK_NAME"

    print_success "Stack removed successfully!"
    echo ""
    print_info "To remove volumes, run:"
    echo "  docker volume prune"
}

show_status() {
    print_header "Stack Status"

    if ! docker stack ls | grep -q "$STACK_NAME"; then
        print_warning "Stack '$STACK_NAME' is not deployed"
        return 0
    fi

    echo ""
    echo "Services:"
    docker stack services "$STACK_NAME"

    echo ""
    echo "Tasks:"
    docker stack ps "$STACK_NAME" --no-trunc
}

show_help() {
    cat << EOF
Marketer App - Docker Swarm Deployment Script

Usage: $0 [options]

Options:
    --init          Initialize Docker Swarm (first time setup)
    --deploy        Deploy or update the stack
    --remove        Remove the stack
    --status        Show stack status
    --help          Show this help message

Examples:
    # First time setup
    $0 --init

    # Deploy the stack
    $0 --deploy

    # Check status
    $0 --status

    # Remove stack
    $0 --remove

Environment:
    Create $ENV_FILE from .env.production template before deploying

Documentation:
    See docs/SWARM_DEPLOYMENT.md for detailed instructions

EOF
}

# Main script
main() {
    case "$1" in
        --init)
            check_requirements || true
            init_swarm
            ;;
        --deploy)
            check_requirements
            deploy_stack
            ;;
        --remove)
            check_requirements
            remove_stack
            ;;
        --status)
            check_requirements
            show_status
            ;;
        --help|"")
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
