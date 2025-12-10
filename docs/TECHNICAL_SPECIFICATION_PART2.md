# MARKETER APP - TECHNICAL SPECIFICATION (Part 2)

**Continuation of TECHNICAL_SPECIFICATION.md**

---

## 7. DATABASE SCHEMA

**⚠️ IMPORTANT:** The inline `INDEX` statements in the original schema were **incorrect for PostgreSQL 16**.
PostgreSQL does not support inline `INDEX` clauses within `CREATE TABLE` statements.

**✅ CORRECTED SCHEMA:** See **DATABASE_SCHEMA.md** for the production-ready PostgreSQL 16 compatible schema with:
- All tables without inline INDEX statements
- Separate `CREATE INDEX` statements (60+ indexes)
- Proper constraints (UNIQUE, FOREIGN KEY, etc.)
- Triggers, views, and migrations

### 7.1 Schema Summary

**Key Tables (16 total):**
- `users` - User accounts and authentication
- `organizations` - Multi-tenant organizations
- `organization_members` - Team membership and roles
- `projects` - Content projects with brand voice
- `campaigns` - Marketing campaigns
- `activities` - Individual content pieces
- `documents` - RAG document storage
- `agent_executions` - Agent audit trail
- `workflow_states` - LangGraph checkpoints
- `agent_api_keys` - Hybrid agent authentication
- `usage_events` - Billing and analytics
- `audit_logs` - Compliance audit trail
- `subscriptions` - Stripe subscriptions
- `invoices` - Billing invoices
- `notifications` - User notifications

**Example Table (Correct Syntax):**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    clerk_id VARCHAR(255) UNIQUE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    -- ... other columns ...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes created separately (NOT inline)
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_clerk_id ON users(clerk_id);
CREATE INDEX idx_users_role ON users(role);
```

**For the complete schema with all 16 tables, 60+ indexes, triggers, and views, see DATABASE_SCHEMA.md**

###  7.2 Migrations (Alembic)

```python
# backend/alembic/versions/001_initial_schema.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Execute corrected schema from DATABASE_SCHEMA.md
    # Read and execute the DDL statements
    with open('docs/DATABASE_SCHEMA.md', 'r') as f:
        # Extract SQL sections and execute
        pass

def downgrade():
    # Drop all tables, views, triggers in reverse order
    # See DATABASE_SCHEMA.md for complete teardown
    pass
```

---

## 8. API SPECIFICATIONS

### 8.1 API Overview

**Base URL:**
- Local: `http://localhost:8000`
- SaaS: `https://api.marketer-app.com`

**Authentication:**
- Header: `Authorization: Bearer <token>`
- SaaS: Clerk JWT token
- Local: Simple JWT token
- Agent: `Authorization: Bearer agnt_<api_key>`

**Response Format:**
```json
{
    "success": true,
    "data": {...},
    "error": null,
    "metadata": {
        "timestamp": "2025-01-14T12:00:00Z",
        "request_id": "uuid-here"
    }
}
```

### 8.2 Authentication Endpoints

#### POST /api/login (Local mode only)
```http
POST /api/login
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "password123"
}

Response 200:
{
    "success": true,
    "data": {
        "token": "eyJhbGciOiJIUzI1NiIs...",
        "user": {
            "id": 1,
            "email": "user@example.com",
            "role": "admin"
        }
    }
}
```

#### GET /api/me
```http
GET /api/me
Authorization: Bearer <token>

Response 200:
{
    "success": true,
    "data": {
        "id": 1,
        "email": "user@example.com",
        "role": "admin",
        "organizations": [
            {
                "id": 1,
                "name": "Acme Corp",
                "slug": "acme-corp",
                "role": "owner"
            }
        ]
    }
}
```

### 8.3 Organization Endpoints

#### POST /api/organizations
```http
POST /api/organizations
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "My Company",
    "slug": "my-company",
    "plan": "free"
}

Response 201:
{
    "success": true,
    "data": {
        "id": 1,
        "name": "My Company",
        "slug": "my-company",
        "plan": "free",
        "created_at": "2025-01-14T12:00:00Z"
    }
}
```

#### GET /api/organizations/:id
```http
GET /api/organizations/1
Authorization: Bearer <token>
X-Organization: my-company

Response 200:
{
    "success": true,
    "data": {
        "id": 1,
        "name": "My Company",
        "slug": "my-company",
        "plan": "pro",
        "max_users": 10,
        "max_projects": 50,
        "usage": {
            "users": 5,
            "projects": 12,
            "storage_gb": 2.5,
            "requests_today": 45
        },
        "llm_mode": "cloud",
        "created_at": "2025-01-14T12:00:00Z"
    }
}
```

### 8.4 Project Endpoints

#### POST /api/projects
```http
POST /api/projects
Authorization: Bearer <token>
X-Organization: my-company
Content-Type: application/json

{
    "name": "Q1 Marketing Campaign",
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,  -- company-name

    -- Subscription
    plan VARCHAR(50) NOT NULL DEFAULT 'free',  -- free, pro, enterprise
    plan_started_at TIMESTAMP,
    plan_expires_at TIMESTAMP,

    -- Billing
    stripe_customer_id VARCHAR(255) UNIQUE,
    stripe_subscription_id VARCHAR(255),

    -- Quotas
    max_users INTEGER NOT NULL DEFAULT 1,
    max_projects INTEGER NOT NULL DEFAULT 3,
    max_storage_gb INTEGER NOT NULL DEFAULT 5,
    requests_per_day INTEGER NOT NULL DEFAULT 100,

    -- Usage tracking
    current_storage_gb DECIMAL(10, 2) DEFAULT 0,
    requests_today INTEGER DEFAULT 0,
    requests_this_month INTEGER DEFAULT 0,
    last_reset_date DATE DEFAULT CURRENT_DATE,

    -- LLM Configuration
    llm_mode VARCHAR(50) DEFAULT 'cloud',  -- cloud, local_agent, hybrid
    agent_status VARCHAR(50),  -- not_configured, connected, disconnected
    agent_last_seen TIMESTAMP,

    -- Encrypted API keys (for cloud LLMs)
    openai_api_key VARCHAR(500),
    anthropic_api_key VARCHAR(500),
    mistral_api_key VARCHAR(500),

    -- Compliance
    compliance_mode VARCHAR(50),  -- standard, hipaa, gdpr, soc2
    data_residency VARCHAR(50),  -- us, eu, asia

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_organizations_slug (slug),
    INDEX idx_organizations_stripe_customer (stripe_customer_id),
    INDEX idx_organizations_plan (plan)
);

-- ============================================================================
-- ORGANIZATION MEMBERS (Team collaboration)
-- ============================================================================

CREATE TABLE organization_members (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',  -- owner, admin, member, viewer

    -- Invitation
    invited_by INTEGER REFERENCES users(id),
    invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invitation_token VARCHAR(255) UNIQUE,
    invitation_expires_at TIMESTAMP,
    joined_at TIMESTAMP,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (user_id, organization_id),
    INDEX idx_org_members_user (user_id),
    INDEX idx_org_members_org (organization_id),
    INDEX idx_org_members_invitation (invitation_token)
);

-- ============================================================================
-- PROJECTS
-- ============================================================================

CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    owner_id INTEGER NOT NULL REFERENCES users(id),

    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Brand voice (for RAG)
    brand_voice JSONB,  -- {tone, style, guidelines, examples}

    -- Settings
    default_tone VARCHAR(50) DEFAULT 'professional',
    default_target_audience TEXT,
    default_keywords TEXT[],

    -- Sharing
    visibility VARCHAR(50) DEFAULT 'organization',  -- private, team, organization

    -- Status
    is_archived BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_projects_org (organization_id),
    INDEX idx_projects_owner (owner_id),
    INDEX idx_projects_visibility (visibility)
);

-- ============================================================================
-- CAMPAIGNS
-- ============================================================================

CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    owner_id INTEGER NOT NULL REFERENCES users(id),

    name VARCHAR(255) NOT NULL,
    description TEXT,
    goal TEXT,

    -- Target
    target_audience TEXT,
    start_date DATE,
    end_date DATE,

    -- Budget (optional)
    budget_amount DECIMAL(10, 2),
    budget_currency VARCHAR(3) DEFAULT 'USD',

    -- Status
    status VARCHAR(50) DEFAULT 'active',  -- planning, active, paused, completed
    is_archived BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_campaigns_project (project_id),
    INDEX idx_campaigns_owner (owner_id),
    INDEX idx_campaigns_status (status)
);

-- ============================================================================
-- ACTIVITIES (Content pieces)
-- ============================================================================

CREATE TABLE activities (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    owner_id INTEGER NOT NULL REFERENCES users(id),

    -- Content details
    type VARCHAR(50) NOT NULL,  -- blog, linkedin, twitter, webpage, email
    topic VARCHAR(255) NOT NULL,
    keywords TEXT[],

    -- Configuration
    tone VARCHAR(50) DEFAULT 'professional',
    target_audience TEXT,
    target_word_count INTEGER,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'draft',  -- draft, generating, completed, published, archived

    -- Content (JSONB for flexibility)
    content JSONB,  -- {
                     --   final_content: string,
                     --   seo_data: {...},
                     --   research_sources: [...],
                     --   social_variants: {...},
                     --   metadata: {...}
                     -- }

    -- Publishing
    published_at TIMESTAMP,
    published_url TEXT,

    -- Workflow
    workflow_state JSONB,  -- LangGraph checkpoint
    workflow_started_at TIMESTAMP,
    workflow_completed_at TIMESTAMP,
    workflow_duration_ms INTEGER,

    -- Usage tracking
    tokens_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 4) DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_activities_campaign (campaign_id),
    INDEX idx_activities_owner (owner_id),
    INDEX idx_activities_status (status),
    INDEX idx_activities_type (type),
    INDEX idx_activities_created (created_at DESC)
);

-- ============================================================================
-- DOCUMENTS (RAG)
-- ============================================================================

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,  -- Optional project association
    uploaded_by INTEGER NOT NULL REFERENCES users(id),

    -- File info
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,  -- S3 path or local path
    file_type VARCHAR(50),  -- pdf, docx, txt
    file_size INTEGER,  -- bytes

    -- Processing
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, processing, indexed, error
    error_message TEXT,

    -- ChromaDB reference
    chroma_collection_id VARCHAR(255),
    chunk_count INTEGER DEFAULT 0,

    -- Metadata
    metadata JSONB,  -- {description, tags, author, date, ...}

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,

    INDEX idx_documents_org (organization_id),
    INDEX idx_documents_project (project_id),
    INDEX idx_documents_status (status),
    INDEX idx_documents_uploaded_by (uploaded_by)
);

-- ============================================================================
-- AGENT EXECUTIONS (Audit trail for agent runs)
-- ============================================================================

CREATE TABLE agent_executions (
    id SERIAL PRIMARY KEY,
    activity_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),

    -- Agent info
    agent_name VARCHAR(100) NOT NULL,  -- seo_research, content_writer, etc.
    agent_version VARCHAR(20),

    -- Execution
    status VARCHAR(50) NOT NULL,  -- running, completed, failed
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,

    -- I/O
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,

    -- LLM usage
    llm_provider VARCHAR(50),  -- ollama, openai, anthropic, mistral
    llm_model VARCHAR(100),
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    tokens_total INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 4) DEFAULT 0,

    INDEX idx_agent_executions_activity (activity_id),
    INDEX idx_agent_executions_org (organization_id),
    INDEX idx_agent_executions_agent_name (agent_name),
    INDEX idx_agent_executions_status (status),
    INDEX idx_agent_executions_started (started_at DESC)
);

-- ============================================================================
-- WORKFLOW STATES (LangGraph checkpoints)
-- ============================================================================

CREATE TABLE workflow_states (
    id SERIAL PRIMARY KEY,
    activity_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,

    checkpoint_id VARCHAR(255) UNIQUE NOT NULL,
    state_data JSONB NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_workflow_states_activity (activity_id),
    INDEX idx_workflow_states_checkpoint (checkpoint_id)
);

-- ============================================================================
-- AGENT API KEYS (For hybrid local agents)
-- ============================================================================

CREATE TABLE agent_api_keys (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    name VARCHAR(100),  -- "Production Server", "Dev Mac"
    key_hash VARCHAR(255) UNIQUE NOT NULL,  -- bcrypt hash of API key
    key_prefix VARCHAR(20) NOT NULL,  -- "agnt_abc..." for identification

    -- Permissions (for future fine-grained access)
    permissions JSONB DEFAULT '{"llm_processing": true}',

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,

    INDEX idx_agent_keys_org (organization_id),
    INDEX idx_agent_keys_hash (key_hash),
    INDEX idx_agent_keys_active (is_active)
);

-- ============================================================================
-- USAGE EVENTS (For billing and analytics)
-- ============================================================================

CREATE TABLE usage_events (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),

    event_type VARCHAR(100) NOT NULL,  -- llm_request, document_upload, activity_created
    event_date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- Metadata
    metadata JSONB,  -- {provider, model, tokens, file_size, etc.}

    -- Cost
    cost_usd DECIMAL(10, 4) DEFAULT 0,

    -- Timestamp
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_usage_events_org_date (organization_id, event_date),
    INDEX idx_usage_events_type (event_type),
    INDEX idx_usage_events_timestamp (timestamp DESC)
);

-- ============================================================================
-- AUDIT LOGS (Compliance)
-- ============================================================================

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Who
    user_id INTEGER REFERENCES users(id),
    organization_id INTEGER REFERENCES organizations(id),
    ip_address VARCHAR(45),  -- IPv6 support
    user_agent TEXT,

    -- What
    action VARCHAR(100) NOT NULL,  -- user.login, document.upload, etc.
    resource_type VARCHAR(50),  -- project, activity, document
    resource_id INTEGER,

    -- Details
    details JSONB,
    status VARCHAR(20) NOT NULL,  -- success, failure

    -- Compliance
    retention_days INTEGER DEFAULT 2555,  -- 7 years

    INDEX idx_audit_logs_user (user_id),
    INDEX idx_audit_logs_org (organization_id),
    INDEX idx_audit_logs_timestamp (timestamp DESC),
    INDEX idx_audit_logs_action (action),
    INDEX idx_audit_logs_resource (resource_type, resource_id)
);

-- ============================================================================
-- SUBSCRIPTIONS (Billing history)
-- ============================================================================

CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Stripe
    stripe_subscription_id VARCHAR(255) UNIQUE NOT NULL,
    stripe_customer_id VARCHAR(255) NOT NULL,
    stripe_price_id VARCHAR(255) NOT NULL,

    -- Plan
    plan VARCHAR(50) NOT NULL,  -- pro, enterprise
    status VARCHAR(50) NOT NULL,  -- active, past_due, canceled, trialing

    -- Billing
    currency VARCHAR(3) DEFAULT 'USD',
    amount INTEGER NOT NULL,  -- cents
    interval VARCHAR(20) NOT NULL,  -- month, year

    -- Dates
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    trial_start TIMESTAMP,
    trial_end TIMESTAMP,
    canceled_at TIMESTAMP,
    ended_at TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_subscriptions_org (organization_id),
    INDEX idx_subscriptions_stripe_sub (stripe_subscription_id),
    INDEX idx_subscriptions_status (status)
);

-- ============================================================================
-- INVOICES
-- ============================================================================

CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    subscription_id INTEGER REFERENCES subscriptions(id),

    -- Stripe
    stripe_invoice_id VARCHAR(255) UNIQUE NOT NULL,
    stripe_hosted_url TEXT,
    stripe_pdf_url TEXT,

    -- Billing
    currency VARCHAR(3) DEFAULT 'USD',
    amount_due INTEGER NOT NULL,  -- cents
    amount_paid INTEGER DEFAULT 0,  -- cents
    status VARCHAR(50) NOT NULL,  -- draft, open, paid, void

    -- Dates
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    due_date TIMESTAMP,
    paid_at TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_invoices_org (organization_id),
    INDEX idx_invoices_stripe (stripe_invoice_id),
    INDEX idx_invoices_status (status)
);

-- ============================================================================
-- NOTIFICATIONS
-- ============================================================================

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,

    type VARCHAR(100) NOT NULL,  -- workflow_complete, team_invite, quota_exceeded
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,

    -- Link (optional)
    link_url TEXT,
    link_text VARCHAR(100),

    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,

    -- Metadata
    metadata JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_notifications_user (user_id),
    INDEX idx_notifications_org (organization_id),
    INDEX idx_notifications_read (is_read),
    INDEX idx_notifications_created (created_at DESC)
);

-- ============================================================================
-- TRIGGERS (Auto-update timestamps)
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_organization_members_updated_at BEFORE UPDATE ON organization_members
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_campaigns_updated_at BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_activities_updated_at BEFORE UPDATE ON activities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS (Useful aggregations)
-- ============================================================================

-- Organization usage summary
CREATE VIEW organization_usage_summary AS
SELECT
    o.id AS organization_id,
    o.name AS organization_name,
    o.plan,
    COUNT(DISTINCT om.user_id) AS user_count,
    COUNT(DISTINCT p.id) AS project_count,
    COUNT(DISTINCT a.id) AS activity_count,
    COUNT(DISTINCT d.id) AS document_count,
    o.current_storage_gb,
    o.requests_today,
    o.requests_this_month,
    SUM(COALESCE(ue.cost_usd, 0)) AS total_cost_this_month
FROM organizations o
LEFT JOIN organization_members om ON o.id = om.organization_id AND om.is_active = TRUE
LEFT JOIN projects p ON o.id = p.organization_id AND p.is_archived = FALSE
LEFT JOIN campaigns c ON p.id = c.project_id
LEFT JOIN activities a ON c.id = a.campaign_id
LEFT JOIN documents d ON o.id = d.organization_id
LEFT JOIN usage_events ue ON o.id = ue.organization_id
    AND ue.event_date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY o.id, o.name, o.plan, o.current_storage_gb, o.requests_today, o.requests_this_month;

-- Recent activity feed
CREATE VIEW recent_activities_feed AS
SELECT
    a.id,
    a.topic,
    a.type,
    a.status,
    a.created_at,
    a.updated_at,
    c.name AS campaign_name,
    p.name AS project_name,
    o.name AS organization_name,
    u.email AS owner_email,
    (a.content->>'word_count')::INTEGER AS word_count
FROM activities a
JOIN campaigns c ON a.campaign_id = c.id
JOIN projects p ON c.project_id = p.id
JOIN organizations o ON p.organization_id = o.id
JOIN users u ON a.owner_id = u.id
ORDER BY a.created_at DESC
LIMIT 100;
```

### 7.2 Migrations (Alembic)

```python
# backend/alembic/versions/001_initial_schema.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Execute schema SQL above
    # ... (implementations match schema)
    pass

def downgrade():
    # Drop all tables in reverse order
    op.drop_table('notifications')
    op.drop_table('invoices')
    op.drop_table('subscriptions')
    # ... etc
    pass
```

---

## 8. API SPECIFICATIONS

### 8.1 API Overview

**Base URL:**
- Local: `http://localhost:8000`
- SaaS: `https://api.marketer-app.com`

**Authentication:**
- Header: `Authorization: Bearer <token>`
- SaaS: Clerk JWT token
- Local: Simple JWT token
- Agent: `Authorization: Bearer agnt_<api_key>`

**Response Format:**
```json
{
    "success": true,
    "data": {...},
    "error": null,
    "metadata": {
        "timestamp": "2025-01-14T12:00:00Z",
        "request_id": "uuid-here"
    }
}
```

### 8.2 Authentication Endpoints

#### POST /api/login (Local mode only)
```http
POST /api/login
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "password123"
}

Response 200:
{
    "success": true,
    "data": {
        "token": "eyJhbGciOiJIUzI1NiIs...",
        "user": {
            "id": 1,
            "email": "user@example.com",
            "role": "admin"
        }
    }
}
```

#### GET /api/me
```http
GET /api/me
Authorization: Bearer <token>

Response 200:
{
    "success": true,
    "data": {
        "id": 1,
        "email": "user@example.com",
        "role": "admin",
        "organizations": [
            {
                "id": 1,
                "name": "Acme Corp",
                "slug": "acme-corp",
                "role": "owner"
            }
        ]
    }
}
```

### 8.3 Organization Endpoints

#### POST /api/organizations
```http
POST /api/organizations
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "My Company",
    "slug": "my-company",
    "plan": "free"
}

Response 201:
{
    "success": true,
    "data": {
        "id": 1,
        "name": "My Company",
        "slug": "my-company",
        "plan": "free",
        "created_at": "2025-01-14T12:00:00Z"
    }
}
```

#### GET /api/organizations/:id
```http
GET /api/organizations/1
Authorization: Bearer <token>
X-Organization: my-company

Response 200:
{
    "success": true,
    "data": {
        "id": 1,
        "name": "My Company",
        "slug": "my-company",
        "plan": "pro",
        "max_users": 10,
        "max_projects": 50,
        "usage": {
            "users": 5,
            "projects": 12,
            "storage_gb": 2.5,
            "requests_today": 45
        },
        "llm_mode": "cloud",
        "created_at": "2025-01-14T12:00:00Z"
    }
}
```

### 8.4 Project Endpoints

#### POST /api/projects
```http
POST /api/projects
Authorization: Bearer <token>
X-Organization: my-company
Content-Type: application/json

{
    "name": "Q1 Marketing Campaign",
    "description": "Focus on product launch",
    "brand_voice": {
        "tone": "professional yet friendly",
        "style": "conversational",
        "guidelines": "Avoid jargon, use active voice"
    },
    "default_tone": "professional",
    "default_target_audience": "B2B marketing managers"
}

Response 201:
{
    "success": true,
    "data": {
        "id": 1,
        "name": "Q1 Marketing Campaign",
        "description": "Focus on product launch",
        "created_at": "2025-01-14T12:00:00Z"
    }
}
```

#### GET /api/projects
```http
GET /api/projects?page=1&per_page=20&is_archived=false
Authorization: Bearer <token>
X-Organization: my-company

Response 200:
{
    "success": true,
    "data": {
        "projects": [
            {
                "id": 1,
                "name": "Q1 Marketing Campaign",
                "description": "Focus on product launch",
                "owner": {
                    "id": 1,
                    "email": "user@example.com"
                },
                "campaigns_count": 3,
                "activities_count": 15,
                "created_at": "2025-01-14T12:00:00Z"
            }
        ],
        "pagination": {
            "total": 12,
            "page": 1,
            "per_page": 20,
            "pages": 1
        }
    }
}
```

### 8.5 Workflow Endpoints

#### POST /api/workflows/execute
```http
POST /api/workflows/execute
Authorization: Bearer <token>
X-Organization: my-company
Content-Type: application/json

{
    "activity_id": 123,
    "project_id": 1,
    "topic": "AI in Marketing Automation",
    "keywords": ["AI", "marketing automation", "personalization"],
    "content_type": "blog",
    "tone": "professional",
    "target_audience": "Marketing managers at B2B companies",
    "target_word_count": 1500
}

Response 202 Accepted:
{
    "success": true,
    "data": {
        "task_id": "uuid-task-id",
        "activity_id": 123,
        "status": "queued",
        "stream_url": "/api/activities/123/stream"
    }
}
```

#### GET /api/activities/:id/stream (SSE)
```http
GET /api/activities/123/stream
Authorization: Bearer <token>
X-Organization: my-company
Accept: text/event-stream

Response 200 (Server-Sent Events):
data: {"step":"seo_research","progress":20,"data":{...}}

data: {"step":"research","progress":40,"data":{...}}

data: {"step":"writing","progress":60,"data":{...}}

data: {"step":"editing","progress":80,"data":{...}}

data: {"step":"social_media","progress":95,"data":{...}}

data: {"step":"complete","progress":100,"data":{...}}
```

### 8.6 Document Endpoints

#### POST /api/documents
```http
POST /api/documents
Authorization: Bearer <token>
X-Organization: my-company
Content-Type: multipart/form-data

--boundary
Content-Disposition: form-data; name="file"; filename="brand-guidelines.pdf"
Content-Type: application/pdf

[Binary PDF data]
--boundary
Content-Disposition: form-data; name="project_id"

1
--boundary--

Response 201:
{
    "success": true,
    "data": {
        "id": 1,
        "filename": "brand-guidelines.pdf",
        "file_size": 1048576,
        "status": "pending",
        "created_at": "2025-01-14T12:00:00Z"
    }
}
```

#### GET /api/documents
```http
GET /api/documents?project_id=1&status=processed
Authorization: Bearer <token>
X-Organization: my-company

Response 200:
{
    "success": true,
    "data": {
        "documents": [
            {
                "id": 1,
                "filename": "brand-guidelines.pdf",
                "file_size": 1048576,
                "file_type": "pdf",
                "status": "processed",
                "chunk_count": 45,
                "created_at": "2025-01-14T12:00:00Z",
                "processed_at": "2025-01-14T12:02:00Z"
            }
        ]
    }
}
```

### 8.7 Agent WebSocket (Hybrid mode)

#### WS /agent/connect
```javascript
// Agent connects to SaaS
const ws = new WebSocket('wss://api.marketer-app.com/agent/connect', {
    headers: {
        'Authorization': 'Bearer agnt_secret_key_here'
    }
});

// Agent receives LLM request
ws.onmessage = (event) => {
    const request = JSON.parse(event.data);

    if (request.type === 'llm_request') {
        // Process locally with Ollama
        const response = await processWithOllama(request);

        // Send response back
        ws.send(JSON.stringify({
            request_id: request.id,
            content: response.content,
            done: true
        }));
    } else if (request.type === 'ping') {
        // Heartbeat
        ws.send(JSON.stringify({ type: 'pong' }));
    }
};
```

### 8.8 Error Responses

```json
// 400 Bad Request
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid request parameters",
        "details": {
            "topic": ["This field is required"],
            "keywords": ["Must be an array of strings"]
        }
    }
}

// 401 Unauthorized
{
    "success": false,
    "error": {
        "code": "UNAUTHORIZED",
        "message": "Invalid or expired authentication token"
    }
}

// 403 Forbidden
{
    "success": false,
    "error": {
        "code": "PERMISSION_DENIED",
        "message": "You do not have permission to perform this action",
        "required_permission": "project:create"
    }
}

// 429 Too Many Requests
{
    "success": false,
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Daily quota exceeded. Upgrade to Pro for higher limits.",
        "retry_after": 86400
    }
}

// 500 Internal Server Error
{
    "success": false,
    "error": {
        "code": "INTERNAL_ERROR",
        "message": "An unexpected error occurred",
        "request_id": "uuid-for-support"
    }
}
```

---

## 9. UI/UX SPECIFICATIONS

### 9.1 Design System

**Typography:**
- Font Family: Inter (headings), System UI (body)
- Sizes:
  - h1: 32px / 2rem
  - h2: 24px / 1.5rem
  - h3: 20px / 1.25rem
  - body: 16px / 1rem
  - small: 14px / 0.875rem

**Colors:**
```css
:root {
    /* Primary */
    --primary-50: #f0f9ff;
    --primary-500: #3b82f6;
    --primary-600: #2563eb;
    --primary-700: #1d4ed8;

    /* Neutral */
    --gray-50: #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-300: #d1d5db;
    --gray-500: #6b7280;
    --gray-700: #374151;
    --gray-900: #111827;

    /* Success */
    --success-500: #10b981;

    /* Warning */
    --warning-500: #f59e0b;

    /* Error */
    --error-500: #ef4444;
}
```

**Spacing:**
- Base: 4px
- Scale: 4, 8, 12, 16, 24, 32, 48, 64, 96px

**Border Radius:**
- sm: 4px
- md: 8px
- lg: 12px
- xl: 16px

### 9.2 Page Layouts

#### Dashboard
```
┌────────────────────────────────────────────────────────┐
│ Topbar: Logo | Projects ▼ | Notifications | Avatar    │
├────────┬───────────────────────────────────────────────┤
│        │                                               │
│ Side   │  Dashboard                           [+ New]  │
│ bar    │                                               │
│        │  ┌─────────────────────────────────────────┐ │
│ - Dash │  │ Quick Actions                           │ │
│ - Proj │  │  [Blog Post] [LinkedIn] [Twitter] [SEO] │ │
│ - Docs │  └─────────────────────────────────────────┘ │
│ - Team │                                               │
│ - Sett │  ┌──────────────────┐ ┌──────────────────┐  │
│        │  │ Recent Activities│ │ Usage This Month │  │
│        │  │                  │ │                  │  │
│        │  │ - AI in Market.. │ │ Requests: 145    │  │
│        │  │ - Social Media.. │ │ Credits: 2,300   │  │
│        │  │ - Blog: Future.. │ │ Storage: 2.3 GB  │  │
│        │  └──────────────────┘ └──────────────────┘  │
│        │                                               │
│        │  ┌─────────────────────────────────────────┐ │
│        │  │ Projects Overview                       │ │
│        │  │                                         │ │
│        │  │ Q1 Campaign         12 activities  ▶   │ │
│        │  │ Q2 Planning          3 activities  ▶   │ │
│        │  └─────────────────────────────────────────┘ │
└────────┴───────────────────────────────────────────────┘
```

#### Activity Wizard (Modal)
```
┌─────────────────────────────────────────────────────────┐
│ Create New Activity                              [X]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Step 1 of 3: Choose Project & Campaign                │
│  ════════════════════════════════════                  │
│                                                         │
│  Project:                                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Q1 Marketing Campaign                     ▼     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Campaign:                                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Product Launch                            ▼     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [+ New Campaign]                                       │
│                                                         │
│                                       [Cancel] [Next]   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Create New Activity                              [X]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Step 2 of 3: Define Content                            │
│              ════════════════════════                   │
│                                                         │
│  Content Type:                                          │
│  [Blog Post] [LinkedIn] [Twitter] [Web Page] [Email]   │
│                                                         │
│  Topic: *                                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │ AI in Marketing Automation                      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Keywords: *                                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │ [AI] [marketing automation] [+]                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Target Audience:                                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Marketing managers at B2B companies             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│                                       [Back]   [Next]   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Create New Activity                              [X]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Step 3 of 3: Customize Options                         │
│                      ════════════════                   │
│                                                         │
│  Tone:                                                  │
│  ( ) Professional  (•) Conversational  ( ) Technical    │
│                                                         │
│  Target Length:                                         │
│  ┌───────────┐                                          │
│  │ 1500      │ words                                    │
│  └───────────┘                                          │
│                                                         │
│  Reference Documents: (Optional)                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ [✓] brand-guidelines.pdf                        │   │
│  │ [ ] tone-reference.docx                         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  SEO Priority:                                          │
│  ( ) Low  (•) Medium  ( ) High                          │
│                                                         │
│                                [Back]   [Generate]      │
└─────────────────────────────────────────────────────────┘
```

#### Workflow Progress
```
┌─────────────────────────────────────────────────────────┐
│ Generating: AI in Marketing Automation                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Progress: ████████████████████░░░░░░░░  80%           │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ✓ SEO Research        (completed in 15s)        │   │
│  │ ✓ Content Research    (completed in 22s)        │   │
│  │ ✓ Writing Draft       (completed in 45s)        │   │
│  │ ▶ Editing & Refining  (in progress...)          │   │
│  │ ⋯ Social Media        (pending)                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Current Step: Reviewing content quality                │
│  Estimated time remaining: 30 seconds                   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Draft Preview                                   │   │
│  │ ─────────────                                   │   │
│  │                                                 │   │
│  │ # AI in Marketing Automation: Transform Your... │   │
│  │                                                 │   │
│  │ Artificial intelligence is revolutionizing...   │   │
│  │                                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│                                            [Cancel]      │
└─────────────────────────────────────────────────────────┘
```

#### Content Editor (Final)
```
┌─────────────────────────────────────────────────────────┐
│ AI in Marketing Automation                [< Back]      │
├─────────┬───────────────────────────────────────────────┤
│         │                                               │
│ Tabs:   │  [Rich Text Editor]                           │
│         │                                               │
│ - Conte │  # AI in Marketing Automation                 │
│ - SEO   │                                               │
│ - Socia │  [Bold] [Italic] [Link] [H1▼] [...]          │
│ - Analy │  ┌────────────────────────────────────────┐  │
│         │  │                                        │  │
│         │  │ Artificial intelligence is transform.. │  │
│         │  │                                        │  │
│         │  │ ## Key Benefits                        │  │
│         │  │                                        │  │
│         │  │ 1. **Personalization at Scale**        │  │
│         │  │    - Dynamic content                   │  │
│         │  │    - Behavioral targeting              │  │
│         │  │                                        │  │
│         │  └────────────────────────────────────────┘  │
│         │                                               │
│         │  Word Count: 1,543  |  Reading Time: 6 min   │
│         │                                               │
│         │  [Regenerate] [Download ▼] [Publish]         │
└─────────┴───────────────────────────────────────────────┘
```

### 9.3 Component Specifications

#### Button Component
```tsx
// frontend/src/components/ui/Button.tsx
interface ButtonProps {
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
    size?: 'sm' | 'md' | 'lg';
    fullWidth?: boolean;
    loading?: boolean;
    disabled?: boolean;
    icon?: React.ReactNode;
    onClick?: () => void;
    children: React.ReactNode;
}

// Usage
<Button variant="primary" size="md" loading={isLoading}>
    Generate Content
</Button>
```

#### Progress Indicator
```tsx
// frontend/src/components/workflow/ProgressIndicator.tsx
interface Step {
    name: string;
    status: 'pending' | 'in_progress' | 'completed' | 'error';
    duration?: number;
}

interface ProgressIndicatorProps {
    steps: Step[];
    currentStep: number;
}

// Displays vertical stepper with status icons
```

#### Rich Text Editor
```tsx
// frontend/src/components/editor/RichTextEditor.tsx
import { useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';

interface RichTextEditorProps {
    initialContent: string;
    onChange: (content: string) => void;
    readOnly?: boolean;
}

// Full-featured editor with:
// - Bold, italic, underline
// - Headings (H1-H6)
// - Lists (ordered, unordered)
// - Links
// - Code blocks
// - Tables
```

### 9.4 Responsive Design

**Breakpoints:**
```css
/* Mobile: 320px - 767px */
@media (max-width: 767px) {
    /* Stack sidebar, single column */
}

/* Tablet: 768px - 1023px */
@media (min-width: 768px) and (max-width: 1023px) {
    /* Collapsible sidebar, 2 columns */
}

/* Desktop: 1024px+ */
@media (min-width: 1024px) {
    /* Full layout, 3 columns */
}
```

---

## 10. MONITORING & OBSERVABILITY

### 10.1 Metrics (Prometheus)

```python
# backend/app/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info

# Application info
app_info = Info('marketer_app', 'Application information')
app_info.info({'version': '1.0.0', 'deployment': 'production'})

# HTTP requests
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Workflow metrics
workflow_executions_total = Counter(
    'workflow_executions_total',
    'Total workflow executions',
    ['content_type', 'status']
)

workflow_duration_seconds = Histogram(
    'workflow_duration_seconds',
    'Workflow execution duration',
    ['content_type']
)

# Agent metrics
agent_executions_total = Counter(
    'agent_executions_total',
    'Total agent executions',
    ['agent_name', 'status']
)

agent_duration_seconds = Histogram(
    'agent_duration_seconds',
    'Agent execution duration',
    ['agent_name']
)

# LLM metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['provider', 'model', 'status']
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total LLM tokens consumed',
    ['provider', 'model', 'type']  # type: input/output
)

llm_cost_usd_total = Counter(
    'llm_cost_usd_total',
    'Total LLM cost in USD',
    ['provider', 'model']
)

# Database metrics
db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['operation']
)

# ChromaDB metrics
chromadb_documents_total = Gauge(
    'chromadb_documents_total',
    'Total documents in ChromaDB',
    ['organization_id']
)

chromadb_query_duration_seconds = Histogram(
    'chromadb_query_duration_seconds',
    'ChromaDB query duration'
)

# Cache metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_key']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_key']
)

# Organization metrics
organizations_total = Gauge(
    'organizations_total',
    'Total organizations',
    ['plan']
)

active_users_total = Gauge(
    'active_users_total',
    'Total active users',
    ['organization_id']
)

# Queue metrics
celery_tasks_pending = Gauge(
    'celery_tasks_pending',
    'Pending Celery tasks',
    ['queue']
)

celery_tasks_processing = Gauge(
    'celery_tasks_processing',
    'Processing Celery tasks',
    ['queue']
)
```

### 10.2 Logging

```python
# backend/app/logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""

    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id

        if hasattr(record, 'org_id'):
            log_data['org_id'] = record.org_id

        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        return json.dumps(log_data)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/logs/app.log')
    ]
)

# Apply JSON formatter
for handler in logging.root.handlers:
    handler.setFormatter(JSONFormatter())
```

### 10.3 Health Checks

```python
# backend/app/health.py
from fastapi import APIRouter, status

router = APIRouter()

@router.get("/health")
async def health_check():
    """Lightweight health check."""
    return {"status": "healthy"}

@router.get("/ready")
async def readiness_check():
    """Check if application is ready to serve traffic."""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "chromadb": await check_chromadb(),
    }

    all_healthy = all(checks.values())

    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks
    }, status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

async def check_database() -> bool:
    try:
        await db.execute("SELECT 1")
        return True
    except:
        return False

async def check_redis() -> bool:
    try:
        await redis_client.ping()
        return True
    except:
        return False

async def check_chromadb() -> bool:
    try:
        response = await httpx.get(f"{settings.CHROMADB_HOST}/api/v1/heartbeat")
        return response.status_code == 200
    except:
        return False
```

---

## 11. PERFORMANCE REQUIREMENTS

### 11.1 Response Time Targets

| Endpoint | Target (p95) | Max Acceptable |
|----------|--------------|----------------|
| GET /api/projects | 200ms | 500ms |
| POST /api/workflows/execute | 500ms | 1s |
| Workflow completion (full) | 60s | 120s |
| Document upload | 2s | 5s |
| ChromaDB search | 100ms | 300ms |
| SSE update frequency | 1s | 2s |

### 11.2 Throughput

- **API requests:** 1,000 req/sec (per backend instance)
- **Concurrent workflows:** 50 (per worker instance)
- **WebSocket connections:** 10,000 (per agent WS server)
- **Database connections:** 100 (per backend instance)

### 11.3 Resource Limits

**Per Organization:**
- Max projects: Varies by plan (3 free, 50 pro, unlimited enterprise)
- Max storage: Varies by plan (5 GB free, 50 GB pro, unlimited enterprise)
- Max requests/day: Varies by plan (100 free, 1000 pro, unlimited enterprise)

**System:**
- Max file upload size: 100 MB
- Max content length: 100,000 characters
- Max concurrent agents per workflow: 5
- Max workflow duration: 10 minutes (timeout)

### 11.4 Scalability

**Horizontal Scaling:**
- Backend API: Scale to 10+ instances
- Celery workers: Scale to 20+ instances
- Agent WS servers: Scale to 5+ instances

**Vertical Scaling:**
- Database: Scale to 32 vCPU, 128 GB RAM
- Redis: Scale to 16 GB RAM
- ChromaDB: Scale to 32 GB RAM

---

## 12. SUMMARY

This technical specification provides a comprehensive blueprint for building the Marketer App with:

✅ **Multi-agent architecture** using LangGraph for orchestration
✅ **Hybrid deployment** supporting local, cloud SaaS, and hybrid modes
✅ **Enterprise-grade security** with encryption, RBAC, and compliance
✅ **Scalable infrastructure** using Kubernetes and managed services
✅ **Complete API** with RESTful endpoints and WebSocket support
✅ **Modern UI** with React, TypeScript, and shadcn/ui components
✅ **Comprehensive monitoring** with Prometheus metrics and structured logging

**Next Steps:**
1. Review and approve this specification
2. Set up development environment
3. Begin Phase 1: Core infrastructure (database, auth, basic API)
4. Begin Phase 2: Agent system implementation
5. Begin Phase 3: Frontend development
6. Begin Phase 4: Testing and deployment

---

**Document Version:** 1.0
**Last Updated:** 2025-01-14
**Status:** Ready for Implementation
