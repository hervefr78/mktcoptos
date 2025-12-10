"""Add pipeline execution history tables

Revision ID: 003_add_pipeline_history
Revises: 002_add_comfyui
Create Date: 2025-11-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_pipeline_history'
down_revision = '002_add_comfyui'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create pipeline_executions table
    op.create_table(
        'pipeline_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pipeline_id', sa.String(50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),

        # Input parameters
        sa.Column('topic', sa.Text(), nullable=False),
        sa.Column('content_type', sa.String(100), server_default='blog post'),
        sa.Column('audience', sa.String(255), server_default='general'),
        sa.Column('goal', sa.String(100), server_default='awareness'),
        sa.Column('brand_voice', sa.String(255), server_default='professional'),
        sa.Column('language', sa.String(50), server_default='English'),
        sa.Column('length_constraints', sa.String(100), server_default='1000-1500 words'),
        sa.Column('context_summary', sa.Text()),

        # Execution status
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('current_stage', sa.String(50)),

        # Final result
        sa.Column('final_result', postgresql.JSON(astext_type=sa.Text())),
        sa.Column('final_content', sa.Text()),

        # Metadata
        sa.Column('word_count', sa.Integer()),
        sa.Column('seo_score', sa.Integer()),
        sa.Column('originality_score', sa.String(20)),

        # Metrics
        sa.Column('total_duration_seconds', sa.Integer()),
        sa.Column('total_tokens_used', sa.Integer()),
        sa.Column('estimated_cost', sa.DECIMAL(10, 4)),

        # Error tracking
        sa.Column('error_message', sa.Text()),
        sa.Column('error_stage', sa.String(50)),

        # Timestamps
        sa.Column('started_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.TIMESTAMP()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('pipeline_id')
    )

    # Create indexes for pipeline_executions
    op.create_index('ix_pipeline_executions_id', 'pipeline_executions', ['id'])
    op.create_index('ix_pipeline_executions_pipeline_id', 'pipeline_executions', ['pipeline_id'])
    op.create_index('ix_pipeline_executions_user_id', 'pipeline_executions', ['user_id'])
    op.create_index('ix_pipeline_executions_status', 'pipeline_executions', ['status'])
    op.create_index('idx_pipeline_user_created', 'pipeline_executions', ['user_id', 'created_at'])
    op.create_index('idx_pipeline_status_created', 'pipeline_executions', ['status', 'created_at'])

    # Create pipeline_step_results table
    op.create_table(
        'pipeline_step_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('execution_id', sa.Integer(), nullable=False),

        # Step identification
        sa.Column('stage', sa.String(50), nullable=False),
        sa.Column('stage_order', sa.Integer(), nullable=False),

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),

        # Result
        sa.Column('result', postgresql.JSON(astext_type=sa.Text())),

        # Metrics
        sa.Column('duration_seconds', sa.Integer()),
        sa.Column('tokens_used', sa.Integer()),

        # Error tracking
        sa.Column('error_message', sa.Text()),
        sa.Column('retry_count', sa.Integer(), server_default='0'),

        # Timestamps
        sa.Column('started_at', sa.TIMESTAMP()),
        sa.Column('completed_at', sa.TIMESTAMP()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['execution_id'], ['pipeline_executions.id'], ondelete='CASCADE')
    )

    # Create indexes for pipeline_step_results
    op.create_index('ix_pipeline_step_results_id', 'pipeline_step_results', ['id'])
    op.create_index('ix_pipeline_step_results_execution_id', 'pipeline_step_results', ['execution_id'])
    op.create_index('ix_pipeline_step_results_stage', 'pipeline_step_results', ['stage'])
    op.create_index('idx_step_execution_stage', 'pipeline_step_results', ['execution_id', 'stage'])


def downgrade() -> None:
    # Drop indexes for pipeline_step_results
    op.drop_index('idx_step_execution_stage', table_name='pipeline_step_results')
    op.drop_index('ix_pipeline_step_results_stage', table_name='pipeline_step_results')
    op.drop_index('ix_pipeline_step_results_execution_id', table_name='pipeline_step_results')
    op.drop_index('ix_pipeline_step_results_id', table_name='pipeline_step_results')

    # Drop pipeline_step_results table
    op.drop_table('pipeline_step_results')

    # Drop indexes for pipeline_executions
    op.drop_index('idx_pipeline_status_created', table_name='pipeline_executions')
    op.drop_index('idx_pipeline_user_created', table_name='pipeline_executions')
    op.drop_index('ix_pipeline_executions_status', table_name='pipeline_executions')
    op.drop_index('ix_pipeline_executions_user_id', table_name='pipeline_executions')
    op.drop_index('ix_pipeline_executions_pipeline_id', table_name='pipeline_executions')
    op.drop_index('ix_pipeline_executions_id', table_name='pipeline_executions')

    # Drop pipeline_executions table
    op.drop_table('pipeline_executions')
