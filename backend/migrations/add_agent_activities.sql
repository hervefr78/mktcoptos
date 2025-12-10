-- Migration: Add agent_activities table for comprehensive agent tracking
-- Date: 2025-11-28
-- Purpose: Track every action each agent takes during pipeline execution

-- Create agent_activities table
CREATE TABLE IF NOT EXISTS agent_activities (
    id SERIAL PRIMARY KEY,
    pipeline_execution_id INTEGER NOT NULL REFERENCES pipeline_executions(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    stage VARCHAR(50) NOT NULL,

    -- Execution tracking
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    status VARCHAR(20) DEFAULT 'running',  -- running, completed, failed

    -- Input/Output
    input_summary JSONB,
    output_summary JSONB,

    -- Decisions & Actions (array - append as they happen)
    decisions JSONB DEFAULT '[]'::jsonb,

    -- RAG tracking
    rag_documents JSONB DEFAULT '[]'::jsonb,

    -- Before/After (for optimization agents)
    content_before TEXT,
    content_after TEXT,
    changes_made JSONB DEFAULT '[]'::jsonb,

    -- Performance metrics
    performance_breakdown JSONB,

    -- LLM usage
    model_used VARCHAR(100),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    estimated_cost DECIMAL(10, 6) DEFAULT 0,

    -- Quality metrics
    quality_metrics JSONB,
    badges JSONB DEFAULT '[]'::jsonb,

    -- Diagnostics
    warnings JSONB DEFAULT '[]'::jsonb,
    errors JSONB DEFAULT '[]'::jsonb,

    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_activities_pipeline ON agent_activities(pipeline_execution_id);
CREATE INDEX IF NOT EXISTS idx_agent_activities_stage ON agent_activities(stage);
CREATE INDEX IF NOT EXISTS idx_agent_activities_status ON agent_activities(status);
CREATE INDEX IF NOT EXISTS idx_agent_activities_created ON agent_activities(created_at DESC);

-- Enhance pipeline_executions table
ALTER TABLE pipeline_executions ADD COLUMN IF NOT EXISTS agent_summary JSONB;
ALTER TABLE pipeline_executions ADD COLUMN IF NOT EXISTS rag_summary JSONB;
ALTER TABLE pipeline_executions ADD COLUMN IF NOT EXISTS quality_score FLOAT;
ALTER TABLE pipeline_executions ADD COLUMN IF NOT EXISTS total_changes_made INTEGER DEFAULT 0;

-- Create indexes on new columns
CREATE INDEX IF NOT EXISTS idx_pipeline_executions_quality_score ON pipeline_executions(quality_score) WHERE quality_score IS NOT NULL;

-- Add comment for documentation
COMMENT ON TABLE agent_activities IS 'Tracks detailed activity for each AI agent during content pipeline execution. Each row represents one agent execution with real-time updates.';
COMMENT ON COLUMN agent_activities.decisions IS 'Array of decision objects: [{timestamp, description, data}]. Updated in real-time as agent makes decisions.';
COMMENT ON COLUMN agent_activities.rag_documents IS 'Array of RAG document usage: [{doc_id, doc_name, chunks_used, influence_score, purpose}]. Logged as documents are accessed.';
COMMENT ON COLUMN agent_activities.changes_made IS 'Array of content changes: [{type, before, after, reason, location}]. Logged by optimization agents (SEO, Final Review).';
