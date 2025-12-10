#!/bin/bash
# Quick script to check RAG processing logs

echo "=== Checking RAG Logs ==="
echo ""

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Checking local logs..."
    if [ -f "backend/app.log" ]; then
        tail -100 backend/app.log | grep -E "RAG RETRIEVAL|WRITER AGENT|📚|🔍|✅|❌"
    else
        echo "No log file found. Backend may not be running."
    fi
    exit 0
fi

echo "📋 Recent RAG-related activity:"
echo "─────────────────────────────────────────────────────"
docker logs marketer_backend --tail 200 2>&1 | grep -E "RAG RETRIEVAL|WRITER AGENT|📚|🔍|✅|❌|⚠️" | tail -30

echo ""
echo "─────────────────────────────────────────────────────"
echo ""
echo "Key indicators:"
echo "  🔍 RAG RETRIEVAL - Document retrieval attempts"
echo "  📚 WRITER AGENT - RAG usage in content generation"
echo "  ✅ - Success (chunks found and used)"
echo "  ❌ - Error (no chunks found)"
echo "  ⚠️ - Warning (using fallback)"
echo ""
echo "To see full logs: docker logs marketer_backend -f"
echo "To see last 100 lines: docker logs marketer_backend --tail 100"
