#!/bin/bash

# Script to stop the Marketing Assistant application

echo "Stopping Marketing Assistant..."

# Stop Docker services
docker compose down

# Stop ComfyUI on macOS if running
if [[ "$OSTYPE" == "darwin"* ]]; then
    # Find and kill ComfyUI process
    COMFYUI_PID=$(pgrep -f "python.*main.py" | head -1)
    if [ -n "$COMFYUI_PID" ]; then
        # Verify it's ComfyUI by checking if port 8188 is in use by this process
        if lsof -i :8188 -sTCP:LISTEN | grep -q "$COMFYUI_PID"; then
            echo "Stopping ComfyUI (PID: $COMFYUI_PID)..."
            kill "$COMFYUI_PID" 2>/dev/null
            echo "✓ ComfyUI stopped"
        fi
    fi
fi

echo "✓ All services stopped"
echo ""
echo "To remove all data (including database and models), run:"
echo "  docker compose down -v"
