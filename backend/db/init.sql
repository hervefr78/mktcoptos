-- ============================================================================
-- MARKETER APP - DATABASE INITIALIZATION SCRIPT
-- PostgreSQL 16 Compatible Schema
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- USERS & AUTHENTICATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    clerk_id VARCHAR(255) UNIQUE,  -- Clerk user ID (SaaS only)
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- Local mode only
    role VARCHAR(50) NOT NULL DEFAULT 'user',  -- user, admin, super_admin
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,

    -- Profile
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    avatar_url TEXT,

    -- Settings
    preferences JSONB DEFAULT '{}',

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_clerk_id ON users(clerk_id);
CREATE INDEX idx_users_role ON users(role);

-- ============================================================================
-- ORGANIZATIONS (Multi-tenancy)
-- ============================================================================

CREATE TABLE IF NOT EXISTS organizations (
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_plan ON organizations(plan);

-- ============================================================================
-- ORGANIZATION MEMBERS (Team collaboration)
-- ============================================================================

CREATE TABLE IF NOT EXISTS organization_members (
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

    UNIQUE (user_id, organization_id)
);

CREATE INDEX idx_org_members_user ON organization_members(user_id);
CREATE INDEX idx_org_members_org ON organization_members(organization_id);

-- ============================================================================
-- PROJECTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS projects (
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

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_projects_org ON projects(organization_id);
CREATE INDEX idx_projects_owner ON projects(owner_id);

-- ============================================================================
-- DOCUMENTS (RAG knowledge base)
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    uploaded_by INTEGER NOT NULL REFERENCES users(id),

    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50),
    file_size_bytes BIGINT,
    storage_path TEXT,

    -- Processing
    processing_status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
    processing_error TEXT,
    processed_at TIMESTAMP,

    -- ChromaDB references
    chromadb_collection_id VARCHAR(255),
    chunk_count INTEGER DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_project ON documents(project_id);
CREATE INDEX idx_documents_status ON documents(processing_status);

-- ============================================================================
-- WORKFLOWS (LangGraph execution)
-- ============================================================================

CREATE TABLE IF NOT EXISTS workflows (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_by INTEGER NOT NULL REFERENCES users(id),

    name VARCHAR(255) NOT NULL,
    workflow_type VARCHAR(100) NOT NULL,  -- blog_post, social_media, email_campaign, etc.

    -- Input
    input_params JSONB NOT NULL,

    -- Execution
    status VARCHAR(50) DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,

    -- Output
    output_data JSONB,
    generated_content TEXT,

    -- LangGraph state
    langgraph_state JSONB,
    current_agent VARCHAR(100),

    -- Metadata
    execution_time_ms INTEGER,
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 4),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_workflows_project ON workflows(project_id);
CREATE INDEX idx_workflows_status ON workflows(status);
CREATE INDEX idx_workflows_created_by ON workflows(created_by);

-- ============================================================================
-- WORKFLOW STEPS (Agent execution trace)
-- ============================================================================

CREATE TABLE IF NOT EXISTS workflow_steps (
    id SERIAL PRIMARY KEY,
    workflow_id INTEGER NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,

    step_number INTEGER NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    agent_type VARCHAR(100),

    -- Input/Output
    input_data JSONB,
    output_data JSONB,

    -- Execution
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,

    -- Metrics
    execution_time_ms INTEGER,
    tokens_used INTEGER,
    llm_model VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_workflow_steps_workflow ON workflow_steps(workflow_id);
CREATE INDEX idx_workflow_steps_status ON workflow_steps(status);

-- ============================================================================
-- USAGE TRACKING (Billing & Analytics)
-- ============================================================================

CREATE TABLE IF NOT EXISTS usage_logs (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    workflow_id INTEGER REFERENCES workflows(id),

    event_type VARCHAR(100) NOT NULL,  -- api_call, llm_request, document_upload, etc.

    -- Resource usage
    tokens_used INTEGER,
    storage_bytes BIGINT,
    execution_time_ms INTEGER,

    -- Cost
    cost_usd DECIMAL(10, 4),

    -- Context
    metadata JSONB,

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_usage_logs_org ON usage_logs(organization_id);
CREATE INDEX idx_usage_logs_user ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_created ON usage_logs(created_at);

-- ============================================================================
-- AUDIT LOGS (Security & Compliance)
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),

    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id INTEGER,

    -- Details
    changes JSONB,
    ip_address INET,
    user_agent TEXT,

    -- Result
    status VARCHAR(50),
    error_message TEXT,

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_org ON audit_logs(organization_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- ============================================================================
-- API KEYS (For external integrations)
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by INTEGER NOT NULL REFERENCES users(id),

    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(20),  -- First 8 chars for display

    -- Permissions
    scopes TEXT[],

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_keys_org ON api_keys(organization_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_organization_members_updated_at BEFORE UPDATE ON organization_members
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflows_updated_at BEFORE UPDATE ON workflows
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SEED DATA (Development/Testing)
-- ============================================================================

-- Insert default admin user (password: admin - hashed with bcrypt)
-- Note: In production, this should be created by the application with proper hashing
INSERT INTO users (email, password_hash, role, first_name, last_name, is_active, email_verified)
VALUES ('admin@marketer.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU2VFKjfR6Pe', 'super_admin', 'Admin', 'User', true, true)
ON CONFLICT (email) DO NOTHING;

-- Insert default organization
INSERT INTO organizations (name, slug, plan, max_users, max_projects, max_storage_gb, requests_per_day)
VALUES ('Default Organization', 'default-org', 'pro', 10, 50, 100, 1000)
ON CONFLICT (slug) DO NOTHING;

-- Link admin to default organization
INSERT INTO organization_members (user_id, organization_id, role, joined_at)
SELECT u.id, o.id, 'owner', CURRENT_TIMESTAMP
FROM users u, organizations o
WHERE u.email = 'admin@marketer.local' AND o.slug = 'default-org'
ON CONFLICT (user_id, organization_id) DO NOTHING;

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully!';
    RAISE NOTICE 'Default admin user: admin@marketer.local / admin';
END $$;
