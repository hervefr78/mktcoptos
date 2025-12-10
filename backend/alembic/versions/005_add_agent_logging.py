"""Add agent logging columns to pipeline_step_results

Revision ID: 005_add_agent_logging
Revises: 004_add_project
Create Date: 2025-11-19 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_agent_logging'
down_revision = '004_add_project'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add logging columns to pipeline_step_results
    op.add_column(
        'pipeline_step_results',
        sa.Column('prompt_system', sa.Text(), nullable=True, comment='System prompt sent to LLM')
    )
    op.add_column(
        'pipeline_step_results',
        sa.Column('prompt_user', sa.Text(), nullable=True, comment='User prompt sent to LLM')
    )
    op.add_column(
        'pipeline_step_results',
        sa.Column('input_context', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Structured input data')
    )
    op.add_column(
        'pipeline_step_results',
        sa.Column('raw_response', sa.Text(), nullable=True, comment='Raw LLM response')
    )
    op.add_column(
        'pipeline_step_results',
        sa.Column('model_used', sa.String(100), nullable=True, comment='LLM model name')
    )
    op.add_column(
        'pipeline_step_results',
        sa.Column('temperature', sa.Float(), nullable=True, comment='Temperature setting')
    )
    op.add_column(
        'pipeline_step_results',
        sa.Column('input_tokens', sa.Integer(), nullable=True, comment='Input token count')
    )
    op.add_column(
        'pipeline_step_results',
        sa.Column('output_tokens', sa.Integer(), nullable=True, comment='Output token count')
    )


def downgrade() -> None:
    # Remove logging columns
    op.drop_column('pipeline_step_results', 'output_tokens')
    op.drop_column('pipeline_step_results', 'input_tokens')
    op.drop_column('pipeline_step_results', 'temperature')
    op.drop_column('pipeline_step_results', 'model_used')
    op.drop_column('pipeline_step_results', 'raw_response')
    op.drop_column('pipeline_step_results', 'input_context')
    op.drop_column('pipeline_step_results', 'prompt_user')
    op.drop_column('pipeline_step_results', 'prompt_system')
