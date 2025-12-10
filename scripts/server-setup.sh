#!/bin/bash
# ============================================================================
# MARKETER APP - SERVER SETUP SCRIPT
# ============================================================================
# This script prepares a fresh Ubuntu server for Docker Swarm deployment
#
# Compatible with: Ubuntu 22.04 LTS, Ubuntu 20.04 LTS, Debian 11+
#
# Usage (run as root):
#   curl -fsSL https://raw.githubusercontent.com/yourusername/marketingAssistant/main/scripts/server-setup.sh | bash
#
# Or download and run:
#   wget https://raw.githubusercontent.com/yourusername/marketingAssistant/main/scripts/server-setup.sh
#   chmod +x server-setup.sh
#   ./server-setup.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

print_info() {
    echo -e "${BLUE}→ $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root"
    exit 1
fi

print_header "Marketer App - Server Setup"
echo ""
print_info "This script will:"
echo "  1. Update system packages"
echo "  2. Install Docker and Docker Compose"
echo "  3. Configure firewall (UFW)"
echo "  4. Install useful utilities"
echo "  5. Set up application directory"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

# Update system
print_header "Updating System"
print_info "Updating package list..."
apt update -y
print_info "Upgrading packages..."
apt upgrade -y
print_success "System updated"

# Install prerequisites
print_header "Installing Prerequisites"
apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    git \
    wget \
    htop \
    vim \
    ufw \
    fail2ban
print_success "Prerequisites installed"

# Install Docker
print_header "Installing Docker"
if command -v docker &> /dev/null; then
    print_success "Docker is already installed"
    docker --version
else
    print_info "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh

    # Enable Docker to start on boot
    systemctl enable docker
    systemctl start docker

    print_success "Docker installed"
    docker --version
fi

# Install Docker Compose (standalone)
print_header "Installing Docker Compose"
if command -v docker-compose &> /dev/null; then
    print_success "Docker Compose is already installed"
    docker-compose --version
else
    print_info "Installing Docker Compose..."
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    print_success "Docker Compose installed"
    docker-compose --version
fi

# Configure firewall
print_header "Configuring Firewall"
print_info "Setting up UFW firewall..."

# Default policies
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (critical!)
ufw allow 22/tcp comment 'SSH'
print_success "SSH allowed (port 22)"

# Allow HTTP/HTTPS
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
print_success "HTTP/HTTPS allowed (ports 80, 443)"

# Allow Docker Swarm ports
ufw allow 2377/tcp comment 'Docker Swarm management'
ufw allow 7946/tcp comment 'Docker Swarm communication'
ufw allow 7946/udp comment 'Docker Swarm communication'
ufw allow 4789/udp comment 'Docker overlay network'
print_success "Docker Swarm ports allowed"

# Enable firewall
ufw --force enable
print_success "Firewall enabled"

# Show status
ufw status numbered

# Configure fail2ban for SSH protection
print_header "Configuring Fail2ban"
systemctl enable fail2ban
systemctl start fail2ban
print_success "Fail2ban enabled (protects SSH)"

# Set up application directory
print_header "Setting Up Application Directory"
APP_DIR="/opt/marketer"
if [ -d "$APP_DIR" ]; then
    print_info "Directory $APP_DIR already exists"
else
    mkdir -p "$APP_DIR"
    print_success "Created directory: $APP_DIR"
fi

# Set up backups directory
BACKUP_DIR="/opt/backups"
if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
    print_success "Created backups directory: $BACKUP_DIR"
fi

# System optimizations
print_header "Applying System Optimizations"

# Increase file descriptors limit
cat >> /etc/security/limits.conf << 'EOF'
# Increased limits for Docker
* soft nofile 65536
* hard nofile 65536
EOF
print_success "Increased file descriptors limit"

# Enable automatic security updates
print_info "Configuring automatic security updates..."
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades
print_success "Automatic security updates enabled"

# Display summary
print_header "Setup Complete!"
echo ""
print_success "Server is ready for Docker Swarm deployment"
echo ""
print_info "System Information:"
echo "  OS: $(lsb_release -d | cut -f2)"
echo "  Kernel: $(uname -r)"
echo "  Docker: $(docker --version | cut -d' ' -f3 | tr -d ',')"
echo "  Docker Compose: $(docker-compose --version | cut -d' ' -f3 | tr -d ',')"
echo ""
print_info "Application directory: $APP_DIR"
print_info "Backups directory: $BACKUP_DIR"
echo ""
print_info "Next steps:"
echo "  1. Clone your repository:"
echo "     cd $APP_DIR"
echo "     git clone https://github.com/yourusername/marketingAssistant.git ."
echo ""
echo "  2. Configure environment:"
echo "     cp .env.production .env.prod"
echo "     nano .env.prod"
echo ""
echo "  3. Initialize Swarm and deploy:"
echo "     ./scripts/swarm-deploy.sh --init"
echo "     ./scripts/swarm-deploy.sh --deploy"
echo ""
print_info "Documentation: docs/SWARM_DEPLOYMENT.md"
echo ""

# Security reminder
print_header "Security Reminders"
echo "  1. Change SSH port (recommended):"
echo "     Edit /etc/ssh/sshd_config, change Port 22 to custom port"
echo "     Update firewall: ufw allow <new-port>/tcp"
echo ""
echo "  2. Disable password authentication (use SSH keys):"
echo "     Edit /etc/ssh/sshd_config, set PasswordAuthentication no"
echo ""
echo "  3. Set up regular backups:"
echo "     See docs/SWARM_DEPLOYMENT.md for backup setup"
echo ""
echo "  4. Update .env.prod with strong passwords!"
echo ""

print_success "Server setup complete!"
