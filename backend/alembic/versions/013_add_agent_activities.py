"""Add agent activities tracking table

Revision ID: 013
Revises: 012
Create Date: 2025-11-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

# revision identifiers, used by Alembic.
revision = '013_add_agent_activities'
down_revision = '012_add_checkpoint_sessions'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'agent_activities',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('pipeline_execution_id', sa.Integer(), sa.ForeignKey('pipeline_executions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('agent_name', sa.String(100), nullable=False),
        sa.Column('stage', sa.String(50), nullable=False),

        # Timing
        sa.Column('started_at', TIMESTAMP, nullable=False),
        sa.Column('completed_at', TIMESTAMP),
        sa.Column('duration_seconds', sa.Float()),

        # Status
        sa.Column('status', sa.String(20), default='running'),

        # Activity tracking
        sa.Column('decisions', JSONB, default=sa.text("'[]'::jsonb")),
        sa.Column('rag_documents', JSONB, default=sa.text("'[]'::jsonb")),
        sa.Column('changes_made', JSONB, default=sa.text("'[]'::jsonb")),

        # Input/Output
        sa.Column('input_summary', JSONB),
        sa.Column('output_summary', JSONB),

        # Content tracking (for optimization agents)
        sa.Column('content_before', sa.Text()),
        sa.Column('content_after', sa.Text()),

        # Metrics
        sa.Column('tokens_used', sa.Integer(), default=0),
        sa.Column('estimated_cost', sa.Float(), default=0.0),
        sa.Column('quality_metrics', JSONB),

        # Performance
        sa.Column('llm_calls', sa.Integer(), default=0),
        sa.Column('cache_hits', sa.Integer(), default=0),

        # Error handling
        sa.Column('error_message', sa.Text()),
        sa.Column('warnings', JSONB, default=sa.text("'[]'::jsonb")),

        # Quality badges
        sa.Column('badges', JSONB, default=sa.text("'[]'::jsonb")),
    )

    # Create indexes for common queries
    op.create_index('idx_agent_activities_execution', 'agent_activities', ['pipeline_execution_id'])
    op.create_index('idx_agent_activities_status', 'agent_activities', ['status'])
    op.create_index('idx_agent_activities_agent', 'agent_activities', ['agent_name'])


def downgrade():
    op.drop_index('idx_agent_activities_agent', 'agent_activities')
    op.drop_index('idx_agent_activities_status', 'agent_activities')
    op.drop_index('idx_agent_activities_execution', 'agent_activities')
    op.drop_table('agent_activities')
