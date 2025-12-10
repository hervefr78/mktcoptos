#!/bin/bash

# Script to view logs from the Marketing Assistant

SERVICE=${1:-}

if [ -z "$SERVICE" ]; then
    echo "Showing logs from all services (press Ctrl+C to exit)..."
    echo ""
    docker compose logs -f
else
    echo "Showing logs from $SERVICE (press Ctrl+C to exit)..."
    echo ""
    docker compose logs -f "$SERVICE"
fi
