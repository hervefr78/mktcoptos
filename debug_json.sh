#!/bin/bash
# Quick debug script for JSON parsing errors
# Usage: ./debug_json.sh [execution_id]

# Run inside Docker container where dependencies are available
docker compose exec backend python /app/scripts/debug_json_error.py "$@"
