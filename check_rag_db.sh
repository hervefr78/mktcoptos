#!/bin/bash
# Script to check RAG documents in database

echo "=== Checking RAG Documents in Database ==="
echo ""

echo "1. Total RAG documents:"
echo "SELECT COUNT(*) as total FROM rag_documents;" | docker exec -i marketer_postgres psql -U marketer_user -d marketer_db
echo ""

echo "2. Documents by collection type:"
echo "SELECT collection, COUNT(*) as count FROM rag_documents GROUP BY collection;" | docker exec -i marketer_postgres psql -U marketer_user -d marketer_db
echo ""

echo "3. Auto-generated documents (filename starts with 'main_content_'):"
echo "SELECT COUNT(*) as count FROM rag_documents WHERE filename LIKE 'main_content_%';" | docker exec -i marketer_postgres psql -U marketer_user -d marketer_db
echo ""

echo "4. Recent RAG documents (last 10):"
echo "SELECT id, filename, status, collection, campaign_id, created_at FROM rag_documents ORDER BY created_at DESC LIMIT 10;" | docker exec -i marketer_postgres psql -U marketer_user -d marketer_db
echo ""

echo "5. Documents with campaign_id (auto-generated from campaigns):"
echo "SELECT id, filename, original_filename, status, campaign_id, collection, created_at FROM rag_documents WHERE campaign_id IS NOT NULL ORDER BY created_at DESC;" | docker exec -i marketer_postgres psql -U marketer_user -d marketer_db
echo ""

echo "6. Recently completed pipeline executions with project_id:"
echo "SELECT id, project_id, topic, status, completed_at, LENGTH(final_content) as content_length FROM pipeline_executions WHERE status = 'completed' AND project_id IS NOT NULL ORDER BY completed_at DESC LIMIT 5;" | docker exec -i marketer_postgres psql -U marketer_user -d marketer_db
echo ""

echo "Done!"
