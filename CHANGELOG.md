# Changelog

All notable changes to the Marketer App project will be documented in this file.

## [Unreleased] - 2025-11-19

### Added

#### Backend
- **Projects API** (`backend/app/projects_routes.py`)
  - Full CRUD operations for projects
  - Endpoints: GET/POST `/api/projects`, GET/PUT/DELETE `/api/projects/{id}`
  - Archive/unarchive functionality: POST `/api/projects/{id}/archive`, `/api/projects/{id}/unarchive`
  - Response models with Pydantic validation

- **Pipeline Execution Persistence**
  - Database migration `003_add_pipeline_history.py`: Added `pipeline_executions` and `pipeline_step_results` tables
  - Database migration `004_add_project_to_pipeline.py`: Added `project_id` foreign key to pipeline executions
  - Full execution history tracking with status, metrics, and error handling

- **Automatic Database Migrations**
  - Created `backend/entrypoint.sh` script that runs migrations on container startup
  - Updated Dockerfile to use entrypoint script
  - Uses `pg_isready` to wait for database before running migrations

- **User ID Forwarding in Pipeline**
  - Added `user_id` field to `PipelineState` dataclass
  - Modified `orchestrator.run()` to accept and forward `user_id` parameter
  - RAG retriever calls now include `user_id` for multi-tenant credential handling
  - Fixed potential security issue with wrong credentials in multi-tenant scenarios

#### Frontend
- **ProjectsPage Improvements** (`frontend/src/components/Projects/ProjectsPage.jsx`)
  - Fixed API calls to use `API_BASE` prefix consistently
  - Content history display for each project
  - Status badges for pipeline executions
  - Create/view/resume content actions

### Fixed

- **Permission Denied Error**: Changed Dockerfile entrypoint from direct execution to `sh /app/entrypoint.sh`
- **JSON Parsing Error**: Added `${API_BASE}` prefix to fetch calls in ProjectsPage.jsx
- **404 on Projects Page**: Created missing `/api/projects` endpoint and registered router in main.py
- **User ID Not Forwarded**: Added user_id parameter throughout the pipeline orchestration chain

### Database Changes

#### New Tables
- `pipeline_executions`: Stores complete pipeline execution history
  - Input parameters (topic, content_type, audience, goal, brand_voice, etc.)
  - Execution status and current stage
  - Final results and content
  - Metrics (duration, tokens, cost)
  - Error tracking

- `pipeline_step_results`: Stores individual step results within executions
  - Stage identification and order
  - Step-level metrics and status
  - Error tracking with retry count

#### New Indexes
- `ix_pipeline_executions_pipeline_id`
- `ix_pipeline_executions_user_id`
- `ix_pipeline_executions_status`
- `idx_pipeline_user_created`
- `idx_pipeline_status_created`
- `idx_pipeline_project_created`
- `ix_pipeline_step_results_execution_id`
- `ix_pipeline_step_results_stage`
- `idx_step_execution_stage`

### Documentation Updated

- **README.md**: Updated features section with new capabilities
- **DATABASE_SCHEMA.md**: Added pipeline_executions and pipeline_step_results table documentation

### Architecture Changes

- **Project-Centric Workflow**: All content generation is now associated with projects
- **Pipeline State Persistence**: Execution state is saved to database for history and resume capabilities
- **Auto-Migration on Startup**: Backend automatically runs pending Alembic migrations on container start

### API Endpoints

#### Projects (`/api/projects`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List all projects for organization |
| GET | `/api/projects/{id}` | Get specific project |
| POST | `/api/projects` | Create new project |
| PUT | `/api/projects/{id}` | Update project |
| DELETE | `/api/projects/{id}` | Delete project |
| POST | `/api/projects/{id}/archive` | Archive project |
| POST | `/api/projects/{id}/unarchive` | Unarchive project |

### Infrastructure

- **Dockerfile Changes**
  ```dockerfile
  RUN chmod +x /app/entrypoint.sh
  ENTRYPOINT ["sh", "/app/entrypoint.sh"]
  ```

- **Entrypoint Script** (`backend/entrypoint.sh`)
  - Waits for PostgreSQL to be ready
  - Runs `python -m alembic upgrade head`
  - Starts the application

---

## Previous Versions

See git history for earlier changes.
