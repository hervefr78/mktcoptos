"""Add language column to projects table

Revision ID: 014
Revises: 013
Create Date: 2025-11-29

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '014_add_language_to_projects'
down_revision = '013_add_agent_activities'
branch_labels = None
depends_on = None


def upgrade():
    # Add language column to projects table
    op.add_column('projects', sa.Column('language', sa.String(50), server_default='auto', nullable=True))


def downgrade():
    # Remove language column from projects table
    op.drop_column('projects', 'language')
