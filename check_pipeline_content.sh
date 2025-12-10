#!/bin/bash
echo "Checking pipeline executions for final_content..."
echo ""

echo "Recent completed pipelines with content status:"
echo "SELECT id, project_id, status, completed_at,
       CASE
           WHEN final_content IS NULL THEN 'NULL'
           WHEN final_content = '' THEN 'EMPTY'
           ELSE 'HAS CONTENT (' || LENGTH(final_content) || ' chars)'
       END as content_status,
       LEFT(topic, 50) as topic_preview
FROM pipeline_executions
WHERE status = 'completed'
  AND project_id IN (SELECT id FROM projects WHERE is_main_project = true)
ORDER BY completed_at DESC
LIMIT 10;" | docker exec -i marketer_postgres psql -U marketer_user -d marketer_db
