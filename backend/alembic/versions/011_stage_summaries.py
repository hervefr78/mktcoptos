"""Add stage_summaries to pipeline_executions

Revision ID: 011_stage_summaries
Revises: 010_image_projects
Create Date: 2025-11-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011_stage_summaries'
down_revision = '010_image_projects'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add stage_summaries JSON column to pipeline_executions table
    op.add_column('pipeline_executions', sa.Column('stage_summaries', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove stage_summaries column
    op.drop_column('pipeline_executions', 'stage_summaries')
