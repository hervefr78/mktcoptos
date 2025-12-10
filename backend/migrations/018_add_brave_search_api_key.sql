-- Migration: Add Brave Search API key for web search integration
-- Date: 2025-12-03
-- Description: Adds brave_search_api_key column to user_settings and organization_settings tables

-- Add brave_search_api_key to user_settings table
ALTER TABLE user_settings
ADD COLUMN IF NOT EXISTS brave_search_api_key VARCHAR(500);

-- Add brave_search_api_key to organization_settings table
ALTER TABLE organization_settings
ADD COLUMN IF NOT EXISTS brave_search_api_key VARCHAR(500);

-- Verify the columns were added
SELECT 'user_settings.brave_search_api_key' as table_column,
       COUNT(*) as exists
FROM information_schema.columns
WHERE table_name = 'user_settings'
  AND column_name = 'brave_search_api_key';

SELECT 'organization_settings.brave_search_api_key' as table_column,
       COUNT(*) as exists
FROM information_schema.columns
WHERE table_name = 'organization_settings'
  AND column_name = 'brave_search_api_key';
