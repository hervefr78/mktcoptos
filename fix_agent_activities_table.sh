#!/bin/bash
# One-command fix for agent_activities table creation issue

echo "🔧 Fixing agent_activities table..."

# Create the table directly using the SQL file
docker cp backend/migrations/add_agent_activities.sql marketer_postgres:/tmp/add_agent_activities.sql
docker exec marketer_postgres psql -U marketer_user -d marketer_db -f /tmp/add_agent_activities.sql

echo ""
echo "✅ Done! Verifying table was created..."
echo ""

# Verify table exists
docker exec marketer_postgres psql -U marketer_user -d marketer_db -c "\d agent_activities"

echo ""
echo "🎉 Table created successfully! You can now run the content pipeline."
