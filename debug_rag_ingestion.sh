#!/bin/bash
# Comprehensive debug script for RAG auto-ingestion

echo "=========================================="
echo "RAG AUTO-INGESTION DIAGNOSTIC REPORT"
echo "=========================================="
echo ""

echo "1. CHECKING PROJECTS WITH CAMPAIGNS"
echo "------------------------------------"
echo "Projects marked as main_project=true:"
echo "SELECT p.id, p.name, p.is_main_project, p.campaign_id, c.campaign_type
FROM projects p
LEFT JOIN campaigns c ON p.campaign_id = c.id
WHERE p.is_main_project = true
ORDER BY p.created_at DESC;" | docker exec -i marketer_postgres psql -U marketer_user -d marketer_db
echo ""

echo "2. CHECKING COMPLETED PIPELINES"
echo "--------------------------------"
echo "Recent completed pipelines with project_id:"
echo "SELECT id, project_id, topic, status, LENGTH(final_content) as content_length, completed_at
FROM pipeline_executions
WHERE status = 'completed'
  AND project_id IS NOT NULL
  AND final_content IS NOT NULL
  AND final_content != ''
ORDER BY completed_at DESC
LIMIT 10;" | docker exec -i marketer_postgres psql -U marketer_user -d marketer_db
echo ""

echo "3. CHECKING RAG DOCUMENTS"
echo "-------------------------"
echo "Total RAG documents:"
echo "SELECT COUNT(*) FROM rag_documents;" | docker exec -i marketer_postgres psql -U marketer_user -d marketer_db
echo ""

echo "Auto-generated documents (main_content_*):"
echo "SELECT id, filename, original_filename, status, campaign_id, collection, created_at
FROM rag_documents
WHERE filename LIKE 'main_content_%'
ORDER BY created_at DESC;" | docker exec -i marketer_postgres psql -U marketer_user -d marketer_db
echo ""

echo "Documents with campaign_id:"
echo "SELECT id, filename, status, campaign_id, collection
FROM rag_documents
WHERE campaign_id IS NOT NULL
ORDER BY created_at DESC;" | docker exec -i marketer_postgres psql -U marketer_user -d marketer_db
echo ""

echo "4. CROSS-CHECK: Completed pipelines vs RAG docs"
echo "------------------------------------------------"
echo "Completed main project pipelines WITHOUT corresponding RAG docs:"
echo "SELECT pe.id as pipeline_id, pe.project_id, p.name as project_name, p.is_main_project, p.campaign_id, c.campaign_type, pe.completed_at
FROM pipeline_executions pe
JOIN projects p ON pe.project_id = p.id
LEFT JOIN campaigns c ON p.campaign_id = c.id
LEFT JOIN rag_documents rd ON rd.campaign_id = p.campaign_id AND rd.filename LIKE '%' || pe.id || '%'
WHERE pe.status = 'completed'
  AND pe.final_content IS NOT NULL
  AND pe.final_content != ''
  AND p.is_main_project = true
  AND p.campaign_id IS NOT NULL
  AND c.campaign_type = 'integrated'
  AND rd.id IS NULL
ORDER BY pe.completed_at DESC
LIMIT 10;" | docker exec -i marketer_postgres psql -U marketer_user -d marketer_db
echo ""

echo "5. CHECK BACKEND LOGS FOR RAG INGESTION"
echo "----------------------------------------"
echo "Last 20 RAG ingestion log entries:"
docker logs marketer_backend 2>&1 | grep -i "RAG\|ingest\|main_content" | tail -20
echo ""

echo "=========================================="
echo "DIAGNOSTIC COMPLETE"
echo "=========================================="
echo ""
echo "WHAT TO LOOK FOR:"
echo "- Section 1: Are there projects with is_main_project=true in integrated campaigns?"
echo "- Section 2: Are there completed pipelines with content?"
echo "- Section 3: Are there any RAG documents with main_content_* prefix?"
echo "- Section 4: This is the KEY section - shows pipelines that SHOULD have RAG docs but DON'T"
echo "- Section 5: Backend logs showing if ingestion was attempted"
echo ""
