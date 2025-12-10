#!/bin/bash
# ============================================================================
# MARKETER APP - SETUP VALIDATION SCRIPT
# ============================================================================
# This script validates that all required files and configurations are in place

set -e

echo "========================================="
echo "Marketer App - Setup Validation"
echo "========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track errors
ERRORS=0

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} Found: $1"
    else
        echo -e "${RED}✗${NC} Missing: $1"
        ERRORS=$((ERRORS + 1))
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} Found: $1/"
    else
        echo -e "${RED}✗${NC} Missing: $1/"
        ERRORS=$((ERRORS + 1))
    fi
}

echo "Checking Core Files..."
echo "----------------------"
check_file "docker-compose.yml"
check_file "Makefile"
check_file ".env.example"
check_file "README.md"
echo ""

echo "Checking Environment..."
echo "----------------------"
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} Found: .env"
else
    echo -e "${YELLOW}!${NC} Missing: .env (will be created from .env.example)"
fi
echo ""

echo "Checking Backend Files..."
echo "-------------------------"
check_dir "backend"
check_file "backend/requirements.txt"
check_file "backend/Dockerfile"
check_dir "backend/app"
check_file "backend/app/main.py"
check_dir "backend/db"
check_file "backend/db/init.sql"
check_dir "backend/tests"
echo ""

echo "Checking Frontend Files..."
echo "--------------------------"
check_dir "frontend"
check_file "frontend/package.json"
check_file "frontend/Dockerfile"
check_dir "frontend/src"
check_dir "frontend/public"
echo ""

echo "Checking Documentation..."
echo "-------------------------"
check_dir "docs"
check_file "docs/INSTALLATION_AND_TESTING.md"
check_file "docs/DEVELOPMENT_SETUP.md"
check_file "docs/DATABASE_SCHEMA.md"
echo ""

echo "Validating docker-compose.yml..."
echo "---------------------------------"
if command -v docker-compose &> /dev/null; then
    docker-compose config > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} docker-compose.yml is valid"
    else
        echo -e "${RED}✗${NC} docker-compose.yml has errors"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${YELLOW}!${NC} docker-compose not installed, skipping validation"
fi
echo ""

echo "Checking Required Commands..."
echo "-----------------------------"
commands=("docker" "docker-compose" "make")
for cmd in "${commands[@]}"; do
    if command -v $cmd &> /dev/null; then
        echo -e "${GREEN}✓${NC} $cmd is installed"
    else
        echo -e "${YELLOW}!${NC} $cmd is not installed (optional for Docker setup)"
    fi
done
echo ""

echo "========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review and update .env file"
    echo "2. Run: make dev"
    echo "   OR: docker-compose up --build"
else
    echo -e "${RED}Found $ERRORS error(s)${NC}"
    echo "Please fix the errors above before continuing"
fi
echo "========================================="

exit $ERRORS
