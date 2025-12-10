# Database Migration Guide - Settings to PostgreSQL

This guide explains how to migrate from JSON file-based settings to PostgreSQL database storage.

## What Changed

### Before (JSON Files)
- Settings stored in `backend/data/settings.json`
- No audit trail
- No multi-user support
- No organization-level defaults

### After (PostgreSQL)
- Settings stored in PostgreSQL tables
- Full audit trail in `settings_history`
- User-specific settings
- Organization-level defaults
- Proper relationships and transactions

## Database Schema

### New Tables Created

1. **user_settings** - Personal settings for each user
   - LLM provider preferences
   - Image generation settings
   - Prompt contexts
   - UI preferences

2. **organization_settings** - Organization-wide defaults
   - Default LLM providers
   - Shared API keys
   - Brand guidelines
   - Content policies

3. **settings_history** - Audit trail
   - All settings changes logged
   - Who changed what, when
   - IP address and user agent tracking

## Migration Steps

### 1. Run Database Migration

The migration will create the new tables:

```bash
# From the backend directory
cd /home/user/marketingAssistant/backend

# Run Alembic migrations (once Docker container is rebuilt)
alembic upgrade head
```

### 2. Migrate Existing JSON Settings (Optional)

If you have existing settings in `backend/data/settings.json`, you can migrate them:

```bash
# Use the migration endpoint
curl -X POST "http://localhost:8000/api/settings/migrate-from-json?json_file_path=/app/data/settings.json" \
  -H "X-User-ID: 1"
```

Or use the Python script:

```python
from app.database import SessionLocal
from app.settings_service import SettingsService
import json

db = SessionLocal()
user_id = 1  # Admin user

# Migrate from JSON
SettingsService.migrate_from_json(
    json_file_path="data/settings.json",
    user_id=user_id,
    db=db
)
```

### 3. Verify Migration

Check that settings were migrated:

```bash
curl "http://localhost:8000/api/settings" \
  -H "X-User-ID: 1"
```

## Features

### User-Specific Settings

Each user can now have their own:
- LLM provider (Ollama vs OpenAI)
- API keys
- Prompt contexts
- UI preferences

### Organization Settings

Organization admins can set:
- Default LLM providers for the team
- Shared API keys
- Brand guidelines
- Content approval workflows

### Audit Trail

All settings changes are logged:
- What changed (field name, old/new values)
- Who changed it (user ID)
- When it changed (timestamp)
- Where from (IP address, user agent)

View history:

```bash
curl "http://localhost:8000/api/settings/history" \
  -H "X-User-ID: 1"
```

## API Endpoints

### Get Settings
```
GET /api/settings
Headers: X-User-ID: 1
```

### Update Settings
```
PUT /api/settings
Headers: X-User-ID: 1
Body: {
  "llmProvider": "openai",
  "llmModel": "gpt-4o",
  "openaiApiKey": "sk-..."
}
```

### Get Settings History
```
GET /api/settings/history?limit=50
Headers: X-User-ID: 1
```

### Test Connections
```
POST /api/settings/ollama/test
POST /api/settings/openai/test
POST /api/settings/sd/test
```

## Benefits

1. **Multi-User Support** - Each user has their own settings
2. **Audit Trail** - Complete history of all changes
3. **Organization Defaults** - Shared settings for teams
4. **Proper Persistence** - PostgreSQL transactions
5. **Scalability** - Ready for production
6. **Security** - Encrypted API keys, audit logs

## Troubleshooting

### Migration fails with "table already exists"

The tables may have been created already. Check:

```sql
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('user_settings', 'organization_settings', 'settings_history');
```

### Settings not loading

Check database connection:

```bash
docker-compose logs postgres
```

Verify tables exist:

```bash
docker-compose exec postgres psql -U marketer_user -d marketer_db -c "\dt"
```

## Rollback (if needed)

To rollback the migration:

```bash
alembic downgrade -1
```

This will drop the settings tables and restore the previous state.

## Notes

- The old `backend/app/settings.py` (JSON-based) is now replaced by `backend/app/settings_routes.py` (database-backed)
- The `SettingsService` class handles all database operations
- All changes are logged to `settings_history` for compliance
- User authentication will be improved in future versions (currently uses X-User-ID header)
