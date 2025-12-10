"""Add project_id to pipeline_executions

Revision ID: 004_add_project
Revises: 003_add_pipeline_history
Create Date: 2025-11-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_add_project'
down_revision = '003_add_pipeline_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add project_id column to pipeline_executions
    op.add_column(
        'pipeline_executions',
        sa.Column('project_id', sa.Integer(), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_pipeline_project',
        'pipeline_executions',
        'projects',
        ['project_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Add index for project_id + created_at
    op.create_index(
        'idx_pipeline_project_created',
        'pipeline_executions',
        ['project_id', 'created_at']
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('idx_pipeline_project_created', table_name='pipeline_executions')

    # Drop foreign key
    op.drop_constraint('fk_pipeline_project', 'pipeline_executions', type_='foreignkey')

    # Drop column
    op.drop_column('pipeline_executions', 'project_id')
