#!/bin/bash

# Script to restart the Marketing Assistant application

SERVICE=${1:-}

if [ -z "$SERVICE" ]; then
    echo "Restarting all services..."
    docker compose restart
    echo "✓ All services restarted"
else
    echo "Restarting $SERVICE..."
    docker compose restart "$SERVICE"
    echo "✓ $SERVICE restarted"
fi

echo ""
echo "Available services:"
docker compose ps
