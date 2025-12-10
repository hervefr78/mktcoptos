#!/bin/bash

# Script to check the status of the Marketing Assistant

echo "=========================================="
echo "  Marketing Assistant Status"
echo "=========================================="
echo ""

echo "Container Status:"
docker compose ps

echo ""
echo "=========================================="
echo ""

echo "Ollama Models:"
docker exec marketer_ollama ollama list 2>/dev/null || echo "Ollama not running"

echo ""
echo "=========================================="
echo ""

echo "Access URLs:"
echo "  Frontend:    http://localhost:3000"
echo "  Backend API: http://localhost:8000"
echo "  API Docs:    http://localhost:8000/docs"
echo ""
