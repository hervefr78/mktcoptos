#!/bin/bash
# Script to run migration 018: Add Brave Search API key columns

echo "🔄 Running migration: Add Brave Search API key columns..."

# Run the migration using docker exec
docker exec -i marketer_postgres psql -U marketer_user -d marketer_db < "$(dirname "$0")/018_add_brave_search_api_key.sql"

if [ $? -eq 0 ]; then
    echo "✅ Migration completed successfully!"
    echo ""
    echo "The following columns have been added:"
    echo "  - user_settings.brave_search_api_key"
    echo "  - organization_settings.brave_search_api_key"
    echo ""
    echo "You can now configure Brave Search API key in the Settings page."
    echo "Get your free API key at: https://brave.com/search/api/"
else
    echo "❌ Migration failed. Please check the error messages above."
    exit 1
fi
