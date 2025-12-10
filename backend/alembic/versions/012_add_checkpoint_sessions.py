"""Add checkpoint sessions table

Revision ID: 012
Revises: 011
Create Date: 2025-11-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, TIMESTAMP

# revision identifiers, used by Alembic.
revision = '012_add_checkpoint_sessions'
down_revision = '011_stage_summaries'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'checkpoint_sessions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('session_id', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('execution_id', sa.Integer(), sa.ForeignKey('pipeline_executions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), index=True),

        # Session configuration
        sa.Column('mode', sa.String(20), nullable=False, default='automatic'),

        # Current state
        sa.Column('status', sa.String(50), nullable=False, default='active', index=True),
        sa.Column('current_stage', sa.String(50)),
        sa.Column('stages_completed', JSON, default=list),

        # Stage results (for editing and resuming)
        sa.Column('stage_results', JSON, default=dict),

        # User modifications tracking
        sa.Column('user_edits', JSON, default=list),

        # Checkpoint history
        sa.Column('checkpoint_actions', JSON, default=list),

        # Next agent instructions
        sa.Column('pending_instructions', sa.Text()),

        # Timestamps
        sa.Column('created_at', TIMESTAMP, default=sa.func.now()),
        sa.Column('last_action_at', TIMESTAMP, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('completed_at', TIMESTAMP),
        sa.Column('expires_at', TIMESTAMP),
    )

    # Create indexes
    op.create_index('idx_checkpoint_user_status', 'checkpoint_sessions', ['user_id', 'status'])
    op.create_index('idx_checkpoint_expires', 'checkpoint_sessions', ['expires_at'])


def downgrade():
    op.drop_index('idx_checkpoint_expires', 'checkpoint_sessions')
    op.drop_index('idx_checkpoint_user_status', 'checkpoint_sessions')
    op.drop_table('checkpoint_sessions')
